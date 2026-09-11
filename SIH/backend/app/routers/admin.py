"""
Admin Management Router for Smriti platform.
Provides full CRUD capabilities for Patients, Clinicians, Activities, Questions, and Media assets.
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
from app.services import firebase_service, cloudinary_service
from app.services.auth_dependency import get_current_user, require_role
from app.routers.activities import ACTIVITIES_CATALOG
from app.limiter import limiter
from app.config import settings
from app.routers.memories import VerifiedMemory
import uuid

router = APIRouter(prefix="/api/admin", tags=["admin"])

admin_only = require_role("admin")

PHOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_PHOTO_SIZE_BYTES = 10 * 1024 * 1024  # 10MB per photo

# Default seeded admin datasets
DEFAULT_QUESTIONS = [
    {
        "id": "q-1",
        "activityId": "memory-garden",
        "question": "Which flower was blooming with bright red petals?",
        "options": ["Bright Red Rose", "Blue Lotus", "White Lily", "Purple Orchid"],
        "correct": "Bright Red Rose",
        "difficulty": "Easy",
    },
    {
        "id": "q-2",
        "activityId": "memory-radio",
        "question": "Which classical string instrument was playing the soothing melody?",
        "options": ["Sitar", "Violin", "Veena", "Guitar"],
        "correct": "Sitar",
        "difficulty": "Medium",
    },
    {
        "id": "q-3",
        "activityId": "culture-quest",
        "question": "During which grand autumn festival are glowing clay diyas placed outside every doorway?",
        "options": ["Diwali", "Holi", "Bihu", "Navratri"],
        "correct": "Diwali",
        "difficulty": "Easy",
    },
]

DEFAULT_MEDIA = {
    "photos": [
        {"id": "photo-1", "title": "Golden Garden Blooms", "category": "Nature", "dateAdded": "2026-09-01"},
        {"id": "photo-2", "title": "Family Harvest Celebration", "category": "Family", "dateAdded": "2026-09-02"},
        {"id": "photo-3", "title": "Heritage Riverside Ghats", "category": "Landmark", "dateAdded": "2026-09-04"},
    ],
    "audio": [
        {"id": "audio-1", "title": "Morning Raga Bhairav (Flute)", "duration": "0:45", "type": "Instrumental"},
        {"id": "audio-2", "title": "Peaceful Evening Sitar Medley", "duration": "0:50", "type": "Classical"},
        {"id": "audio-3", "title": "Harmonium Folk Rhythm", "duration": "0:40", "type": "Tradition"},
    ],
}


# --- Patient CRUD ---
# NOTE: this now reads/writes the same "users" collection (role=patient) that
# signup and the clinician portal use. It used to point at a separate
# "patients" collection that nothing ever populated — real signed-up patients
# never showed up here, so admin was managing a disconnected demo dataset.
@router.get("/patients")
def get_all_patients(user=Depends(admin_only)):
    patients = firebase_service.query_by_field("users", "role", "patient")
    return [{k: v for k, v in p.items() if k != "hashed_password"} for p in patients]


@router.patch("/patients/{patient_id}")
def update_patient(patient_id: str, changes: dict, user=Depends(admin_only)):
    """Admin can edit any patient field except password/role/id directly."""
    patient = firebase_service.get_document("users", patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    changes = {k: v for k, v in changes.items() if k not in ("hashed_password", "role", "id")}
    firebase_service.update_document("users", patient_id, changes)
    return {"status": "success"}


@router.delete("/patients/{patient_id}")
def delete_patient(patient_id: str, user=Depends(admin_only)):
    """Removes a patient's account. Also cleans up their uploaded photos."""
    photos = firebase_service.query_by_field("patient_photos", "patient_id", patient_id)
    for photo in photos:
        cloudinary_service.delete_photo(photo["cloudinary_id"])
        firebase_service.delete_document("patient_photos", photo["_id"])
    firebase_service.delete_document("users", patient_id)
    return {"status": "success"}


# --- Signup / login activity feed ---
# Polled by the admin dashboard so the admin is informed, in near-real-time,
# whenever a patient or doctor/nurse signs up or signs in. There's no
# websocket layer in this app, so "immediately informed" is implemented as
# short-interval polling from the frontend against this cheap endpoint
# rather than the admin needing to refresh the whole Patients/Staff tabs.
@router.get("/activity-feed")
def get_activity_feed(user=Depends(admin_only)):
    users = firebase_service.query_all("users")
    events = []
    for u in users:
        if u.get("role") not in ("patient", "doctor"):
            continue
        base = {"id": u.get("id") or u.get("_id"), "name": u.get("name"), "role": u.get("role"), "email": u.get("email")}
        if u.get("created_at"):
            events.append({**base, "type": "signup", "at": u["created_at"]})
        if u.get("last_login") and u.get("last_login") != u.get("created_at"):
            events.append({**base, "type": "login", "at": u["last_login"]})
    events.sort(key=lambda e: e.get("at", ""), reverse=True)
    return events[:30]


