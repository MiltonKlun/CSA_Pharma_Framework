"""
CSA Step 3 — Assurance Activity: Audit Trail Verification

Tests that every database mutation is captured in the audit_trail table,
satisfying 21 CFR Part 11 §11.10(e) requirements for audit trails.
"""
import pytest
from .conftest import auth_headers


class TestAuditTrailOnCreate:
    """Verify that creating a record generates a CREATE audit entry."""

    def test_deviation_create_generates_audit(self, client, operator_user, db_session):
        headers = auth_headers(client, "test_operator")
        resp = client.post(
            "/deviations/",
            json={"title": "Audit Test Deviation", "description": "Testing audit trail capture"},
            headers=headers
        )
        assert resp.status_code == 201

        # Query audit trail for the CREATE entry
        from demo_app.app.models import AuditTrail
        audits = db_session.query(AuditTrail).filter(
            AuditTrail.table_name == "deviations",
            AuditTrail.action == "CREATE"
        ).all()

        assert len(audits) >= 1
        latest = audits[-1]
        assert latest.new_values is not None
        assert "Audit Test Deviation" in str(latest.new_values)


class TestAuditTrailOnUpdate:
    """Verify that updating a record generates an UPDATE audit entry with old and new values."""

    def test_deviation_status_change_audited(self, client, operator_user, manager_user, db_session):
        # Create a deviation
        op_headers = auth_headers(client, "test_operator")
        create_resp = client.post(
            "/deviations/",
            json={"title": "Update Audit Test", "description": "For audit update testing"},
            headers=op_headers
        )
        assert create_resp.status_code == 201
        dev_id = create_resp.json()["id"]

        # Assign it (changes status to investigating)
        mgr_headers = auth_headers(client, "test_manager")
        assign_resp = client.put(
            f"/deviations/{dev_id}/assign",
            json={"assigned_to_id": operator_user.id},
            headers=mgr_headers
        )
        assert assign_resp.status_code == 200

        # Check for UPDATE audit entry
        from demo_app.app.models import AuditTrail
        update_audits = db_session.query(AuditTrail).filter(
            AuditTrail.table_name == "deviations",
            AuditTrail.action == "UPDATE"
        ).all()

        assert len(update_audits) >= 1
        latest = update_audits[-1]
        assert latest.old_values is not None
        assert latest.new_values is not None


class TestAuditTrailImmutability:
    """Verify that audit trail entries cannot be modified or deleted via the API."""

    def test_no_delete_endpoint_for_audit_trail(self, client, admin_user):
        headers = auth_headers(client, "test_admin")
        # There should be no DELETE endpoint for audit trail
        resp = client.delete("/audit_trail/1", headers=headers)
        assert resp.status_code in [404, 405]  # Not Found or Method Not Allowed

    def test_no_put_endpoint_for_audit_trail(self, client, admin_user):
        headers = auth_headers(client, "test_admin")
        resp = client.put("/audit_trail/1", json={"action": "TAMPERED"}, headers=headers)
        assert resp.status_code in [404, 405]

class TestAuditTrailCompliance:
    """Verify 21 CFR Part 11 strict constraints on the audit trail explicitly."""
    
    def test_business_action_without_user_logs_violation(self, db_session, operator_user):
        from demo_app.app.models import Deviation, AuditTrail
        from demo_app.app.audit_trail import current_user_id_ctx
        
        # Intentionally no user context
        token_ctx = current_user_id_ctx.set(None)
        try:
            # Create a deviation without user context (but satisfying DB constraints)
            dev = dict(title="Ghost Dev", description="No user", status="OPEN", reported_by_id=operator_user.id)
            dev_obj = Deviation(**dev)
            db_session.add(dev_obj)
            db_session.commit()
            
            # The system must have logged a COMPLIANCE_ALERT
            alerts = db_session.query(AuditTrail).filter(AuditTrail.action == "COMPLIANCE_ALERT").all()
            assert len(alerts) >= 1
            latest = alerts[-1]
            assert latest.new_values is not None
            assert "violation" in latest.new_values
            assert "Ghost Dev" in str(latest.new_values) or "deviations" in str(latest.new_values)
            
        finally:
            current_user_id_ctx.reset(token_ctx)

    def test_system_event_logging(self, db_session):
        from demo_app.app.audit_trail import log_system_event
        from demo_app.app.models import AuditTrail
        
        log_system_event(db_session, action="LOGIN_FAILED", details={"ip": "127.0.0.1", "user": "hacker"})
        db_session.commit()
        
        event = db_session.query(AuditTrail).filter(AuditTrail.action == "LOGIN_FAILED").first()
        assert event is not None
        assert event.new_values.get("user") == "hacker"
