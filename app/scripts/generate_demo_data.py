import os
import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password
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
from app.models.recall import Recall
from app.models.case import InvestigationCase, CaseNote
from app.models.audit import AuditLog

def create_sample_packaging_image(
    output_path: Path,
    title: str,
    manufacturer: str,
    batch_no: str,
    exp_date: str,
    accent_color=(30, 80, 160),
    is_counterfeit: bool = False
):
    """Generates a realistic synthetic pharmaceutical blister / box packaging mockup image."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 700, 500
    img = Image.new("RGB", (width, height), color=(248, 250, 252))
    draw = ImageDraw.Draw(img)

    # Packaging outer border / card styling
    draw.rectangle([15, 15, width - 15, height - 15], outline=(200, 210, 225), width=2)
    
    # Brand header banner
    banner_color = (180, 40, 40) if is_counterfeit and "defect" in title.lower() else accent_color
    draw.rectangle([15, 15, width - 15, 95], fill=banner_color)

    # Banner text
    draw.text((35, 30), "PHARMACEUTICAL SPECIMEN - CLINICAL SCREENING", fill=(255, 255, 255))
    draw.text((35, 52), f"Rx Only | {manufacturer.upper()}", fill=(210, 230, 255))

    # Security Hologram Mockup
    holo_color = (200, 180, 60) if not is_counterfeit else (160, 160, 160)
    draw.rectangle([width - 120, 30, width - 35, 80], fill=holo_color, outline=(255, 255, 255), width=2)
    draw.text((width - 110, 48), "SECURE" if not is_counterfeit else "FAUX", fill=(20, 20, 20))

    # Product Title
    draw.text((40, 130), title.upper(), fill=(15, 25, 45))
    draw.line([40, 165, 350, 165], fill=accent_color, width=3)

    # Dosage / Description
    draw.text((40, 185), "Active Ingredient: Standard Compendial Grade", fill=(80, 95, 115))
    draw.text((40, 210), "Store below 25°C. Keep out of reach of children.", fill=(100, 115, 130))

    # Printed Batch & Expiry Area (Dot-matrix style box)
    draw.rectangle([40, 260, 450, 370], fill=(235, 240, 248), outline=(180, 195, 215), width=1)
    draw.text((55, 275), "VARIABLE DATA PRINT AREA (LASER ETCHED):", fill=(50, 65, 85))
    draw.text((55, 300), f"B.No / LOT : {batch_no}", fill=(10, 20, 30))
    draw.text((55, 325), f"MFG. DATE  : 03/2024", fill=(10, 20, 30))
    draw.text((55, 345), f"EXP. DATE  : {exp_date}", fill=(180, 20, 20) if "2024" in exp_date or "SMEARED" in exp_date else (10, 20, 30))

    # Mock Barcode / DataMatrix
    draw.rectangle([width - 180, 260, width - 40, 420], fill=(255, 255, 255), outline=(180, 195, 215))
    for x in range(width - 165, width - 55, 6):
        draw.line([x, 280, x, 390], fill=(20, 30, 40), width=2)
    draw.text((width - 170, 400), "GTIN-089421", fill=(60, 75, 95))

    # Watermark indicator
    draw.text((40, 440), "[DEMO SYNTHETIC SPECIMEN - FOR EDUCATIONAL SCREENING ONLY]", fill=(160, 175, 190))

    img.save(str(output_path), quality=95)
    return str(output_path)

def seed_database_if_empty(db: Session):
    """Populates database with initial users, products, batches, reference images, recalls, and inspections."""
    if db.query(User).count() > 0:
        return # Already seeded

    print("[MediShield AI] Seeding initial database with synthetic demo records...")

    # 1. Create Default Users (Admin, Inspector, Reviewer)
    admin_user = User(
        email="admin@medishield.ai",
        hashed_password=hash_password("admin123"),
        full_name="Dr. Eleanor Vance (Administrator)",
        role="admin",
        is_active=True
    )
    inspector_user = User(
        email="inspector@medishield.ai",
        hashed_password=hash_password("inspector123"),
        full_name="Juee (Field Inspector)",
        role="inspector",
        is_active=True
    )
    reviewer_user = User(
        email="reviewer@medishield.ai",
        hashed_password=hash_password("reviewer123"),
        full_name="Priti (QA Reviewer)",
        role="reviewer",
        is_active=True
    )
    db.add_all([admin_user, inspector_user, reviewer_user])
    db.commit()

    # 2. Create Products
    p1 = Product(
        name="Amoxicillin 500mg Capsules",
        brand_or_manufacturer="Novapharm Labs Ltd.",
        dosage_form="Capsule",
        packaging_type="Blister Pack",
        product_identifier="NDC-54868-0112",
        description="Broad-spectrum aminopenicillin antibiotic prescribed for bacterial infections.",
        record_status="active",
        is_demo=True,
        notes="Synthetic test product for blister packaging verification."
    )
    p2 = Product(
        name="Paracetamol Extra 500mg/65mg",
        brand_or_manufacturer="Zenith Healthcare",
        dosage_form="Tablet",
        packaging_type="Blister Pack",
        product_identifier="NDC-42192-3341",
        description="Analgesic and antipyretic formulation with caffeine enhancer.",
        record_status="active",
        is_demo=True,
        notes="Used for testing expired date detection."
    )
    p3 = Product(
        name="Augmentin 625mg Duo",
        brand_or_manufacturer="GlaxoSmithKline",
        dosage_form="Tablet",
        packaging_type="Box",
        product_identifier="NDC-00029-6086",
        description="Co-amoxiclav formulation with potassium clavulanate.",
        record_status="active",
        is_demo=True,
        notes="Target product for suspected packaging typo anomalies."
    )
    p4 = Product(
        name="Cetirizine Hydrochloride 10mg",
        brand_or_manufacturer="Apex Pharmaceuticals Inc.",
        dosage_form="Tablet",
        packaging_type="Bottle",
        product_identifier="NDC-65862-201-10",
        description="Second-generation antihistamine used in allergic rhinitis.",
        record_status="active",
        is_demo=True,
        notes="Clean baseline reference product."
    )
    db.add_all([p1, p2, p3, p4])
    db.commit()

    # 3. Create Batches
    now = datetime.now(timezone.utc)
    b1 = ProductBatch(
        product_id=p1.id,
        batch_number="AMX-89421",
        manufacturer=p1.brand_or_manufacturer,
        manufacturing_date=now - timedelta(days=200),
        expiry_date=now + timedelta(days=400),
        recall_status="none",
        is_demo=True,
        reference_source="Internal Batch Registry"
    )
    b2 = ProductBatch(
        product_id=p2.id,
        batch_number="PAR-44109",
        manufacturer=p2.brand_or_manufacturer,
        manufacturing_date=now - timedelta(days=700),
        expiry_date=now - timedelta(days=60), # Expired batch!
        recall_status="none",
        is_demo=True,
        reference_source="Zenith Quality Release Ledger"
    )
    b3 = ProductBatch(
        product_id=p3.id,
        batch_number="AUG-99482",
        manufacturer=p3.brand_or_manufacturer,
        manufacturing_date=now - timedelta(days=150),
        expiry_date=now + timedelta(days=350),
        recall_status="recalled", # Recalled batch!
        is_demo=True,
        reference_source="GSK Global Distribution Registry"
    )
    db.add_all([b1, b2, b3])
    db.commit()

    # 4. Create Approved Reference Images
    ref_img1 = settings.REFERENCE_DIR / "ref_amoxicillin_blister.jpg"
    create_sample_packaging_image(
        ref_img1,
        title="Amoxicillin 500mg Capsules",
        manufacturer="Novapharm Labs Ltd.",
        batch_no="AMX-89421",
        exp_date="02/2027",
        accent_color=(20, 90, 160),
        is_counterfeit=False
    )
    r1 = ReferenceImage(
        product_id=p1.id,
        packaging_type="Blister Front",
        image_path=f"/storage/references/{ref_img1.name}",
        source="Authorized Manufacturer Archive",
        description="Official high-resolution reference packaging for 500mg blister cards.",
        verification_notes="Verified against manufacturer CAD packaging master template v4.",
        status="approved",
        is_authoritative=True,
        is_demo=True,
        created_by_user_id=admin_user.id
    )

    ref_img2 = settings.REFERENCE_DIR / "ref_paracetamol_box.jpg"
    create_sample_packaging_image(
        ref_img2,
        title="Paracetamol Extra 500mg",
        manufacturer="Zenith Healthcare",
        batch_no="PAR-44109",
        exp_date="12/2024",
        accent_color=(30, 140, 110),
        is_counterfeit=False
    )
    r2 = ReferenceImage(
        product_id=p2.id,
        packaging_type="Blister Pack",
        image_path=f"/storage/references/{ref_img2.name}",
        source="Regulatory Submission Specimen",
        description="Approved blister seal and font template.",
        status="approved",
        is_authoritative=True,
        is_demo=True,
        created_by_user_id=admin_user.id
    )
    db.add_all([r1, r2])
    db.commit()

    # 5. Create Recalls
    rec1 = Recall(
        recall_code="REC-2026-081",
        product_id=p3.id,
        batch_id=b3.id,
        title="Voluntary Recall: Packaging Seal Defect on Batch AUG-99482",
        reason="Manufacturer flagged potential seal micro-pinholes compromising atmospheric barrier in tropical climates.",
        source="Synthetic Demonstration Notice (Simulated Regulatory Alert)",
        effective_date=now - timedelta(days=25),
        status="active",
        severity="class_i",
        is_demo=True,
        created_by="Administrator"
    )
    db.add(rec1)
    db.commit()

    # 6. Create Seed Inspections (1 Clean, 1 Expired, 1 Visual Anomaly / Counterfeit Risk)
    insp1_img = settings.UPLOAD_DIR / "sample_amoxicillin_genuine.jpg"
    create_sample_packaging_image(
        insp1_img,
        title="Amoxicillin 500mg Capsules",
        manufacturer="Novapharm Labs Ltd.",
        batch_no="AMX-89421",
        exp_date="02/2027",
        accent_color=(20, 90, 160),
        is_counterfeit=False
    )
    insp1 = Inspection(
        inspection_code="INS-AMX-001",
        user_id=inspector_user.id,
        product_id=p1.id,
        batch_id=b1.id,
        reference_image_id=r1.id,
        original_image_path=f"/storage/uploads/{insp1_img.name}",
        image_width=700,
        image_height=500,
        file_size_bytes=48200,
        status="completed",
        model_provider="demo",
        processing_time_ms=64.2,
        is_demo=True,
        risk_level="low",
        risk_score=8.0,
        risk_summary="Low screening risk. Clean packaging baseline, valid batch ledger match, and verified expiry date.",
        reason_codes_json=json.dumps([]),
        comparison_performed=True,
        comparison_score=0.92,
        comparison_notes="ORB structural keypoint alignment confirmed 92% visual correlation with approved reference."
    )
    db.add(insp1)
    db.commit()

    pred1 = ModelPrediction(
        inspection_id=insp1.id,
        model_name="MediShield-DemoVision-v1.0",
        task_type="classification",
        predicted_class="No visual anomaly detected",
        confidence=0.92,
        raw_probabilities_json=json.dumps({"No visual anomaly detected": 0.92, "Visual anomaly flagged": 0.08}),
        detected_boxes_json=json.dumps([{"label": "Approved Packaging Typography", "confidence": 0.94, "box": [40, 130, 400, 150]}]),
        is_demo=True,
        explanation_note="Synthetic demo prediction. Not a calibrated clinical authenticity guarantee."
    )
    ocr1 = OCRResult(
        inspection_id=insp1.id,
        raw_text="AMOXICILLIN 500mg CAPSULES BP\nNovapharm Labs Ltd.\nBatch: AMX-89421\nExp: 02/2027",
        detected_product_name="Amoxicillin 500mg Capsules",
        detected_manufacturer="Novapharm Labs Ltd.",
        detected_batch_number="AMX-89421",
        detected_expiry_date="02/2027",
        expiry_status="not_expired",
        parsed_expiry_iso=datetime(2027, 2, 1),
        label_flags_json=json.dumps([])
    )
    verif1 = VerificationResult(
        inspection_id=insp1.id,
        product_match_status="matched",
        batch_match_status="matched",
        expiry_match_status="valid",
        recall_status="none",
        verification_source="Local Registry",
        summary_text="Confirmed in internal product and batch ledger."
    )
    db.add_all([pred1, ocr1, verif1])
    db.commit()

    # Inspection 2: Suspected Counterfeit / Typo Flaw
    insp2_img = settings.UPLOAD_DIR / "sample_augmentin_counterfeit.jpg"
    create_sample_packaging_image(
        insp2_img,
        title="Augmentin 625mg Duo",
        manufacturer="GlaxoSimthKllne", # Altered typography
        batch_no="99482",
        exp_date="SMEARED",
        accent_color=(180, 40, 40),
        is_counterfeit=True
    )
    insp2 = Inspection(
        inspection_code="INS-AUG-002",
        user_id=inspector_user.id,
        product_id=p3.id,
        batch_id=b3.id,
        original_image_path=f"/storage/uploads/{insp2_img.name}",
        image_width=700,
        image_height=500,
        file_size_bytes=51100,
        status="manual_review_recommended",
        model_provider="demo",
        processing_time_ms=88.5,
        is_demo=True,
        risk_level="high",
        risk_score=85.0,
        risk_summary="High risk detected. Visual typography discrepancies, active recall on batch, and unreadable expiry date.",
        reason_codes_json=json.dumps([
            "RC_ACTIVE_PRODUCT_RECALL",
            "RC_VISUAL_ANOMALY_FLAGGED",
            "RC_SUSPICIOUS_BRAND_TYPOGRAPHY",
            "RC_UNREADABLE_EXPIRY_INFO"
        ])
    )
    db.add(insp2)
    db.commit()

    pred2 = ModelPrediction(
        inspection_id=insp2.id,
        model_name="MediShield-DemoVision-v1.0",
        task_type="classification",
        predicted_class="Visual anomaly flagged",
        confidence=0.88,
        raw_probabilities_json=json.dumps({"Visual anomaly flagged": 0.88, "No visual anomaly detected": 0.12}),
        detected_boxes_json=json.dumps([{"label": "Typography Kerning Anomaly", "confidence": 0.89, "box": [35, 52, 350, 40]}]),
        is_demo=True,
        explanation_note="Synthetic demo prediction flagging manufacturer name irregularity."
    )
    ocr2 = OCRResult(
        inspection_id=insp2.id,
        raw_text="AUGMENTIN 625mg DUO\nGlaxoSimthKllne\nLot: 99482\nExp: SMEARED",
        detected_product_name="Augmentin 625mg Duo",
        detected_manufacturer="GlaxoSimthKllne",
        detected_batch_number="99482",
        detected_expiry_date="SMEARED",
        expiry_status="unreadable",
        label_flags_json=json.dumps(["FLAG_UNREADABLE_EXPIRY", "FLAG_SUSPICIOUS_MANUFACTURER_TYPO"])
    )
    verif2 = VerificationResult(
        inspection_id=insp2.id,
        product_match_status="mismatch",
        batch_match_status="matched",
        expiry_match_status="unknown",
        recall_status="active_recall_flagged",
        verification_source="Local Registry",
        summary_text="Batch AUG-99482 is linked to ACTIVE RECALL notice REC-2026-081."
    )
    db.add_all([pred2, ocr2, verif2])
    db.commit()

    # 7. Create Seed Investigation Case for the suspicious inspection
    c1 = InvestigationCase(
        case_number="CAS-00912",
        inspection_id=insp2.id,
        product_id=p3.id,
        batch_id=b3.id,
        title="Suspected Counterfeit Packaging & Active Recall: Augmentin Batch 99482",
        priority="critical",
        status="under_review",
        reason_codes_json=insp2.reason_codes_json,
        risk_assessment=insp2.risk_summary,
        evidence_summary="Inspection INS-AUG-002 flagged for active recall REC-2026-081 and visual typo on packaging 'GlaxoSimthKllne'.",
        assigned_to_user_id=reviewer_user.id,
        created_by_user_id=inspector_user.id,
        is_confirmed_counterfeit=False
    )
    db.add(c1)
    db.commit()

    note1 = CaseNote(
        case_id=c1.id,
        user_id=inspector_user.id,
        note_text="Field inspection uploaded from pharmacy retail audit. Packaging text has observable typo in manufacturer name."
    )
    db.add(note1)
    db.commit()

    # 8. Create Audit Logs
    log1 = AuditLog(
        user_id=admin_user.id,
        actor_name=admin_user.full_name,
        action="DATABASE_INITIALIZED",
        target_type="system",
        target_id="0",
        details_json=json.dumps({"demo_mode": True, "seeded_products": 4}),
        outcome="success",
        timestamp=now - timedelta(hours=2)
    )
    db.add(log1)
    db.commit()

    print("[MediShield AI] Synthetic demo data successfully seeded!")

if __name__ == "__main__":
    from app.core.database import SessionLocal, init_db
    init_db()
    db = SessionLocal()
    try:
        seed_database_if_empty(db)
    finally:
        db.close()

