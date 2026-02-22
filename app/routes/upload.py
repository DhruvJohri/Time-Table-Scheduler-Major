"""
Upload routes for importing Excel master and assignment files into the DB.
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends
from typing import List
import pandas as pd
import io
from app.models.database import get_db
from sqlalchemy.orm import Session
from app.models.models import Branch, YearSection, Subject, Faculty
from datetime import datetime
from app.services.scheduling_engine import SchedulerEngine

router = APIRouter(prefix="/api/upload", tags=["upload"])

# Branch normalization map
BRANCH_MAP = {
    "CS": "CSE",
    "C.S.": "CSE",
    "COMPUTER SCIENCE": "CSE"
}


def _normalize_branch(name: str) -> str:
    if not name:
        return name
    n = name.strip().upper()
    return BRANCH_MAP.get(n, n)


def _get_or_create_branch(db: Session, code: str) -> Branch:
    code_norm = _normalize_branch(code)
    branch = db.query(Branch).filter(Branch.code == code_norm).first()
    if branch:
        return branch
    branch = Branch(code=code_norm, name=code_norm)
    db.add(branch)
    db.flush()
    db.refresh(branch)
    return branch


def _get_or_create_year_section(db: Session, branch: Branch, year: int, section: str) -> YearSection:
    section = (section or "A").strip().upper()
    ys = db.query(YearSection).filter(
        YearSection.branch_id == branch.id,
        YearSection.year == year,
        YearSection.section == section
    ).first()
    if ys:
        return ys
    ys = YearSection(branch_id=branch.id, year=year, section=section)
    db.add(ys)
    db.flush()
    db.refresh(ys)
    return ys


def _get_or_create_unassigned_faculty(db: Session) -> Faculty:
    fac = db.query(Faculty).filter(Faculty.employee_id == "UNASSIGNED").first()
    if fac:
        return fac
    fac = Faculty(employee_id="UNASSIGNED", name="Unassigned", department="GENERAL")
    db.add(fac)
    db.flush()
    db.refresh(fac)
    return fac


@router.post("/master")
async def import_master(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import master subjects Excel into `subjects` table."""

    # -------------------------
    # FILE VALIDATION
    # -------------------------
    try:
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) allowed")

        contents = await file.read()

        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")

        df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel: {e}")

    subjects_imported = 0
    warnings: List[str] = []

    # Ensure placeholder objects exist
    unassigned_fac = _get_or_create_unassigned_faculty(db)
    default_branch = _get_or_create_branch(db, "GEN")
    default_year_section = _get_or_create_year_section(db, default_branch, 1, "A")

    # -------------------------
    # SAFE DATABASE TRANSACTION
    # -------------------------
    try:
        for _, row in df.iterrows():
            name = (row.get("SubjectName") or row.get("Subject") or "").strip()
            code = (row.get("SubjectCode") or row.get("Code") or "").strip()
            lectures = int(row.get("Lecture") or row.get("Lectures") or 0)
            tutorials = int(row.get("Tutorial") or row.get("Tutorials") or 0)
            labs = int(row.get("Lab") or row.get("Labs") or 0)
            lab_duration = int(row.get("LabDuration") or 2)

            if not code and not name:
                warnings.append("Skipped empty master row")
                continue

            subject = None

            if code:
                subject = db.query(Subject).filter(Subject.code == code).first()

            if not subject and name:
                subject = db.query(Subject).filter(Subject.name == name).first()

            if subject:
                subject.name = name or subject.name
                subject.code = code or subject.code
                subject.lectures_per_week = lectures
                subject.tutorials_per_week = tutorials
                subject.lab_periods_per_week = labs
                subject.lab_duration = lab_duration
                db.add(subject)
            else:
                subj = Subject(
                    code=code or name[:8],
                    name=name or code,
                    branch_id=default_branch.id,
                    year=default_year_section.year,
                    section=default_year_section.section,
                    lectures_per_week=lectures,
                    tutorials_per_week=tutorials,
                    lab_periods_per_week=labs,
                    seminar_periods_per_week=0,
                    lab_duration=lab_duration,
                    faculty_id=unassigned_fac.id
                )
                db.add(subj)

            subjects_imported += 1

        # Commit once after all rows processed
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Master import failed: {e}")

    # -------------------------
    # OPTIONAL: Trigger Regeneration
    # -------------------------
    try:
        scheduler = SchedulerEngine(db)
        success, report = scheduler.schedule_all(force_clear=True)
    except Exception as e:
        report = {"error": f"Scheduling failed: {e}"}

    return {
        "subjects_imported": subjects_imported,
        "warnings": warnings,
        "scheduling_report": report
    }


