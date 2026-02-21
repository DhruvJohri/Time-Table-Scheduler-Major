"""
Constraint validators for the timetable scheduler.
Validates all hard and soft constraints.
"""

from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from app.models.models import (
    TimetableEntry, Faculty, Classroom, LabRoom, Subject, 
    DayOfWeek, SessionType, YearSection
)
from enum import Enum


class Period(Enum):
    """Period configuration."""
    P1 = 1
    P2 = 2
    P3 = 3
    P4 = 4
    P5 = 5
    P6 = 6
    P7 = 7


class ConstraintValidator:
    """
    Validates all scheduling constraints.
    """
    
    # Period configurations
    NORMAL_DAYS = [DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY, 
                   DayOfWeek.FRIDAY, DayOfWeek.SATURDAY]
    THURSDAY = DayOfWeek.THURSDAY
    
    # Lab allowed periods
    LAB_ALLOWED_NORMAL = [3, 4, 5, 6, 7]  # P3-P7
    LAB_ALLOWED_THURSDAY = [3, 4, 5, 6]   # P3-P6
    LAB_NOT_ALLOWED = [1, 2]              # P1, P2 not allowed for labs
    
    # Lecture only periods
    LECTURE_ONLY_PERIODS = [1, 2]  # P1, P2 lecture only on normal days
    
    def __init__(self, db: Session):
        self.db = db
    
    def is_faculty_available(
        self, 
        faculty_id: int, 
        day: DayOfWeek, 
        period: int,
        exclude_entry_id: Optional[int] = None
    ) -> bool:
        """Check if faculty is available at given day/period."""
        query = self.db.query(TimetableEntry).filter(
            TimetableEntry.faculty_id == faculty_id,
            TimetableEntry.day_of_week == day,
            TimetableEntry.period_number == period
        )
        
        if exclude_entry_id:
            query = query.filter(TimetableEntry.id != exclude_entry_id)
        
        return query.first() is None
    
    def is_classroom_available(
        self, 
        classroom_id: int, 
        day: DayOfWeek, 
        period: int,
        exclude_entry_id: Optional[int] = None
    ) -> bool:
        """Check if classroom is available at given day/period."""
        query = self.db.query(TimetableEntry).filter(
            TimetableEntry.classroom_id == classroom_id,
            TimetableEntry.day_of_week == day,
            TimetableEntry.period_number == period,
            TimetableEntry.session_type != SessionType.CLUB
        )
        
        if exclude_entry_id:
            query = query.filter(TimetableEntry.id != exclude_entry_id)
        
        return query.first() is None
    
    def is_labroom_available(
        self, 
        labroom_id: int, 
        day: DayOfWeek, 
        period: int,
        exclude_entry_id: Optional[int] = None
    ) -> bool:
        """Check if lab room is available at given day/period."""
        query = self.db.query(TimetableEntry).filter(
            TimetableEntry.labroom_id == labroom_id,
            TimetableEntry.day_of_week == day,
            TimetableEntry.period_number == period
        )
        
        if exclude_entry_id:
            query = query.filter(TimetableEntry.id != exclude_entry_id)
        
        return query.first() is None
    
    def is_branch_slot_free(
        self, 
        branch_id: int,
        year_section_id: int,
        day: DayOfWeek, 
        period: int,
        exclude_entry_id: Optional[int] = None
    ) -> bool:
        """Check if a branch-year-section slot is free."""
        query = self.db.query(TimetableEntry).filter(
            TimetableEntry.branch_id == branch_id,
            TimetableEntry.year_section_id == year_section_id,
            TimetableEntry.day_of_week == day,
            TimetableEntry.period_number == period
        )
        
        if exclude_entry_id:
            query = query.filter(TimetableEntry.id != exclude_entry_id)
        
        return query.first() is None
    
    def can_schedule_lecture_or_tutorial(
        self,
        branch_id: int,
        year_section_id: int,
        faculty_id: int,
        classroom_id: int,
        day: DayOfWeek,
        period: int,
        exclude_entry_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if a lecture/tutorial can be scheduled at given slot.
        Returns (is_valid, error_message)
        """
        # Check branch slot is free
        if not self.is_branch_slot_free(branch_id, year_section_id, day, period, exclude_entry_id):
            return False, f"Branch slot occupied on {day.value} P{period}"
        
        # Check faculty available
        if not self.is_faculty_available(faculty_id, day, period, exclude_entry_id):
            return False, f"Faculty not available on {day.value} P{period}"
        
        # Check classroom available
        if not self.is_classroom_available(classroom_id, day, period, exclude_entry_id):
            return False, f"Classroom not available on {day.value} P{period}"
        
        return True, None
    
    def can_schedule_lab(
        self,
        branch_id: int,
        year_section_id: int,
        faculty_id: int,
        labroom_id: int,
        day: DayOfWeek,
        start_period: int,
        duration: int = 2,  # 2 or 3 consecutive periods
        exclude_entry_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if a lab can be scheduled at given slot with duration.
        Labs must be consecutive periods.
        Returns (is_valid, error_message)
        """
        end_period = start_period + duration - 1
        
        # Validate period range
        if end_period > 7:
            return False, f"Lab extends beyond period 7 (P{start_period}-P{end_period})"
        
        # Check lab allowed on this day and periods
        if day == self.THURSDAY:
            if start_period < 3 or end_period > 6:
                return False, f"Labs only allowed P3-P6 on Thursday"
            if start_period in self.LAB_NOT_ALLOWED:
                return False, f"Labs not allowed in P{start_period}"
        else:
            if start_period in self.LAB_NOT_ALLOWED:
                return False, f"Labs not allowed in P{start_period} on normal days"
        
        # Check all consecutive periods are free
        for period in range(start_period, end_period + 1):
            # Check branch slot
            if not self.is_branch_slot_free(branch_id, year_section_id, day, period, exclude_entry_id):
                return False, f"Branch slot occupied on {day.value} P{period}"
            
            # Check faculty available
            if not self.is_faculty_available(faculty_id, day, period, exclude_entry_id):
                return False, f"Faculty not available on {day.value} P{period}"
            
            # Check labroom available
            if not self.is_labroom_available(labroom_id, day, period, exclude_entry_id):
                return False, f"Lab room not available on {day.value} P{period}"
        
        return True, None
    
    def can_schedule_seminar(
        self,
        branch_id: int,
        year_section_id: int,
        faculty_id: int,
        classroom_id: int,
        day: DayOfWeek,
        period: int,
        exclude_entry_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """Validate if a seminar can be scheduled (same as lecture)."""
        return self.can_schedule_lecture_or_tutorial(
            branch_id, year_section_id, faculty_id, classroom_id, 
            day, period, exclude_entry_id
        )
    
    def is_valid_lab_placement(
        self, 
        day: DayOfWeek, 
        start_period: int, 
        duration: int = 2
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if lab placement respects day/period rules.
        """
        end_period = start_period + duration - 1
        
        if day == self.THURSDAY:
            if start_period < 3 or end_period > 6:
                return False, "Labs only allowed P3-P6 on Thursday"
        else:
            if start_period <= 2:
                return False, "Labs not allowed P1-P2 on normal days"
            if end_period > 7:
                return False, "Cannot exceed P7"
        
        return True, None
    
    def is_thursday_rule_valid(
        self, 
        period: int, 
        session_type: SessionType
    ) -> Tuple[bool, Optional[str]]:
        """Check Thursday special rules."""
        if session_type == SessionType.CLUB:
            if period != 1 and period != 7:
                return False, "Clubs allowed only in P1 and P7 on Thursday"
        else:
            if period in [1, 7]:
                return False, f"Academic classes not allowed in P{period} on Thursday"
        
        return True, None
    
    def get_faculty_conflicts(
        self, 
        faculty_id: int,
        day: DayOfWeek,
        start_period: int,
        end_period: int
    ) -> List[TimetableEntry]:
        """Get all conflicting entries for a faculty in given time range."""
        return self.db.query(TimetableEntry).filter(
            TimetableEntry.faculty_id == faculty_id,
            TimetableEntry.day_of_week == day,
            TimetableEntry.period_number >= start_period,
            TimetableEntry.period_number <= end_period
        ).all()
    
    def get_classroom_conflicts(
        self, 
        classroom_id: int,
        day: DayOfWeek,
        start_period: int,
        end_period: int
    ) -> List[TimetableEntry]:
        """Get all conflicting entries for a classroom in given time range."""
        return self.db.query(TimetableEntry).filter(
            TimetableEntry.classroom_id == classroom_id,
            TimetableEntry.day_of_week == day,
            TimetableEntry.period_number >= start_period,
            TimetableEntry.period_number <= end_period,
            TimetableEntry.session_type != SessionType.CLUB
        ).all()
    
    def get_labroom_conflicts(
        self, 
        labroom_id: int,
        day: DayOfWeek,
        start_period: int,
        end_period: int
    ) -> List[TimetableEntry]:
        """Get all conflicting entries for a lab room in given time range."""
        return self.db.query(TimetableEntry).filter(
            TimetableEntry.labroom_id == labroom_id,
            TimetableEntry.day_of_week == day,
            TimetableEntry.period_number >= start_period,
            TimetableEntry.period_number <= end_period
        ).all()
    
    def validate_full_schedule(self) -> Tuple[bool, List[str]]:
        """
        Validate entire schedule for conflicts.
        Returns (is_valid, list_of_conflicts)
        """
        conflicts = []
        
        # Get all entries grouped by (day, period)
        all_entries = self.db.query(TimetableEntry).all()
        
        entries_by_slot = {}
        for entry in all_entries:
            key = (entry.day_of_week, entry.period_number)
            if key not in entries_by_slot:
                entries_by_slot[key] = []
            entries_by_slot[key].append(entry)
        
        # Check for faculty conflicts
        for entry in all_entries:
            faculty_conflicts = self.db.query(TimetableEntry).filter(
                TimetableEntry.faculty_id == entry.faculty_id,
                TimetableEntry.day_of_week == entry.day_of_week,
                TimetableEntry.period_number == entry.period_number,
                TimetableEntry.id != entry.id
            ).all()
            
            if faculty_conflicts:
                conflicts.append(
                    f"Faculty conflict: {entry.faculty.name} on {entry.day_of_week.value} P{entry.period_number}"
                )
        
        # Check for classroom conflicts
        for entry in all_entries:
            if entry.classroom_id:
                classroom_conflicts = self.db.query(TimetableEntry).filter(
                    TimetableEntry.classroom_id == entry.classroom_id,
                    TimetableEntry.day_of_week == entry.day_of_week,
                    TimetableEntry.period_number == entry.period_number,
                    TimetableEntry.id != entry.id,
                    TimetableEntry.session_type != SessionType.CLUB
                ).all()
                
                if classroom_conflicts:
                    conflicts.append(
                        f"Classroom conflict: {entry.classroom.room_number} on {entry.day_of_week.value} P{entry.period_number}"
                    )
        
        # Check for labroom conflicts
        for entry in all_entries:
            if entry.labroom_id:
                labroom_conflicts = self.db.query(TimetableEntry).filter(
                    TimetableEntry.labroom_id == entry.labroom_id,
                    TimetableEntry.day_of_week == entry.day_of_week,
                    TimetableEntry.period_number == entry.period_number,
                    TimetableEntry.id != entry.id
                ).all()
                
                if labroom_conflicts:
                    conflicts.append(
                        f"Lab room conflict: {entry.labroom.room_number} on {entry.day_of_week.value} P{entry.period_number}"
                    )
        
        return len(conflicts) == 0, conflicts
