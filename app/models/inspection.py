from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class Inspection(Base):
    __tablename__ = "inspections"

    id = Column(Integer, primary_key=True, index=True)
    inspection_code = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    batch_id = Column(Integer, ForeignKey("product_batches.id"), nullable=True)
    reference_image_id = Column(Integer, ForeignKey("reference_images.id"), nullable=True)

    original_image_path = Column(String(500), nullable=False)
    image_width = Column(Integer, nullable=True)
    image_height = Column(Integer, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    mime_type = Column(String(50), default="image/jpeg", nullable=False)

    status = Column(String(50), default="pending", nullable=False) 
    # pending, completed, failed, manual_review_recommended, model_unavailable

    model_provider = Column(String(50), default="demo", nullable=False)
    processing_time_ms = Column(Float, nullable=True)
    is_demo = Column(Boolean, default=False, nullable=False)

    # Risk assessment
    risk_level = Column(String(50), default="insufficient_evidence", nullable=False) 
    # low, medium, high, insufficient_evidence
    risk_score = Column(Float, nullable=True) # 0.0 - 100.0 or None
    risk_summary = Column(Text, nullable=True)
    reason_codes_json = Column(Text, default="[]", nullable=False) # JSON list of reason codes

    # Reference comparison summary
    comparison_performed = Column(Boolean, default=False, nullable=False)
    comparison_score = Column(Float, nullable=True) # 0.0 - 1.0 or None
    comparison_difference_path = Column(String(500), nullable=True)
    comparison_notes = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    user = relationship("User", back_populates="inspections")
    product = relationship("Product", back_populates="inspections")
    batch = relationship("ProductBatch", back_populates="inspections")
    reference_image = relationship("ReferenceImage", back_populates="inspections_compared")

    prediction = relationship("ModelPrediction", uselist=False, back_populates="inspection", cascade="all, delete-orphan")
    explainability = relationship("ExplainabilityArtifact", uselist=False, back_populates="inspection", cascade="all, delete-orphan")
    ocr_result = relationship("OCRResult", uselist=False, back_populates="inspection", cascade="all, delete-orphan")
    verification_result = relationship("VerificationResult", uselist=False, back_populates="inspection", cascade="all, delete-orphan")
    cases = relationship("InvestigationCase", back_populates="inspection")

class ModelPrediction(Base):
    __tablename__ = "model_predictions"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    model_name = Column(String(100), nullable=False)
    task_type = Column(String(50), default="classification", nullable=False) # classification, detection
    predicted_class = Column(String(100), nullable=True) # Visual anomaly flagged, No visual anomaly detected, etc.
    confidence = Column(Float, nullable=True) # 0.0 - 1.0
    raw_probabilities_json = Column(Text, default="{}", nullable=False)
    detected_boxes_json = Column(Text, default="[]", nullable=False) # List of boxes: [x, y, w, h, label, score]
    is_demo = Column(Boolean, default=False, nullable=False)
    explanation_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    inspection = relationship("Inspection", back_populates="prediction")

class ExplainabilityArtifact(Base):
    __tablename__ = "explainability_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    method = Column(String(50), default="gradcam", nullable=False) # gradcam, feature_attribution, bounding_box, edge_gradient
    artifact_image_path = Column(String(500), nullable=True)
    explanation_text = Column(Text, nullable=False)
    limitations_text = Column(Text, nullable=False)
    is_supported = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    inspection = relationship("Inspection", back_populates="explainability")

class OCRResult(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    raw_text = Column(Text, nullable=True)
    
    # Extracted fields
    detected_product_name = Column(String(255), nullable=True)
    detected_manufacturer = Column(String(255), nullable=True)
    detected_batch_number = Column(String(100), nullable=True)
    detected_mfg_date = Column(String(50), nullable=True)
    detected_expiry_date = Column(String(50), nullable=True)
    detected_registration_id = Column(String(100), nullable=True)

    # User correction tracking
    edited_fields_json = Column(Text, default="{}", nullable=False) # stores overridden field values
    is_edited = Column(Boolean, default=False, nullable=False)
    confidence_scores_json = Column(Text, default="{}", nullable=False)

    # Expiry evaluation
    expiry_status = Column(String(50), default="unknown", nullable=False) 
    # not_expired, expired, unreadable, missing, unknown
    parsed_expiry_iso = Column(DateTime, nullable=True)

    # Label rule flags
    label_flags_json = Column(Text, default="[]", nullable=False) 
    # list of flags: ["EXPIRED_DATE", "MISSING_BATCH", "NAME_MISMATCH"]

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    inspection = relationship("Inspection", back_populates="ocr_result")

class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("inspections.id"), nullable=False)
    
    product_match_status = Column(String(50), default="not_found", nullable=False) # matched, not_found, mismatch
    batch_match_status = Column(String(50), default="not_found", nullable=False) # matched, not_found, mismatch
    expiry_match_status = Column(String(50), default="unknown", nullable=False) # valid, expired, mismatch, unknown
    recall_status = Column(String(50), default="none", nullable=False) # none, active_recall_flagged
    
    verification_source = Column(String(100), default="local_registry", nullable=False)
    summary_text = Column(Text, nullable=False)
    details_json = Column(Text, default="{}", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    inspection = relationship("Inspection", back_populates="verification_result")

