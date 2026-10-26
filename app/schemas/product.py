from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ProductBatchCreate(BaseModel):
    batch_number: str
    manufacturer: Optional[str] = None
    manufacturing_date: Optional[datetime] = None
    expiry_date: datetime
    reference_source: Optional[str] = "Internal Registry"
    verification_notes: Optional[str] = None

class ProductBatchResponse(BaseModel):
    id: int
    product_id: int
    batch_number: str
    manufacturer: Optional[str]
    manufacturing_date: Optional[datetime]
    expiry_date: datetime
    recall_status: str
    is_demo: bool
    reference_source: str
    verification_notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class ProductCreate(BaseModel):
    name: str
    brand_or_manufacturer: str
    dosage_form: Optional[str] = "Tablet"
    packaging_type: Optional[str] = "Blister Pack"
    product_identifier: Optional[str] = None
    description: Optional[str] = None
    record_status: Optional[str] = "active"
    notes: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    brand_or_manufacturer: Optional[str] = None
    dosage_form: Optional[str] = None
    packaging_type: Optional[str] = None
    product_identifier: Optional[str] = None
    description: Optional[str] = None
    record_status: Optional[str] = None
    notes: Optional[str] = None

class ProductResponse(BaseModel):
    id: int
    name: str
    brand_or_manufacturer: str
    dosage_form: Optional[str]
    packaging_type: Optional[str]
    product_identifier: Optional[str]
    description: Optional[str]
    record_status: str
    is_demo: bool
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    batches: List[ProductBatchResponse] = []

    class Config:
        from_attributes = True

