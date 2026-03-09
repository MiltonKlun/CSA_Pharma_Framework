from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models import CAPA, Deviation, CAPAStatus, UserRole, User
from .auth import get_current_active_user, require_role, verify_e_signature, ESignatureData

router = APIRouter()

class CAPACreate(BaseModel):
    deviation_id: int
    title: str
    description: str
    assigned_to_id: int

class CAPAImplement(BaseModel):
    implementation_notes: str | None = None

class CAPAEffectivenessCheck(BaseModel):
    check_notes: str | None = None

class CAPAApprove(BaseModel):
    signature: ESignatureData

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_capa(
    capa_in: CAPACreate,
    current_user: Annotated[User, Depends(require_role([UserRole.QA, UserRole.MANAGER, UserRole.ADMIN]))],
    db: Session = Depends(get_db)
):
    # Verify deviation exists
    deviation = db.query(Deviation).filter(Deviation.id == capa_in.deviation_id).first()
    if not deviation:
        raise HTTPException(status_code=404, detail="Associated deviation not found")

    capa = CAPA(
        deviation_id=capa_in.deviation_id,
        title=capa_in.title,
        description=capa_in.description,
        assigned_to_id=capa_in.assigned_to_id,
        status=CAPAStatus.OPEN
    )
    db.add(capa)
    db.commit()
    db.refresh(capa)
    return capa

@router.get("/")
async def list_capas(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    capas = db.query(CAPA).all()
    return capas

@router.get("/{capa_id}")
async def get_capa(
    capa_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    capa = db.query(CAPA).filter(CAPA.id == capa_id).first()
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
    return capa

@router.put("/{capa_id}/implement")
async def implement_capa(
    capa_id: int,
    implement_data: CAPAImplement,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    capa = db.query(CAPA).filter(CAPA.id == capa_id).first()
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
        
    if capa.assigned_to_id != current_user.id and current_user.role not in [UserRole.QA, UserRole.ADMIN]:
        raise HTTPException(status_code=403, detail="Not authorized to implement this CAPA")
        
    capa.status = CAPAStatus.IMPLEMENTED
    # (assuming notes would be saved via an audit trail or additional comment table in a deeper system)
    db.commit()
    db.refresh(capa)
    return capa

@router.put("/{capa_id}/check_effectiveness")
async def check_capa_effectiveness(
    capa_id: int,
    check_data: CAPAEffectivenessCheck,
    current_user: Annotated[User, Depends(require_role([UserRole.QA, UserRole.ADMIN]))],
    db: Session = Depends(get_db)
):
    capa = db.query(CAPA).filter(CAPA.id == capa_id).first()
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
        
    if capa.status != CAPAStatus.IMPLEMENTED:
        raise HTTPException(status_code=400, detail="CAPA must be implemented before checking effectiveness")
        
    capa.status = CAPAStatus.EFFECTIVENESS_CHECK
    db.commit()
    db.refresh(capa)
    return capa

@router.put("/{capa_id}/close")
async def close_capa(
    capa_id: int,
    approval_data: CAPAApprove,
    current_user: Annotated[User, Depends(require_role([UserRole.QA, UserRole.ADMIN]))],
    db: Session = Depends(get_db)
):
    # E-Signature verification
    await verify_e_signature(approval_data.signature, current_user)
    
    capa = db.query(CAPA).filter(CAPA.id == capa_id).first()
    if not capa:
        raise HTTPException(status_code=404, detail="CAPA not found")
        
    if capa.status != CAPAStatus.EFFECTIVENESS_CHECK:
        raise HTTPException(status_code=400, detail="CAPA effectiveness must be checked before closing")
        
    capa.status = CAPAStatus.CLOSED
    capa.closed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(capa)
    return capa
