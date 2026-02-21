"""
College Timetable System — Pydantic Schemas
Guide-compliant field definitions.
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
    password: str                 # plain-text on input; stored as bcrypt hash

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
    section: str = "A"             # "A" | "B" | "C" (guide §4 required field)
    lectures_per_week: int


class AssignmentUploadResponse(BaseModel):
    upload_id: str
    admin_email: str
    rows_parsed: int
    assignments_preview: List[Dict[str, Any]]


# ── Guide §4 Timetable Slot ───────────────────────────────────────────────────

class TimetableSlot(BaseModel):
    """
    A single period in the generated timetable — exact guide §4 fields only.
    """
    day: str         # "Monday" … "Saturday"
    period: int      # 1-based, 1–7
    branch: str
    year: int        # integer (guide requirement)
    section: str     # "A" | "B" | "C"
    subject: str
    faculty: str
    room: str
    type: str        # "LECTURE" | "LAB" | "TUTORIAL" | "SEMINAR" | "CLUB"


# ── Generate Request / Response ───────────────────────────────────────────────

class GenerateTimetableRequest(BaseModel):
    admin_id: str
    branch: Optional[str] = None    # if None → generate for all branches
    year: Optional[str] = None      # if None → generate for all years
    section: Optional[str] = None   # if None → generate for all sections
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
