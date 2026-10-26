import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.models.audit import AuditLog

def log_audit_event(
    db: Session,
    action: str,
    target_type: str,
    target_id: Optional[str] = None,
    user_id: Optional[int] = None,
    actor_name: str = "System",
    outcome: str = "success",
    reason_code: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ip_address: str = "127.0.0.1"
) -> AuditLog:
    """Records an immutable security/operational audit event into database."""
    entry = AuditLog(
        user_id=user_id,
        actor_name=actor_name,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        details_json=json.dumps(details or {}),
        outcome=outcome,
        reason_code=reason_code,
        ip_address=ip_address,
        timestamp=datetime.now(timezone.utc)
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

