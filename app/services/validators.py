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

    # ADDED CONSTRAINT: Valid tutorial periods — P3, P4, P5, P6 only
    # (P1/P2 are lecture-only; P1 has tea-break after P2; lunch after P4;
    #  P7 on Thursday is the club slot)
    TUTORIAL_ALLOWED_PERIODS = [3, 4, 5, 6]
    
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

    # ADDED CONSTRAINT: Check whether a lab already exists for the given
    # branch-year-section on the specified day (one lab per day per section rule).
    def has_lab_on_day(
        self,
        branch_id: int,
        year_section_id: int,
        day: DayOfWeek
    ) -> bool:
        """
        Return True if a LAB session already exists for the given
        branch_id + year_section_id on the specified day.

        ADDED CONSTRAINT: Only ONE lab per day per branch-year-section.
        """
        existing = self.db.query(TimetableEntry).filter(
            TimetableEntry.branch_id == branch_id,
            TimetableEntry.year_section_id == year_section_id,
            TimetableEntry.day_of_week == day,
            TimetableEntry.session_type == SessionType.LAB
        ).first()
        return existing is not None

    def can_schedule_lecture_or_tutorial(
        self,
        branch_id: int,
        year_section_id: int,
        faculty_id: int,
        classroom_id: int,
        day: DayOfWeek,
        period: int,
        session_type: Optional[SessionType] = None,
        exclude_entry_id: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if a lecture/tutorial can be scheduled at given slot.
        Returns (is_valid, error_message)

        ADDED CONSTRAINT: When session_type is TUTORIAL the period must be
        one of P3, P4, P5, P6 (tutorials not allowed in P1, P2, or Thursday P7).
        Lecture behaviour is completely preserved.
        """
        # ADDED CONSTRAINT: Tutorial period restriction
        # Tutorials are NOT allowed in P1 or P2 (lecture-only / break periods).
        # Tutorials are NOT allowed in P7 on Thursday (club slot).
        # Tutorials are only allowed in P3, P4, P5, P6.
        if session_type == SessionType.TUTORIAL:
            if period not in self.TUTORIAL_ALLOWED_PERIODS:
                return False, (
                    f"Tutorial not allowed in P{period} — "
                    f"tutorials are only permitted in P3, P4, P5, P6"
                )
            # ADDED CONSTRAINT: Tutorial not allowed in Thursday P7 (club slot)
            if day == self.THURSDAY and period == 7:
                return False, "Tutorial not allowed in Thursday P7 (club slot)"

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

        ADDED CONSTRAINT: Lab duration is always 2 periods (enforced here).
        ADDED CONSTRAINT: Only ONE lab allowed per day per branch-year-section.
        """
        end_period = start_period + duration - 1

         # ADDED FIX: Strict lab duration enforcement
        # Lab duration must ALWAYS be exactly 2 periods.
        if duration != 2:
            return False, (
                f"Invalid lab duration: {duration}. "
                f"Lab duration must be exactly 2 periods."
            )

        
        # Validate period range
        if end_period > 7:
            return False, f"Lab extends beyond period 7 (P{start_period}-P{end_period})"

        # ADDED CONSTRAINT: Lab must not start in P1 or P2
        if start_period in self.LAB_NOT_ALLOWED:
            return False, f"Lab must not start in P{start_period} (P1 and P2 are not allowed for labs)"

        # ADDED CONSTRAINT: Lab must not end in P1 or P2 either
        # (end_period check is covered by start_period >= 3 and duration >= 2,
        #  but we keep the explicit not-allowed check for start_period)
        
        # Check lab allowed on this day and periods
        if day == self.THURSDAY:
            if start_period < 3 or end_period > 6:
                return False, f"Labs only allowed P3-P6 on Thursday"
            if start_period in self.LAB_NOT_ALLOWED:
                return False, f"Labs not allowed in P{start_period}"
        else:
            if start_period in self.LAB_NOT_ALLOWED:
                return False, f"Labs not allowed in P{start_period} on normal days"

        # ADDED CONSTRAINT: Only ONE lab per day per branch-year-section
        if self.has_lab_on_day(branch_id, year_section_id, day):
            return False, (
                f"Lab already scheduled for this branch-section on {day.value} — "
                f"only one lab per day per branch-year-section is allowed"
            )
        
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
            day, period, None, exclude_entry_id
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
        session_type: SessionType,
        day: DayOfWeek
    ) -> Tuple[bool, Optional[str]]:

        if day != self.THURSDAY:
            return True, None

        if session_type == SessionType.CLUB:
            if period != 7:
                return False, "Clubs allowed only in P7 on Thursday"
        else:
            if period == 7:
                return False, "Academic classes not allowed in P7 on Thursday (club slot)"
            if period == 1:
                return False, "Academic classes not allowed in P1 on Thursday"

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
        conflicts = set()
        
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
                conflicts.add(
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
                    conflicts.add(
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
                    conflicts.add(
                        f"Lab room conflict: {entry.labroom.room_number} on {entry.day_of_week.value} P{entry.period_number}"
                    )

                # ADDED FIX: Enforce Thursday special rule globally
        for entry in all_entries:
            if entry.day_of_week == self.THURSDAY:
                is_valid, error = self.is_thursday_rule_valid(
                    entry.period_number,
                    entry.session_type,
                    entry.day_of_week
                )
                if not is_valid and error:
                    conflict_msg = (
                        f"Thursday rule violation: {error} "
                        f"on {entry.day_of_week.value} P{entry.period_number}"
                    )
                    if conflict_msg not in conflicts:
                        conflicts.add(conflict_msg)            

        # ADDED CONSTRAINT: Section clash validation
        # Ensure no two entries exist for the same branch_id + year_section_id
        # on the same day and same period (excluding club entries which are shared).
        seen_section_slots = {}
        for entry in all_entries:
            # Build a unique key per section-day-period
            sec_key = (
                entry.branch_id,
                entry.year_section_id,
                entry.day_of_week,
                entry.period_number
            )
            if sec_key in seen_section_slots and entry.session_type != SessionType.CLUB:
                # Retrieve branch and year_section names for a meaningful message
                branch_name = str(entry.branch_id)
                year_section_name = str(entry.year_section_id)
                try:
                    if entry.branch:
                        branch_name = entry.branch.name
                except Exception:
                    pass
                try:
                    if entry.year_section:
                       year_section_name = f"{entry.year_section.year}{entry.year_section.section}"
                except Exception:
                    pass
                conflict_msg = (
                    f"Section conflict: {branch_name} {year_section_name} "
                    f"on {entry.day_of_week.value} P{entry.period_number}"
                )
                if conflict_msg not in conflicts:
                    conflicts.add(conflict_msg)
            else:
                seen_section_slots[sec_key] = entry.id
        
        return len(conflicts) == 0, list(conflicts)
