"""
Constraint validators for the timetable scheduler.
Validates hard constraints against the active timetable version.
"""

from typing import List, Tuple, Optional
from sqlalchemy.orm import Session, Query
from app.models.models import (
    TimetableEntry, DayOfWeek, SessionType, TimetableVersion
)


class ConstraintValidator:

    THURSDAY = DayOfWeek.THURSDAY
    LAB_NOT_ALLOWED = {1, 2}

    def __init__(self, db: Session, version_id: Optional[int] = None):
        self.db = db
        self.version_id = version_id

    def _resolve_version_id(self) -> Optional[int]:
        if self.version_id is not None:
            return self.version_id
        active = self.db.query(TimetableVersion).filter(
            TimetableVersion.is_active == True
        ).order_by(TimetableVersion.created_at.desc()).first()
        return active.id if active else None

    def set_version(self, version_id: Optional[int]) -> None:
        self.version_id = version_id

    def _query_entries(self) -> Query:
        query = self.db.query(TimetableEntry)
        version_id = self._resolve_version_id()
        if version_id is not None:
            query = query.filter(TimetableEntry.version_id == version_id)
        return query

    def is_faculty_available(self, faculty_id, day, period, exclude_entry_id=None):
        query = self._query_entries().filter(
            TimetableEntry.faculty_id == faculty_id,
            TimetableEntry.day_of_week == day,
            TimetableEntry.period_number == period
        )
        if exclude_entry_id is not None:
            query = query.filter(TimetableEntry.id != exclude_entry_id)
        return query.first() is None

    def is_classroom_available(self, classroom_id, day, period, exclude_entry_id=None):
        query = self._query_entries().filter(
            TimetableEntry.classroom_id == classroom_id,
            TimetableEntry.day_of_week == day,
            TimetableEntry.period_number == period,
            TimetableEntry.session_type.notin_([SessionType.CLUB, SessionType.BREAK])
        )
        if exclude_entry_id is not None:
            query = query.filter(TimetableEntry.id != exclude_entry_id)
        return query.first() is None

    def is_labroom_available(self, labroom_id, day, period, exclude_entry_id=None):
        query = self._query_entries().filter(
            TimetableEntry.labroom_id == labroom_id,
            TimetableEntry.day_of_week == day,
            TimetableEntry.period_number == period
        )
        if exclude_entry_id is not None:
            query = query.filter(TimetableEntry.id != exclude_entry_id)
        return query.first() is None

    def is_branch_slot_free(self, branch_id, year_section_id, day, period, exclude_entry_id=None):
        query = self._query_entries().filter(
            TimetableEntry.branch_id == branch_id,
            TimetableEntry.year_section_id == year_section_id,
            TimetableEntry.day_of_week == day,
            TimetableEntry.period_number == period
        )
        if exclude_entry_id is not None:
            query = query.filter(TimetableEntry.id != exclude_entry_id)
        return query.first() is None

    def can_schedule_lecture_or_tutorial(
        self,
        branch_id,
        year_section_id,
        faculty_id,
        classroom_id,
        day,
        period,
        exclude_entry_id=None
    ):
        if not self.is_branch_slot_free(branch_id, year_section_id, day, period, exclude_entry_id):
            return False, f"Branch slot occupied on {day.value} P{period}"

        if not self.is_faculty_available(faculty_id, day, period, exclude_entry_id):
            return False, f"Faculty not available on {day.value} P{period}"

        if not self.is_classroom_available(classroom_id, day, period, exclude_entry_id):
            return False, f"Classroom not available on {day.value} P{period}"

        return True, None

    def can_schedule_lab(
        self,
        branch_id,
        year_section_id,
        faculty_id,
        labroom_id,
        day,
        start_period,
        duration=2,
        exclude_entry_id=None
    ):

        end_period = start_period + duration - 1

        if duration != 2:
            return False, "Lab duration must be exactly 2 periods"

        if end_period > 7:
            return False, f"Lab exceeds period limit (P{start_period}-P{end_period})"

        if start_period in self.LAB_NOT_ALLOWED:
            return False, f"Labs cannot start in P{start_period}"

        if day == self.THURSDAY and end_period > 6:
            return False, "Thursday labs allowed only in P3-P6"

        # Only one lab per section per day
        existing_lab = self._query_entries().filter(
            TimetableEntry.branch_id == branch_id,
            TimetableEntry.year_section_id == year_section_id,
            TimetableEntry.day_of_week == day,
            TimetableEntry.session_type == SessionType.LAB
        )

        if exclude_entry_id is not None:
            existing_lab = existing_lab.filter(
                TimetableEntry.id != exclude_entry_id
            )

        if existing_lab.first():
            return False, f"Only one lab allowed per day on {day.value}"

        # Validate both periods
        for period in range(start_period, end_period + 1):

            if not self.is_branch_slot_free(branch_id, year_section_id, day, period, exclude_entry_id):
                return False, f"Branch slot occupied on {day.value} P{period}"

            if not self.is_faculty_available(faculty_id, day, period, exclude_entry_id):
                return False, f"Faculty not available on {day.value} P{period}"

            if not self.is_labroom_available(labroom_id, day, period, exclude_entry_id):
                return False, f"Lab room not available on {day.value} P{period}"

        return True, None

    def can_schedule_seminar(
        self,
        branch_id,
        year_section_id,
        faculty_id,
        classroom_id,
        day,
        period,
        exclude_entry_id=None
    ):
        return self.can_schedule_lecture_or_tutorial(
            branch_id,
            year_section_id,
            faculty_id,
            classroom_id,
            day,
            period,
            exclude_entry_id
        )

    def validate_full_schedule(self):

        conflicts = []
        entries = self._query_entries().all()

        for entry in entries:

            base_query = self._query_entries().filter(
                TimetableEntry.day_of_week == entry.day_of_week,
                TimetableEntry.period_number == entry.period_number,
                TimetableEntry.id != entry.id
            )

            if entry.faculty_id is not None:
                if base_query.filter(
                    TimetableEntry.faculty_id == entry.faculty_id
                ).first():
                    conflicts.append(
                        f"Faculty conflict on {entry.day_of_week.value} P{entry.period_number}"
                    )

            if entry.classroom_id is not None:
                if base_query.filter(
                    TimetableEntry.classroom_id == entry.classroom_id,
                    TimetableEntry.session_type.notin_([SessionType.CLUB, SessionType.BREAK])
                ).first():
                    conflicts.append(
                        f"Classroom conflict on {entry.day_of_week.value} P{entry.period_number}"
                    )

            if entry.labroom_id is not None:
                if base_query.filter(
                    TimetableEntry.labroom_id == entry.labroom_id
                ).first():
                    conflicts.append(
                        f"Lab room conflict on {entry.day_of_week.value} P{entry.period_number}"
                    )

            if base_query.filter(
                TimetableEntry.branch_id == entry.branch_id,
                TimetableEntry.year_section_id == entry.year_section_id
            ).first():
                conflicts.append(
                    f"Section conflict on {entry.day_of_week.value} P{entry.period_number}"
                )

        unique_conflicts = sorted(set(conflicts))
        return len(unique_conflicts) == 0, unique_conflicts