import contextvars
import logging
from datetime import datetime, timezone
import json
from sqlalchemy.orm import Session, attributes
from sqlalchemy.orm.attributes import get_history
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from jose import jwt
import os

ALGORITHM = "HS256"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# Compliance logger: surfaces critical data integrity violations to the application log
compliance_log = logging.getLogger("csa.compliance")
logging.basicConfig(level=logging.WARNING)

# Context variable to hold the user id or username making the current request
current_user_id_ctx = contextvars.ContextVar("current_user_id", default=None)

class AuditLogMiddleware(BaseHTTPMiddleware):
    """
    Middleware that decodes the JWT token (if present) to extract the user ID
    and stores it in a context variable for the SQLAlchemy event listener.
    """
    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("Authorization")
        user_id = None
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
                user_id = payload.get("id")
            except Exception:
                pass
        
        token_ctx = current_user_id_ctx.set(user_id)
        response = await call_next(request)
        current_user_id_ctx.reset(token_ctx)
        
        return response

def _assert_user_attributable(session: Session, action: str, table_name: str, record_id, user_id) -> None:
    """
    21 CFR Part 11 §11.10(e) Compliance Enforcement.

    Business actions (CREATE, UPDATE, DELETE) MUST be attributable to a specific user.
    If no user_id is present on a business action, this function:
      1. Logs a CRITICAL compliance alert to the application logger.
      2. Writes a COMPLIANCE_ALERT record into the audit trail itself as its own
         self-referencing evidence of the violation.

    System events (LOGIN, LOGIN_FAILED, etc.) are intentionally exempt and
    should use `log_system_event()` directly instead of going through track_changes().
    """
    from .models import AuditTrail  # avoid circular import

    msg = (
        f"[21 CFR Part 11 VIOLATION] Business action '{action}' on '{table_name}' "
        f"(record_id={record_id}) has no user_id. Action is not attributable!"
    )
    compliance_log.critical(msg)

    # Write the violation as its own audit trail record for evidentiary completeness
    alert_record = AuditTrail(
        user_id=None,
        action="COMPLIANCE_ALERT",
        table_name=table_name,
        record_id=str(record_id) if record_id else None,
        new_values={"violation": msg, "triggering_action": action}
    )
    session.add(alert_record)


def log_system_event(session: Session, action: str, user_id=None, details: dict = None) -> None:
    """
    Log an explicit system-level event (LOGIN, LOGIN_FAILED, SYSTEM_STARTUP, etc.).

    This is the correct, intentional path for events where user_id may legitimately
    be None (e.g., a failed login attempt before user identity is verified).
    Uses this instead of relying on the ORM track_changes() hook for system events.
    """
    from .models import AuditTrail  # avoid circular import

    record = AuditTrail(
        user_id=user_id,
        action=action,
        table_name=None,
        record_id=None,
        new_values=details or {}
    )
    session.add(record)


def default_json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    return str(obj)

def track_changes(session: Session, flush_context, instances):
    """
    SQLAlchemy before_flush event listener.
    Intercepts any new, dirty, or deleted object in the session and logs to AuditTrail.
    """
    from .models import AuditTrail  # Import here to avoid circular dependencies

    user_id = current_user_id_ctx.get()
    BUSINESS_ACTIONS_REQUIRE_USER = True  # 21 CFR Part 11 §11.10(e)
    
    for obj in session.new:
        if isinstance(obj, AuditTrail):
            continue
        
        state = attributes.instance_state(obj)
        table_name = state.class_.__tablename__
        pk = getattr(obj, state.mapper.primary_key[0].key, None)

        # 21 CFR Part 11 enforcement: flag unattributable business actions
        if BUSINESS_ACTIONS_REQUIRE_USER and user_id is None:
            _assert_user_attributable(session, "CREATE", table_name, pk, user_id)
        
        new_values = {}
        for attr in state.mapper.column_attrs:
            val = getattr(obj, attr.key)
            new_values[attr.key] = default_json_serializer(val) if val is not None else None
            
        # Get pk, though it might be None if autoincrement hasn't fired yet
        pk = getattr(obj, state.mapper.primary_key[0].key, None)
            
        audit_record = AuditTrail(
            user_id=user_id,
            action="CREATE",
            table_name=table_name,
            record_id=str(pk) if pk else None,
            new_values=new_values
        )
        session.add(audit_record)

    for obj in session.dirty:
        if isinstance(obj, AuditTrail):
            continue
            
        state = attributes.instance_state(obj)
        table_name = state.class_.__tablename__
        pk = getattr(obj, state.mapper.primary_key[0].key, None)

        # 21 CFR Part 11 enforcement
        if BUSINESS_ACTIONS_REQUIRE_USER and user_id is None:
            _assert_user_attributable(session, "UPDATE", table_name, pk, user_id)
        
        old_values = {}
        new_values = {}
        
        for attr in state.mapper.column_attrs:
            history = get_history(obj, attr.key)
            if history.has_changes():
                old_val = history.deleted[0] if history.deleted else None
                new_val = history.added[0] if history.added else None
                
                old_values[attr.key] = default_json_serializer(old_val) if old_val is not None else None
                new_values[attr.key] = default_json_serializer(new_val) if new_val is not None else None
                
        if old_values or new_values:
            audit_record = AuditTrail(
                user_id=user_id,
                action="UPDATE",
                table_name=table_name,
                record_id=str(pk),
                old_values=old_values,
                new_values=new_values
            )
            session.add(audit_record)

    for obj in session.deleted:
        if isinstance(obj, AuditTrail):
            continue
            
        state = attributes.instance_state(obj)
        table_name = state.class_.__tablename__
        pk = getattr(obj, state.mapper.primary_key[0].key, None)

        # 21 CFR Part 11 enforcement
        if BUSINESS_ACTIONS_REQUIRE_USER and user_id is None:
            _assert_user_attributable(session, "DELETE", table_name, pk, user_id)

        old_values = {}
        for attr in state.mapper.column_attrs:
            val = getattr(obj, attr.key)
            old_values[attr.key] = default_json_serializer(val) if val is not None else None
            
        audit_record = AuditTrail(
            user_id=user_id,
            action="DELETE",
            table_name=table_name,
            record_id=str(pk),
            old_values=old_values
        )
        session.add(audit_record)
