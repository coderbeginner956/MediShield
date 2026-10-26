import os
from pathlib import Path
from typing import List

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
STORAGE_DIR = BASE_DIR / "storage"

class Settings:
    BASE_DIR: Path = BASE_DIR
    STORAGE_DIR: Path = BASE_DIR / "storage"
    APP_NAME: str = os.getenv("APP_NAME", "MediShield AI")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1", "yes")
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "medishield_super_secret_development_key_change_in_production_2026")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR}/medishield.db")

    # Storage paths
    UPLOAD_DIR: Path = STORAGE_DIR / "uploads"
    REFERENCE_DIR: Path = STORAGE_DIR / "references"
    ARTIFACT_DIR: Path = STORAGE_DIR / "artifacts"
    REPORTS_DIR: Path = STORAGE_DIR / "reports"

    # Model Configuration
    # Supported: demo, pretrained_cpu, unavailable
    MODEL_PROVIDER: str = os.getenv("MODEL_PROVIDER", "demo")
    MODEL_TASK: str = os.getenv("MODEL_TASK", "classification")
    MODEL_PATH: str = os.getenv("MODEL_PATH", "")
    MODEL_DEVICE: str = os.getenv("MODEL_DEVICE", "cpu")
    ENABLE_DEMO_DATA: bool = os.getenv("ENABLE_DEMO_DATA", "True").lower() in ("true", "1", "yes")

    # OCR Configuration
    # Supported: mock, easyocr, tesseract
    OCR_PROVIDER: str = os.getenv("OCR_PROVIDER", "mock")

    # Allowed CORS Origins
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*"
    ]

settings = Settings()

# Ensure directories exist
for folder in [settings.UPLOAD_DIR, settings.REFERENCE_DIR, settings.ARTIFACT_DIR, settings.REPORTS_DIR]:
    folder.mkdir(parents=True, exist_ok=True)
