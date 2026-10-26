from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class InvestigationCase(Base):
    __tablename__ = "investigation_cases"

    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(50), unique=True, index=True, nullable=False)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    batch_id = Column(Integer, ForeignKey("product_batches.id"), nullable=True)
    
    title = Column(String(255), nullable=False)
    priority = Column(String(50), default="medium", nullable=False) # low, medium, high, critical
    status = Column(String(50), default="new", nullable=False) 
    # new, under_review, awaiting_information, escalated, resolved, closed

    reason_codes_json = Column(Text, default="[]", nullable=False)
    risk_assessment = Column(Text, nullable=False)
    evidence_summary = Column(Text, nullable=False)

    assigned_to_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    resolution_details = Column(Text, nullable=True)
    is_confirmed_counterfeit = Column(Boolean, default=False, nullable=False)
    authoritative_source = Column(String(255), nullable=True) # Required if confirmed counterfeit

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    inspection = relationship("Inspection", back_populates="cases")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id], back_populates="assigned_cases")
    notes = relationship("CaseNote", back_populates="case", cascade="all, delete-orphan")

class CaseNote(Base):
    __tablename__ = "case_notes"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("investigation_cases.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    note_text = Column(Text, nullable=False)
    attachment_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    case = relationship("InvestigationCase", back_populates="notes")
    user = relationship("User", back_populates="case_notes")