@router.post("/assignments")
async def import_assignments(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import assignments Excel and create/update linked subjects and faculty."""

    # -------------------------
    # FILE VALIDATION
    # -------------------------
    try:
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail="Only Excel files (.xlsx, .xls) allowed")

        contents = await file.read()

        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File too large (max 5MB)")

        df = pd.read_excel(io.BytesIO(contents), engine="openpyxl")

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read Excel: {e}")

    tasks_imported = 0
    warnings: List[str] = []

    # -------------------------
    # SAFE DATABASE TRANSACTION
    # -------------------------
    try:
        for _, row in df.iterrows():
            subject_name = (row.get("SubjectName") or row.get("Subject") or "").strip()
            teacher_name = (row.get("TeacherName") or row.get("Teacher") or "Unassigned").strip()
            branch_raw = (row.get("Branch") or row.get("Dept") or "").strip()
            year = int(row.get("Year") or 1)
            lectures = int(row.get("LecturesPerWeek") or row.get("Lectures") or 0)
            section = (row.get("Section") or "A").strip().upper()

            if not subject_name:
                warnings.append("Skipped assignment with empty subject")
                continue

            # Normalize branch
            branch_code = _normalize_branch(branch_raw or "GEN")
            branch = _get_or_create_branch(db, branch_code)

            # Year/Section
            ys = _get_or_create_year_section(db, branch, year, section)

            # Find subject safely (branch + year + section scoped)
            subject = db.query(Subject).filter(
                Subject.name == subject_name,
                Subject.branch_id == branch.id,
                Subject.year == year,
                Subject.section == section
            ).first()

            if not subject:
                warnings.append(f"{subject_name} missing in master; auto-created")

                unassigned_fac = _get_or_create_unassigned_faculty(db)

                subject = Subject(
                    code=subject_name[:8].upper(),
                    name=subject_name,
                    branch_id=branch.id,
                    year=year,
                    section=section,
                    lectures_per_week=lectures,
                    tutorials_per_week=0,
                    lab_periods_per_week=0,
                    seminar_periods_per_week=0,
                    lab_duration=2,
                    faculty_id=unassigned_fac.id
                )

                db.add(subject)
                db.flush()
                db.refresh(subject)

            # Find or create teacher
            faculty = db.query(Faculty).filter(Faculty.name == teacher_name).first()

            if not faculty:
                faculty = Faculty(
                    employee_id=(teacher_name[:10] or "T000"),
                    name=teacher_name
                )
                db.add(faculty)
                db.flush()
                db.refresh(faculty)

            # Update subject mapping
            subject.branch_id = branch.id
            subject.year = year
            subject.section = section
            subject.lectures_per_week = lectures or subject.lectures_per_week
            subject.faculty_id = faculty.id

            db.add(subject)
            tasks_imported += 1

        # Commit all changes safely
        db.commit()

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Assignment import failed: {e}")

    # -------------------------
    # OPTIONAL: Trigger Regeneration
    # -------------------------
    try:
        scheduler = SchedulerEngine(db)
        success, report = scheduler.schedule_all(force_clear=True)
    except Exception as e:
        report = {"error": f"Scheduling failed: {e}"}

    return {
        "tasks_imported": tasks_imported,
        "warnings": warnings,
        "scheduling_report": report
    }