# --- Staff CRUD ---
@router.get("/staff")
def get_all_staff(user=Depends(admin_only)):
    staff = firebase_service.query_all("staff")
    if not staff:
        default_staff = [
            {"id": "doc-1", "name": "Dr. Ananya Sharma", "role": "Senior Geriatric Neurologist", "email": "ananya@smriti.com"},
            {"id": "doc-2", "name": "Nurse Priya Patel", "role": "Smriti Coordinator", "email": "priya@smriti.com"},
        ]
        for s in default_staff:
            firebase_service.add_document("staff", s, doc_id=s["id"])
        return default_staff
    return staff


@router.post("/staff")
def create_staff(data: dict, user=Depends(admin_only)):
    staff_id = data.get("id") or f"staff-{uuid.uuid4().hex[:6]}"
    data["id"] = staff_id
    firebase_service.add_document("staff", data, doc_id=staff_id)
    return {"status": "success", "staff": data}


@router.delete("/staff/{staff_id}")
def delete_staff(staff_id: str, user=Depends(admin_only)):
    firebase_service.delete_document("staff", staff_id)
    return {"status": "success"}


# --- Activities CRUD ---
@router.get("/activities")
def get_activities_admin(user=Depends(admin_only)):
    return ACTIVITIES_CATALOG


@router.patch("/activities/{activity_id}")
def update_activity_admin(activity_id: str, changes: dict, user=Depends(admin_only)):
    firebase_service.update_document("activities", activity_id, changes)
    return {"status": "success"}


# --- Questions CRUD ---
@router.get("/questions")
def get_questions_admin(user=Depends(admin_only)):
    questions = firebase_service.query_all("questions")
    if not questions:
        for q in DEFAULT_QUESTIONS:
            firebase_service.add_document("questions", q, doc_id=q["id"])
        return DEFAULT_QUESTIONS
    return questions


@router.post("/questions")
def create_question_admin(data: dict, user=Depends(admin_only)):
    q_id = data.get("id") or f"q-{uuid.uuid4().hex[:6]}"
    data["id"] = q_id
    firebase_service.add_document("questions", data, doc_id=q_id)
    return {"status": "success", "question": data}


@router.delete("/questions/{question_id}")
def delete_question_admin(question_id: str, user=Depends(admin_only)):
    firebase_service.delete_document("questions", question_id)
    return {"status": "success"}


# --- Media Management ---
@router.get("/media")
def get_media_admin(user=Depends(admin_only)):
    media = firebase_service.query_all("media")
    if not media:
        return DEFAULT_MEDIA
    
    photos = [m for m in media if m.get("type") == "photo"]
    audio = [m for m in media if m.get("type") == "audio"]
    return {"photos": photos, "audio": audio}

@router.post("/media/photos")
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_global_photo(
    request: Request,
    title: str = Form(default="Untitled"),
    category: str = Form(default="General"),
    file: UploadFile = File(...),
    user=Depends(admin_only),
):
    if file.content_type not in PHOTO_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WEBP images are allowed.")
    image_bytes = await file.read()
    if len(image_bytes) > MAX_PHOTO_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Photo exceeds the 10MB limit.")
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")
    
    photo_id = f"photo-{uuid.uuid4().hex[:8]}"
    cloudinary_id = f"global/photos/{photo_id}"
    url = cloudinary_service.upload_photo(image_bytes, cloudinary_id)

    record = {
        "id": photo_id,
        "type": "photo",
        "title": title.strip(),
        "category": category.strip(),
        "dateAdded": datetime.utcnow().isoformat()[:10],
        "url": url,
        "cloudinary_id": cloudinary_id
    }
    firebase_service.add_document("media", record, doc_id=photo_id)
    return {"status": "success", "photo": record}

