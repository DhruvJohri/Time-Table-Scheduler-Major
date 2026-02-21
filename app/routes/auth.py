"""
Auth Routes — College Timetable System
POST /api/auth/login   — verify email + password, return JWT
"""

import os
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr
from jose import jwt
from passlib.context import CryptContext

from app.models.database import users_collection

router = APIRouter(prefix="/api/auth", tags=["auth"])

JWT_SECRET      = os.getenv("JWT_SECRET", "change-this-secret")
JWT_ALGORITHM   = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "24"))

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Request / Response schemas ────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    admin: dict


# ── Helpers ───────────────────────────────────────────────────────────────────

def _create_token(admin_id: str, email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {"sub": admin_id, "email": email, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def _safe_admin(doc: dict) -> dict:
    """Strip password hash and convert ObjectId before returning to client."""
    out = {k: v for k, v in doc.items() if k != "password_hash"}
    out["id"] = str(out.pop("_id", ""))
    return out


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """
    Authenticate with email + password.
    Returns a 24-hour JWT on success.
    """
    admin = users_collection.find_one({"email": body.email})
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    pw_hash = admin.get("password_hash", "")
    if not pw_hash or not _pwd_ctx.verify(body.password, pw_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    admin_id = str(admin["_id"])
    token = _create_token(admin_id, str(admin["email"]))

    return TokenResponse(
        access_token=token,
        admin=_safe_admin(admin),
    )
