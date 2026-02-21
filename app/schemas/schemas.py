"""
Pydantic schemas for API request/response validation.
"""

from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, validator
from enum import Enum


class DayOfWeekEnum(str, Enum):
    """Days of the week."""
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"


class SessionTypeEnum(str, Enum):
    """Type of class session."""
    LECTURE = "LECTURE"
    TUTORIAL = "TUTORIAL"
    LAB = "LAB"
    SEMINAR = "SEMINAR"
    CLUB = "CLUB"


# Branch Schemas
class BranchBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=10)
    name: str = Field(..., min_length=1, max_length=100)


class BranchCreate(BranchBase):
    pass


class BranchUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None


class BranchResponse(BranchBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# YearSection Schemas
class YearSectionBase(BaseModel):
    branch_id: int
    year: int = Field(..., ge=1, le=4)
    section: str = Field(..., min_length=1, max_length=5)


class YearSectionCreate(YearSectionBase):
    pass


class YearSectionResponse(YearSectionBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Faculty Schemas
class FacultyBase(BaseModel):
    employee_id: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    department: Optional[str] = None
    email: Optional[str] = None


class FacultyCreate(FacultyBase):
    pass


class FacultyUpdate(BaseModel):
    name: Optional[str] = None
    department: Optional[str] = None
    email: Optional[str] = None
    is_active: Optional[bool] = None


class FacultyResponse(FacultyBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Classroom Schemas
class ClassroomBase(BaseModel):
    room_number: str = Field(..., min_length=1, max_length=20)
    capacity: int = Field(..., ge=1)
    building: Optional[str] = None


class ClassroomCreate(ClassroomBase):
    pass


class ClassroomUpdate(BaseModel):
    room_number: Optional[str] = None
    capacity: Optional[int] = None
    building: Optional[str] = None
    is_active: Optional[bool] = None


class ClassroomResponse(ClassroomBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# LabRoom Schemas
class LabRoomBase(BaseModel):
    room_number: str = Field(..., min_length=1, max_length=20)
    lab_type: str = Field(..., min_length=1, max_length=50)
    capacity: int = Field(..., ge=1)
    building: Optional[str] = None


class LabRoomCreate(LabRoomBase):
    pass


class LabRoomUpdate(BaseModel):
    room_number: Optional[str] = None
    lab_type: Optional[str] = None
    capacity: Optional[int] = None
    building: Optional[str] = None
    is_active: Optional[bool] = None


class LabRoomResponse(LabRoomBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Subject Schemas
class SubjectBase(BaseModel):
    code: str = Field(..., min_length=1, max_length=20)
    name: str = Field(..., min_length=1, max_length=100)
    branch_id: int
    year: int = Field(..., ge=1, le=4)
    section: str = Field(..., min_length=1, max_length=5)
    lectures_per_week: int = Field(default=0, ge=0)
    tutorials_per_week: int = Field(default=0, ge=0)
    lab_periods_per_week: int = Field(default=0, ge=0)
    seminar_periods_per_week: int = Field(default=0, ge=0)
    lab_duration: int = Field(default=2, ge=2, le=3)
    faculty_id: int
    classroom_id: Optional[int] = None
    labroom_id: Optional[int] = None


class SubjectCreate(SubjectBase):
    pass


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    lectures_per_week: Optional[int] = None
    tutorials_per_week: Optional[int] = None
    lab_periods_per_week: Optional[int] = None
    seminar_periods_per_week: Optional[int] = None
    lab_duration: Optional[int] = None
    faculty_id: Optional[int] = None
    classroom_id: Optional[int] = None
    labroom_id: Optional[int] = None
    is_active: Optional[bool] = None


class SubjectResponse(SubjectBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# Timetable Entry Schemas
class TimetableEntryBase(BaseModel):
    day_of_week: DayOfWeekEnum
    period_number: int = Field(..., ge=1, le=7)
    branch_id: int
    year_section_id: int
    subject_id: int
    faculty_id: int
    classroom_id: Optional[int] = None
    labroom_id: Optional[int] = None
    session_type: SessionTypeEnum


class TimetableEntryCreate(TimetableEntryBase):
    pass


class TimetableEntryUpdate(BaseModel):
    classroom_id: Optional[int] = None
    labroom_id: Optional[int] = None
    is_locked: Optional[bool] = None


class TimetableEntryResponse(TimetableEntryBase):
    id: int
    created_at: datetime
    is_locked: bool

    class Config:
        from_attributes = True


# Timetable Display Schema
class TimetableDisplayEntry(BaseModel):
    day_of_week: str
    period_number: int
    branch_code: str
    year: int
    section: str
    subject_code: str
    subject_name: str
    faculty_name: str
    room_number: Optional[str]
    session_type: str


class TimetableViewBranchYearSection(BaseModel):
    branch_code: str
    year: int
    section: str
    entries: List[TimetableDisplayEntry]


# Schedule Generation Request/Response
class GenerateScheduleRequest(BaseModel):
    seed: Optional[int] = None
    force_regenerate: bool = False
    include_clubs: bool = True


class ScheduleGenerationResponse(BaseModel):
    success: bool
    message: str
    generation_time_ms: Optional[int] = None
    conflict_count: int = 0
    unallocated_subjects: int = 0
    failed_subjects: Optional[List[str]] = None


# Validation Report
class ConflictReport(BaseModel):
    conflict_type: str
    day_of_week: str
    period_number: int
    involved_subjects: List[str]
    involved_resources: Optional[List[str]] = None
    description: str


class ValidationReport(BaseModel):
    is_valid: bool
    total_conflicts: int
    conflicts: List[ConflictReport]
    unallocated_subjects: List[str]
    allocation_percentage: float


# Statistics
class ScheduleStatistics(BaseModel):
    total_entries: int
    total_subjects: int
    total_branches: int
    total_faculty: int
    total_classrooms: int
    total_labrooms: int
    lectures_scheduled: int
    tutorials_scheduled: int
    labs_scheduled: int
    seminars_scheduled: int
    clubs_scheduled: int
    faculty_utilization: float
    classroom_utilization: float
    labroom_utilization: float


# Error Response
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
