"""
Admin Profile Routes — College Timetable System
POST   /api/profiles        — create admin profile (hashes password)
GET    /api/profiles/{email}
PUT    /api/profiles/{email}
DELETE /api/profiles/{email}
"""

from fastapi import APIRouter, HTTPException, status
from bson.objectid import ObjectId
from passlib.context import CryptContext

from app.schemas import AdminProfileSchema
from app.models.database import users_collection

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _ser(doc: dict) -> dict:
    """Convert MongoDB doc to JSON-safe dict — strips password_hash, ObjectId → str."""
    doc = {k: v for k, v in doc.items() if k != "password_hash"}
    doc["id"] = str(doc.pop("_id", ""))
    return doc


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_profile(profile: AdminProfileSchema):
    """
    Create a new admin profile.
    Password is hashed with bcrypt before storage.
    Returns existing profile (without hash) if email already registered.
    """
    existing = users_collection.find_one({"email": profile.email})
    if existing:
        return _ser(existing)

    data = profile.model_dump()
    raw_password = data.pop("password")
    data["password_hash"] = _pwd_ctx.hash(raw_password)

    result = users_collection.insert_one(data)
    data["id"] = str(result.inserted_id)
    return data


@router.get("/{email}")
async def get_profile(email: str):
    """Get admin profile by email (no password_hash returned)."""
    profile = users_collection.find_one({"email": email})
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Profile not found")
    return _ser(profile)


@router.put("/{email}")
async def update_profile(email: str, profile: AdminProfileSchema):
    """Update admin profile. Re-hashes password if provided."""
    existing = users_collection.find_one({"email": email})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Profile not found")

    data = profile.model_dump()
    raw_password = data.pop("password")
    data["password_hash"] = _pwd_ctx.hash(raw_password)

    users_collection.update_one({"email": email}, {"$set": data})
    updated = users_collection.find_one({"email": email})
    return _ser(updated)


@router.delete("/{email}", status_code=status.HTTP_200_OK)
async def delete_profile(email: str):
    """Delete admin profile."""
    result = users_collection.delete_one({"email": email})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Profile not found")
    return {"message": "Profile deleted"}
