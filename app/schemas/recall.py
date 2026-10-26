from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class RecallCreate(BaseModel):
    product_id: int
    batch_id: Optional[int] = None
    title: str
    reason: str
    source: Optional[str] = "Synthetic Demonstration Recall Notice"
    effective_date: datetime
    severity: Optional[str] = "class_i" # class_i, class_ii, class_iii

class RecallUpdate(BaseModel):
    title: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = None # active, resolved, withdrawn
    severity: Optional[str] = None

class RecallResponse(BaseModel):
    id: int
    recall_code: str
    product_id: int
    batch_id: Optional[int]
    title: str
    reason: str
    source: str
    effective_date: datetime
    status: str
    severity: str
    is_demo: bool
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

