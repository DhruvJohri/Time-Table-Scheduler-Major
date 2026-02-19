"""
Timetable Routes
"""

from fastapi import APIRouter, HTTPException, status
from bson.objectid import ObjectId
from datetime import datetime
from app.schemas import (
    GenerateTimetableRequest,
    RegenerateRequest,
    TimetableSchema
)
from app.models.database import users_collection, timetables_collection
from app.services.scheduling_engine import get_scheduling_engine

router = APIRouter(prefix="/api/timetables", tags=["timetables"])
engine = get_scheduling_engine()


@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_timetable(request: GenerateTimetableRequest):
    """Generate a new timetable based on user profile"""
    try:
        # Fetch user profile
        profile = users_collection.find_one({"_id": ObjectId(request.user_id)})
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found"
            )

        # Convert profile to dict format for engine
        start_date = request.start_date or datetime.now().strftime("%Y-%m-%d")
        
        # Generate timetable based on type
        if request.timetable_type == "weekly":
            timetable = engine.generate_weekly_timetable(profile, start_date)
        elif request.timetable_type == "weekend":
            timetable = engine.generate_weekend_timetable(profile, start_date)
        else:  # daily
            timetable = engine.generate_daily_timetable(profile, start_date)

        # Apply optimization if requested
        if request.optimization:
            if isinstance(timetable, dict) and "days" in timetable:
                # Weekly timetable
                timetable["days"] = engine.apply_optimization(timetable["days"], request.optimization)
            else:
                # Daily timetable
                timetable = engine.apply_optimization([timetable], request.optimization)[0]

        # Store in database
        timetable_doc = {
            "user_id": request.user_id,
            "type": request.timetable_type,
            "date": start_date,
            "timetable": timetable,
            "modifications": [],
            "created_at": datetime.now(),
            "updated_at": datetime.now()
        }

        result = timetables_collection.insert_one(timetable_doc)
        timetable_doc["_id"] = str(result.inserted_id)
        timetable_doc["id"] = str(result.inserted_id)
        
        return timetable_doc

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{timetable_id}", response_model=dict)
async def get_timetable(timetable_id: str):
    """Get timetable by ID"""
    try:
        timetable = timetables_collection.find_one({"_id": ObjectId(timetable_id)})
        if not timetable:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable not found"
            )
        timetable["id"] = str(timetable.get("_id"))
        return timetable
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/user/{user_id}", response_model=list)
async def get_user_timetables(user_id: str):
    """Get all timetables for a user"""
    try:
        timetables = list(
            timetables_collection.find({"user_id": user_id})
            .sort("created_at", -1)
        )
        for tt in timetables:
            tt["id"] = str(tt.get("_id"))
        return timetables
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/{timetable_id}/regenerate")
async def regenerate_timetable(timetable_id: str, request: RegenerateRequest):
    """Regenerate timetable with optimization"""
    try:
        timetable_doc = timetables_collection.find_one({"_id": ObjectId(timetable_id)})
        if not timetable_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable not found"
            )

        # Get original timetable blocks
        original_timetable = timetable_doc.get("timetable", {})
        
        if isinstance(original_timetable, dict) and "days" in original_timetable:
            # Weekly timetable
            original_blocks = original_timetable.get("days", [])
        else:
            # Daily timetable
            original_blocks = [original_timetable] if original_timetable else []

        # Store previous version
        previous_timetable = [dict(b) for b in original_blocks]

        # Apply optimization
        new_timetable = engine.apply_optimization(original_blocks, request.optimization)

        # Record modification
        modification = {
            "type": request.optimization,
            "timestamp": datetime.now(),
            "previous_timetable": previous_timetable,
            "new_timetable": new_timetable
        }

        # Update timetable
        if isinstance(original_timetable, dict) and "days" in original_timetable:
            original_timetable["days"] = new_timetable
        else:
            original_timetable = new_timetable[0] if new_timetable else {}

        timetables_collection.update_one(
            {"_id": ObjectId(timetable_id)},
            {
                "$set": {
                    "timetable": original_timetable,
                    "updated_at": datetime.now()
                },
                "$push": {"modifications": modification}
            }
        )

        updated = timetables_collection.find_one({"_id": ObjectId(timetable_id)})
        updated["id"] = str(updated.get("_id"))
        return updated

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{timetable_id}")
async def update_timetable(timetable_id: str, timetable_data: dict):
    """Update/edit timetable manually"""
    try:
        timetables_collection.update_one(
            {"_id": ObjectId(timetable_id)},
            {
                "$set": {
                    "timetable": timetable_data.get("timetable"),
                    "updated_at": datetime.now()
                }
            }
        )

        updated = timetables_collection.find_one({"_id": ObjectId(timetable_id)})
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable not found"
            )
        updated["id"] = str(updated.get("_id"))
        return updated

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{timetable_id}", status_code=status.HTTP_200_OK)
async def delete_timetable(timetable_id: str):
    """Delete timetable"""
    try:
        result = timetables_collection.delete_one({"_id": ObjectId(timetable_id)})
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Timetable not found"
            )
        return {"message": "Timetable deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
