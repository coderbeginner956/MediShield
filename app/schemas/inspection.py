from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ModelPredictionResponse(BaseModel):
    id: int
    model_name: str
    task_type: str
    predicted_class: Optional[str]
    confidence: Optional[float]
    raw_probabilities: Dict[str, float] = {}
    detected_boxes: List[Dict[str, Any]] = []
    is_demo: bool
    explanation_note: Optional[str]

    class Config:
        from_attributes = True

class ExplainabilityResponse(BaseModel):
    id: int
    method: str
    artifact_image_url: Optional[str]
    explanation_text: str
    limitations_text: str
    is_supported: bool

    class Config:
        from_attributes = True

class OCRResponse(BaseModel):
    id: int
    raw_text: Optional[str]
    detected_product_name: Optional[str]
    detected_manufacturer: Optional[str]
    detected_batch_number: Optional[str]
    detected_mfg_date: Optional[str]
    detected_expiry_date: Optional[str]
    detected_registration_id: Optional[str]
    expiry_status: str
    parsed_expiry_iso: Optional[datetime]
    label_flags: List[str] = []
    confidence_scores: Dict[str, float] = {}
    is_edited: bool
    edited_fields: Dict[str, Any] = {}

    class Config:
        from_attributes = True

class OCRUpdateRequest(BaseModel):
    product_name: Optional[str] = None
    manufacturer: Optional[str] = None
    batch_number: Optional[str] = None
    expiry_date: Optional[str] = None
    registration_id: Optional[str] = None

class VerificationResponse(BaseModel):
    id: int
    product_match_status: str
    batch_match_status: str
    expiry_match_status: str
    recall_status: str
    verification_source: str
    summary_text: str

    class Config:
        from_attributes = True

class InspectionResponse(BaseModel):
    id: int
    inspection_code: str
    user_id: int
    product_id: Optional[int] = None
    batch_id: Optional[int] = None
    reference_image_id: Optional[int] = None
    original_image_path: Optional[str] = None
    original_image_url: Optional[str] = None
    image_width: Optional[int] = None
    image_height: Optional[int] = None
    file_size_bytes: Optional[int] = None
    status: str
    model_provider: str
    processing_time_ms: Optional[float] = None
    is_demo: bool
    risk_level: str
    risk_score: Optional[float] = None
    risk_summary: Optional[str] = None
    reason_codes: List[str] = []
    
    # Comparison summary
    comparison_performed: bool = False
    comparison_score: Optional[float] = None
    comparison_difference_path: Optional[str] = None
    comparison_difference_url: Optional[str] = None
    comparison_notes: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class InspectionDetailResponse(InspectionResponse):
    prediction: Optional[ModelPredictionResponse] = None
    explainability: Optional[ExplainabilityResponse] = None
    ocr_result: Optional[OCRResponse] = None
    verification_result: Optional[VerificationResponse] = None
