from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.deps import get_db
from app.core.config import settings
from app.models.inspection import Inspection, ModelPrediction, OCRResult, VerificationResult
from app.models.case import InvestigationCase
from app.models.recall import Recall
from app.schemas.analytics import DashboardSummaryResponse, TimeSeriesPoint, CategoryBreakdownItem

router = APIRouter(prefix="/analytics", tags=["Analytics & Risk Intelligence"])

@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    include_demo: bool = Query(True, description="Whether to include synthetic demo records"),
    db: Session = Depends(get_db)
):
    """
    Calculates operational and clinical risk KPI metrics directly from database records.
    Separates demo records dynamically based on query parameter.
    """
    insp_query = db.query(Inspection)
    case_query = db.query(InvestigationCase)
    recall_query = db.query(Recall)

    if not include_demo:
        insp_query = insp_query.filter(Inspection.is_demo == False)
        recall_query = recall_query.filter(Recall.is_demo == False)

    total_inspections = insp_query.count()
    successful_analyses = insp_query.filter(Inspection.status.in_(["completed", "manual_review_recommended"])).count()
    manual_reviews_required = insp_query.filter(Inspection.status == "manual_review_recommended").count()
    visual_anomalies_flagged = insp_query.filter(Inspection.risk_level.in_(["medium", "high"])).count()

    # Expired flags
    expired_count = db.query(OCRResult).join(Inspection).filter(
        OCRResult.expiry_status == "expired"
    )
    if not include_demo:
        expired_count = expired_count.filter(Inspection.is_demo == False)
    expired_products_flagged = expired_count.count()

    # Active recall flags
    active_recall_flags = recall_query.filter(Recall.status == "active").count()

    # Unresolved cases
    unresolved_cases = case_query.filter(
        InvestigationCase.status.in_(["new", "under_review", "awaiting_information", "escalated"])
    ).count()

    return {
        "total_inspections": total_inspections,
        "successful_analyses": successful_analyses,
        "manual_reviews_required": manual_reviews_required,
        "visual_anomalies_flagged": visual_anomalies_flagged,
        "expired_products_flagged": expired_products_flagged,
        "active_recall_flags": active_recall_flags,
        "unresolved_cases": unresolved_cases,
        "model_availability": "Online" if settings.MODEL_PROVIDER != "unavailable" else "Offline",
        "demo_mode_active": settings.MODEL_PROVIDER == "demo" or settings.ENABLE_DEMO_DATA
    }

@router.get("/by-date", response_model=List[TimeSeriesPoint])
def get_inspections_by_date(
    days: int = Query(7, ge=1, le=90),
    include_demo: bool = True,
    db: Session = Depends(get_db)
):
    """Returns daily inspection volume and anomaly trends for charting."""
    now = datetime.now(timezone.utc)
    results = []

    for i in range(days - 1, -1, -1):
        day_start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        day_str = day_start.strftime("%b %d")

        query = db.query(Inspection).filter(
            Inspection.created_at >= day_start,
            Inspection.created_at < day_end
        )
        if not include_demo:
            query = query.filter(Inspection.is_demo == False)

        day_total = query.count()
        day_anomalies = query.filter(Inspection.risk_level.in_(["medium", "high"])).count()
        
        # Expired check
        day_expired = db.query(OCRResult).join(Inspection).filter(
            Inspection.created_at >= day_start,
            Inspection.created_at < day_end,
            OCRResult.expiry_status == "expired"
        )
        if not include_demo:
            day_expired = day_expired.filter(Inspection.is_demo == False)

        results.append({
            "date": day_str,
            "inspections": day_total,
            "anomalies": day_anomalies,
            "expired": day_expired.count()
        })

    return results

@router.get("/by-category", response_model=List[CategoryBreakdownItem])
def get_outcomes_by_category(include_demo: bool = True, db: Session = Depends(get_db)):
    """Returns distribution of risk levels across historical inspections."""
    query = db.query(Inspection)
    if not include_demo:
        query = query.filter(Inspection.is_demo == False)

    total = max(1, query.count())
    levels = ["low", "medium", "high", "insufficient_evidence"]
    breakdown = []

    label_map = {
        "low": "Clean / Baseline (Low Risk)",
        "medium": "Flagged for Secondary Review (Medium)",
        "high": "Critical Risk / Discrepancies (High)",
        "insufficient_evidence": "Inconclusive / Insufficient Evidence"
    }

    for lvl in levels:
        cnt = query.filter(Inspection.risk_level == lvl).count()
        breakdown.append({
            "name": label_map[lvl],
            "value": cnt,
            "percentage": round((cnt / total) * 100, 1)
        })

    return breakdown

@router.get("/cases")
def get_case_status_distribution(db: Session = Depends(get_db)):
    """Returns breakdown of investigation cases by status and priority."""
    statuses = ["new", "under_review", "awaiting_information", "escalated", "resolved", "closed"]
    status_counts = {}
    for st in statuses:
        status_counts[st] = db.query(InvestigationCase).filter(InvestigationCase.status == st).count()

    priorities = ["low", "medium", "high", "critical"]
    priority_counts = {}
    for pr in priorities:
        priority_counts[pr] = db.query(InvestigationCase).filter(InvestigationCase.priority == pr).count()

    confirmed_counterfeit_count = db.query(InvestigationCase).filter(
        InvestigationCase.is_confirmed_counterfeit == True
    ).count()

    return {
        "status_distribution": status_counts,
        "priority_distribution": priority_counts,
        "confirmed_counterfeit_count": confirmed_counterfeit_count
    }

