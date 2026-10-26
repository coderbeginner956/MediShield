from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.inspection import Inspection
from app.services.report_service import generate_inspection_pdf_report
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/reports", tags=["Inspection Reports"])

@router.get("/inspection/{inspection_id}")
def download_inspection_report(
    inspection_id: int,
    db: Session = Depends(get_db)
):
    """
    Generates and returns an official PDF inspection report.
    Includes full metadata, OCR results, reference comparison, and statutory disclaimers.
    """
    inspection = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection record not found.")

    pdf_filename = f"Report_{inspection.inspection_code}.pdf"
    output_path = settings.REPORTS_DIR / pdf_filename

    try:
        generate_inspection_pdf_report(inspection, output_path)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"PDF generation error: {str(e)}")

    log_audit_event(
        db=db,
        action="REPORT_DOWNLOADED",
        target_type="inspection",
        target_id=str(inspection.id),
        user_id=None,
        actor_name="Verified Inspector",
        details={"inspection_code": inspection.inspection_code, "filename": pdf_filename}
    )

    return FileResponse(
        path=str(output_path),
        filename=pdf_filename,
        media_type="application/pdf"
    )
