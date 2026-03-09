from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..database import get_db
from ..models import Document, DocumentStatus, UserRole, User
from .auth import get_current_active_user, require_role, verify_e_signature, ESignatureData

router = APIRouter()

class DocumentCreate(BaseModel):
    title: str
    content: str
    version: str = "1.0"

class DocumentApprove(BaseModel):
    signature: ESignatureData

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_document(
    doc_in: DocumentCreate,
    current_user: Annotated[User, Depends(require_role([UserRole.MANAGER, UserRole.QA, UserRole.ADMIN]))],
    db: Session = Depends(get_db)
):
    document = Document(
        title=doc_in.title,
        content=doc_in.content,
        version=doc_in.version,
        status=DocumentStatus.DRAFT,
        author_id=current_user.id
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document

@router.get("/")
async def list_documents(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    documents = db.query(Document).all()
    return documents

@router.get("/{document_id}")
async def get_document(
    document_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.put("/{document_id}/review")
async def review_document(
    document_id: int,
    current_user: Annotated[User, Depends(require_role([UserRole.QA, UserRole.MANAGER, UserRole.ADMIN]))],
    db: Session = Depends(get_db)
):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if document.status != DocumentStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only DRAFT documents can be sent for review")
        
    document.status = DocumentStatus.UNDER_REVIEW
    db.commit()
    db.refresh(document)
    return document

@router.put("/{document_id}/approve")
async def approve_document(
    document_id: int,
    approval_data: DocumentApprove,
    current_user: Annotated[User, Depends(require_role([UserRole.QA, UserRole.ADMIN]))],
    db: Session = Depends(get_db)
):
    # E-Signature verification
    await verify_e_signature(approval_data.signature, current_user)
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    if document.status != DocumentStatus.UNDER_REVIEW:
        raise HTTPException(status_code=400, detail="Document must be UNDER_REVIEW to be approved")
        
    document.status = DocumentStatus.APPROVED
    document.approver_id = current_user.id
    document.approved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(document)
    return document

@router.put("/{document_id}/obsolete")
async def obsolete_document(
    document_id: int,
    approval_data: DocumentApprove, # Using E-signature to obsolete documents
    current_user: Annotated[User, Depends(require_role([UserRole.MANAGER, UserRole.QA, UserRole.ADMIN]))],
    db: Session = Depends(get_db)
):
    # E-Signature verification for obsoleting a document
    await verify_e_signature(approval_data.signature, current_user)
    
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
        
    document.status = DocumentStatus.OBSOLETE
    db.commit()
    db.refresh(document)
    return document
