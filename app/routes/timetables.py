"""
API routes for timetable generation and management.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.models.database import get_db
from app.models.models import (
    TimetableEntry, Subject, Faculty, Classroom, LabRoom,
    Branch, YearSection, ScheduleMetadata, DayOfWeek, SessionType
)
from app.schemas.schemas import (
    GenerateScheduleRequest, ScheduleGenerationResponse, TimetableEntryResponse,
    TimetableViewBranchYearSection, TimetableDisplayEntry, ValidationReport,
    ConflictReport, ScheduleStatistics, ErrorResponse
)
from app.services.scheduling_engine import SchedulerEngine
from app.services.validators import ConstraintValidator

router = APIRouter(prefix="/api/timetable", tags=["timetable"])


@router.post("/generate", response_model=ScheduleGenerationResponse)
async def generate_timetable(
    request: GenerateScheduleRequest,
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None
):
    """
    Generate a timetable for all branches.
    
    - **seed**: Optional seed for deterministic scheduling
    - **force_regenerate**: If True, clears existing timetable first
    - **include_clubs**: If True, schedules club activities
    """
    try:
        # Create scheduler
        scheduler = SchedulerEngine(db, seed=request.seed)
        
        # Clear if requested
        if request.force_regenerate:
            db.query(TimetableEntry).delete()
            db.commit()
        
        # Schedule all subjects
        success, report = scheduler.schedule_all(force_clear=False)
        
        # Schedule clubs if requested
        if request.include_clubs:
            scheduler.schedule_clubs()
        
        # Save metadata
        metadata = ScheduleMetadata(
            generated_at=datetime.utcnow(),
            generation_seed=request.seed,
            generation_time_ms=report.get("generation_time_ms", 0),
            is_valid=success,
            conflict_count=report.get("conflicts", 0),
            unallocated_subjects_count=report.get("failed", 0)
        )
        db.add(metadata)
        db.commit()
        
        return ScheduleGenerationResponse(
            success=success,
            message=report.get("message", "Timetable generated"),
            generation_time_ms=report.get("generation_time_ms"),
            conflict_count=report.get("conflicts", 0),
            unallocated_subjects=report.get("failed", 0),
            failed_subjects=[f[0] for f in report.get("failed_subjects", [])]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating timetable: {str(e)}"
        )


@router.get("", response_model=dict)
async def get_full_timetable(db: Session = Depends(get_db)):
    """
    Get the complete generated timetable.
    """
    try:
        entries = db.query(TimetableEntry).all()
        
        if not entries:
            return {
                "total_entries": 0,
                "days": [],
                "message": "No timetable generated yet"
            }
        
        # Group by day
        timetable_by_day = {}
        for entry in entries:
            day = entry.day_of_week.value
            if day not in timetable_by_day:
                timetable_by_day[day] = []
            
            timetable_by_day[day].append({
                "period": entry.period_number,
                "branch": entry.branch.code if entry.branch else None,
                "year_section": f"{entry.year_section.year}{entry.year_section.section}" if entry.year_section else None,
                "subject": entry.subject.code if entry.subject else None,
                "faculty": entry.faculty.name if entry.faculty else None,
                "classroom": entry.classroom.room_number if entry.classroom else None,
                "labroom": entry.labroom.room_number if entry.labroom else None,
                "type": entry.session_type.value
            })
        
        return {
            "total_entries": len(entries),
            "days": timetable_by_day,
            "generated_at": entries[0].created_at if entries else None
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving timetable: {str(e)}"
        )


@router.get("/{branch_code}/{year}/{section}")
async def get_branch_timetable(
    branch_code: str,
    year: int,
    section: str,
    db: Session = Depends(get_db)
):
    """
    Get timetable for a specific branch, year, and section.
    """
    try:
        # Find branch
        branch = db.query(Branch).filter(Branch.code == branch_code).first()
        if not branch:
            raise HTTPException(
                status_code=404,
                detail=f"Branch {branch_code} not found"
            )
        
        # Find year section
        year_section = db.query(YearSection).filter(
            YearSection.branch_id == branch.id,
            YearSection.year == year,
            YearSection.section == section
        ).first()
        
        if not year_section:
            raise HTTPException(
                status_code=404,
                detail=f"Year/Section {year}{section} not found for {branch_code}"
            )
        
        # Get entries
        entries = db.query(TimetableEntry).filter(
            TimetableEntry.branch_id == branch.id,
            TimetableEntry.year_section_id == year_section.id
        ).order_by(
            TimetableEntry.day_of_week,
            TimetableEntry.period_number
        ).all()
        
        if not entries:
            return {
                "branch": branch_code,
                "year": year,
                "section": section,
                "entries": [],
                "message": "No timetable entries found"
            }
        
        # Format entries
        formatted_entries = []
        for entry in entries:
            formatted_entries.append({
                "day": entry.day_of_week.value,
                "period": entry.period_number,
                "subject": entry.subject.code if entry.subject else None,
                "subject_name": entry.subject.name if entry.subject else None,
                "faculty": entry.faculty.name if entry.faculty else None,
                "classroom": entry.classroom.room_number if entry.classroom else None,
                "labroom": entry.labroom.room_number if entry.labroom else None,
                "type": entry.session_type.value,
                "locked": entry.is_locked
            })
        
        return {
            "branch": branch_code,
            "year": year,
            "section": section,
            "entries": formatted_entries,
            "total": len(formatted_entries)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving timetable: {str(e)}"
        )


@router.delete("/clear")
async def clear_timetable(db: Session = Depends(get_db)):
    """
    Clear all timetable entries (use with caution).
    """
    try:
        count = db.query(TimetableEntry).delete()
        db.commit()
        return {
            "success": True,
            "message": f"Cleared {count} timetable entries"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error clearing timetable: {str(e)}"
        )


@router.post("/validate", response_model=ValidationReport)
async def validate_schedule(db: Session = Depends(get_db)):
    """
    Validate the current schedule for conflicts.
    """
    try:
        validator = ConstraintValidator(db)
        is_valid, conflicts = validator.validate_full_schedule()
        
        # Get unallocated subjects
        all_subjects = db.query(Subject).filter(Subject.is_active == True).all()
        allocated_subject_ids = set()
        
        entries = db.query(TimetableEntry).all()
        for entry in entries:
            if entry.subject_id:
                allocated_subject_ids.add(entry.subject_id)
        
        unallocated = [
            s.code for s in all_subjects
            if s.id not in allocated_subject_ids
        ]
        
        # Format conflicts
        formatted_conflicts = [
            ConflictReport(
                conflict_type="Faculty" if "Faculty" in conflict else "Classroom" if "Classroom" in conflict else "Lab Room",
                day_of_week="",
                period_number=0,
                involved_subjects=[],
                description=conflict
            )
            for conflict in conflicts
        ]
        
        total_subjects = len(all_subjects)
        allocated_count = len(allocated_subject_ids)
        allocation_percentage = (allocated_count / total_subjects * 100) if total_subjects > 0 else 0
        
        return ValidationReport(
            is_valid=is_valid,
            total_conflicts=len(conflicts),
            conflicts=formatted_conflicts,
            unallocated_subjects=unallocated,
            allocation_percentage=allocation_percentage
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error validating schedule: {str(e)}"
        )


@router.get("/statistics", response_model=ScheduleStatistics)
async def get_schedule_statistics(db: Session = Depends(get_db)):
    """
    Get statistics about the generated schedule.
    """
    try:
        # Count entries by type
        total_entries = db.query(TimetableEntry).count()
        lectures = db.query(TimetableEntry).filter(
            TimetableEntry.session_type == SessionType.LECTURE
        ).count()
        tutorials = db.query(TimetableEntry).filter(
            TimetableEntry.session_type == SessionType.TUTORIAL
        ).count()
        labs = db.query(TimetableEntry).filter(
            TimetableEntry.session_type == SessionType.LAB
        ).count()
        seminars = db.query(TimetableEntry).filter(
            TimetableEntry.session_type == SessionType.SEMINAR
        ).count()
        clubs = db.query(TimetableEntry).filter(
            TimetableEntry.session_type == SessionType.CLUB
        ).count()
        
        # Count resources
        total_subjects = db.query(Subject).filter(Subject.is_active == True).count()
        total_branches = db.query(Branch).count()
        total_faculty = db.query(Faculty).filter(Faculty.is_active == True).count()
        total_classrooms = db.query(Classroom).filter(Classroom.is_active == True).count()
        total_labrooms = db.query(LabRoom).filter(LabRoom.is_active == True).count()
        
        # Calculate utilization (simplified)
        faculty_slots_used = db.query(TimetableEntry).filter(
            TimetableEntry.faculty_id.isnot(None)
        ).count()
        classroom_slots_used = db.query(TimetableEntry).filter(
            TimetableEntry.classroom_id.isnot(None),
            TimetableEntry.session_type != SessionType.CLUB
        ).count()
        labroom_slots_used = db.query(TimetableEntry).filter(
            TimetableEntry.labroom_id.isnot(None)
        ).count()
        
        faculty_utilization = (faculty_slots_used / (total_faculty * 42)) * 100 if total_faculty > 0 else 0  # 6 days * 7 periods
        classroom_utilization = (classroom_slots_used / (total_classrooms * 42)) * 100 if total_classrooms > 0 else 0
        labroom_utilization = (labroom_slots_used / (total_labrooms * 42)) * 100 if total_labrooms > 0 else 0
        
        return ScheduleStatistics(
            total_entries=total_entries,
            total_subjects=total_subjects,
            total_branches=total_branches,
            total_faculty=total_faculty,
            total_classrooms=total_classrooms,
            total_labrooms=total_labrooms,
            lectures_scheduled=lectures,
            tutorials_scheduled=tutorials,
            labs_scheduled=labs,
            seminars_scheduled=seminars,
            clubs_scheduled=clubs,
            faculty_utilization=min(100, faculty_utilization),
            classroom_utilization=min(100, classroom_utilization),
            labroom_utilization=min(100, labroom_utilization)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving statistics: {str(e)}"
        )
