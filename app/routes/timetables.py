"""
API routes for timetable generation and management.
"""

from datetime import datetime
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.models import (
    Branch, Classroom, DayOfWeek, Faculty, LabRoom, ScheduleMetadata,
    SessionType, Subject, TimetableEntry, TimetableVersion, YearSection
)
from app.schemas.schemas import (
    ConflictReport, GenerateScheduleRequest, ScheduleGenerationResponse,
    ScheduleStatistics, ValidationReport
)
from app.services.scheduling_engine import SchedulerEngine, activate_new_version, get_active_version
from app.services.validators import ConstraintValidator

router = APIRouter(prefix="/api/timetable", tags=["timetable"])


class LockRequest(BaseModel):
    locked: bool = True


class MoveEntryRequest(BaseModel):
    entry_id: int
    day_of_week: DayOfWeek
    period_number: int = Field(..., ge=1, le=7)


class SwapEntriesRequest(BaseModel):
    first_entry_id: int
    second_entry_id: int


class AssignEntryRequest(BaseModel):
    branch_code: str
    year: int
    section: str
    day_of_week: DayOfWeek
    period_number: int = Field(..., ge=1, le=7)
    session_type: SessionType
    subject_code: Optional[str] = None
    lock: bool = False


class ReshuffleRequest(BaseModel):
    seed: Optional[int] = None
    include_clubs: bool = True
    fill_extracurricular: bool = True


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_simple_pdf(lines: List[str]) -> bytes:
    text_commands = ["BT", "/F1 10 Tf", "50 780 Td", "14 TL"]
    for idx, line in enumerate(lines):
        if idx == 0:
            text_commands.append(f"({_escape_pdf_text(line)}) Tj")
        else:
            text_commands.append(f"T* ({_escape_pdf_text(line)}) Tj")
    text_commands.append("ET")
    content_stream = "\n".join(text_commands).encode("latin-1", errors="replace")

    objects: List[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objects.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
    )
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    objects.append(
        f"<< /Length {len(content_stream)} >>\nstream\n".encode("latin-1")
        + content_stream
        + b"\nendstream"
    )

    pdf = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("latin-1"))
        pdf.extend(obj)
        pdf.extend(b"\nendobj\n")

    xref_start = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
    pdf.extend(
        (
            "trailer\n"
            f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_start}\n%%EOF\n"
        ).encode("latin-1")
    )
    return bytes(pdf)


def _active_version_or_404(db: Session) -> TimetableVersion:
    version = get_active_version(db)
    if version is None:
        raise HTTPException(status_code=404, detail="No active timetable version found")
    return version

def _subject_required_allocations(subject: Subject) -> int:
    return (
        int(subject.lectures_per_week or 0)
        + int(subject.tutorials_per_week or 0)
        + int(subject.seminar_periods_per_week or 0)
        + (int(subject.lab_periods_per_week or 0) * 2)
    )


def _subject_allocated_entries_count(db: Session, version_id: int, subject_id: int) -> int:
    return db.query(TimetableEntry).filter(
        TimetableEntry.version_id == version_id,
        TimetableEntry.subject_id == subject_id
    ).count()


def _allocation_report(db: Session, version_id: int) -> Tuple[List[str], float]:
    subjects = db.query(Subject).filter(Subject.is_active == True).all()
    if not subjects:
        return [], 0.0

    unallocated: List[str] = []
    fully_allocated = 0
    for subject in subjects:
        required = _subject_required_allocations(subject)
        allocated = _subject_allocated_entries_count(db, version_id, subject.id)
        if allocated < required:
            unallocated.append(subject.code)
        else:
            fully_allocated += 1

    percent = (fully_allocated / len(subjects)) * 100 if subjects else 0.0
    return unallocated, percent


