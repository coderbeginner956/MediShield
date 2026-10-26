from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from app.core.database import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    actor_name = Column(String(255), default="System", nullable=False)
    action = Column(String(100), index=True, nullable=False) # LOGIN, INSPECT_IMAGE, APPROVE_REFERENCE, CREATE_RECALL, etc.
    target_type = Column(String(100), index=True, nullable=False) # inspection, product, batch, recall, case, user
    target_id = Column(String(100), nullable=True)
    details_json = Column(Text, default="{}", nullable=False)
    outcome = Column(String(50), default="success", nullable=False) # success, failure, warning
    reason_code = Column(String(100), nullable=True)
    ip_address = Column(String(50), default="127.0.0.1", nullable=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)

