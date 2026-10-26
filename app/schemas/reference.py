from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReferenceImageResponse(BaseModel):
    id: int
    product_id: int
    packaging_type: Optional[str]
    image_path: str
    source: str
    description: Optional[str]
    verification_notes: Optional[str]
    status: str
    is_authoritative: bool
    is_demo: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ReferenceImageUpdate(BaseModel):
    status: Optional[str] = None
    verification_notes: Optional[str] = None
    description: Optional[str] = None

class ReferenceCompareRequest(BaseModel):
    inspection_id: int
    reference_id: int

class ReferenceCompareResponse(BaseModel):
    comparison_possible: bool
    reference_id: int
    method_used: str
    similarity_score: Optional[float]
    difference_overlay_url: Optional[str]
    keypoint_matches_count: Optional[int]
    notes: str
    limitations: str

