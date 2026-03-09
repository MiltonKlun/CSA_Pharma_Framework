from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models import Deviation, DeviationStatus, UserRole, User
from .auth import get_current_active_user, require_role, verify_e_signature, ESignatureData

router = APIRouter()

class DeviationCreate(BaseModel):
    title: str
    description: str

class DeviationAssign(BaseModel):
    assigned_to_id: int

class DeviationInvestigate(BaseModel):
    root_cause: str

class DeviationApprove(BaseModel):
    signature: ESignatureData

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_deviation(
    deviation_in: DeviationCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    deviation = Deviation(
        title=deviation_in.title,
        description=deviation_in.description,
        status=DeviationStatus.OPEN,
        reported_by_id=current_user.id
    )
    db.add(deviation)
    db.commit()
    db.refresh(deviation)
    return deviation

@router.get("/")
async def list_deviations(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    deviations = db.query(Deviation).all()
    return deviations

@router.get("/{deviation_id}")
async def get_deviation(
    deviation_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    deviation = db.query(Deviation).filter(Deviation.id == deviation_id).first()
    if not deviation:
        raise HTTPException(status_code=404, detail="Deviation not found")
    return deviation

@router.put("/{deviation_id}/assign")
async def assign_deviation(
    deviation_id: int,
    assign_data: DeviationAssign,
    current_user: Annotated[User, Depends(require_role([UserRole.MANAGER, UserRole.QA, UserRole.ADMIN]))],
    db: Session = Depends(get_db)
):
    deviation = db.query(Deviation).filter(Deviation.id == deviation_id).first()
    if not deviation:
        raise HTTPException(status_code=404, detail="Deviation not found")
        
    deviation.assigned_to_id = assign_data.assigned_to_id
    deviation.status = DeviationStatus.INVESTIGATING
    db.commit()
    db.refresh(deviation)
    return deviation

@router.put("/{deviation_id}/investigate")
async def investigate_deviation(
    deviation_id: int,
    investigation_data: DeviationInvestigate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    deviation = db.query(Deviation).filter(Deviation.id == deviation_id).first()
    if not deviation:
        raise HTTPException(status_code=404, detail="Deviation not found")
        
    if deviation.assigned_to_id != current_user.id and current_user.role not in [UserRole.QA, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized to investigate this deviation")
        
    deviation.root_cause = investigation_data.root_cause
    deviation.status = DeviationStatus.PENDING_APPROVAL
    db.commit()
    db.refresh(deviation)
    return deviation

@router.put("/{deviation_id}/approve")
async def approve_deviation(
    deviation_id: int,
    approval_data: DeviationApprove,
    current_user: Annotated[User, Depends(require_role([UserRole.QA, UserRole.ADMIN]))],
    db: Session = Depends(get_db)
):
    # E-Signature verification
    await verify_e_signature(approval_data.signature, current_user)
    
    deviation = db.query(Deviation).filter(Deviation.id == deviation_id).first()
    if not deviation:
        raise HTTPException(status_code=404, detail="Deviation not found")
        
    if deviation.status != DeviationStatus.PENDING_APPROVAL:
        raise HTTPException(status_code=400, detail="Deviation must be pending approval to be closed")
        
    deviation.status = DeviationStatus.CLOSED
    deviation.qa_approval_id = current_user.id
    deviation.closed_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(deviation)
    return deviation
