import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

# Add app to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.main import app
from app.core.database import SessionLocal, init_db
from app.scripts.generate_demo_data import seed_database_if_empty
from sqlalchemy import text

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    init_db()
    db = SessionLocal()
    seed_database_if_empty(db)
    db.close()
    yield
    clean_db = SessionLocal()
    try:
        clean_db.execute(text("DELETE FROM model_predictions WHERE inspection_id > 2"))
        clean_db.execute(text("DELETE FROM explainability_artifacts WHERE inspection_id > 2"))
        clean_db.execute(text("DELETE FROM ocr_results WHERE inspection_id > 2"))
        clean_db.execute(text("DELETE FROM verification_results WHERE inspection_id > 2"))
        clean_db.execute(text("DELETE FROM inspections WHERE id > 2"))
        clean_db.commit()
    except Exception:
        clean_db.rollback()
    finally:
        clean_db.close()

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def admin_token(client):
    res = client.post("/api/auth/login", json={"email": "admin@medishield.ai", "password": "admin123"})
    assert res.status_code == 200
    return res.json()["access_token"]

@pytest.fixture
def inspector_token(client):
    res = client.post("/api/auth/login", json={"email": "inspector@medishield.ai", "password": "inspector123"})
    assert res.status_code == 200
    return res.json()["access_token"]

