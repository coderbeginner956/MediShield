import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_role
from app.models.user import User
from app.models.product import Product
from app.models.recall import Recall
from app.schemas.recall import RecallCreate, RecallUpdate, RecallResponse
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/recalls", tags=["Recalls"])

@router.get("", response_model=List[RecallResponse])
def list_recalls(
    status_filter: Optional[str] = None,
    product_id: Optional[int] = None,
    include_demo: bool = True,
    db: Session = Depends(get_db)
):
    """Lists registered regulatory and manufacturer product recalls."""
    query = db.query(Recall)
    if status_filter:
        query = query.filter(Recall.status == status_filter)
    if product_id:
        query = query.filter(Recall.product_id == product_id)
    if not include_demo:
        query = query.filter(Recall.is_demo == False)

    return query.order_by(Recall.effective_date.desc()).all()

@router.post("", response_model=RecallResponse, status_code=status.HTTP_201_CREATED)
def create_recall(
    recall_in: RecallCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Creates a new pharmaceutical recall notice."""
    product = db.query(Product).filter(Product.id == recall_in.product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target product not found.")

    recall_code = f"REC-{uuid.uuid4().hex[:6].upper()}"
    recall = Recall(
        recall_code=recall_code,
        product_id=recall_in.product_id,
        batch_id=recall_in.batch_id,
        title=recall_in.title,
        reason=recall_in.reason,
        source=recall_in.source or "Synthetic Demonstration Notice",
        effective_date=recall_in.effective_date,
        status="active",
        severity=recall_in.severity or "class_i",
        is_demo=False,
        created_by=current_user.full_name
    )
    db.add(recall)
    db.commit()
    db.refresh(recall)

    log_audit_event(
        db=db,
        action="RECALL_CREATED",
        target_type="recall",
        target_id=str(recall.id),
        user_id=current_user.id,
        actor_name=current_user.full_name,
        details={"code": recall_code, "product_id": recall.product_id}
    )

    return recall

@router.patch("/{recall_id}", response_model=RecallResponse)
def update_recall(
    recall_id: int,
    recall_update: RecallUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Updates recall status (e.g. active -> resolved/withdrawn) or details."""
    recall = db.query(Recall).filter(Recall.id == recall_id).first()
    if not recall:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recall notice not found.")

    update_data = recall_update.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(recall, key, val)

    db.commit()
    db.refresh(recall)

    log_audit_event(
        db=db,
        action="RECALL_UPDATED",
        target_type="recall",
        target_id=str(recall.id),
        user_id=current_user.id,
        actor_name=current_user.full_name,
        details=update_data
    )

    return recall

