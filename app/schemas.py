"""
College Timetable System — Pydantic Schemas
"""

from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# ── Admin Profile ─────────────────────────────────────────────────────────────

class AdminProfileSchema(BaseModel):
    """Admin / institution profile."""
    email: EmailStr
    name: str
    college_name: str
    role: str = "admin"           # admin | coordinator | viewer

    class Config:
        from_attributes = True


# ── Master Data (Upload 1) ────────────────────────────────────────────────────

class TeacherEntry(BaseModel):
    teacher_name: str
    subjects: List[str] = []
    max_hours_per_day: int = 6


class SubjectEntry(BaseModel):
    subject_name: str
    is_lab: bool = False
    default_room_type: str = "lecture"   # lecture | lab


class RoomEntry(BaseModel):
    room_name: str
    capacity: int = 60
    room_type: str = "lecture"           # lecture | lab


class MasterDataUploadResponse(BaseModel):
    upload_id: str
    admin_email: str
    teachers_count: int
    subjects_count: int
    rooms_count: int
    teachers_preview: List[str]
    subjects_preview: List[str]
    rooms_preview: List[str]


# ── Assignment Data (Upload 2) ────────────────────────────────────────────────

class AssignmentEntry(BaseModel):
    teacher_name: str
    subject_name: str
    year: str                      # "1" | "2" | "3" | "4"
    branch: str                    # "CS" | "EC" | "ME" | ...
    lectures_per_week: int


class AssignmentUploadResponse(BaseModel):
    upload_id: str
    admin_email: str
    rows_parsed: int
    assignments_preview: List[Dict[str, Any]]


# ── Timetable Slot ────────────────────────────────────────────────────────────

class TimetableSlot(BaseModel):
    """A single period in the generated timetable."""
    day: str                       # Monday … Saturday
    period: int                    # 1-based slot index
    start_time: str                # HH:MM
    end_time: str                  # HH:MM
    subject: str
    teacher: str
    room: str
    branch: str
    year: str
    is_lab: bool = False
    is_free: bool = False


# ── Generate Request / Response ───────────────────────────────────────────────

class GenerateTimetableRequest(BaseModel):
    admin_id: str
    branch: Optional[str] = None   # if None → generate for all branches
    year: Optional[str] = None     # if None → generate for all years
    start_date: Optional[str] = None


class TimetableVersionSummary(BaseModel):
    """Lightweight version entry for history list."""
    id: str
    version: int
    label: str
    branch: str
    year: str
    created_at: Optional[datetime] = None


# ── Export ────────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    format: str    # pdf | xlsx | csv | json
