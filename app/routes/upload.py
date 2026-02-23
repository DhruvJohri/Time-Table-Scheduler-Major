"""
Upload routes for frontend Excel uploads.

These endpoints parse and synchronize uploaded .xlsx files with SQL data.
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.services.excel_sync import import_master_file, import_assignment_file

router = APIRouter(prefix="/upload", tags=["upload"])


def _validate_excel_file(file: UploadFile) -> None:
    filename = (file.filename or "").lower()
    if not filename.endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Only .xlsx files are allowed")


@router.post("/master")
async def upload_master(file: UploadFile = File(...), db: Session = Depends(get_db)):
    _validate_excel_file(file)
    content = await file.read()
    report = import_master_file(db, content)
    if not report.get("success"):
        raise HTTPException(status_code=400, detail=report.get("message", "Master upload failed"))
    return {
        "success": report.get("success", True),
        "filename": file.filename,
        "size_bytes": len(content),
        "message": report.get("message", "Master file synchronized"),
        "processed_rows": report.get("processed_rows", 0),
        "issues": report.get("issues", []),
    }


@router.post("/assignment")
async def upload_assignment(file: UploadFile = File(...), db: Session = Depends(get_db)):
    _validate_excel_file(file)
    content = await file.read()
    report = import_assignment_file(db, content)
    if not report.get("success"):
        raise HTTPException(status_code=400, detail=report.get("message", "Assignment upload failed"))
    return {
        "success": report.get("success", True),
        "filename": file.filename,
        "size_bytes": len(content),
        "message": report.get("message", "Assignment file synchronized"),
        "processed_rows": report.get("processed_rows", 0),
        "issues": report.get("issues", []),
    }