@router.post("/media/audio")
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_global_audio(
    request: Request,
    title: str = Form(default="Untitled"),
    category: str = Form(default="Audio"),
    file: UploadFile = File(...),
    user=Depends(admin_only),
):
    audio_bytes = await file.read()
    if len(audio_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Audio exceeds 20MB limit.")
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")
        
    audio_id = f"audio-{uuid.uuid4().hex[:8]}"
    cloudinary_id = f"global/audio/{audio_id}"
    # assuming cloudinary_service.upload_photo can handle raw/audio types if configured,
    # or just use it (it uses auto resource type).
    url = cloudinary_service.upload_photo(audio_bytes, cloudinary_id)

    record = {
        "id": audio_id,
        "type": "audio",
        "title": title.strip(),
        "category": category.strip(),
        "duration": "0:00", # Need client to send duration if desired
        "url": url,
        "cloudinary_id": cloudinary_id
    }
    firebase_service.add_document("media", record, doc_id=audio_id)
    return {"status": "success", "audio": record}

@router.delete("/media/{media_id}")
def delete_media_admin(media_id: str, user=Depends(admin_only)):
    media = firebase_service.get_document("media", media_id)
    if not media:
        raise HTTPException(status_code=404, detail="Media not found")
    if media.get("cloudinary_id"):
        res_type = "video" if media.get("type") == "audio" else "image"
        cloudinary_service.delete_photo(media["cloudinary_id"], resource_type=res_type)
    firebase_service.delete_document("media", media_id)
    return {"status": "success"}

# --- Activity Sessions ---
@router.get("/sessions")
def get_all_sessions_admin(user=Depends(admin_only)):
    return firebase_service.query_all("activity_sessions")


# --- Per-Patient Photo Folders ---
# Photos are stored in Cloudinary under patients/{patient_id}/photos/{photo_id}
# and tracked in the "patient_photos" collection so they show up as an
# organized, per-patient gallery instead of a flat shared bank.
@router.post("/patients/{patient_id}/photos")
@limiter.limit(settings.RATE_LIMIT_UPLOAD)
async def upload_patient_photo(
    request: Request,
    patient_id: str,
    caption: str = Form(default=""),
    relationship: str = Form(default=""),
    location: str = Form(default=""),
    file: UploadFile = File(...),
    user=Depends(admin_only),
):
    patient = firebase_service.get_document("users", patient_id)
    if not patient or patient.get("role") != "patient":
        raise HTTPException(status_code=404, detail="Patient not found")

    if file.content_type not in PHOTO_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, or WEBP images are allowed.")

    image_bytes = await file.read()
    if len(image_bytes) > MAX_PHOTO_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="Photo exceeds the 10MB limit.")
    if len(image_bytes) == 0:
        raise HTTPException(status_code=400, detail="Empty file.")

    photo_id = uuid.uuid4().hex[:12]
    # patient_id is validated against a real patient record above (not raw
    # client input used blindly), so this path is safe to build server-side.
    cloudinary_id = f"patients/{patient_id}/photos/{photo_id}"
    url = cloudinary_service.upload_photo(image_bytes, cloudinary_id)

    record = {
        "patient_id": patient_id,
        "cloudinary_id": cloudinary_id,
        "url": url,
        "caption": caption.strip(),
        "relationship": relationship.strip(),
        "location": location.strip(),
        "uploaded_by": user.get("uid"),
        "uploaded_at": datetime.utcnow().isoformat(),
    }
    firebase_service.add_document("patient_photos", record, doc_id=photo_id)
    return {"status": "success", "photo": {**record, "id": photo_id}}


@router.get("/patients/{patient_id}/photos")
def list_patient_photos(patient_id: str, user=Depends(admin_only)):
    photos = firebase_service.query_by_field("patient_photos", "patient_id", patient_id)
    return sorted(photos, key=lambda p: p.get("uploaded_at", ""), reverse=True)


@router.delete("/patients/{patient_id}/photos/{photo_id}")
def delete_patient_photo(patient_id: str, photo_id: str, user=Depends(admin_only)):
    photo = firebase_service.get_document("patient_photos", photo_id)
    if not photo or photo.get("patient_id") != patient_id:
        raise HTTPException(status_code=404, detail="Photo not found")
    firebase_service.delete_document("patient_photos", photo_id)
    return {"status": "success"}

@router.post("/patients/{patient_id}/memories")
def save_admin_patient_memory(patient_id: str, memory: VerifiedMemory, user=Depends(admin_only)):
    """
    Admin-only endpoint to save a verified memory on behalf of a patient.
    Requires a valid pending_memories record created by this admin.
    """
    patient = firebase_service.get_document("users", patient_id)
    if not patient or patient.get("role") != "patient":
        raise HTTPException(status_code=404, detail="Patient not found")

    pending = firebase_service.get_document("pending_memories", memory.memory_id)
    if not pending or pending.get("user_id") != user["uid"]:
        raise HTTPException(
            status_code=403,
            detail="This memory_id was not produced by your own /analyze call.",
        )

    existing = firebase_service.get_document("memories", memory.memory_id)
    if existing:
        raise HTTPException(status_code=403, detail="Memory already exists.")

    data = {
        **memory.model_dump(),
        "photo_url": pending["photo_url"],
        "user_id": patient_id,
        "verified": True,
        "created_at": datetime.utcnow().isoformat(),
    }
    firebase_service.add_document("memories", data, doc_id=memory.memory_id)
    firebase_service.delete_document("pending_memories", memory.memory_id)
    return data

