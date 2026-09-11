"""
App entrypoint for Smriti / SMRITI-AI Platform.
Cross-cutting security controls:
  - CORS allowlist (including local Vite dev server port 5173)
  - Rate limiting
  - Security response headers
  - Catch-all exception handling
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import logging

from app.config import settings
from app.limiter import limiter
from app.services import firebase_service, cloudinary_service, vision_service, accessibility_service, face_service
from app.routers import (
    auth,
    activities,
    clinician,
    admin,
    family_members,
    memories,
    quiz,
    reminders,
    accessibility,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

app = FastAPI(title="Smriti Platform API", version="2.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


# --- Security headers ---
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


# --- Catch-all exception handler ---
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error on {request.method} {request.url.path}")
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})


# Mount Routers
app.include_router(auth.router)
app.include_router(activities.router)
app.include_router(clinician.router)
app.include_router(admin.router)
app.include_router(family_members.router)
app.include_router(memories.router)
app.include_router(quiz.router)
app.include_router(reminders.router)
app.include_router(accessibility.router)


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/health/integrations")
def integrations_status():
    """
    Reports whether each external integration is genuinely live or running
    on its local/offline fallback. No secrets are returned - booleans only.
    Use this to answer "is Firebase/Cloudinary/Gemini actually working?"
    without digging through server logs.
    """
    return {
        "firebase": {
            "connected": firebase_service._db is not None,
            "note": "If false, all data lives in server memory only and is lost on restart."
                    if firebase_service._db is None
                    else "Firestore is live.",
        },
        "cloudinary": {
            "connected": cloudinary_service._CLOUDINARY_AVAILABLE,
            "note": "Photo upload will fail until real credentials are set in .env."
                    if not cloudinary_service._CLOUDINARY_AVAILABLE
                    else "Cloudinary is configured.",
        },
        "gemini_vision": {
            "connected": vision_service._GENAI_AVAILABLE and bool(settings.GEMINI_API_KEY),
            "note": "Photo analysis will return a placeholder hypothesis instead of a real one."
                    if not (vision_service._GENAI_AVAILABLE and bool(settings.GEMINI_API_KEY))
                    else "Gemini is configured (key presence only - not validated against Google here).",
        },
        "text_to_speech": {
            "connected": accessibility_service._GTTS_AVAILABLE,
        },
        "face_recognition": {
            "connected": face_service._DEPS_OK,
        },
    }
