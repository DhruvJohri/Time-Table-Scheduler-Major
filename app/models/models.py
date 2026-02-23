"""
SQLAlchemy models for the Timetable Generator system.
"""

from datetime import datetime
from enum import Enum
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean, Text, Enum as SQLEnum, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Branch(Base):
    """Represents an engineering branch (CSE, ECE, ME, CE, etc.)."""
    __tablename__ = "branches"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False)  # CSE, ECE, ME, etc.
    name = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    year_sections = relationship("YearSection", back_populates="branch")
    subjects = relationship("Subject", back_populates="branch")
    timetable_entries = relationship("TimetableEntry", back_populates="branch")


class YearSection(Base):
    """Represents a year and section within a branch."""
    __tablename__ = "year_sections"
    
    id = Column(Integer, primary_key=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    year = Column(Integer, nullable=False)  # 1, 2, 3, 4
    section = Column(String(5), nullable=False)  # A, B, C, etc.
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    branch = relationship("Branch", back_populates="year_sections")
    timetable_entries = relationship("TimetableEntry", back_populates="year_section")
    
    __table_args__ = (Index("ix_branch_year_section", "branch_id", "year", "section"),)


class Faculty(Base):
    """Represents a faculty member."""
    __tablename__ = "faculty"
    
    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(20), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    department = Column(String(50), nullable=True)
    email = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subjects = relationship("Subject", back_populates="faculty")
    timetable_entries = relationship("TimetableEntry", back_populates="faculty")


class Classroom(Base):
    """Represents a lecture/tutorial classroom."""
    __tablename__ = "classrooms"
    
    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(String(20), unique=True, nullable=False)
    capacity = Column(Integer, nullable=False)
    building = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subjects = relationship("Subject", back_populates="classroom")
    timetable_entries = relationship("TimetableEntry", back_populates="classroom")


class LabRoom(Base):
    """Represents a laboratory room."""
    __tablename__ = "lab_rooms"
    
    id = Column(Integer, primary_key=True, index=True)
    room_number = Column(String(20), unique=True, nullable=False)
    lab_type = Column(String(50), nullable=False)  # DSA Lab, CN Lab, DBMS Lab, etc.
    capacity = Column(Integer, nullable=False)
    building = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    subjects = relationship("Subject", back_populates="labroom")
    timetable_entries = relationship("TimetableEntry", back_populates="labroom")


class SessionType(str, Enum):
    """Type of class session."""
    LECTURE = "LECTURE"
    TUTORIAL = "TUTORIAL"
    LAB = "LAB"
    SEMINAR = "SEMINAR"
    CLUB = "CLUB"
    BREAK = "BREAK"
    EXTRACURRICULAR = "EXTRACURRICULAR"


class Subject(Base):
    """Represents a subject/course."""
    __tablename__ = "subjects"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    year = Column(Integer, nullable=False)  # 1, 2, 3, 4
    section = Column(String(5), nullable=False)  # A, B, C
    
    # Weekly requirements
    lectures_per_week = Column(Integer, default=0)
    tutorials_per_week = Column(Integer, default=0)
    lab_periods_per_week = Column(Integer, default=0)  # Each lab block counts as consecutive periods
    seminar_periods_per_week = Column(Integer, default=0)
    lab_duration = Column(Integer, default=2)  # 2 or 3 consecutive periods
    
    # Faculty and resource allocation
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=False)
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=True)
    labroom_id = Column(Integer, ForeignKey("lab_rooms.id"), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    branch = relationship("Branch", back_populates="subjects")
    faculty = relationship("Faculty", back_populates="subjects")
    classroom = relationship("Classroom", back_populates="subjects")
    labroom = relationship("LabRoom", back_populates="subjects")
    timetable_entries = relationship("TimetableEntry", back_populates="subject")
    
    __table_args__ = (Index("ix_subject_branch_year_section", "branch_id", "year", "section"),)


class DayOfWeek(str, Enum):
    """Days of the week."""
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"


class TimetableEntry(Base):
    """Represents a single entry in the timetable."""
    __tablename__ = "timetable_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Time information
    day_of_week = Column(SQLEnum(DayOfWeek), nullable=False)
    period_number = Column(Integer, nullable=False)  # 1-7
    version_id = Column(Integer, ForeignKey("timetable_versions.id"), nullable=True)
    
    # Assignment information
    branch_id = Column(Integer, ForeignKey("branches.id"), nullable=False)
    year_section_id = Column(Integer, ForeignKey("year_sections.id"), nullable=False)
    # Club periods may not have an academic subject/faculty assignment.
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    faculty_id = Column(Integer, ForeignKey("faculty.id"), nullable=True)
    
    # Room assignment
    classroom_id = Column(Integer, ForeignKey("classrooms.id"), nullable=True)
    labroom_id = Column(Integer, ForeignKey("lab_rooms.id"), nullable=True)
    
    # Session type
    session_type = Column(SQLEnum(SessionType), nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    is_locked = Column(Boolean, default=False)  # If locked, won't be rescheduled
    
    # Relationships
    branch = relationship("Branch", back_populates="timetable_entries")
    year_section = relationship("YearSection", back_populates="timetable_entries")
    subject = relationship("Subject", back_populates="timetable_entries")
    faculty = relationship("Faculty", back_populates="timetable_entries")
    classroom = relationship("Classroom", back_populates="timetable_entries")
    labroom = relationship("LabRoom", back_populates="timetable_entries")
    version = relationship("TimetableVersion", back_populates="entries")
    
    __table_args__ = (
        Index("ix_timetable_day_period_branch_year", "day_of_week", "period_number", "branch_id", "year_section_id"),
        Index("ix_timetable_faculty_day_period", "faculty_id", "day_of_week", "period_number"),
        Index("ix_timetable_classroom_day_period", "classroom_id", "day_of_week", "period_number"),
        Index("ix_timetable_labroom_day_period", "labroom_id", "day_of_week", "period_number"),
        Index("ix_timetable_version", "version_id"),
    )


class TimetableVersion(Base):
    """A generated timetable snapshot; only one version is active at a time."""
    __tablename__ = "timetable_versions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    source = Column(String(50), nullable=True)  # generated, manual, import-sync
    created_at = Column(DateTime, default=datetime.utcnow)

    entries = relationship("TimetableEntry", back_populates="version")

    __table_args__ = (
        Index("ix_timetable_versions_active", "is_active"),
        Index("ix_timetable_versions_created_at", "created_at"),
    )


class ConstraintConfig(Base):
    """Configuration for scheduling constraints."""
    __tablename__ = "constraint_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Time constraints
    college_start_time = Column(String(5), default="08:00")  # HH:MM format
    college_end_time = Column(String(5), default="16:10")
    periods_per_day = Column(Integer, default=7)
    normal_period_duration = Column(Integer, default=50)  # minutes
    thursday_period_duration = Column(Integer, default=50)  # minutes
    
    # Break times
    tea_break_after_period = Column(Integer, default=2)
    tea_break_duration = Column(Integer, default=20)  # minutes
    tea_break_2_after_period = Column(Integer, default=6)
    tea_break_2_duration = Column(Integer, default=15)  # minutes
    lunch_after_period = Column(Integer, default=4)
    lunch_duration = Column(Integer, default=60)  # minutes
    
    # Lab constraints
    min_lab_duration = Column(Integer, default=2)  # consecutive periods
    max_lab_duration = Column(Integer, default=3)
    
    # Created
    created_at = Column(DateTime, default=datetime.utcnow)


class ScheduleMetadata(Base):
    """Metadata about the schedule generation."""
    __tablename__ = "schedule_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Generation info
    generated_at = Column(DateTime, default=datetime.utcnow)
    generation_seed = Column(Integer, nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    
    # Status
    is_valid = Column(Boolean, default=True)
    conflict_count = Column(Integer, default=0)
    unallocated_subjects_count = Column(Integer, default=0)
    
    # Details
    notes = Column(Text, nullable=True)
    
    __table_args__ = (Index("ix_schedule_generated_at", "generated_at"),)
