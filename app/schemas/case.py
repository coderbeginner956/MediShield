from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class CaseNoteCreate(BaseModel):
    note_text: str

class CaseNoteResponse(BaseModel):
    id: int
    case_id: int
    user_id: int
    author_name: Optional[str] = "Investigator"
    note_text: str
    created_at: datetime

    class Config:
        from_attributes = True

class CaseCreate(BaseModel):
    inspection_id: int
    title: str
    priority: Optional[str] = "medium" # low, medium, high, critical
    notes: Optional[str] = None

class CaseUpdate(BaseModel):
    status: Optional[str] = None # new, under_review, awaiting_information, escalated, resolved, closed
    priority: Optional[str] = None
    assigned_to_user_id: Optional[int] = None
    resolution_details: Optional[str] = None
    is_confirmed_counterfeit: Optional[bool] = None
    authoritative_source: Optional[str] = None

class CaseResponse(BaseModel):
    id: int
    case_number: str
    inspection_id: int
    product_id: Optional[int]
    batch_id: Optional[int]
    title: str
    priority: str
    status: str
    reason_codes: List[str] = []
    risk_assessment: str
    evidence_summary: str
    assigned_to_user_id: Optional[int]
    created_by_user_id: int
    resolution_details: Optional[str]
    is_confirmed_counterfeit: bool
    authoritative_source: Optional[str]
    created_at: datetime
    updated_at: datetime
    notes: List[CaseNoteResponse] = []

    class Config:
        from_attributes = True

