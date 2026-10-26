from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), index=True, nullable=False)
    brand_or_manufacturer = Column(String(255), index=True, nullable=False)
    dosage_form = Column(String(100), nullable=True) # Tablet, Capsule, Syrup, Injection
    packaging_type = Column(String(100), nullable=True) # Blister Pack, Bottle, Vial, Box
    product_identifier = Column(String(100), unique=True, index=True, nullable=True) # NDC / GTIN
    description = Column(Text, nullable=True)
    record_status = Column(String(50), default="active", nullable=False) # active, draft, archived
    is_demo = Column(Boolean, default=False, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    batches = relationship("ProductBatch", back_populates="product", cascade="all, delete-orphan")
    reference_images = relationship("ReferenceImage", back_populates="product", cascade="all, delete-orphan")
    inspections = relationship("Inspection", back_populates="product")
    recalls = relationship("Recall", back_populates="product")

class ProductBatch(Base):
    __tablename__ = "product_batches"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_number = Column(String(100), index=True, nullable=False)
    manufacturer = Column(String(255), nullable=True)
    manufacturing_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=False)
    recall_status = Column(String(50), default="none", nullable=False) # none, recalled, investigation
    is_demo = Column(Boolean, default=False, nullable=False)
    reference_source = Column(String(255), default="Internal Registry", nullable=False)
    verification_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product", back_populates="batches")
    inspections = relationship("Inspection", back_populates="batch")
    recalls = relationship("Recall", back_populates="batch")

