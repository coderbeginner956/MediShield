import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, require_role
from app.models.user import User
from app.models.audit import AuditLog
from app.schemas.auth import UserResponse, UserUpdateRole
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/admin", tags=["Administration & Audit"])

@router.get("/audit-logs")
def list_audit_logs(
    action: Optional[str] = None,
    target_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "reviewer"]))
):
    """Retrieves immutable system audit records."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if target_type:
        query = query.filter(AuditLog.target_type == target_type)

    logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "user_id": log.user_id,
            "actor_name": log.actor_name,
            "action": log.action,
            "target_type": log.target_type,
            "target_id": log.target_id,
            "details": json.loads(log.details_json or "{}"),
            "outcome": log.outcome,
            "reason_code": log.reason_code,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp
        }
        for log in logs
    ]

@router.get("/users", response_model=List[UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Lists registered user accounts (Admin only)."""
    return db.query(User).order_by(User.created_at.desc()).all()

@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user_role(
    user_id: int,
    user_update: UserUpdateRole,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    """Updates user role or activation status (Admin only)."""
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    if user_update.role not in ["admin", "inspector", "reviewer"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role specified.")

    target_user.role = user_update.role
    if user_update.is_active is not None:
        target_user.is_active = user_update.is_active

    db.commit()
    db.refresh(target_user)

    log_audit_event(
        db=db,
        action="USER_ROLE_UPDATED",
        target_type="user",
        target_id=str(target_user.id),
        user_id=current_user.id,
        actor_name=current_user.full_name,
        details={"target_email": target_user.email, "new_role": target_user.role}
    )

    return target_user

