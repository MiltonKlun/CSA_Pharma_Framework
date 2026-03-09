import enum
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum, Text, JSON
from sqlalchemy.orm import relationship

from .database import Base

class UserRole(str, enum.Enum):
    OPERATOR = "operator"
    QA = "qa"
    MANAGER = "manager"
    ADMIN = "admin"

class DeviationStatus(str, enum.Enum):
    OPEN = "open"
    INVESTIGATING = "investigating"
    PENDING_APPROVAL = "pending_approval"
    CLOSED = "closed"

class CAPAStatus(str, enum.Enum):
    OPEN = "open"
    IMPLEMENTED = "implemented"
    EFFECTIVENESS_CHECK = "effectiveness_check"
    CLOSED = "closed"

class DocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    OBSOLETE = "obsolete"

class BatchRecordStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), default=UserRole.OPERATOR, nullable=False)
    is_active = Column(Boolean, default=True)

class Deviation(Base):
    __tablename__ = "deviations"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(DeviationStatus), default=DeviationStatus.OPEN, nullable=False)
    root_cause = Column(Text, nullable=True)
    
    reported_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    qa_approval_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    closed_at = Column(DateTime, nullable=True)
    
    reported_by = relationship("User", foreign_keys=[reported_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])
    qa_approval = relationship("User", foreign_keys=[qa_approval_id])
    capas = relationship("CAPA", back_populates="deviation")

class CAPA(Base):
    __tablename__ = "capas"

    id = Column(Integer, primary_key=True, index=True)
    deviation_id = Column(Integer, ForeignKey("deviations.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(Enum(CAPAStatus), default=CAPAStatus.OPEN, nullable=False)
    
    assigned_to_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    closed_at = Column(DateTime, nullable=True)

    deviation = relationship("Deviation", back_populates="capas")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    version = Column(String, nullable=False, default="1.0")
    content = Column(Text, nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.DRAFT, nullable=False)
    
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    approved_at = Column(DateTime, nullable=True)
    
    author = relationship("User", foreign_keys=[author_id])
    approver = relationship("User", foreign_keys=[approver_id])

class BatchRecord(Base):
    __tablename__ = "batch_records"

    id = Column(Integer, primary_key=True, index=True)
    batch_number = Column(String, unique=True, index=True, nullable=False)
    product_name = Column(String, nullable=False)
    status = Column(Enum(BatchRecordStatus), default=BatchRecordStatus.DRAFT, nullable=False)
    
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    manufacturing_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    review_date = Column(DateTime, nullable=True)
    
    operator = relationship("User", foreign_keys=[operator_id])
    reviewer = relationship("User", foreign_keys=[reviewer_id])

class AuditTrail(Base):
    __tablename__ = "audit_trail"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Nullable for system actions or failed logins
    action = Column(String, nullable=False)  # e.g., CREATE, UPDATE, DELETE, LOGIN, LOGIN_FAILED, APPROVE
    table_name = Column(String, nullable=True)
    record_id = Column(String, nullable=True)
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    
    user = relationship("User", foreign_keys=[user_id])
