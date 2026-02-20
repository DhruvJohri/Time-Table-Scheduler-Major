"""
Assignment Data Upload Route
POST /api/upload/assignment
Columns required: TeacherName | SubjectName | Year | Branch | LecturesPerWeek
Admin is identified by the admin_email query param passed by the frontend.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Query, status
from io import BytesIO
from datetime import datetime
from typing import Optional
import pandas as pd

from app.models.database import users_collection, assignment_data_collection

router = APIRouter(prefix="/api/upload", tags=["upload"])

REQUIRED_COLUMNS = {"TeacherName", "SubjectName", "Year", "Branch", "LecturesPerWeek"}
ALLOWED_EXTS = (".xlsx", ".xls")


def _validate_columns(df: pd.DataFrame):
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Missing required columns: {sorted(missing)}. Required: {sorted(REQUIRED_COLUMNS)}"
        )


def _validate_row(row: pd.Series, idx: int):
    try:
        lpw = int(row["LecturesPerWeek"])
    except (ValueError, TypeError):
        raise HTTPException(status_code=422,
                            detail=f"Row {idx}: LecturesPerWeek must be an integer.")
    if lpw < 1 or lpw > 20:
        raise HTTPException(status_code=422,
                            detail=f"Row {idx}: LecturesPerWeek must be 1–20, got {lpw}.")
    for col in ("TeacherName", "SubjectName", "Year", "Branch"):
        val = str(row.get(col, "")).strip()
        if not val:
            raise HTTPException(status_code=422,
                                detail=f"Row {idx}: '{col}' must not be empty.")


def _find_admin(email: str):
    """Case-insensitive admin lookup. Returns (admin_id, email) or raises 422."""
    email = email.strip()
    admin = users_collection.find_one(
        {"email": {"$regex": f"^{email}$", "$options": "i"}}
    )
    if not admin:
        raise HTTPException(
            status_code=422,
            detail=f"No admin profile for '{email}'. Create one via POST /api/profiles first."
        )
    return str(admin["_id"]), str(admin["email"])


@router.post("/assignment", status_code=status.HTTP_201_CREATED)
async def upload_assignment_data(
    file: UploadFile = File(...),
    admin_email: Optional[str] = Query(None, description="Admin email (required)"),
):
    """
    Upload Assignment Data Excel file.
    Required columns: TeacherName, SubjectName, Year, Branch, LecturesPerWeek
    Admin is identified via the admin_email query parameter.
    """
    if not admin_email:
        raise HTTPException(
            status_code=422,
            detail="admin_email query parameter is required."
        )

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

    # Resolve admin from query param
    resolved_id, resolved_email = _find_admin(admin_email)

    assignments = []
    for _, row in df.iterrows():
        assignments.append({
            "teacher_name":      str(row["TeacherName"]).strip(),
            "subject_name":      str(row["SubjectName"]).strip(),
            "year":              str(row["Year"]).strip(),
            "branch":            str(row["Branch"]).strip(),
            "lectures_per_week": int(row["LecturesPerWeek"]),
        })

    doc = {
        "admin_email": resolved_email,
        "admin_id":    resolved_id,
        "filename":    filename,
        "assignments": assignments,
        "created_at":  datetime.utcnow(),
    }
    res = assignment_data_collection.insert_one(doc)
    return {
        "upload_id":           str(res.inserted_id),
        "admin_email":         resolved_email,
        "admin_id":            resolved_id,
        "rows_parsed":         len(assignments),
        "assignments_preview": assignments[:5],
    }
