"""
Pydantic schemas for request/response validation
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime
from pydantic import Field


class Subject(BaseModel):
    """Subject/Task definition"""
    name: str
    priority: int  # 1-5, 1 is highest
    daily_hours: float
    topics: Optional[List[str]] = None


class UserProfileSchema(BaseModel):
    """User profile schema"""
    email: EmailStr
    name: str
    wake_up_time: str  # HH:MM format
    sleep_time: str  # HH:MM format
    work_start_time: Optional[str] = None
    work_end_time: Optional[str] = None
    is_student: bool
    subjects: List[Subject]
    productivity_type: str  # morning_person, night_owl, balanced
    goal_type: str  # exam_prep, work_productivity, balanced_life, fitness_focus
    break_frequency: int  # minutes
    lunch_time_preference: str
    tea_time_preference: str
    exercise_time: Optional[str] = None
    exercise_duration: Optional[int] = None  # minutes
    free_time_required: float  # hours
    preferred_timetable_type: str  # daily, weekly, exam_mode, workday, weekend

    class Config:
        from_attributes = True


class TimeBlock(BaseModel):
    """Individual time block in timetable"""
    start: str  # HH:MM
    end: str  # HH:MM
    type: str  # study, work, break, meal, exercise, sleep, free_time, meditation, revision
    subject: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None
    energy_level: Optional[str] = None  # high, medium, low
    is_fixed: Optional[bool] = False
    category_color: Optional[str] = None


class DayTimetableSchema(BaseModel):
    """Daily timetable"""
    date: Optional[str] = None
    day: str
    blocks: List[TimeBlock]
    total_study_hours: Optional[float] = None
    total_work_hours: Optional[float] = None


class WeekTimetableSummary(BaseModel):
    """Weekly timetable summary"""
    total_study_hours: float
    total_work_hours: float
    subject_distribution: Dict[str, float]


class WeekTimetableSchema(BaseModel):
    """Weekly timetable"""
    week_start: str
    week_end: str
    days: List[DayTimetableSchema]
    summary: Optional[WeekTimetableSummary] = None


class TimetableSchema(BaseModel):
    """Timetable response"""
    id: Optional[str] = None
    user_id: str
    type: str  # daily, weekly, exam_mode, workday, weekend
    date: str
    timetable: Dict  # Can be list of DayTimetable or WeekTimetable
    modifications: Optional[List[Dict]] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerateTimetableRequest(BaseModel):
    """Request to generate timetable"""
    user_id: str
    timetable_type: str
    start_date: Optional[str] = None
    optimization: Optional[str] = None  # reduce_stress, more_focus, add_revision, weekend_relax


class RegenerateRequest(BaseModel):
    """Request to regenerate with optimization"""
    optimization: str


class ExportRequest(BaseModel):
    """Request to export timetable"""
    format: str  # pdf, csv, json
