import uuid
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.product import Product, ProductBatch
from app.models.reference import ReferenceImage
from app.models.inspection import (
    Inspection,
    ModelPrediction,
    ExplainabilityArtifact,
    OCRResult,
    VerificationResult
)
from app.schemas.inspection import (
    InspectionResponse,
    InspectionDetailResponse,
    OCRUpdateRequest
)
from app.utils.image_helpers import save_uploaded_image
from app.services.ml_service import analyze_medicine_image
from app.services.explainability_service import generate_visual_explanation
from app.services.reference_comparison_service import compare_inspection_with_reference
from app.services.ocr_service import perform_ocr_extraction, parse_and_validate_expiry, evaluate_label_flags
from app.services.verification_service import verify_extracted_records
from app.services.risk_assessment_service import compute_multi_factor_risk
from app.services.audit_service import log_audit_event

router = APIRouter(prefix="/inspections", tags=["Inspections"])

def _to_response_dict(insp: Inspection) -> dict:
    """Helper to convert Inspection DB model into full response schema dict."""
    reason_codes = json.loads(insp.reason_codes_json or "[]")
    
    # Prediction
    pred_data = None
    if insp.prediction:
        p = insp.prediction
        pred_data = {
            "id": p.id,
            "model_name": p.model_name,
            "task_type": p.task_type,
            "predicted_class": p.predicted_class,
            "confidence": p.confidence,
            "raw_probabilities": json.loads(p.raw_probabilities_json or "{}"),
            "detected_boxes": json.loads(p.detected_boxes_json or "[]"),
            "is_demo": p.is_demo,
            "explanation_note": p.explanation_note
        }

    # Explainability
    explain_data = None
    if insp.explainability:
        e = insp.explainability
        explain_data = {
            "id": e.id,
            "method": e.method,
            "artifact_image_url": e.artifact_image_path,
            "explanation_text": e.explanation_text,
            "limitations_text": e.limitations_text,
            "is_supported": e.is_supported
        }

    # OCR
    ocr_data = None
    if insp.ocr_result:
        o = insp.ocr_result
        ocr_data = {
            "id": o.id,
            "raw_text": o.raw_text,
            "detected_product_name": o.detected_product_name,
            "detected_manufacturer": o.detected_manufacturer,
            "detected_batch_number": o.detected_batch_number,
            "detected_mfg_date": o.detected_mfg_date,
            "detected_expiry_date": o.detected_expiry_date,
            "detected_registration_id": o.detected_registration_id,
            "expiry_status": o.expiry_status,
            "parsed_expiry_iso": o.parsed_expiry_iso,
            "label_flags": json.loads(o.label_flags_json or "[]"),
            "confidence_scores": json.loads(o.confidence_scores_json or "{}"),
            "is_edited": o.is_edited,
            "edited_fields": json.loads(o.edited_fields_json or "{}")
        }

    # Verification
    verif_data = None
    if insp.verification_result:
        v = insp.verification_result
        verif_data = {
            "id": v.id,
            "product_match_status": v.product_match_status,
            "batch_match_status": v.batch_match_status,
            "expiry_match_status": v.expiry_match_status,
            "recall_status": v.recall_status,
            "verification_source": v.verification_source,
            "summary_text": v.summary_text
        }

    return {
        "id": insp.id,
        "inspection_code": insp.inspection_code,
        "user_id": insp.user_id,
        "product_id": insp.product_id,
        "batch_id": insp.batch_id,
        "reference_image_id": insp.reference_image_id,
        "original_image_url": insp.original_image_path,
        "image_width": insp.image_width,
        "image_height": insp.image_height,
        "file_size_bytes": insp.file_size_bytes,
        "status": insp.status,
        "model_provider": insp.model_provider,
        "processing_time_ms": insp.processing_time_ms,
        "is_demo": insp.is_demo,
        "risk_level": insp.risk_level,
        "risk_score": insp.risk_score,
        "risk_summary": insp.risk_summary,
        "reason_codes": reason_codes,
        "comparison_performed": insp.comparison_performed,
        "comparison_score": insp.comparison_score,
        "comparison_difference_url": insp.comparison_difference_path,
        "comparison_notes": insp.comparison_notes,
        "created_at": insp.created_at,
        "updated_at": insp.updated_at,
        "prediction": pred_data,
        "explainability": explain_data,
        "ocr_result": ocr_data,
        "verification_result": verif_data
    }

