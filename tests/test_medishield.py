import io
import uuid
from PIL import Image
from app.services.ocr_service import parse_and_validate_expiry, evaluate_label_flags
from app.services.verification_service import verify_extracted_records
from app.core.database import SessionLocal

# ==================== Health & Diagnostics ====================

def test_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "MediShield AI" in data["service"]

def test_model_info_endpoint(client):
    res = client.get("/api/model/info")
    assert res.status_code == 200
    data = res.json()
    assert "provider" in data
    assert "capabilities" in data
    assert "disclaimer" in data

def test_model_metrics_endpoint(client):
    res = client.get("/api/model/metrics")
    assert res.status_code == 200
    data = res.json()
    assert data["hardware_profile"] == "CPU (Energy Efficient)"

# ==================== Auth & RBAC ====================

def test_login_success(client):
    res = client.post("/api/auth/login", json={"email": "admin@medishield.ai", "password": "admin123"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "admin"

def test_login_invalid_password(client):
    res = client.post("/api/auth/login", json={"email": "admin@medishield.ai", "password": "wrongpassword"})
    assert res.status_code == 401

def test_registration_and_me(client):
    unique_email = f"user_{uuid.uuid4().hex[:6]}@medishield.ai"
    res = client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "securepass123",
        "full_name": "Test Inspector",
        "role": "inspector"
    })
    assert res.status_code == 201
    
    login_res = client.post("/api/auth/login", json={"email": unique_email, "password": "securepass123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == unique_email

# ==================== Analytics ====================

def test_analytics_summary(client):
    res = client.get("/api/analytics/summary")
    assert res.status_code == 200
    data = res.json()
    assert "total_inspections" in data
    assert "visual_anomalies_flagged" in data
    assert data["total_inspections"] >= 2

def test_analytics_by_date(client):
    res = client.get("/api/analytics/by-date?days=7")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 7

def test_analytics_by_category(client):
    res = client.get("/api/analytics/by-category")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) == 4

# ==================== OCR & Rule Engine ====================

def test_parse_valid_future_date():
    dt, status = parse_and_validate_expiry("10/2030")
    assert status == "not_expired"
    assert dt is not None
    assert dt.year == 2030

def test_parse_expired_past_date():
    dt, status = parse_and_validate_expiry("01/2020")
    assert status == "expired"
    assert dt is not None
    assert dt.year == 2020

def test_parse_unreadable_date():
    dt, status = parse_and_validate_expiry("SMEARED")
    assert status == "unreadable"
    assert dt is None

def test_evaluate_label_flags():
    flags = evaluate_label_flags(
        name="Augmentin",
        mfr="GlaxoSimthKllne",
        batch=None,
        exp="SMEARED",
        expiry_status="unreadable"
    )
    assert "FLAG_MISSING_BATCH" in flags
    assert "FLAG_UNREADABLE_EXPIRY" in flags
    assert "FLAG_SUSPICIOUS_MANUFACTURER_TYPO" in flags

# ==================== Verification Ledger ====================

def test_verification_matched_batch():
    db = SessionLocal()
    try:
        res = verify_extracted_records(
            db=db,
            product_name="Amoxicillin 500mg Capsules",
            manufacturer="Novapharm Labs Ltd.",
            batch_number="AMX-89421",
            expiry_date="02/2027"
        )
        assert res["product_match_status"] == "matched"
        assert res["batch_match_status"] == "matched"
        assert res["recall_status"] == "none"
    finally:
        db.close()

def test_verification_active_recall_flag():
    db = SessionLocal()
    try:
        res = verify_extracted_records(
            db=db,
            product_name="Augmentin 625mg Duo",
            manufacturer="GlaxoSmithKline",
            batch_number="AUG-99482",
            expiry_date="10/2027"
        )
        assert res["recall_status"] == "active_recall_flagged"
    finally:
        db.close()

# ==================== Inspections & Screening ====================

def test_list_inspections(client):
    res = client.get("/api/inspections")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert len(data) >= 1

def test_inspection_detail(client):
    res = client.get("/api/inspections")
    first_id = res.json()[0]["id"]
    detail_res = client.get(f"/api/inspections/{first_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert "prediction" in detail
    assert "ocr_result" in detail
    assert "risk_level" in detail

def test_upload_and_analyze_inspection(client, inspector_token):
    img = Image.new("RGB", (300, 200), color=(50, 100, 150))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    buf.seek(0)

    files = {"file": ("test_packaging.jpg", buf, "image/jpeg")}
    res = client.post(
        "/api/inspections",
        headers={"Authorization": f"Bearer {inspector_token}"},
        files=files,
        data={"auto_analyze": "true"}
    )
    assert res.status_code == 201
    data = res.json()
    assert "inspection_code" in data
    assert data["status"] in ["completed", "manual_review_recommended"]
    assert data["prediction"] is not None

