"""
Admin Profile Routes — College Timetable System
POST /api/profiles      — create or return existing admin profile
GET  /api/profiles/{email}
PUT  /api/profiles/{email}
DELETE /api/profiles/{email}
"""

from fastapi import APIRouter, HTTPException, status
from bson.objectid import ObjectId
from app.schemas import AdminProfileSchema
from app.models.database import users_collection

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


def _ser(doc: dict) -> dict:
    """Convert MongoDB doc to JSON-safe dict (ObjectId → str)."""
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id", ""))
    return doc


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_profile(profile: AdminProfileSchema):
    """Create a new admin profile. Returns existing if email already registered."""
    existing = users_collection.find_one({"email": profile.email})
    if existing:
        return _ser(existing)

    profile_dict = profile.model_dump()
    result = users_collection.insert_one(profile_dict)
    profile_dict["id"] = str(result.inserted_id)
    return profile_dict


@router.get("/{email}")
async def get_profile(email: str):
    """Get admin profile by email."""
    profile = users_collection.find_one({"email": email})
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Profile not found")
    return _ser(profile)


@router.put("/{email}")
async def update_profile(email: str, profile: AdminProfileSchema):
    """Update admin profile."""
    existing = users_collection.find_one({"email": email})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail="Profile not found")
    users_collection.update_one({"email": email}, {"$set": profile.model_dump()})
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
