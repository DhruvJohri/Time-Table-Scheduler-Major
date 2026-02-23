"""
Scheduler engine for timetable generation using constraint-aware placement.
"""

import random
from math import ceil
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

from sqlalchemy.orm import Session

from app.models.models import (
    Subject, TimetableEntry, DayOfWeek, SessionType, YearSection, TimetableVersion
)
from app.services.validators import ConstraintValidator

logger = logging.getLogger(__name__)


@dataclass
class SchedulingTask:
    subject_id: int
    subject_code: str
    session_type: SessionType
    count: int
    duration: int = 1
    priority: int = 0

    def __lt__(self, other):
        return self.priority > other.priority


class SchedulerEngine:
    DAYS = [
        DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
        DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY
    ]
    PERIODS = [1, 2, 3, 4, 5, 6, 7]

    def __init__(self, db: Session, seed: Optional[int] = None, version_id: Optional[int] = None):
        self.db = db
        self.seed = seed
        self.version_id = version_id
        self.validator = ConstraintValidator(db, version_id=version_id)
        if seed is not None:
            random.seed(seed)

        self.failed_subjects: List[Tuple[str, str]] = []
        self.backtrack_count = 0
        self._year_section_cache: Dict[Tuple[int, int, str], Optional[int]] = {}

    def set_version(self, version_id: Optional[int]) -> None:
        self.version_id = version_id
        self.validator.set_version(version_id)

    def _entry_query(self):
        query = self.db.query(TimetableEntry)
        if self.version_id is not None:
            query = query.filter(TimetableEntry.version_id == self.version_id)
        return query

    def _get_year_section_id(self, subject: Subject) -> Optional[int]:
        key = (subject.branch_id, subject.year, subject.section)
        if key in self._year_section_cache:
            return self._year_section_cache[key]
        ys = self.db.query(YearSection).filter(
            YearSection.branch_id == subject.branch_id,
            YearSection.year == subject.year,
            YearSection.section == subject.section
        ).first()
        value = ys.id if ys else None
        self._year_section_cache[key] = value
        return value

    def _existing_subject_allocation(self, subject: Subject, session_type: SessionType) -> int:
        entries = self._entry_query().filter(
            TimetableEntry.subject_id == subject.id,
            TimetableEntry.session_type == session_type
        ).count()
        if session_type == SessionType.LAB:
            return ceil(entries / 2) if entries > 0 else 0
        return entries

    def _create_scheduling_tasks(self, subjects: List[Subject]) -> List[SchedulingTask]:
        tasks: List[SchedulingTask] = []
        for subject in subjects:
            if subject.lab_periods_per_week > 0:
                remaining = max(subject.lab_periods_per_week - self._existing_subject_allocation(subject, SessionType.LAB), 0)
                if remaining > 0:
                    tasks.append(SchedulingTask(
                        subject_id=subject.id,
                        subject_code=subject.code,
                        session_type=SessionType.LAB,
                        count=remaining,
                        duration=2,
                        priority=5
                    ))

            if subject.lectures_per_week > 0:
                remaining = max(subject.lectures_per_week - self._existing_subject_allocation(subject, SessionType.LECTURE), 0)
                if remaining > 0:
                    tasks.append(SchedulingTask(
                        subject_id=subject.id,
                        subject_code=subject.code,
                        session_type=SessionType.LECTURE,
                        count=remaining,
                        duration=1,
                        priority=4
                    ))

            if subject.tutorials_per_week > 0:
                remaining = max(subject.tutorials_per_week - self._existing_subject_allocation(subject, SessionType.TUTORIAL), 0)
                if remaining > 0:
                    tasks.append(SchedulingTask(
                        subject_id=subject.id,
                        subject_code=subject.code,
                        session_type=SessionType.TUTORIAL,
                        count=remaining,
                        duration=1,
                        priority=3
                    ))

            if subject.seminar_periods_per_week > 0:
                remaining = max(subject.seminar_periods_per_week - self._existing_subject_allocation(subject, SessionType.SEMINAR), 0)
                if remaining > 0:
                    tasks.append(SchedulingTask(
                        subject_id=subject.id,
                        subject_code=subject.code,
                        session_type=SessionType.SEMINAR,
                        count=remaining,
                        duration=1,
                        priority=2
                    ))

        tasks.sort()
        return tasks

    def _candidate_lab_slots(self, day: DayOfWeek) -> List[int]:
        if day == DayOfWeek.THURSDAY:
            starts = [3, 4, 5]  # P5-P6 is max valid 2-period block.
        else:
            starts = [3, 4, 5, 6]  # P6-P7 max.
        random.shuffle(starts)
        return starts

    def _candidate_single_slots(self, day: DayOfWeek) -> List[int]:
        periods = self.PERIODS[:]
        if day == DayOfWeek.THURSDAY:
            periods = [p for p in periods if p not in (1, 7)]
        # Push first period earlier in selection to satisfy "first lecture should be course".
        ordered = sorted(periods, key=lambda p: (0 if p == 1 else 1, p))
        head = ordered[:2]
        tail = ordered[2:]
        random.shuffle(tail)
        return head + tail

    def _schedule_lab(self, subject: Subject, count: int) -> bool:
        if subject.labroom_id is None:
            self.failed_subjects.append((subject.code, "No lab room assigned"))
            return False
        ys_id = self._get_year_section_id(subject)
        if ys_id is None:
            self.failed_subjects.append((subject.code, "Year/section mapping not found"))
            return False

        scheduled = 0
        for _ in range(count):
            placed = False
            day_order = self.DAYS[:]
            random.shuffle(day_order)
            for day in day_order:
                for start_period in self._candidate_lab_slots(day):
                    can_place, _ = self.validator.can_schedule_lab(
                        subject.branch_id, ys_id, subject.faculty_id,
                        subject.labroom_id, day, start_period, duration=2
                    )
                    if not can_place:
                        continue
                    for period in (start_period, start_period + 1):
                        self.db.add(TimetableEntry(
                            day_of_week=day,
                            period_number=period,
                            version_id=self.version_id,
                            branch_id=subject.branch_id,
                            year_section_id=ys_id,
                            subject_id=subject.id,
                            faculty_id=subject.faculty_id,
                            labroom_id=subject.labroom_id,
                            session_type=SessionType.LAB
                        ))
                    scheduled += 1
                    placed = True
                    break
                if placed:
                    break
            if not placed:
                self.backtrack_count += 1
                break

        self.db.flush()
        return scheduled == count

    def _schedule_single(self, subject: Subject, count: int, session_type: SessionType) -> bool:
        if subject.classroom_id is None:
            self.failed_subjects.append((subject.code, "No classroom assigned"))
            return False
        ys_id = self._get_year_section_id(subject)
        if ys_id is None:
            self.failed_subjects.append((subject.code, "Year/section mapping not found"))
            return False

        scheduled = 0
        for _ in range(count):
            placed = False
            day_order = self.DAYS[:]
            random.shuffle(day_order)
            for day in day_order:
                for period in self._candidate_single_slots(day):
                    if session_type == SessionType.SEMINAR:
                        can_place, _ = self.validator.can_schedule_seminar(
                            subject.branch_id, ys_id, subject.faculty_id, subject.classroom_id, day, period
                        )
                    else:
                        can_place, _ = self.validator.can_schedule_lecture_or_tutorial(
                            subject.branch_id, ys_id, subject.faculty_id, subject.classroom_id, day, period
                        )
                    if not can_place:
                        continue
                    self.db.add(TimetableEntry(
                        day_of_week=day,
                        period_number=period,
                        version_id=self.version_id,
                        branch_id=subject.branch_id,
                        year_section_id=ys_id,
                        subject_id=subject.id,
                        faculty_id=subject.faculty_id,
                        classroom_id=subject.classroom_id,
                        session_type=session_type
                    ))
                    scheduled += 1
                    placed = True
                    break
                if placed:
                    break
            if not placed:
                self.backtrack_count += 1
                break

        self.db.flush()
        return scheduled == count

    def schedule_clubs(self) -> bool:
        try:
            year_sections = self.db.query(YearSection).all()
            for ys in year_sections:
                for period in (1, 7):
                    if self.validator.is_branch_slot_free(ys.branch_id, ys.id, DayOfWeek.THURSDAY, period):
                        self.db.add(TimetableEntry(
                            day_of_week=DayOfWeek.THURSDAY,
                            period_number=period,
                            version_id=self.version_id,
                            branch_id=ys.branch_id,
                            year_section_id=ys.id,
                            subject_id=None,
                            faculty_id=None,
                            session_type=SessionType.CLUB
                        ))
            self.db.flush()
            return True
        except Exception as exc:
            logger.error("Error scheduling clubs: %s", exc)
            return False

    def fill_extracurricular(self) -> int:
        filled = 0
        year_sections = self.db.query(YearSection).all()
        for ys in year_sections:
            for day in self.DAYS:
                for period in self.PERIODS:
                    if period == 1:
                        # Keep first period reserved for academic subjects.
                        continue
                    if day == DayOfWeek.THURSDAY and period in (1, 7):
                        continue
                    if not self.validator.is_branch_slot_free(ys.branch_id, ys.id, day, period):
                        continue
                    self.db.add(TimetableEntry(
                        day_of_week=day,
                        period_number=period,
                        version_id=self.version_id,
                        branch_id=ys.branch_id,
                        year_section_id=ys.id,
                        subject_id=None,
                        faculty_id=None,
                        session_type=SessionType.EXTRACURRICULAR
                    ))
                    filled += 1
        self.db.flush()
        return filled

    def schedule_all(
        self,
        force_clear: bool = False,
        include_clubs: bool = True,
        fill_extracurricular: bool = True
    ) -> Tuple[bool, Dict]:
        start = datetime.utcnow()
        self.failed_subjects = []
        self.backtrack_count = 0

        if force_clear:
            query = self.db.query(TimetableEntry)
            if self.version_id is not None:
                query = query.filter(TimetableEntry.version_id == self.version_id)
            query.delete(synchronize_session=False)
            self.db.flush()

        subjects = self.db.query(Subject).filter(Subject.is_active == True).all()
        if not subjects:
            return False, {
                "success": False,
                "message": "No active subjects found",
                "scheduled": 0,
                "failed": 0,
                "conflicts": 0,
                "failed_subjects": [],
            }

        tasks = self._create_scheduling_tasks(subjects)
        scheduled_tasks = 0

        for task in tasks:
            subject = self.db.query(Subject).filter(Subject.id == task.subject_id).first()
            if not subject:
                continue
            ok = False
            if task.session_type == SessionType.LAB:
                ok = self._schedule_lab(subject, task.count)
            elif task.session_type == SessionType.LECTURE:
                ok = self._schedule_single(subject, task.count, SessionType.LECTURE)
            elif task.session_type == SessionType.TUTORIAL:
                ok = self._schedule_single(subject, task.count, SessionType.TUTORIAL)
            elif task.session_type == SessionType.SEMINAR:
                ok = self._schedule_single(subject, task.count, SessionType.SEMINAR)

            if ok:
                scheduled_tasks += 1
            else:
                self.failed_subjects.append((subject.code, f"Failed to schedule all {task.session_type.value} slots"))

        if include_clubs:
            self.schedule_clubs()
        extra_count = self.fill_extracurricular() if fill_extracurricular else 0

        self.db.commit()
        is_valid, conflicts = self.validator.validate_full_schedule()
        elapsed = int((datetime.utcnow() - start).total_seconds() * 1000)

        report = {
            "success": len(self.failed_subjects) == 0 and is_valid,
            "message": f"Scheduled {scheduled_tasks}/{len(tasks)} tasks",
            "scheduled": scheduled_tasks,
            "failed": len(self.failed_subjects),
            "conflicts": len(conflicts),
            "generation_time_ms": elapsed,
            "backtrack_count": self.backtrack_count,
            "failed_subjects": self.failed_subjects,
            "extracurricular_filled": extra_count,
        }
        return report["success"], report

    def reshuffle_preserving_locked(
        self,
        include_clubs: bool = True,
        fill_extracurricular: bool = True
    ) -> Tuple[bool, Dict]:
        query = self._entry_query().filter(TimetableEntry.is_locked == False)
        removed = query.delete(synchronize_session=False)
        self.db.flush()
        success, report = self.schedule_all(
            force_clear=False,
            include_clubs=include_clubs,
            fill_extracurricular=fill_extracurricular
        )
        report["removed_unlocked"] = removed
        return success, report

    def get_scheduling_report(self) -> Dict:
        query = self._entry_query()
        total_entries = query.count()
        by_type = {
            st.value: query.filter(TimetableEntry.session_type == st).count()
            for st in SessionType
        }
        is_valid, conflicts = self.validator.validate_full_schedule()
        return {
            "total_entries": total_entries,
            "by_type": by_type,
            "is_valid": is_valid,
            "conflicts": len(conflicts),
            "failed_subjects": len(self.failed_subjects),
            "backtrack_count": self.backtrack_count,
        }


def activate_new_version(db: Session, name: str, source: str = "generated") -> TimetableVersion:
    db.query(TimetableVersion).filter(TimetableVersion.is_active == True).update(
        {TimetableVersion.is_active: False},
        synchronize_session=False
    )
    version = TimetableVersion(name=name, is_active=True, source=source)
    db.add(version)
    db.flush()
    return version


def get_active_version(db: Session) -> Optional[TimetableVersion]:
    return db.query(TimetableVersion).filter(
        TimetableVersion.is_active == True
    ).order_by(TimetableVersion.created_at.desc()).first()
