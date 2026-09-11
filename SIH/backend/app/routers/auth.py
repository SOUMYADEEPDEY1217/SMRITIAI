import re
import datetime
import jwt
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, Literal
from passlib.context import CryptContext
from app.services import firebase_service
from app.services.auth_dependency import get_current_user
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])

RoleType = Literal["patient", "doctor", "admin"]
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=100)
    role: RoleType = "patient"


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=4, max_length=100)
    role: RoleType = "patient"
    language: Optional[str] = "en"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "user"


def _make_token(uid: str, email: str, role: str) -> str:
    payload = {
        "uid": uid,
        "email": email,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


@router.post("/signup")
def signup(payload: SignupRequest):
    clean_email = payload.email.strip().lower()
    uid = f"{payload.role}-{_slugify(clean_email)}"
    
    # Check if email is already registered
    existing = firebase_service.get_document("users", uid)
    if existing:
        raise HTTPException(status_code=400, detail="Account with this email and role already exists.")

    # Check if username (name) is unique across users
    clean_name = payload.name.strip()
    existing_name = firebase_service.query_by_field("users", "name", clean_name)
    if existing_name:
        raise HTTPException(status_code=400, detail="Username is already taken. Please choose another.")

    hashed_password = pwd_context.hash(payload.password)
    
    now_iso = datetime.datetime.utcnow().isoformat()
    new_user = {
        "id": uid,
        "name": clean_name,
        "email": clean_email,
        "role": payload.role,
        "difficulty": "Medium",
        "language": payload.language or "en",
        "hashed_password": hashed_password,
        "created_at": now_iso,
        "last_login": now_iso,
    }

    firebase_service.add_document("users", new_user, doc_id=uid)
    token = _make_token(uid, new_user["email"], new_user["role"])

    user_info = {k: v for k, v in new_user.items() if k != "hashed_password"}

    return {
        "status": "success",
        "token": token,
        "user": user_info,
    }


@router.post("/login")
def login(payload: LoginRequest):
    clean_email = payload.email.strip().lower()
    uid = f"{payload.role}-{_slugify(clean_email)}"
    profile = firebase_service.get_document("users", uid)
    
    if not profile or not profile.get("hashed_password"):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
        
    if not pwd_context.verify(payload.password, profile["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials.")

    firebase_service.update_document("users", uid, {"last_login": datetime.datetime.utcnow().isoformat()})
    profile["last_login"] = datetime.datetime.utcnow().isoformat()

    token = _make_token(uid, profile["email"], profile["role"])
    user_info = {k: v for k, v in profile.items() if k != "hashed_password"}

    return {
        "status": "success",
        "token": token,
        "user": user_info,
    }


@router.get("/me")
def get_profile(user=Depends(get_current_user)):
    stored = firebase_service.get_document("users", user.get("uid"))
    if stored:
        return {k: v for k, v in stored.items() if k != "hashed_password"}
    raise HTTPException(status_code=404, detail="User not found")
