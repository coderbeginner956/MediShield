from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Recall(Base):
    __tablename__ = "recalls"

    id = Column(Integer, primary_key=True, index=True)
    recall_code = Column(String(50), unique=True, index=True, nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("product_batches.id"), nullable=True) # None = all batches of product
    
    title = Column(String(255), nullable=False)
    reason = Column(Text, nullable=False)
    source = Column(String(255), default="Synthetic Demonstration Recall Notice", nullable=False)
    effective_date = Column(DateTime, nullable=False)
    status = Column(String(50), default="active", nullable=False) # active, resolved, withdrawn
    severity = Column(String(50), default="class_i", nullable=False) # class_i (high), class_ii (moderate), class_iii (low)
    is_demo = Column(Boolean, default=False, nullable=False)
    created_by = Column(String(100), default="System Administrator", nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    product = relationship("Product", back_populates="recalls")
    batch = relationship("ProductBatch", back_populates="recalls")

