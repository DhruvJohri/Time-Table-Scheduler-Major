"""
Constraint Builder Module
Applies academic scheduling constraints to the OR-Tools CP-SAT model.
"""

from ortools.sat.python import cp_model
from typing import Dict, List, Any


# College time-slot definitions (Mon–Sat, 7 periods/day)
DAYS    = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
PERIODS = list(range(1, 8))   # 1-based, 7 periods per day
PERIOD_TIMES = {
    1: ("08:00", "09:00"),
    2: ("09:00", "10:00"),
    3: ("10:15", "11:15"),
    4: ("11:15", "12:15"),
    5: ("13:00", "14:00"),
    6: ("14:00", "15:00"),
    7: ("15:15", "16:15"),
}


class ConstraintBuilder:
    """
    Applies domain-specific college scheduling constraints to a CP-SAT model.
    """

    def __init__(
        self,
        model:       cp_model.CpModel,
        x:           Dict,          # x[(teacher, subject, branch, year, day, period, room)] = BoolVar
        teachers:    List[str],
        subjects:    List[str],
        rooms:       List[str],
        branches:    List[str],
        years:       List[str],
        assignments: List[Dict[str, Any]],  # {teacher, subject, branch, year, lectures_per_week}
        lab_subjects: List[str],
        cs_subjects:  List[str],    # subjects with CS split (CS1/CS2)
    ):
        self.model       = model
        self.x           = x
        self.teachers    = teachers
        self.subjects    = subjects
        self.rooms       = rooms
        self.branches    = branches
        self.years       = years
        self.assignments = assignments
        self.lab_subjects = lab_subjects
        self.cs_subjects  = cs_subjects

    def apply_all(self) -> None:
        self._teacher_uniqueness()
        self._room_availability()
        self._lecture_count()
        self._lab_two_hour_blocks()
        self._first_slot_priority()
        self._thursday_club_rule()

    # ── 1. Teacher Uniqueness ─────────────────────────────────────────────────
    def _teacher_uniqueness(self) -> None:
        """A teacher cannot appear in more than one slot simultaneously."""
        for day in DAYS:
            for period in PERIODS:
                for teacher in self.teachers:
                    slots = [
                        self.x[k]
                        for k in self.x
                        if k[0] == teacher and k[4] == day and k[5] == period
                    ]
                    if slots:
                        self.model.add_at_most_one(slots)

    # ── 2. Room Availability ──────────────────────────────────────────────────
    def _room_availability(self) -> None:
        """No two classes may be scheduled in the same room at the same time."""
        for day in DAYS:
            for period in PERIODS:
                for room in self.rooms:
                    slots = [
                        self.x[k]
                        for k in self.x
                        if k[6] == room and k[4] == day and k[5] == period
                    ]
                    if slots:
                        self.model.add_at_most_one(slots)

    # ── 3. Lecture Count ──────────────────────────────────────────────────────
    def _lecture_count(self) -> None:
        """Each assignment must have exactly lectures_per_week slots assigned."""
        for asgn in self.assignments:
            teacher = asgn["teacher_name"]
            subject = asgn["subject_name"]
            branch  = asgn["branch"]
            year    = asgn["year"]
            required = asgn["lectures_per_week"]

            slots = [
                self.x[k]
                for k in self.x
                if k[0] == teacher and k[1] == subject
                and k[2] == branch and k[3] == year
            ]
            if slots:
                self.model.add(sum(slots) == required)

    # ── 4. Lab 2-Hour Blocks ─────────────────────────────────────────────────
    def _lab_two_hour_blocks(self) -> None:
        """Lab subjects occupy exactly two consecutive periods."""
        for subject in self.lab_subjects:
            for day in DAYS:
                for p in PERIODS[:-1]:   # need p and p+1
                    for k in self.x:
                        if k[1] == subject and k[4] == day and k[5] == p:
                            # If this slot is used, the next must also be used
                            k_next = (k[0], k[1], k[2], k[3], day, p + 1, k[6])
                            if k_next in self.x:
                                self.model.add(self.x[k_next] == self.x[k])

    # ── 5. First Slot Priority ────────────────────────────────────────────────
    def _first_slot_priority(self) -> None:
        """
        Encourage lecture-type subjects to be placed in early periods (1–2).
        Implemented as a soft preference by adding a bonus to objective later.
        Here we enforce: no free period 1 for a branch/year that has lectures.
        """
        # Hard rule: at least one class must be scheduled in period 1 each day
        # for each branch/year combination that has assignments.
        by = set((a["branch"], a["year"]) for a in self.assignments)
        for day in DAYS:
            for branch, year in by:
                slots_p1 = [
                    self.x[k]
                    for k in self.x
                    if k[2] == branch and k[3] == year
                    and k[4] == day and k[5] == 1
                ]
                if slots_p1:
                    self.model.add(sum(slots_p1) >= 1)

    # ── 6. Thursday Club Rule ─────────────────────────────────────────────────
    def _thursday_club_rule(self) -> None:
        """Last period on Thursday is reserved for club activity — no classes."""
        last_period = PERIODS[-1]
        thursday_slots = [
            self.x[k]
            for k in self.x
            if k[4] == "Thursday" and k[5] == last_period
        ]
        for var in thursday_slots:
            self.model.add(var == 0)
