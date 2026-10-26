from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class ReferenceImage(Base):
    __tablename__ = "reference_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    packaging_type = Column(String(100), nullable=True) # Blister Front, Blister Back, Box Side, Bottle Label
    image_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    source = Column(String(255), default="Manufacturer Authorized Sample", nullable=False)
    description = Column(Text, nullable=True)
    verification_notes = Column(Text, nullable=True)
    status = Column(String(50), default="approved", nullable=False) # pending_review, approved, archived
    is_authoritative = Column(Boolean, default=True, nullable=False) # Differentiates authoritative from user-submitted
    is_demo = Column(Boolean, default=False, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product", back_populates="reference_images")
    inspections_compared = relationship("Inspection", back_populates="reference_image")

