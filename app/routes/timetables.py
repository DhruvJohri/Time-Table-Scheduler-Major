"""
Timetable generation and management API.
Frozen spec compliant (6 days × 7 periods, deterministic grid).
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, List
from sqlalchemy.orm import joinedload
from app.models.database import get_db
from app.models.models import (
    TimetableEntry,
    Subject,
    Faculty,
    Classroom,
    LabRoom,
    Branch,
    YearSection,
    ScheduleMetadata,
    DayOfWeek,
    SessionType,
)
from app.schemas.schemas import (
    GenerateScheduleRequest,
    ScheduleGenerationResponse,
    ValidationReport,
    ConflictReport,
    ScheduleStatistics,
)
from app.services.scheduling_engine import SchedulerEngine
from app.services.validators import ConstraintValidator

router = APIRouter(prefix="/api/timetable", tags=["timetable"])

# =========================================================
# GENERATE TIMETABLE
# =========================================================
@router.post("/generate", response_model=ScheduleGenerationResponse)
async def generate_timetable(
    request: GenerateScheduleRequest,
    db: Session = Depends(get_db),
):
    """
    Generate timetable (always fresh).
    Frozen rules:
    - 6 days
    - 7 periods
    - clean regenerate
    """
    try:
        scheduler = SchedulerEngine(db, seed=request.seed)

        # # ALWAYS clear existing timetable
        # db.query(TimetableEntry).delete()
        # db.commit()

        # Run scheduler
        success, report = scheduler.schedule_all(
            force_clear=True,
            include_clubs=request.include_clubs
        )

        # Clubs optional
        if request.include_clubs:
            scheduler.schedule_clubs()

        # Final conflict validation
        validator = ConstraintValidator(db)
        is_valid, conflicts = validator.validate_full_schedule()

        # Compute final success
        success = success and is_valid
        # Clear old metadata (keep only latest generation)
        db.query(ScheduleMetadata).delete()
        db.commit()
        # Save metadata
        metadata = ScheduleMetadata(
            generated_at=datetime.utcnow(),
            generation_seed=request.seed,   
            generation_time_ms=report.get("generation_time_ms", 0),
            is_valid=success,
            conflict_count=len(conflicts),
            unallocated_subjects_count=report.get("failed", 0),
            capacity=report.get("capacity"),
            demand=report.get("demand"),
            expected_empty=report.get("expected_empty"),
        )
        db.add(metadata)
        db.commit()

        return ScheduleGenerationResponse(
            success=success,
            message=report.get("message", "Timetable generated"),
            generation_time_ms=report.get("generation_time_ms"),
            conflict_count=len(conflicts),
            unallocated_subjects_count=report.get("failed", 0),
            failed_subjects=report.get("failed_subjects", []),
            capacity=report.get("capacity"),
            demand=report.get("demand"),
            expected_empty=report.get("expected_empty"),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# FULL TIMETABLE
# =========================================================
@router.get("")
async def get_full_timetable(db: Session = Depends(get_db)):
    """
    Return all timetable entries grouped by day.
    """
    try:
        entries = db.query(TimetableEntry).options(
        joinedload(TimetableEntry.branch),
        joinedload(TimetableEntry.year_section),
        joinedload(TimetableEntry.subject),
        joinedload(TimetableEntry.faculty),
        joinedload(TimetableEntry.classroom),
        joinedload(TimetableEntry.labroom),
    ).order_by(
        TimetableEntry.day_of_week,
        TimetableEntry.period_number
    ).all()

        if not entries:
            return {
                "total_entries": 0,
                "days": {},
                "generated_at": None
            }

        timetable: Dict[str, List] = {}

        for e in entries:
            day = e.day_of_week.value
            timetable.setdefault(day, []).append(
                {
                    "period": e.period_number,
                    "branch": e.branch.code if e.branch else None,
                    "year_section": f"{e.year_section.year}{e.year_section.section}"
                    if e.year_section
                    else None,
                    "subject": e.subject.code if e.subject else None,
                    "faculty": e.faculty.name if e.faculty else None,
                    "classroom": e.classroom.room_number if e.classroom else None,
                    "labroom": e.labroom.room_number if e.labroom else None,
                    "type": e.session_type.value,
                }
            )
        # Get latest metadata safely
        latest_meta = db.query(ScheduleMetadata).order_by(
            ScheduleMetadata.generated_at.desc()
        ).first()

        generated_at = latest_meta.generated_at if latest_meta else None

        return {
            "total_entries": len(entries),
            "days": timetable,
            "generated_at": generated_at,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# BRANCH TIMETABLE
# =========================================================
def _get_branch_section(db: Session, branch_code: str, year: int, section: str):
    branch = db.query(Branch).filter(Branch.code == branch_code).first()
    if not branch:
        raise HTTPException(404, f"Branch {branch_code} not found")

    ys = (
        db.query(YearSection)
        .filter(
            YearSection.branch_id == branch.id,
            YearSection.year == year,
            YearSection.section == section,
        )
        .first()
    )
    if not ys:
        raise HTTPException(404, f"{branch_code} {year}{section} not found")

    return branch, ys


@router.get("/{branch_code}/{year}/{section}")
async def get_branch_timetable(
    branch_code: str,
    year: int,
    section: str,
    db: Session = Depends(get_db),
):
    """
    Branch/year/section timetable list.
    """
    try:
        branch, ys = _get_branch_section(db, branch_code, year, section)

        entries = (
            db.query(TimetableEntry)
            .options(
                joinedload(TimetableEntry.subject),
                joinedload(TimetableEntry.faculty),
                joinedload(TimetableEntry.classroom),
                joinedload(TimetableEntry.labroom),
            )
            .filter(
                TimetableEntry.branch_id == branch.id,
                TimetableEntry.year_section_id == ys.id,
            )
            .order_by(TimetableEntry.day_of_week, TimetableEntry.period_number)
            .all()
        )

        result = [
            {
                "day": e.day_of_week.value,
                "period": e.period_number,
                "subject": e.subject.code if e.subject else None,
                "subject_name": e.subject.name if e.subject else None,
                "faculty": e.faculty.name if e.faculty else None,
                "classroom": e.classroom.room_number if e.classroom else None,
                "labroom": e.labroom.room_number if e.labroom else None,
                "type": e.session_type.value,
                "locked": e.is_locked,
            }
            for e in entries
        ]

        return {
            "branch": branch_code,
            "year": year,
            "section": section,
            "entries": result,
            "total": len(result),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# MATRIX GRID (STABLE UI)
# =========================================================
@router.get("/{branch_code}/{year}/{section}/matrix")
async def get_branch_timetable_matrix(
    branch_code: str,
    year: int,
    section: str,
    db: Session = Depends(get_db),
):
    """
    Frozen grid: Mon–Sat × 7 periods.
    Explicit empty slots included.
    """
    try:
        branch, ys = _get_branch_section(db, branch_code, year, section)

        days = [d.value for d in DayOfWeek]
        periods = list(range(1, 8))

        grid = {day: {p: None for p in periods} for day in days}

        entries = db.query(TimetableEntry).options(
            joinedload(TimetableEntry.subject),
            joinedload(TimetableEntry.faculty),
            joinedload(TimetableEntry.classroom),
            joinedload(TimetableEntry.labroom),
        ).filter(
            TimetableEntry.branch_id == branch.id,
            TimetableEntry.year_section_id == ys.id,
        ).all()

        for e in entries:
            grid[e.day_of_week.value][e.period_number] = {
                "subject_code": e.subject.code if e.subject else None,
                "subject_name": e.subject.name if e.subject else None,
                "faculty": e.faculty.name if e.faculty else None,
                "type": e.session_type.value,
                "classroom": e.classroom.room_number if e.classroom else None,
                "labroom": e.labroom.room_number if e.labroom else None,
                "locked": e.is_locked,
            }

        return {
            "branch": branch_code,
            "year": year,
            "section": section,
            "days": days,
            "periods": periods,
            "grid": grid,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# CLEAR
# =========================================================
@router.delete("/clear")
async def clear_timetable(db: Session = Depends(get_db)):
    try:
        count = db.query(TimetableEntry).delete()
        db.commit()
        return {"success": True, "cleared": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# VALIDATE
# =========================================================
@router.post("/validate", response_model=ValidationReport)
async def validate_schedule(db: Session = Depends(get_db)):
    """
    Full constraint validation + required allocation counts.
    """
    try:
        validator = ConstraintValidator(db)
        is_valid, conflicts = validator.validate_full_schedule()

        # required vs scheduled counts
        required_map = validator.required_subject_counts()
        scheduled_map = validator.scheduled_subject_counts()

        unallocated = [
            subj for subj, req in required_map.items()
            if scheduled_map.get(subj, 0) < req
        ]

        formatted_conflicts = [
            ConflictReport(
                conflict_type="General",
                day_of_week="",
                period_number=0,
                involved_subjects=[],
                description=c,
            )
            for c in conflicts
        ]

        total = len(required_map)
        allocated = total - len(unallocated)
        percent = (allocated / total * 100) if total else 0

        return ValidationReport(
            is_valid=is_valid,
            total_conflicts=len(conflicts),
            conflicts=formatted_conflicts,
            unallocated_subjects=unallocated,
            allocation_percentage=percent,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# STATISTICS
# =========================================================
@router.get("/statistics", response_model=ScheduleStatistics)
async def get_schedule_statistics(db: Session = Depends(get_db)):
    """
    Timetable resource utilization statistics.
    """
    try:
        total_entries = db.query(TimetableEntry).count()

        def count_type(t):
            return db.query(TimetableEntry).filter(
                TimetableEntry.session_type == t
            ).count()

        lectures = count_type(SessionType.LECTURE)
        tutorials = count_type(SessionType.TUTORIAL)
        labs = count_type(SessionType.LAB)
        seminars = count_type(SessionType.SEMINAR)
        clubs = count_type(SessionType.CLUB)

        total_subjects = db.query(Subject).filter(Subject.is_active == True).count()
        total_branches = db.query(Branch).count()
        total_faculty = db.query(Faculty).filter(Faculty.is_active == True).count()
        total_classrooms = db.query(Classroom).filter(Classroom.is_active == True).count()
        total_labrooms = db.query(LabRoom).filter(LabRoom.is_active == True).count()

        slots_per_week = 42  # 6 × 7

        faculty_slots = db.query(TimetableEntry).filter(
            TimetableEntry.faculty_id.isnot(None)
        ).count()
        classroom_slots = db.query(TimetableEntry).filter(
            TimetableEntry.classroom_id.isnot(None)
        ).count()
        labroom_slots = db.query(TimetableEntry).filter(
            TimetableEntry.labroom_id.isnot(None)
        ).count()

        faculty_util = min(100, (faculty_slots / (total_faculty * slots_per_week)) * 100) if total_faculty else 0
        classroom_util = min(100, (classroom_slots / (total_classrooms * slots_per_week)) * 100) if total_classrooms else 0
        labroom_util = min(100, (labroom_slots / (total_labrooms * slots_per_week)) * 100) if total_labrooms else 0

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
            faculty_utilization=faculty_util,
            classroom_utilization=classroom_util,
            labroom_utilization=labroom_util,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))