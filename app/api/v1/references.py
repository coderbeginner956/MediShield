from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.api.deps import get_db, get_current_user, require_role
from app.core.config import settings
from app.models.user import User
from app.models.product import Product
from app.models.reference import ReferenceImage
from app.models.inspection import Inspection
from app.schemas.reference import (
    ReferenceImageResponse,
    ReferenceImageUpdate,
    ReferenceCompareRequest,
    ReferenceCompareResponse
)
from app.utils.image_helpers import save_uploaded_image
from app.services.reference_comparison_service import compare_inspection_with_reference
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/references", tags=["Reference Library"])

@router.get("", response_model=List[ReferenceImageResponse])
def list_references(
    product_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Lists reference images with optional product and status filtering."""
    query = db.query(ReferenceImage)
    if product_id:
        query = query.filter(ReferenceImage.product_id == product_id)
    if status_filter:
        query = query.filter(ReferenceImage.status == status_filter)

    return query.order_by(ReferenceImage.created_at.desc()).all()

@router.post("", response_model=ReferenceImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_reference_image(
    product_id: int = Form(...),
    packaging_type: Optional[str] = Form("Blister Front"),
    source: Optional[str] = Form("Manufacturer Authorized Sample"),
    description: Optional[str] = Form(None),
    verification_notes: Optional[str] = Form(None),
    is_authoritative: bool = Form(True),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "reviewer"]))
):
    """Uploads and registers an approved or pending reference packaging image."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target product not found.")

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size exceeds 10MB limit.")

    try:
        saved_info = save_uploaded_image(file_bytes, settings.REFERENCE_DIR, prefix=f"ref_p{product_id}")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    relative_img_path = f"/storage/references/{saved_info['filename']}"

    ref_img = ReferenceImage(
        product_id=product_id,
        packaging_type=packaging_type,
        image_path=relative_img_path,
        source=source or "Authorized Sample",
        description=description,
        verification_notes=verification_notes,
        status="approved" if is_authoritative else "pending_review",
        is_authoritative=is_authoritative,
        is_demo=False,
        created_by_user_id=current_user.id
    )
    db.add(ref_img)
    db.commit()
    db.refresh(ref_img)

    log_audit_event(
        db=db,
        action="REFERENCE_IMAGE_UPLOADED",
        target_type="reference_image",
        target_id=str(ref_img.id),
        user_id=current_user.id,
        actor_name=current_user.full_name,
        details={"product_id": product_id, "source": ref_img.source}
    )

    return ref_img

@router.get("/{reference_id}", response_model=ReferenceImageResponse)
def get_reference(reference_id: int, db: Session = Depends(get_db)):
    """Retrieves single reference image record."""
    ref = db.query(ReferenceImage).filter(ReferenceImage.id == reference_id).first()
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference image not found.")
    return ref

@router.patch("/{reference_id}", response_model=ReferenceImageResponse)
def update_reference(
    reference_id: int,
    ref_update: ReferenceImageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "reviewer"]))
):
    """Updates status (e.g. approve or archive) or notes of a reference image."""
    ref = db.query(ReferenceImage).filter(ReferenceImage.id == reference_id).first()
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference image not found.")

    update_data = ref_update.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        setattr(ref, key, val)

    db.commit()
    db.refresh(ref)

    log_audit_event(
        db=db,
        action="REFERENCE_STATUS_UPDATED",
        target_type="reference_image",
        target_id=str(ref.id),
        user_id=current_user.id,
        actor_name=current_user.full_name,
        details=update_data
    )

    return ref

@router.post("/{reference_id}/compare", response_model=ReferenceCompareResponse)
def compare_with_inspection(
    reference_id: int,
    req: ReferenceCompareRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Executes pair-wise visual comparison between an inspection image and this reference."""
    ref = db.query(ReferenceImage).filter(ReferenceImage.id == reference_id).first()
    if not ref:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reference image not found.")

    inspection = db.query(Inspection).filter(Inspection.id == req.inspection_id).first()
    if not inspection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found.")

    # Resolve local file paths
    ref_abs = str(settings.STORAGE_DIR / ref.image_path.replace("/storage/", "").replace("/", "\\"))
    upload_abs = str(settings.STORAGE_DIR / inspection.original_image_path.replace("/storage/", "").replace("/", "\\"))

    result = compare_inspection_with_reference(
        uploaded_image_path=upload_abs,
        reference_image_path=ref_abs,
        output_dir=settings.ARTIFACT_DIR
    )

    # Update inspection record
    if result["comparison_possible"]:
        inspection.comparison_performed = True
        inspection.reference_image_id = ref.id
        inspection.comparison_score = result["similarity_score"]
        diff_path = result["difference_overlay_path"]
        if diff_path:
            diff_rel = f"/storage/artifacts/{Path(diff_path).name}"
            inspection.comparison_difference_path = diff_rel
            result["difference_overlay_url"] = diff_rel
        inspection.comparison_notes = result["notes"]
        db.commit()

    return {
        "comparison_possible": result["comparison_possible"],
        "reference_id": ref.id,
        "method_used": result["method_used"],
        "similarity_score": result["similarity_score"],
        "difference_overlay_url": result.get("difference_overlay_url"),
        "keypoint_matches_count": result["keypoint_matches_count"],
        "notes": result["notes"],
        "limitations": result["limitations"]
    }

