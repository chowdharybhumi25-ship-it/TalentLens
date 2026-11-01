from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from app.core.config import settings
from app.database.session import engine
from app.models import base  # noqa - registers all models
from app.api.v1 import auth, jobs, candidates, matching, shortlist, analytics, interview

# Create upload directory
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="Smart Recruitment Platform API",
    description="AI-powered recruitment assistance platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(candidates.router, prefix="/api/candidates", tags=["Candidates"])
app.include_router(matching.router, prefix="/api/matching", tags=["Matching"])
app.include_router(shortlist.router, prefix="/api/shortlist", tags=["Shortlist"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(interview.router, prefix="/api/interview", tags=["Interview"])

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# Mount frontend static files
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "frontend")
FRONTEND_STATIC = os.path.join(FRONTEND_DIR, "static")

if os.path.exists(FRONTEND_STATIC):
    app.mount("/static", StaticFiles(directory=FRONTEND_STATIC), name="static")


@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


# Serve the SPA for all non-API routes
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str, request: Request):
    frontend_index = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(frontend_index):
        return FileResponse(frontend_index)
    return {"message": "Frontend not found. API is available at /api/docs"}


@app.on_event("startup")
async def startup_event():
    """Initialize database tables on startup."""
    from app.database.session import Base
    Base.metadata.create_all(bind=engine)