@router.post("", response_model=InspectionDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_inspection(
    product_id: Optional[int] = Form(None),
    batch_id: Optional[int] = Form(None),
    reference_image_id: Optional[int] = Form(None),
    auto_analyze: bool = Form(True),
    condition: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Accepts uploaded medicine packaging image, performs validation,
    creates inspection record, and optionally triggers full screening pipeline.
    """
    file_bytes = await file.read()
    if len(file_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File size exceeds 15MB limit.")

    try:
        saved_info = save_uploaded_image(file_bytes, settings.UPLOAD_DIR, prefix="insp")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    inspection_code = f"INS-{uuid.uuid4().hex[:8].upper()}"
    relative_img_path = f"/storage/uploads/{saved_info['filename']}"

    insp = Inspection(
        inspection_code=inspection_code,
        user_id=current_user.id,
        product_id=product_id,
        batch_id=batch_id,
        reference_image_id=reference_image_id,
        original_image_path=relative_img_path,
        image_width=saved_info["width"],
        image_height=saved_info["height"],
        file_size_bytes=saved_info["size_bytes"],
        mime_type=saved_info["mime_type"],
        status="pending",
        model_provider=settings.MODEL_PROVIDER,
        is_demo=settings.MODEL_PROVIDER == "demo"
    )
    db.add(insp)
    db.commit()
    db.refresh(insp)

    log_audit_event(
        db=db,
        action="INSPECTION_CREATED",
        target_type="inspection",
        target_id=str(insp.id),
        user_id=current_user.id,
        actor_name=current_user.full_name,
        details={"code": inspection_code, "filesize": insp.file_size_bytes}
    )

    if auto_analyze:
        _execute_full_inspection_pipeline(db, insp, file_bytes, saved_info["filepath"], original_filename=file.filename or "", condition=condition)

    db.refresh(insp)
    return _to_response_dict(insp)

def _execute_full_inspection_pipeline(db: Session, insp: Inspection, file_bytes: bytes, abs_image_path: str, original_filename: str = "", condition: Optional[str] = None):
    """Executes AI screening, Explainability, Reference Comparison, OCR, and Multi-factor Risk Synthesis."""
    eval_filename = f"{original_filename} {Path(abs_image_path).name}".strip()

    # 1. AI Visual Screening
    analysis = analyze_medicine_image(image_bytes=file_bytes, filename=eval_filename, condition=condition)
    pred = ModelPrediction(
        inspection_id=insp.id,
        model_name=analysis["model_name"],
        task_type=analysis["task_type"],
        predicted_class=analysis["predicted_class"],
        confidence=analysis["confidence"],
        raw_probabilities_json=json.dumps(analysis.get("raw_probabilities", {})),
        detected_boxes_json=json.dumps(analysis.get("detected_boxes", [])),
        is_demo=analysis.get("is_demo", False),
        explanation_note=analysis.get("explanation_note")
    )
    db.add(pred)
    insp.processing_time_ms = analysis.get("processing_time_ms", 0.0)

    # 2. Explainability Artifact
    explain_res = generate_visual_explanation(
        image_path=abs_image_path,
        prediction_info=analysis,
        output_dir=settings.ARTIFACT_DIR
    )
    artifact_rel = f"/storage/artifacts/{Path(explain_res['artifact_image_path']).name}" if explain_res.get("artifact_image_path") else None
    explain = ExplainabilityArtifact(
        inspection_id=insp.id,
        method=explain_res["method"],
        artifact_image_path=artifact_rel,
        explanation_text=explain_res["explanation_text"],
        limitations_text=explain_res["limitations_text"],
        is_supported=explain_res["is_supported"]
    )
    db.add(explain)

    # 3. OCR Label Inspection
    ocr_res = perform_ocr_extraction(abs_image_path, provider=settings.OCR_PROVIDER, original_filename=eval_filename, condition=condition)
    ocr = OCRResult(
        inspection_id=insp.id,
        raw_text=ocr_res["raw_text"],
        detected_product_name=ocr_res["detected_product_name"],
        detected_manufacturer=ocr_res["detected_manufacturer"],
        detected_batch_number=ocr_res["detected_batch_number"],
        detected_mfg_date=ocr_res["detected_mfg_date"],
        detected_expiry_date=ocr_res["detected_expiry_date"],
        detected_registration_id=ocr_res["detected_registration_id"],
        expiry_status=ocr_res["expiry_status"],
        parsed_expiry_iso=ocr_res["parsed_expiry_iso"],
        label_flags_json=json.dumps(ocr_res["label_flags"]),
        confidence_scores_json=json.dumps(ocr_res["confidence_scores"]),
        is_edited=False
    )
    db.add(ocr)

    # 4. Database Record & Recall Verification
    verif_res = verify_extracted_records(
        db=db,
        product_name=ocr_res["detected_product_name"],
        manufacturer=ocr_res["detected_manufacturer"],
        batch_number=ocr_res["detected_batch_number"],
        expiry_date=ocr_res["detected_expiry_date"],
        selected_product_id=insp.product_id,
        selected_batch_id=insp.batch_id
    )
    verif = VerificationResult(
        inspection_id=insp.id,
        product_match_status=verif_res["product_match_status"],
        batch_match_status=verif_res["batch_match_status"],
        expiry_match_status=verif_res["expiry_match_status"],
        recall_status=verif_res["recall_status"],
        verification_source=verif_res["verification_source"],
        summary_text=verif_res["summary_text"]
    )
    db.add(verif)

    if verif_res.get("matched_product_id") and not insp.product_id:
        insp.product_id = verif_res["matched_product_id"]
    if verif_res.get("matched_batch_id") and not insp.batch_id:
        insp.batch_id = verif_res["matched_batch_id"]

    # 5. Optional Reference Comparison if reference is linked or found for product
    comp_summary = None
    ref = None
    if insp.reference_image_id:
        ref = db.query(ReferenceImage).filter(ReferenceImage.id == insp.reference_image_id).first()
    elif insp.product_id:
        ref = db.query(ReferenceImage).filter(
            ReferenceImage.product_id == insp.product_id,
            ReferenceImage.status == "approved"
        ).first()

    if ref:
        ref_abs = str(settings.STORAGE_DIR / ref.image_path.replace("/storage/", "").replace("/", "\\"))
        comp_res = compare_inspection_with_reference(
            uploaded_image_path=abs_image_path,
            reference_image_path=ref_abs,
            output_dir=settings.ARTIFACT_DIR
        )
        if comp_res["comparison_possible"]:
            insp.comparison_performed = True
            insp.reference_image_id = ref.id
            insp.comparison_score = comp_res["similarity_score"]
            if comp_res.get("difference_overlay_path"):
                insp.comparison_difference_path = f"/storage/artifacts/{Path(comp_res['difference_overlay_path']).name}"
            insp.comparison_notes = comp_res["notes"]
            comp_summary = comp_res

    # 6. Multi-Factor Risk Assessment Synthesis
    risk_data = compute_multi_factor_risk(
        model_prediction=analysis,
        comparison_result=comp_summary,
        ocr_result=ocr_res,
        verification_result=verif_res
    )
    insp.risk_level = risk_data["risk_level"]
    insp.risk_score = risk_data["risk_score"]
    insp.risk_summary = risk_data["risk_summary"]
    insp.reason_codes_json = json.dumps(risk_data["reason_codes"])

    # Determine final inspection status
    if insp.risk_level == "high":
        insp.status = "manual_review_recommended"
    else:
        insp.status = "completed"

    db.commit()

@router.get("", response_model=List[InspectionResponse])
def list_inspections(
    status_filter: Optional[str] = None,
    risk_level: Optional[str] = None,
    product_id: Optional[int] = None,
    include_demo: bool = True,
    db: Session = Depends(get_db)
):
    """Retrieves list of past inspections with filtering."""
    query = db.query(Inspection)
    if status_filter:
        query = query.filter(Inspection.status == status_filter)
    if risk_level:
        query = query.filter(Inspection.risk_level == risk_level)
    if product_id:
        query = query.filter(Inspection.product_id == product_id)
    if not include_demo:
        query = query.filter(Inspection.is_demo == False)

    inspections = query.order_by(Inspection.created_at.desc()).all()
    return [_to_response_dict(insp) for insp in inspections]

@router.get("/{inspection_id}", response_model=InspectionDetailResponse)
def get_inspection_detail(inspection_id: int, db: Session = Depends(get_db)):
    """Retrieves full inspection record with predictions, explainability, OCR, and verification results."""
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection not found.")
    return _to_response_dict(insp)

@router.patch("/{inspection_id}/ocr", response_model=InspectionDetailResponse)
def update_ocr_fields(
    inspection_id: int,
    ocr_update: OCRUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Allows user/reviewer to correct extracted OCR fields and re-evaluates verification and risk."""
    insp = db.query(Inspection).filter(Inspection.id == inspection_id).first()
    if not insp or not insp.ocr_result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inspection or OCR result not found.")

    ocr = insp.ocr_result
    edited_dict = json.loads(ocr.edited_fields_json or "{}")

    # Update fields if provided
    if ocr_update.product_name is not None:
        ocr.detected_product_name = ocr_update.product_name
        edited_dict["product_name"] = ocr_update.product_name
    if ocr_update.manufacturer is not None:
        ocr.detected_manufacturer = ocr_update.manufacturer
        edited_dict["manufacturer"] = ocr_update.manufacturer
    if ocr_update.batch_number is not None:
        ocr.detected_batch_number = ocr_update.batch_number
        edited_dict["batch_number"] = ocr_update.batch_number
    if ocr_update.expiry_date is not None:
        ocr.detected_expiry_date = ocr_update.expiry_date
        edited_dict["expiry_date"] = ocr_update.expiry_date
        parsed_dt, status_exp = parse_and_validate_expiry(ocr_update.expiry_date)
        ocr.parsed_expiry_iso = parsed_dt
        ocr.expiry_status = status_exp
    if ocr_update.registration_id is not None:
        ocr.detected_registration_id = ocr_update.registration_id
        edited_dict["registration_id"] = ocr_update.registration_id

    ocr.is_edited = True
    ocr.edited_fields_json = json.dumps(edited_dict)
    
    # Re-evaluate flags
    new_flags = evaluate_label_flags(
        ocr.detected_product_name,
        ocr.detected_manufacturer,
        ocr.detected_batch_number,
        ocr.detected_expiry_date,
        ocr.expiry_status
    )
    ocr.label_flags_json = json.dumps(new_flags)

    # Re-run verification against database
    verif_res = verify_extracted_records(
        db=db,
        product_name=ocr.detected_product_name,
        manufacturer=ocr.detected_manufacturer,
        batch_number=ocr.detected_batch_number,
        expiry_date=ocr.detected_expiry_date,
        selected_product_id=insp.product_id,
        selected_batch_id=insp.batch_id
    )

    if insp.verification_result:
        insp.verification_result.product_match_status = verif_res["product_match_status"]
        insp.verification_result.batch_match_status = verif_res["batch_match_status"]
        insp.verification_result.expiry_match_status = verif_res["expiry_match_status"]
        insp.verification_result.recall_status = verif_res["recall_status"]
        insp.verification_result.summary_text = verif_res["summary_text"]

    # Re-compute risk
    risk_data = compute_multi_factor_risk(
        model_prediction={"predicted_class": insp.prediction.predicted_class if insp.prediction else ""},
        comparison_result={"comparison_possible": insp.comparison_performed, "similarity_score": insp.comparison_score},
        ocr_result={"label_flags": new_flags},
        verification_result=verif_res
    )
    insp.risk_level = risk_data["risk_level"]
    insp.risk_score = risk_data["risk_score"]
    insp.risk_summary = risk_data["risk_summary"]
    insp.reason_codes_json = json.dumps(risk_data["reason_codes"])

    db.commit()
    db.refresh(insp)

    log_audit_event(
        db=db,
        action="OCR_FIELDS_CORRECTED",
        target_type="inspection",
        target_id=str(insp.id),
        user_id=current_user.id,
        actor_name=current_user.full_name,
        details=edited_dict
    )

    return _to_response_dict(insp)
