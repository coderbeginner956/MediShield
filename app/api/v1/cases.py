import uuid
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user, require_role
from app.models.user import User
from app.models.inspection import Inspection
from app.models.case import InvestigationCase, CaseNote
from app.schemas.case import CaseCreate, CaseUpdate, CaseNoteCreate, CaseResponse, CaseNoteResponse
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/cases", tags=["Investigation Cases"])

def _format_case_dict(c: InvestigationCase) -> dict:
    return {
        "id": c.id,
        "case_number": c.case_number,
        "inspection_id": c.inspection_id,
        "product_id": c.product_id,
        "batch_id": c.batch_id,
        "title": c.title,
        "priority": c.priority,
        "status": c.status,
        "reason_codes": json.loads(c.reason_codes_json or "[]"),
        "risk_assessment": c.risk_assessment,
        "evidence_summary": c.evidence_summary,
        "assigned_to_user_id": c.assigned_to_user_id,
        "created_by_user_id": c.created_by_user_id,
        "resolution_details": c.resolution_details,
        "is_confirmed_counterfeit": c.is_confirmed_counterfeit,
        "authoritative_source": c.authoritative_source,
        "created_at": c.created_at,
        "updated_at": c.updated_at,
        "notes": [
            {
                "id": n.id,
                "case_id": n.case_id,
                "user_id": n.user_id,
                "author_name": n.user.full_name if n.user else "Investigator",
                "note_text": n.note_text,
                "created_at": n.created_at
            }
            for n in c.notes
        ]
    }

@router.get("", response_model=List[CaseResponse])
def list_cases(
    status_filter: Optional[str] = None,
    priority: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lists all active and resolved investigation cases."""
    query = db.query(InvestigationCase)
    if status_filter:
        query = query.filter(InvestigationCase.status == status_filter)
    if priority:
        query = query.filter(InvestigationCase.priority == priority)

    cases = query.order_by(InvestigationCase.created_at.desc()).all()
    return [_format_case_dict(c) for c in cases]

@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(
    case_in: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Escalates an inspection into an official investigation case."""
    inspection = db.query(Inspection).filter(Inspection.id == case_in.inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection record not found.")

    case_num = f"CAS-{uuid.uuid4().hex[:6].upper()}"

    # Build initial evidence summary from inspection
    evidence_parts = [
        f"Inspection: {inspection.inspection_code}",
        f"Risk Level: {inspection.risk_level.upper()} ({inspection.risk_score or 0}/100)",
        f"Risk Summary: {inspection.risk_summary or 'None'}"
    ]
    if inspection.prediction:
        evidence_parts.append(f"AI Model Output: {inspection.prediction.predicted_class} ({int((inspection.prediction.confidence or 0)*100)}%)")
    if inspection.ocr_result:
        evidence_parts.append(f"Extracted Product: {inspection.ocr_result.detected_product_name or 'N/A'}, Batch: {inspection.ocr_result.detected_batch_number or 'N/A'}")
    if inspection.verification_result:
        evidence_parts.append(f"Verification: {inspection.verification_result.summary_text}")

    evidence_summary = " | ".join(evidence_parts)

    case = InvestigationCase(
        case_number=case_num,
        inspection_id=inspection.id,
        product_id=inspection.product_id,
        batch_id=inspection.batch_id,
        title=case_in.title,
        priority=case_in.priority or "medium",
        status="new",
        reason_codes_json=inspection.reason_codes_json or "[]",
        risk_assessment=inspection.risk_summary or "Escalated for manual review",
        evidence_summary=evidence_summary,
        created_by_user_id=current_user.id
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    # Add initial note if provided
    if case_in.notes:
        note = CaseNote(
            case_id=case.id,
            user_id=current_user.id,
            note_text=case_in.notes
        )
        db.add(note)
        db.commit()
        db.refresh(case)

    log_audit_event(
        db=db,
        action="INVESTIGATION_CASE_OPENED",
        target_type="case",
        target_id=str(case.id),
        user_id=current_user.id,
        actor_name=current_user.full_name,
        details={"case_number": case.case_number, "priority": case.priority}
    )

    return _format_case_dict(case)

@router.get("/{case_id}", response_model=CaseResponse)
def get_case_detail(case_id: int, db: Session = Depends(get_db)):
    """Retrieves single investigation case with full evidence ledger and notes."""
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation case not found.")
    return _format_case_dict(case)

@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(
    case_id: int,
    case_update: CaseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "reviewer"]))
):
    """
    Updates case status, assignment, or marks confirmed counterfeit
    (REQUIRES documented authoritative source).
    """
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation case not found.")

    update_data = case_update.model_dump(exclude_unset=True)

    # Enforce strict policy: Confirmed counterfeit requires documented authoritative source!
    if update_data.get("is_confirmed_counterfeit") is True:
        auth_src = update_data.get("authoritative_source") or case.authoritative_source
        if not auth_src or len(auth_src.strip()) < 5:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A confirmed counterfeit finding requires an explicitly documented authoritative source (e.g. Laboratory Assay Report, Manufacturer Certificate of Forgery, or Regulatory Seizure Notice)."
            )

    for key, val in update_data.items():
        setattr(case, key, val)

    db.commit()
    db.refresh(case)

    log_audit_event(
        db=db,
        action="CASE_STATUS_UPDATED",
        target_type="case",
        target_id=str(case.id),
        user_id=current_user.id,
        actor_name=current_user.full_name,
        details=update_data
    )

    return _format_case_dict(case)

@router.post("/{case_id}/notes", response_model=CaseNoteResponse, status_code=status.HTTP_201_CREATED)
def add_case_note(
    case_id: int,
    note_in: CaseNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Appends an investigative note to a case."""
    case = db.query(InvestigationCase).filter(InvestigationCase.id == case_id).first()
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    note = CaseNote(
        case_id=case.id,
        user_id=current_user.id,
        note_text=note_in.note_text
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return {
        "id": note.id,
        "case_id": note.case_id,
        "user_id": note.user_id,
        "author_name": current_user.full_name,
        "note_text": note.note_text,
        "created_at": note.created_at
    }

