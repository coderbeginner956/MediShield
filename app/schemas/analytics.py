from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class MetricCardData(BaseModel):
    title: str
    value: Any
    change: Optional[str] = None
    status: str = "neutral" # neutral, positive, warning, negative
    description: Optional[str] = None

class DashboardSummaryResponse(BaseModel):
    total_inspections: int
    successful_analyses: int
    manual_reviews_required: int
    visual_anomalies_flagged: int
    expired_products_flagged: int
    active_recall_flags: int
    unresolved_cases: int
    model_availability: str
    demo_mode_active: bool

class TimeSeriesPoint(BaseModel):
    date: str
    inspections: int
    anomalies: int
    expired: int

class CategoryBreakdownItem(BaseModel):
    name: str
    value: int
    percentage: float

