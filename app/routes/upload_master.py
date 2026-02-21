"""
Master Data Upload Route
POST /api/upload/master?admin_email=...
Columns required: TeacherName | SubjectName | Year | Branch | Classroom
Each row represents: teacher X teaches subject Y to branch Z / year W in room R.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, status
from io import BytesIO
from datetime import datetime
from typing import Optional
import pandas as pd

from app.models.database import users_collection, master_data_collection


router = APIRouter(prefix="/api/upload", tags=["upload"])

REQUIRED_COLUMNS = {"TeacherName", "SubjectName", "Year", "Branch", "Classroom"}
ALLOWED_EXTS     = (".xlsx", ".xls")


def _validate_columns(df: pd.DataFrame):
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required columns: {sorted(missing)}. Required: {sorted(REQUIRED_COLUMNS)}"
        )


def _validate_row(row: pd.Series, idx: int):
    for col in REQUIRED_COLUMNS:
        val = str(row.get(col, "")).strip()
        if not val or val.lower() == "nan":
            raise HTTPException(
                status_code=422,
                detail=f"Row {idx}: '{col}' must not be empty."
            )


@router.post("/master", status_code=status.HTTP_201_CREATED)
async def upload_master_data(
    file: UploadFile = File(...),
    admin_email: Optional[str] = Query(None, description="Admin email"),
):
    """
    Upload Master Data Excel file.
    Required columns: TeacherName, SubjectName, Year, Branch, Classroom
    Each row encodes one teaching assignment with its classroom.
    """
    filename = file.filename or ""
    if not any(filename.lower().endswith(ext) for ext in ALLOWED_EXTS):
        raise HTTPException(status_code=422, detail="Only .xlsx and .xls files are accepted.")

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")

    try:
        df = pd.read_excel(BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Cannot parse Excel: {exc}")

    if df.empty:
        raise HTTPException(status_code=422, detail="Excel file contains no data rows.")

    _validate_columns(df)

    for idx, row in df.iterrows():
        _validate_row(row, idx + 2)

    # ── Resolve admin (optional – still used to tag data) ─────────────────────
    admin_id = None
    resolved_email = admin_email.strip() if admin_email else None
    if resolved_email:
        admin = users_collection.find_one(
            {"email": {"$regex": f"^{resolved_email}$", "$options": "i"}}
        )
        if not admin:
            raise HTTPException(
                status_code=422,
                detail=f"No admin profile for '{resolved_email}'. Create one via POST /api/profiles first."
            )
        admin_id      = str(admin["_id"])
        resolved_email = str(admin["email"])

    # ── Parse rows ────────────────────────────────────────────────────────────
    records = []
    for _, row in df.iterrows():
        teacher   = str(row["TeacherName"]).strip()
        subject   = str(row["SubjectName"]).strip()
        year      = str(row["Year"]).strip()
        branch    = str(row["Branch"]).strip()
        classroom = str(row["Classroom"]).strip()

        records.append({
            "teacher_name": teacher,
            "subject_name": subject,
            "year":         year,
            "branch":       branch,
            "classroom":    classroom,
        })

    # ── Derive unique lists from rows ─────────────────────────────────────────
    teachers   = sorted({r["teacher_name"] for r in records})
    subjects   = sorted({r["subject_name"] for r in records})
    classrooms = sorted({r["classroom"]    for r in records})

    # ── Store ─────────────────────────────────────────────────────────────────
    doc = {
        "admin_email": resolved_email,
        "admin_id":    admin_id,
        "filename":    filename,
        "records":     records,
        # Derived unique lists for convenience
        "teachers":    teachers,
        "subjects":    subjects,
        "classrooms":  classrooms,
        "created_at":  datetime.utcnow(),
    }
    res = master_data_collection.insert_one(doc)

    return {
        "upload_id":          str(res.inserted_id),
        "admin_id":           admin_id,
        "admin_email":        resolved_email or "",
        "rows_parsed":        len(records),
        "teachers_count":     len(teachers),
        "subjects_count":     len(subjects),
        "classrooms_count":   len(classrooms),
        "records_preview":    records[:5],
    }
