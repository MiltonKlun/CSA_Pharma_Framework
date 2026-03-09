from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models import BatchRecord, BatchRecordStatus, UserRole, User
from .auth import get_current_active_user, require_role, verify_e_signature, ESignatureData

router = APIRouter()

class BatchRecordCreate(BaseModel):
    batch_number: str
    product_name: str

class BatchRecordApprove(BaseModel):
    signature: ESignatureData

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_batch_record(
    batch_in: BatchRecordCreate,
    current_user: Annotated[User, Depends(require_role([UserRole.OPERATOR, UserRole.MANAGER, UserRole.ADMIN]))],
    db: Session = Depends(get_db)
):
    # Unique check
    existing = db.query(BatchRecord).filter(BatchRecord.batch_number == batch_in.batch_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="Batch number already exists")

    batch_record = BatchRecord(
        batch_number=batch_in.batch_number,
        product_name=batch_in.product_name,
        status=BatchRecordStatus.DRAFT,
        operator_id=current_user.id
    )
    db.add(batch_record)
    db.commit()
    db.refresh(batch_record)
    return batch_record

@router.get("/")
async def list_batch_records(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    batch_records = db.query(BatchRecord).all()
    return batch_records

@router.get("/{batch_record_id}")
async def get_batch_record(
    batch_record_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    batch_record = db.query(BatchRecord).filter(BatchRecord.id == batch_record_id).first()
    if not batch_record:
        raise HTTPException(status_code=404, detail="Batch Record not found")
    return batch_record

@router.put("/{batch_record_id}/review")
async def review_batch_record(
    batch_record_id: int,
    current_user: Annotated[User, Depends(require_role([UserRole.QA, UserRole.MANAGER, UserRole.ADMIN]))],
    db: Session = Depends(get_db)
):
    batch_record = db.query(BatchRecord).filter(BatchRecord.id == batch_record_id).first()
    if not batch_record:
        raise HTTPException(status_code=404, detail="Batch Record not found")
        
    if batch_record.status != BatchRecordStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT batch records can be sent for review")
        
    batch_record.status = BatchRecordStatus.PENDING_REVIEW
    db.commit()
    db.refresh(batch_record)
    return batch_record

@router.put("/{batch_record_id}/approve")
async def approve_batch_record(
    batch_record_id: int,
    approval_data: BatchRecordApprove,
    current_user: Annotated[User, Depends(require_role([UserRole.QA, UserRole.ADMIN]))],
    db: Session = Depends(get_db)
):
    # E-Signature verification
    await verify_e_signature(approval_data.signature, current_user)
    
    batch_record = db.query(BatchRecord).filter(BatchRecord.id == batch_record_id).first()
    if not batch_record:
        raise HTTPException(status_code=404, detail="Batch Record not found")
        
    if batch_record.status != BatchRecordStatus.PENDING_REVIEW:
        raise HTTPException(status_code=400, detail="Batch record must be PENDING_REVIEW to be approved")
        
    batch_record.status = BatchRecordStatus.APPROVED
    batch_record.reviewer_id = current_user.id
    batch_record.review_date = datetime.now(timezone.utc)
    db.commit()
    db.refresh(batch_record)
    return batch_record

@router.put("/{batch_record_id}/reject")
async def reject_batch_record(
    batch_record_id: int,
    approval_data: BatchRecordApprove,
    current_user: Annotated[User, Depends(require_role([UserRole.QA, UserRole.ADMIN]))],
    db: Session = Depends(get_db)
):
    # E-Signature verification for rejecting
    await verify_e_signature(approval_data.signature, current_user)
    
    batch_record = db.query(BatchRecord).filter(BatchRecord.id == batch_record_id).first()
    if not batch_record:
        raise HTTPException(status_code=404, detail="Batch Record not found")
        
    if batch_record.status != BatchRecordStatus.PENDING_REVIEW:
        raise HTTPException(status_code=400, detail="Batch record must be PENDING_REVIEW to be rejected")
        
    batch_record.status = BatchRecordStatus.REJECTED
    batch_record.reviewer_id = current_user.id
    batch_record.review_date = datetime.now(timezone.utc)
    db.commit()
    db.refresh(batch_record)
    return batch_record
