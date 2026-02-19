"""
User Profile Routes
"""

from fastapi import APIRouter, HTTPException, status
from bson.objectid import ObjectId
from app.schemas import UserProfileSchema
from app.models.database import users_collection
from typing import Optional

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.post("", response_model=UserProfileSchema, status_code=status.HTTP_201_CREATED)
async def create_profile(profile: UserProfileSchema):
    """Create a new user profile"""
    try:
        profile_dict = profile.model_dump()
        
        # Check if email already exists
        existing = users_collection.find_one({"email": profile.email})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        
        result = users_collection.insert_one(profile_dict)
        profile_dict["_id"] = str(result.inserted_id)
        return profile_dict
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{email}", response_model=dict)
async def get_profile(email: str):
    """Get user profile by email"""
    profile = users_collection.find_one({"email": email})
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    profile["id"] = str(profile.get("_id", ""))
    return profile


@router.put("/{email}", response_model=dict)
async def update_profile(email: str, profile: UserProfileSchema):
    """Update user profile"""
    existing = users_collection.find_one({"email": email})
    if not existing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    
    profile_dict = profile.model_dump()
    users_collection.update_one({"email": email}, {"$set": profile_dict})
    
    updated = users_collection.find_one({"email": email})
    updated["id"] = str(updated.get("_id", ""))
    return updated


@router.delete("/{email}", status_code=status.HTTP_200_OK)
async def delete_profile(email: str):
    """Delete user profile"""
    result = users_collection.delete_one({"email": email})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found"
        )
    return {"message": "Profile deleted"}
