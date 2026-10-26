from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.core.config import settings
from app.core.database import init_db, SessionLocal
from app.api.v1 import (
    auth,
    health,
    products,
    references,
    inspections,
    recalls,
    cases,
    analytics,
    reports,
    admin
)
from app.scripts.generate_demo_data import seed_database_if_empty

# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Pharmaceutical Visual Inspection, Counterfeit Risk Screening, and Risk Intelligence Platform",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount local storage folder for image & artifact serving
storage_path = settings.STORAGE_DIR
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")

# Include API v1 Routers
app.include_router(health.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(references.router, prefix="/api")
app.include_router(inspections.router, prefix="/api")
app.include_router(recalls.router, prefix="/api")
app.include_router(cases.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(admin.router, prefix="/api")

# Mount frontend
frontend_dist = settings.BASE_DIR.parent / "frontend" / "dist"
frontend_src = settings.BASE_DIR.parent / "frontend"

if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend_dist")
elif frontend_src.exists():
    app.mount("/", StaticFiles(directory=str(frontend_src), html=True), name="frontend_src")
else:
    @app.get("/")
    def root_status():
        return {
            "name": settings.APP_NAME,
            "status": "online",
            "version": "1.0.0",
            "docs_url": "/docs",
            "message": "MediShield AI Pharmaceutical Inspection & Risk Platform API is running."
        }

@app.on_event("startup")
def on_startup():
    """Initializes tables and seeds synthetic demo data on first startup."""
    init_db()
    db = SessionLocal()
    try:
        if settings.ENABLE_DEMO_DATA:
            seed_database_if_empty(db)
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