@router.post("/generate", response_model=ScheduleGenerationResponse)
async def generate_timetable(
    request: GenerateScheduleRequest,
    db: Session = Depends(get_db),
):
    try:
        version_name = f"v-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        version = activate_new_version(db, name=version_name, source="generated")
        scheduler = SchedulerEngine(db, seed=request.seed, version_id=version.id)

        success, report = scheduler.schedule_all(
            force_clear=True,
            include_clubs=request.include_clubs,
            fill_extracurricular=request.fill_extracurricular
        )

        metadata = ScheduleMetadata(
            generated_at=datetime.utcnow(),
            generation_seed=request.seed,
            generation_time_ms=report.get("generation_time_ms", 0),
            is_valid=success,
            conflict_count=report.get("conflicts", 0),
            unallocated_subjects_count=report.get("failed", 0),
            notes=f"version_id={version.id}"
        )
        db.add(metadata)
        db.commit()

        return ScheduleGenerationResponse(
            success=success,
            message=report.get("message", "Timetable generated"),
            version_id=version.id,
            generation_time_ms=report.get("generation_time_ms"),
            conflict_count=report.get("conflicts", 0),
            unallocated_subjects=report.get("failed", 0),
            failed_subjects=[f[0] for f in report.get("failed_subjects", [])]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating timetable: {str(e)}")


@router.get("/versions")
async def list_versions(db: Session = Depends(get_db)):
    versions = db.query(TimetableVersion).order_by(TimetableVersion.created_at.desc()).all()
    return [
        {
            "id": v.id,
            "name": v.name,
            "is_active": v.is_active,
            "source": v.source,
            "created_at": v.created_at,
            "entries": db.query(TimetableEntry).filter(TimetableEntry.version_id == v.id).count(),
        }
        for v in versions
    ]


@router.post("/versions/{version_id}/activate")
async def activate_version(version_id: int, db: Session = Depends(get_db)):
    target = db.query(TimetableVersion).filter(TimetableVersion.id == version_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="Version not found")
    db.query(TimetableVersion).update({TimetableVersion.is_active: False}, synchronize_session=False)
    target.is_active = True
    db.commit()
    return {"success": True, "active_version_id": target.id}


@router.post("/reshuffle")
async def reshuffle_schedule(request: ReshuffleRequest, db: Session = Depends(get_db)):
    version = _active_version_or_404(db)
    scheduler = SchedulerEngine(db, seed=request.seed, version_id=version.id)
    success, report = scheduler.reshuffle_preserving_locked(
        include_clubs=request.include_clubs,
        fill_extracurricular=request.fill_extracurricular
    )
    return {"success": success, "message": report.get("message"), "report": report}


@router.get("", response_model=dict)
async def get_full_timetable(db: Session = Depends(get_db)):
    try:
        version = get_active_version(db)
        if version is None:
            return {"version_id": None, "total_entries": 0, "days": [], "message": "No timetable generated yet"}
        query = db.query(TimetableEntry).filter(TimetableEntry.version_id == version.id)
        entries = query.order_by(TimetableEntry.day_of_week, TimetableEntry.period_number).all()
        if not entries:
            return {"version_id": version.id, "total_entries": 0, "days": [], "message": "No timetable generated yet"}

        timetable_by_day = {}
        for entry in entries:
            day = entry.day_of_week.value
            timetable_by_day.setdefault(day, []).append({
                "id": entry.id,
                "period": entry.period_number,
                "branch": entry.branch.code if entry.branch else None,
                "year_section": f"{entry.year_section.year}{entry.year_section.section}" if entry.year_section else None,
                "subject": entry.subject.code if entry.subject else None,
                "faculty": entry.faculty.name if entry.faculty else None,
                "classroom": entry.classroom.room_number if entry.classroom else None,
                "labroom": entry.labroom.room_number if entry.labroom else None,
                "type": entry.session_type.value,
                "locked": entry.is_locked,
            })

        return {
            "version_id": version.id,
            "version_name": version.name,
            "total_entries": len(entries),
            "days": timetable_by_day,
            "generated_at": entries[0].created_at if entries else None
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving timetable: {str(e)}")


@router.get("/{branch_code}/{year}/{section}")
async def get_branch_timetable(
    branch_code: str,
    year: int,
    section: str,
    db: Session = Depends(get_db)
):
    try:
        version = get_active_version(db)
        if version is None:
            return {
                "version_id": None,
                "branch": branch_code,
                "year": year,
                "section": section,
                "entries": [],
                "message": "No timetable generated yet"
            }
        branch = db.query(Branch).filter(Branch.code == branch_code).first()
        if not branch:
            raise HTTPException(status_code=404, detail=f"Branch {branch_code} not found")

        year_section = db.query(YearSection).filter(
            YearSection.branch_id == branch.id,
            YearSection.year == year,
            YearSection.section == section
        ).first()
        if not year_section:
            raise HTTPException(status_code=404, detail=f"Year/Section {year}{section} not found for {branch_code}")

        entries = db.query(TimetableEntry).filter(
            TimetableEntry.version_id == version.id,
            TimetableEntry.branch_id == branch.id,
            TimetableEntry.year_section_id == year_section.id
        ).order_by(
            TimetableEntry.day_of_week, TimetableEntry.period_number
        ).all()

        if not entries:
            return {
                "version_id": version.id,
                "branch": branch_code,
                "year": year,
                "section": section,
                "entries": [],
                "message": "No timetable entries found"
            }

        formatted = [{
            "id": e.id,
            "day": e.day_of_week.value,
            "period": e.period_number,
            "subject": e.subject.code if e.subject else None,
            "subject_name": e.subject.name if e.subject else ("Break" if e.session_type == SessionType.BREAK else "Extracurricular" if e.session_type == SessionType.EXTRACURRICULAR else None),
            "faculty": e.faculty.name if e.faculty else None,
            "classroom": e.classroom.room_number if e.classroom else None,
            "labroom": e.labroom.room_number if e.labroom else None,
            "type": e.session_type.value,
            "locked": e.is_locked
        } for e in entries]

        return {
            "version_id": version.id,
            "branch": branch_code,
            "year": year,
            "section": section,
            "entries": formatted,
            "total": len(formatted)
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving timetable: {str(e)}")


@router.get("/export/{branch_code}/{year}/{section}")
async def export_branch_timetable_pdf(
    branch_code: str,
    year: int,
    section: str,
    db: Session = Depends(get_db)
):
    try:
        version = _active_version_or_404(db)
        branch = db.query(Branch).filter(Branch.code == branch_code).first()
        if not branch:
            raise HTTPException(status_code=404, detail=f"Branch {branch_code} not found")

        year_section = db.query(YearSection).filter(
            YearSection.branch_id == branch.id,
            YearSection.year == year,
            YearSection.section == section
        ).first()
        if not year_section:
            raise HTTPException(status_code=404, detail=f"Year/Section {year}{section} not found for {branch_code}")

        entries = db.query(TimetableEntry).filter(
            TimetableEntry.version_id == version.id,
            TimetableEntry.branch_id == branch.id,
            TimetableEntry.year_section_id == year_section.id
        ).order_by(
            TimetableEntry.day_of_week, TimetableEntry.period_number
        ).all()

        if not entries:
            raise HTTPException(status_code=404, detail="No timetable entries found")

        lines = [f"Timetable Export - {branch_code} Year {year} Section {section} ({version.name})", ""]
        for entry in entries:
            subject = entry.subject.code if entry.subject else entry.session_type.value
            faculty = entry.faculty.name if entry.faculty else "N/A"
            room = entry.classroom.room_number if entry.classroom else entry.labroom.room_number if entry.labroom else "N/A"
            lines.append(
                f"{entry.day_of_week.value} P{entry.period_number}: {subject} | {faculty} | {room} | {entry.session_type.value}"
            )

        pdf_bytes = _build_simple_pdf(lines)
        filename = f"timetable_{branch_code}_{year}_{section}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error exporting timetable: {str(e)}")


@router.post("/entry/{entry_id}/lock")
async def lock_entry(entry_id: int, request: LockRequest, db: Session = Depends(get_db)):
    version = _active_version_or_404(db)
    entry = db.query(TimetableEntry).filter(
        TimetableEntry.id == entry_id,
        TimetableEntry.version_id == version.id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found in active version")
    entry.is_locked = request.locked
    db.commit()
    return {"success": True, "entry_id": entry.id, "locked": entry.is_locked}


@router.post("/entry/move")
async def move_entry(request: MoveEntryRequest, db: Session = Depends(get_db)):
    version = _active_version_or_404(db)
    entry = db.query(TimetableEntry).filter(
        TimetableEntry.id == request.entry_id,
        TimetableEntry.version_id == version.id
    ).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found in active version")
    if entry.is_locked:
        raise HTTPException(status_code=400, detail="Entry is locked")
    if entry.session_type == SessionType.LAB:
        raise HTTPException(status_code=400, detail="Use swap/assign for labs to preserve 2-period blocks")

    validator = ConstraintValidator(db, version_id=version.id)
    if request.day_of_week == DayOfWeek.THURSDAY and request.period_number in (1, 7):
        raise HTTPException(status_code=400, detail="Thursday P1/P7 are reserved")

    if entry.classroom_id is not None:
        if entry.session_type == SessionType.SEMINAR:
            ok, reason = validator.can_schedule_seminar(
                entry.branch_id, entry.year_section_id, entry.faculty_id, entry.classroom_id,
                request.day_of_week, request.period_number, exclude_entry_id=entry.id
            )
        else:
            ok, reason = validator.can_schedule_lecture_or_tutorial(
                entry.branch_id, entry.year_section_id, entry.faculty_id, entry.classroom_id,
                request.day_of_week, request.period_number, exclude_entry_id=entry.id
            )
    else:
        ok = validator.is_branch_slot_free(
            entry.branch_id, entry.year_section_id, request.day_of_week, request.period_number, exclude_entry_id=entry.id
        )
        reason = None if ok else "Target slot is occupied"

    if not ok:
        raise HTTPException(status_code=400, detail=reason or "Cannot move entry")

    entry.day_of_week = request.day_of_week
    entry.period_number = request.period_number
    db.commit()
    return {"success": True, "entry_id": entry.id}


@router.post("/entry/swap")
async def swap_entries(request: SwapEntriesRequest, db: Session = Depends(get_db)):
    version = _active_version_or_404(db)
    first = db.query(TimetableEntry).filter(
        TimetableEntry.id == request.first_entry_id,
        TimetableEntry.version_id == version.id
    ).first()
    second = db.query(TimetableEntry).filter(
        TimetableEntry.id == request.second_entry_id,
        TimetableEntry.version_id == version.id
    ).first()
    if not first or not second:
        raise HTTPException(status_code=404, detail="One or both entries not found")
    if first.is_locked or second.is_locked:
        raise HTTPException(status_code=400, detail="Locked entries cannot be swapped")
    if first.session_type == SessionType.LAB or second.session_type == SessionType.LAB:
        raise HTTPException(status_code=400, detail="Lab swap should be done using assign flow to keep 2-period integrity")

    validator = ConstraintValidator(db, version_id=version.id)
    f_day, f_period = first.day_of_week, first.period_number
    s_day, s_period = second.day_of_week, second.period_number

    if first.classroom_id is not None:
        ok1, reason1 = validator.can_schedule_lecture_or_tutorial(
            first.branch_id, first.year_section_id, first.faculty_id, first.classroom_id,
            s_day, s_period, exclude_entry_id=first.id
        )
    else:
        ok1 = validator.is_branch_slot_free(first.branch_id, first.year_section_id, s_day, s_period, exclude_entry_id=first.id)
        reason1 = None if ok1 else "First entry conflicts at target slot"

    if second.classroom_id is not None:
        ok2, reason2 = validator.can_schedule_lecture_or_tutorial(
            second.branch_id, second.year_section_id, second.faculty_id, second.classroom_id,
            f_day, f_period, exclude_entry_id=second.id
        )
    else:
        ok2 = validator.is_branch_slot_free(second.branch_id, second.year_section_id, f_day, f_period, exclude_entry_id=second.id)
        reason2 = None if ok2 else "Second entry conflicts at target slot"

    if not ok1:
        raise HTTPException(status_code=400, detail=reason1 or "Invalid swap for first entry")
    if not ok2:
        raise HTTPException(status_code=400, detail=reason2 or "Invalid swap for second entry")

    first.day_of_week, second.day_of_week = second.day_of_week, first.day_of_week
    first.period_number, second.period_number = second.period_number, first.period_number
    db.commit()
    return {"success": True}


@router.post("/entry/assign")
async def assign_entry(request: AssignEntryRequest, db: Session = Depends(get_db)):
    version = _active_version_or_404(db)
    if request.day_of_week == DayOfWeek.THURSDAY and request.period_number in (1, 7):
        raise HTTPException(status_code=400, detail="Thursday P1/P7 are reserved")
    if request.session_type == SessionType.LAB and request.period_number in (1, 2, 7):
        raise HTTPException(status_code=400, detail="Labs cannot start in P1/P2/P7")

    branch = db.query(Branch).filter(Branch.code == request.branch_code).first()
    if not branch:
        raise HTTPException(status_code=404, detail="Branch not found")

    ys = db.query(YearSection).filter(
        YearSection.branch_id == branch.id,
        YearSection.year == request.year,
        YearSection.section == request.section
    ).first()
    if not ys:
        raise HTTPException(status_code=404, detail="Year/Section not found")

    validator = ConstraintValidator(db, version_id=version.id)
    subject = None
    if request.subject_code:
        subject = db.query(Subject).filter(
            Subject.code == request.subject_code,
            Subject.branch_id == branch.id,
            Subject.year == request.year,
            Subject.section == request.section,
            Subject.is_active == True
        ).first()
        if not subject:
            raise HTTPException(status_code=404, detail="Subject not found")

    if not validator.is_branch_slot_free(branch.id, ys.id, request.day_of_week, request.period_number):
        raise HTTPException(status_code=400, detail="Slot already occupied")

    if subject and request.session_type == SessionType.LAB:
        if subject.labroom_id is None:
            raise HTTPException(status_code=400, detail="Selected subject has no lab room")
        ok, reason = validator.can_schedule_lab(
            branch.id, ys.id, subject.faculty_id, subject.labroom_id,
            request.day_of_week, request.period_number, duration=2
        )
        if not ok:
            raise HTTPException(status_code=400, detail=reason)
        periods = [request.period_number, request.period_number + 1]
    elif subject and request.session_type == SessionType.SEMINAR:
        if subject.classroom_id is None:
            raise HTTPException(status_code=400, detail="Selected subject has no classroom")
        ok, reason = validator.can_schedule_seminar(
            branch.id, ys.id, subject.faculty_id, subject.classroom_id,
            request.day_of_week, request.period_number
        )
        if not ok:
            raise HTTPException(status_code=400, detail=reason)
        periods = [request.period_number]
    elif subject and request.session_type in (SessionType.LECTURE, SessionType.TUTORIAL):
        if subject.classroom_id is None:
            raise HTTPException(status_code=400, detail="Selected subject has no classroom")
        ok, reason = validator.can_schedule_lecture_or_tutorial(
            branch.id, ys.id, subject.faculty_id, subject.classroom_id,
            request.day_of_week, request.period_number
        )
        if not ok:
            raise HTTPException(status_code=400, detail=reason)
        periods = [request.period_number]
    else:
        periods = [request.period_number]

    created = 0
    for p in periods:
        db.add(TimetableEntry(
            day_of_week=request.day_of_week,
            period_number=p,
            version_id=version.id,
            branch_id=branch.id,
            year_section_id=ys.id,
            subject_id=subject.id if subject else None,
            faculty_id=subject.faculty_id if subject else None,
            classroom_id=subject.classroom_id if subject else None,
            labroom_id=subject.labroom_id if subject else None,
            session_type=request.session_type,
            is_locked=request.lock
        ))
        created += 1
    db.commit()
    return {"success": True, "created_entries": created}


@router.delete("/clear")
async def clear_timetable(db: Session = Depends(get_db)):
    try:
        deleted_entries = db.query(TimetableEntry).delete(synchronize_session=False)
        deleted_versions = db.query(TimetableVersion).delete(synchronize_session=False)
        db.commit()
        return {"success": True, "message": f"Cleared {deleted_entries} entries and {deleted_versions} versions"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error clearing timetable: {str(e)}")


@router.post("/validate", response_model=ValidationReport)
async def validate_schedule(db: Session = Depends(get_db)):
    try:
        version = _active_version_or_404(db)
        validator = ConstraintValidator(db, version_id=version.id)
        is_valid, conflicts = validator.validate_full_schedule()
        unallocated, allocation_percentage = _allocation_report(db, version.id)
        formatted_conflicts = [
            ConflictReport(
                conflict_type="Faculty" if "Faculty" in conflict else "Classroom" if "Classroom" in conflict else "Section" if "Section" in conflict else "Lab Room",
                day_of_week="",
                period_number=0,
                involved_subjects=[],
                description=conflict
            )
            for conflict in conflicts
        ]
        return ValidationReport(
            is_valid=is_valid,
            total_conflicts=len(conflicts),
            conflicts=formatted_conflicts,
            unallocated_subjects=unallocated,
            allocation_percentage=allocation_percentage
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error validating schedule: {str(e)}")


@router.get("/statistics", response_model=ScheduleStatistics)
async def get_schedule_statistics(db: Session = Depends(get_db)):
    try:
        version = _active_version_or_404(db)
        entries_query = db.query(TimetableEntry).filter(TimetableEntry.version_id == version.id)

        total_entries = entries_query.count()
        lectures = entries_query.filter(TimetableEntry.session_type == SessionType.LECTURE).count()
        tutorials = entries_query.filter(TimetableEntry.session_type == SessionType.TUTORIAL).count()
        labs = entries_query.filter(TimetableEntry.session_type == SessionType.LAB).count()
        seminars = entries_query.filter(TimetableEntry.session_type == SessionType.SEMINAR).count()
        clubs = entries_query.filter(TimetableEntry.session_type == SessionType.CLUB).count()

        total_subjects = db.query(Subject).filter(Subject.is_active == True).count()
        total_branches = db.query(Branch).count()
        total_faculty = db.query(Faculty).filter(Faculty.is_active == True).count()
        total_classrooms = db.query(Classroom).filter(Classroom.is_active == True).count()
        total_labrooms = db.query(LabRoom).filter(LabRoom.is_active == True).count()

        faculty_slots_used = entries_query.filter(TimetableEntry.faculty_id.isnot(None)).count()
        classroom_slots_used = entries_query.filter(
            TimetableEntry.classroom_id.isnot(None),
            TimetableEntry.session_type != SessionType.CLUB
        ).count()
        labroom_slots_used = entries_query.filter(TimetableEntry.labroom_id.isnot(None)).count()

        faculty_utilization = (faculty_slots_used / (total_faculty * 42)) * 100 if total_faculty > 0 else 0
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
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving statistics: {str(e)}")
