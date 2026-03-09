from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db
from ..models import Deviation, CAPA, Document, BatchRecord, User
from .auth import get_current_active_user

router = APIRouter()

@router.get("/metrics")
async def get_dashboard_metrics(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    """
    Returns basic QMS quality metrics for the dashboard.
    """
    metrics = {
        "deviations": {
            status: count for status, count in db.query(Deviation.status, func.count(Deviation.id)).group_by(Deviation.status).all()
        },
        "capas": {
            status: count for status, count in db.query(CAPA.status, func.count(CAPA.id)).group_by(CAPA.status).all()
        },
        "documents": {
            status: count for status, count in db.query(Document.status, func.count(Document.id)).group_by(Document.status).all()
        },
        "batch_records": {
            status: count for status, count in db.query(BatchRecord.status, func.count(BatchRecord.id)).group_by(BatchRecord.status).all()
        }
    }
    
    return metrics
