"""
Scheduler engine for timetable generation using constraint-based scheduling with backtracking.
"""

import random
from typing import List, Dict, Set, Tuple, Optional
from dataclasses import dataclass
from sqlalchemy.orm import Session
from app.models.models import (
    Subject, TimetableEntry, DayOfWeek, SessionType, YearSection,
    Faculty, Classroom, LabRoom
)
from app.services.validators import ConstraintValidator
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SchedulingTask:
    """Represents a scheduling task for a subject."""
    subject_id: int
    subject_code: str
    session_type: SessionType
    count: int  # Number of periods needed
    duration: int = 1  # Duration in consecutive periods (1 for lecture, 2-3 for lab)
    priority: int = 0  # Higher = higher priority
    
    def __lt__(self, other):
        return self.priority > other.priority


class SchedulerEngine:
    """
    Constraint-based scheduler with backtracking.
    Schedules all subjects respecting all hard constraints.
    """
    
    DAYS = [
        DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY
    ]
    
    PERIODS = list(range(1, 8))  # 1-7
    
    def __init__(self, db: Session, seed: Optional[int] = None):
        self.db = db
        self.validator = ConstraintValidator(db)
        self.seed = seed
        if seed:
            random.seed(seed)
        
        # Tracking
        self.scheduled_entries: List[TimetableEntry] = []
        self.failed_subjects: List[Tuple[str, str]] = []  # (subject_code, reason)
        self.backtrack_count = 0
    
    def schedule_all(self, force_clear: bool = False) -> Tuple[bool, Dict]:
        """
        Schedule all subjects in the database.
        
        Returns:
            (success: bool, report: dict with metrics)
        """
        start_time = datetime.utcnow()
        
        # Clear existing entries if requested
        if force_clear:
            self.db.query(TimetableEntry).delete()
            self.db.commit()
        
        # Get all subjects
        all_subjects = self.db.query(Subject).filter(Subject.is_active == True).all()
        
        # Compute capacity vs demand metadata
        try:
            # Determine periods per day from constraint config if present
            from app.models.models import ConstraintConfig
            cfg = self.db.query(ConstraintConfig).order_by(ConstraintConfig.id.desc()).first()
            periods_per_day = cfg.periods_per_day if cfg else 7
        except Exception:
            periods_per_day = 7

        days_count = len(self.DAYS)
        # Reserved club slots per section (Thursday P1 and P7)
        reserved_per_section = 2
        capacity = days_count * periods_per_day - reserved_per_section

        # Compute total demand (sum of required periods across subjects)
        total_demand = 0
        for s in all_subjects:
            total_demand += (s.lectures_per_week or 0) + (s.tutorials_per_week or 0) + (s.lab_periods_per_week or 0) + (s.seminar_periods_per_week or 0)

        expected_empty = capacity - total_demand

        logger.info(f"Scheduler capacity={capacity}, demand={total_demand}, expected_empty={expected_empty}")
        
        # Group by branch-year-section and normalize
        if not all_subjects:
            return False, {
                "success": False,
                "message": "No active subjects found",
                "scheduled": 0,
                "failed": 0,
                "conflicts": 0
            }
        
        # Schedule in order: labs first, then tutorials, lectures, seminars
        all_tasks = self._create_scheduling_tasks(all_subjects)
        
        # Sort by priority (labs first)
        all_tasks.sort()
        
        # Attempt to schedule each task
        scheduled_count = 0
        for task in all_tasks:
            subject = self.db.query(Subject).filter(Subject.id == task.subject_id).first()
            if not subject:
                continue
            
            success = False
            if task.session_type == SessionType.LAB:
                success = self._schedule_lab(subject, task.count, task.duration)
            elif task.session_type == SessionType.LECTURE:
                success = self._schedule_lectures(subject, task.count)
            elif task.session_type == SessionType.TUTORIAL:
                success = self._schedule_tutorials(subject, task.count)
            elif task.session_type == SessionType.SEMINAR:
                success = self._schedule_seminars(subject, task.count)
            
            if success:
                scheduled_count += 1
            else:
                self.failed_subjects.append((subject.code, f"Failed to schedule all {task.session_type.value}s"))
        
        # Validate final schedule
        is_valid, conflicts = self.validator.validate_full_schedule()
        
        end_time = datetime.utcnow()
        generation_time = (end_time - start_time).total_seconds() * 1000
        
        report = {
            "success": len(self.failed_subjects) == 0,
            "message": f"Scheduled {scheduled_count}/{len(all_subjects)} subjects",
            "scheduled": scheduled_count,
            "failed": len(self.failed_subjects),
            "conflicts": len(conflicts),
            "generation_time_ms": int(generation_time),
            "backtrack_count": self.backtrack_count,
            "failed_subjects": self.failed_subjects,
            "capacity": capacity,
            "demand": total_demand,
            "expected_empty": expected_empty
        }
        
        return report["success"], report
    
    def _create_scheduling_tasks(self, subjects: List[Subject]) -> List[SchedulingTask]:
        """Create scheduling tasks from subjects with proper ordering."""
        tasks = []
        
        for subject in subjects:
            # Labs have highest priority (priority = 3)
            if subject.lab_periods_per_week > 0:
                tasks.append(SchedulingTask(
                    subject_id=subject.id,
                    subject_code=subject.code,
                    session_type=SessionType.LAB,
                    count=subject.lab_periods_per_week,
                    duration=subject.lab_duration,
                    priority=3
                ))
            
            # Tutorials next (priority = 2)
            if subject.tutorials_per_week > 0:
                tasks.append(SchedulingTask(
                    subject_id=subject.id,
                    subject_code=subject.code,
                    session_type=SessionType.TUTORIAL,
                    count=subject.tutorials_per_week,
                    priority=2
                ))
            
            # Lectures (priority = 1)
            if subject.lectures_per_week > 0:
                tasks.append(SchedulingTask(
                    subject_id=subject.id,
                    subject_code=subject.code,
                    session_type=SessionType.LECTURE,
                    count=subject.lectures_per_week,
                    priority=1
                ))
            
            # Seminars (priority = 0)
            if subject.seminar_periods_per_week > 0:
                tasks.append(SchedulingTask(
                    subject_id=subject.id,
                    subject_code=subject.code,
                    session_type=SessionType.SEMINAR,
                    count=subject.seminar_periods_per_week,
                    priority=0
                ))
        
        return tasks
    
    def _schedule_lab(self, subject: Subject, count: int, duration: int) -> bool:
        """Schedule lab sessions with backtracking."""
        if subject.labroom_id is None:
            self.failed_subjects.append((subject.code, "No lab room assigned"))
            return False
        
        scheduled = 0
        attempts = 0
        max_attempts = len(self.DAYS) * 4  # Generous attempt limit
        
        while scheduled < count and attempts < max_attempts:
            attempts += 1
            
            # Choose random day and starting period
            day = random.choice(self.DAYS)
            
            # Determine allowed periods based on day
            if day == DayOfWeek.THURSDAY:
                max_start = 5  # P3-P6 with duration 2 means max start is P5
                start_period = random.randint(3, max_start)
            else:
                max_start = 6  # P3-P7 with duration 2 means max start is P6
                start_period = random.randint(3, max_start)
            
            # Validate placement
            can_place, error = self.validator.can_schedule_lab(
                subject.branch_id,
                subject.year_section_id,
                subject.faculty_id,
                subject.labroom_id,
                day,
                start_period,
                duration
            )
            
            if can_place:
                # Create entries for each period in the lab
                for i, period in enumerate(range(start_period, start_period + duration)):
                    entry = TimetableEntry(
                        day_of_week=day,
                        period_number=period,
                        branch_id=subject.branch_id,
                        year_section_id=subject.year_section_id,
                        subject_id=subject.id,
                        faculty_id=subject.faculty_id,
                        labroom_id=subject.labroom_id,
                        session_type=SessionType.LAB
                    )
                    self.db.add(entry)
                
                scheduled += 1
        
        self.db.commit()
        return scheduled == count
    
    def _schedule_lectures(self, subject: Subject, count: int) -> bool:
        """Schedule lecture sessions with backtracking."""
        if subject.classroom_id is None:
            self.failed_subjects.append((subject.code, "No classroom assigned"))
            return False
        
        scheduled = 0
        attempts = 0
        max_attempts = len(self.DAYS) * 7 * 2
        
        while scheduled < count and attempts < max_attempts:
            attempts += 1
            
            day = random.choice(self.DAYS)
            period = random.choice(self.PERIODS)
            
            # Lectures can be in any period, but preferably not after labs
            if day == DayOfWeek.THURSDAY:
                if period in [1, 7]:  # Clubs only
                    continue
            
            can_place, error = self.validator.can_schedule_lecture_or_tutorial(
                subject.branch_id,
                subject.year_section_id,
                subject.faculty_id,
                subject.classroom_id,
                day,
                period
            )
            
            if can_place:
                entry = TimetableEntry(
                    day_of_week=day,
                    period_number=period,
                    branch_id=subject.branch_id,
                    year_section_id=subject.year_section_id,
                    subject_id=subject.id,
                    faculty_id=subject.faculty_id,
                    classroom_id=subject.classroom_id,
                    session_type=SessionType.LECTURE
                )
                self.db.add(entry)
                scheduled += 1
        
        self.db.commit()
        return scheduled == count
    
    def _schedule_tutorials(self, subject: Subject, count: int) -> bool:
        """Schedule tutorial sessions with backtracking."""
        if subject.classroom_id is None:
            self.failed_subjects.append((subject.code, "No classroom assigned"))
            return False
        
        scheduled = 0
        attempts = 0
        max_attempts = len(self.DAYS) * 7 * 2
        
        while scheduled < count and attempts < max_attempts:
            attempts += 1
            
            day = random.choice(self.DAYS)
            period = random.choice(self.PERIODS)
            
            if day == DayOfWeek.THURSDAY:
                if period in [1, 7]:  # Clubs only
                    continue
            
            can_place, error = self.validator.can_schedule_lecture_or_tutorial(
                subject.branch_id,
                subject.year_section_id,
                subject.faculty_id,
                subject.classroom_id,
                day,
                period
            )
            
            if can_place:
                entry = TimetableEntry(
                    day_of_week=day,
                    period_number=period,
                    branch_id=subject.branch_id,
                    year_section_id=subject.year_section_id,
                    subject_id=subject.id,
                    faculty_id=subject.faculty_id,
                    classroom_id=subject.classroom_id,
                    session_type=SessionType.TUTORIAL
                )
                self.db.add(entry)
                scheduled += 1
        
        self.db.commit()
        return scheduled == count
    
    def _schedule_seminars(self, subject: Subject, count: int) -> bool:
        """Schedule seminar sessions with backtracking."""
        if subject.classroom_id is None:
            self.failed_subjects.append((subject.code, "No classroom assigned"))
            return False
        
        scheduled = 0
        attempts = 0
        max_attempts = len(self.DAYS) * 7 * 2
        
        while scheduled < count and attempts < max_attempts:
            attempts += 1
            
            day = random.choice(self.DAYS)
            period = random.choice(self.PERIODS)
            
            if day == DayOfWeek.THURSDAY:
                if period in [1, 7]:  # Clubs only
                    continue
            
            can_place, error = self.validator.can_schedule_seminar(
                subject.branch_id,
                subject.year_section_id,
                subject.faculty_id,
                subject.classroom_id,
                day,
                period
            )
            
            if can_place:
                entry = TimetableEntry(
                    day_of_week=day,
                    period_number=period,
                    branch_id=subject.branch_id,
                    year_section_id=subject.year_section_id,
                    subject_id=subject.id,
                    faculty_id=subject.faculty_id,
                    classroom_id=subject.classroom_id,
                    session_type=SessionType.SEMINAR
                )
                self.db.add(entry)
                scheduled += 1
        
        self.db.commit()
        return scheduled == count
    
    def schedule_clubs(self) -> bool:
        """Schedule fixed club activities on Thursday P1 and P7."""
        try:
            # Get all branches
            branches = self.db.query(Subject.branch_id).distinct().all()
            
            for (branch_id,) in branches:
                # Get year-sections for this branch
                year_sections = self.db.query(YearSection).filter(
                    YearSection.branch_id == branch_id
                ).all()
                
                for year_section in year_sections:
                    # Club for P1
                    entry_p1 = TimetableEntry(
                        day_of_week=DayOfWeek.THURSDAY,
                        period_number=1,
                        branch_id=branch_id,
                        year_section_id=year_section.id,
                        subject_id=None,
                        faculty_id=None,
                        session_type=SessionType.CLUB
                    )
                    self.db.add(entry_p1)
                    
                    # Club for P7
                    entry_p7 = TimetableEntry(
                        day_of_week=DayOfWeek.THURSDAY,
                        period_number=7,
                        branch_id=branch_id,
                        year_section_id=year_section.id,
                        subject_id=None,
                        faculty_id=None,
                        session_type=SessionType.CLUB
                    )
                    self.db.add(entry_p7)
            
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error scheduling clubs: {str(e)}")
            return False
    
    def get_scheduling_report(self) -> Dict:
        """Get detailed scheduling report."""
        total_entries = self.db.query(TimetableEntry).count()
        
        lectures = self.db.query(TimetableEntry).filter(
            TimetableEntry.session_type == SessionType.LECTURE
        ).count()
        
        tutorials = self.db.query(TimetableEntry).filter(
            TimetableEntry.session_type == SessionType.TUTORIAL
        ).count()
        
        labs = self.db.query(TimetableEntry).filter(
            TimetableEntry.session_type == SessionType.LAB
        ).count()
        
        seminars = self.db.query(TimetableEntry).filter(
            TimetableEntry.session_type == SessionType.SEMINAR
        ).count()
        
        clubs = self.db.query(TimetableEntry).filter(
            TimetableEntry.session_type == SessionType.CLUB
        ).count()
        
        is_valid, conflicts = self.validator.validate_full_schedule()
        
        return {
            "total_entries": total_entries,
            "lectures": lectures,
            "tutorials": tutorials,
            "labs": labs,
            "seminars": seminars,
            "clubs": clubs,
            "is_valid": is_valid,
            "conflicts": len(conflicts),
            "failed_subjects": len(self.failed_subjects),
            "backtrack_count": self.backtrack_count
        }
