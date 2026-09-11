from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from app.services import firebase_service
from app.services.auth_dependency import get_current_user, require_role
from app.routers.activities import DEFAULT_DOMAINS

router = APIRouter(prefix="/api/clinician", tags=["clinician"])

# Only doctors/nurses use this portal day to day; admins can also reach it
# since the admin role has full oversight of both clinical and patient sides.
clinical_staff = require_role("doctor", "admin")

# Patient-editable fields are never accepted here — this list is the
# allowlist for what a clinician is permitted to change about a patient.
EDITABLE_DETAIL_FIELDS = {
    "age", "gender", "stage", "diagnosis", "riskStatus",
    "primaryCaregiver", "phone", "doctorAssigned",
}


class ClinicalNotePayload(BaseModel):
    text: str = Field(..., min_length=2, max_length=1500)


class DifficultyUpdatePayload(BaseModel):
    difficulty: str = Field(..., pattern="^(Easy|Medium|Hard)$")


class PatientDetailsPayload(BaseModel):
    age: Optional[int] = Field(default=None, ge=0, le=130)
    gender: Optional[str] = None
    stage: Optional[str] = None
    diagnosis: Optional[str] = None
    riskStatus: Optional[str] = None
    primaryCaregiver: Optional[str] = None
    phone: Optional[str] = None
    doctorAssigned: Optional[str] = None


@router.get("/patients")
def list_patients(user=Depends(clinical_staff)):
    """Returns patient roster — only real users with role=patient from Firebase.
    No fake/sample data is ever returned or seeded. Includes a lightweight
    session summary per patient so the roster table doesn't need N+1 calls.
    """
    all_patients = firebase_service.query_by_field("users", "role", "patient")
    all_sessions = firebase_service.query_all("activity_sessions")

    result = []
    for p in all_patients:
        safe = {k: v for k, v in p.items() if k != "hashed_password"}
        p_sessions = [s for s in all_sessions if s.get("patient_id") == p.get("id") or s.get("patient_id") == p.get("_id")]
        safe["sessionCount"] = len(p_sessions)
        safe["avgScore"] = round(sum(s.get("score", 0) for s in p_sessions) / len(p_sessions)) if p_sessions else None
        result.append(safe)
    return result


@router.get("/patient/{patient_id}")
def get_patient_profile(patient_id: str, user=Depends(clinical_staff)):
    """Returns full patient profile with longitudinal sessions and cognitive domains."""
    patient = firebase_service.get_document("users", patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    patient_safe = {k: v for k, v in patient.items() if k != "hashed_password"}

    # Retrieve real activity sessions
    sessions = firebase_service.query_by_field("activity_sessions", "patient_id", patient_id)

    # Retrieve cognitive domains
    domains = firebase_service.get_document("cognitive_domains", patient_id) or DEFAULT_DOMAINS

    return {
        "patient": patient_safe,
        "sessions": sessions,
        "cognitive_domains": domains,
    }


@router.patch("/patient/{patient_id}/details")
def update_patient_details(patient_id: str, payload: PatientDetailsPayload, user=Depends(clinical_staff)):
    """Doctor/nurse edits to a patient's clinical details (diagnosis, stage,
    risk status, caregiver contact, etc). Name/email/role/password can't be
    changed through this endpoint — those stay tied to the patient's own account.
    """
    patient = firebase_service.get_document("users", patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    changes = {k: v for k, v in payload.model_dump().items() if v is not None and k in EDITABLE_DETAIL_FIELDS}
    if not changes:
        return {"status": "success", "changes": {}}

    firebase_service.update_document("users", patient_id, changes)
    return {"status": "success", "changes": changes}


@router.post("/patient/{patient_id}/notes")
def add_patient_note(patient_id: str, payload: ClinicalNotePayload, user=Depends(clinical_staff)):
    """Appends an observation note to the patient profile. Doctor/nurse only."""
    patient = firebase_service.get_document("users", patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    notes = patient.get("notes", [])
    author_name = user.get("name") or user.get("email") or "Care Team"
    new_note = {
        "date": datetime.utcnow().strftime("%Y-%m-%d"),
        "author": author_name,
        "text": payload.text.strip(),
    }
    notes.insert(0, new_note)
    firebase_service.update_document("users", patient_id, {"notes": notes})
    return {"status": "success", "notes": notes}


@router.patch("/patient/{patient_id}/difficulty")
def update_patient_difficulty(patient_id: str, payload: DifficultyUpdatePayload, user=Depends(clinical_staff)):
    """Adjusts baseline/starting difficulty level for a patient's games. Doctor/nurse only."""
    patient = firebase_service.get_document("users", patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    firebase_service.update_document("users", patient_id, {"difficulty": payload.difficulty})
    return {"status": "success", "difficulty": payload.difficulty}

