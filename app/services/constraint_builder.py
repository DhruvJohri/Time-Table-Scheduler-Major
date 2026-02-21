"""
Constraint Builder Module
Applies academic scheduling constraints to the OR-Tools CP-SAT model.
Guide compliant: hard lab P1/P2 block, consecutive lab, faculty/room uniqueness,
Thursday P1+P7 club reservation, weekly load.
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

    Variable key tuple layout:
        (teacher, subject, branch, year, section, day, period, room)
          [0]      [1]      [2]    [3]   [4]      [5]  [6]     [7]
    """

    def __init__(
        self,
        model:        cp_model.CpModel,
        x:            Dict,          # x[(teacher, subject, branch, year, section, day, period, room)]
        teachers:     List[str],
        subjects:     List[str],
        rooms:        List[str],
        branches:     List[str],
        years:        List[str],
        assignments:  List[Dict[str, Any]],
        lab_subjects: List[str],
        cs_subjects:  List[str],
    ):
        self.model        = model
        self.x            = x
        self.teachers     = teachers
        self.subjects     = subjects
        self.rooms        = rooms
        self.branches     = branches
        self.years        = years
        self.assignments  = assignments
        self.lab_subjects = lab_subjects
        self.cs_subjects  = cs_subjects

    def apply_all(self) -> None:
        self._teacher_uniqueness()
        self._room_availability()
        self._lecture_count()
        self._lab_no_early_periods()    # Phase 3: hard P1/P2 block for labs
        self._lab_two_hour_blocks()
        self._thursday_club_rule()
        self._first_slot_priority()

    # ── 1. Teacher Uniqueness ─────────────────────────────────────────────────
    def _teacher_uniqueness(self) -> None:
        """A teacher cannot appear in more than one slot at the same time."""
        for day in DAYS:
            for period in PERIODS:
                for teacher in self.teachers:
                    slots = [
                        self.x[k]
                        for k in self.x
                        if k[0] == teacher and k[5] == day and k[6] == period
                    ]
                    if slots:
                        self.model.add_at_most_one(slots)

    # ── 2. Room Availability ──────────────────────────────────────────────────
    def _room_availability(self) -> None:
        """No two classes may be in the same room at the same time."""
        for day in DAYS:
            for period in PERIODS:
                for room in self.rooms:
                    slots = [
                        self.x[k]
                        for k in self.x
                        if k[7] == room and k[5] == day and k[6] == period
                    ]
                    if slots:
                        self.model.add_at_most_one(slots)

    # ── 3. Lecture Count (weekly load) ────────────────────────────────────────
    def _lecture_count(self) -> None:
        """Each assignment must have exactly lectures_per_week slots assigned."""
        for asgn in self.assignments:
            teacher  = asgn["teacher_name"]
            subject  = asgn["subject_name"]
            branch   = asgn["branch"]
            year     = asgn["year"]
            section  = asgn.get("section", "A")
            required = asgn["lectures_per_week"]

            slots = [
                self.x[k]
                for k in self.x
                if k[0] == teacher and k[1] == subject
                and k[2] == branch and k[3] == year
                and k[4] == section
            ]
            if slots:
                self.model.add(sum(slots) == required)

    # ── 4. HARD: Labs NOT in P1 or P2 ────────────────────────────────────────
    def _lab_no_early_periods(self) -> None:
        """
        Phase 3 — Hard constraint: lab subjects cannot be placed in P1 or P2.
        Sets every decision variable for a lab subject at period 1 or 2 to 0.
        """
        for k, var in self.x.items():
            if k[1] in self.lab_subjects and k[6] in (1, 2):
                self.model.add(var == 0)

    # ── 5. Lab 2-Hour Consecutive Blocks ─────────────────────────────────────
    def _lab_two_hour_blocks(self) -> None:
        """Lab subjects occupy exactly two consecutive periods."""
        for subject in self.lab_subjects:
            for day in DAYS:
                for p in PERIODS[:-1]:   # need p and p+1
                    for k in self.x:
                        if k[1] == subject and k[5] == day and k[6] == p:
                            # If slot at period p is used, p+1 must also be used
                            k_next = (k[0], k[1], k[2], k[3], k[4], day, p + 1, k[7])
                            if k_next in self.x:
                                self.model.add(self.x[k_next] == self.x[k])

    # ── 6. Thursday Club Rule ─────────────────────────────────────────────────
    def _thursday_club_rule(self) -> None:
        """
        Thursday P1 and P7 are reserved for Club Activity.
        No academic classes allowed in these two slots.
        Guide §7: 'Thursday P1 & P7 always show Club Activity'
        """
        club_periods = {PERIODS[0], PERIODS[-1]}   # periods 1 and 7
        for k, var in self.x.items():
            if k[5] == "Thursday" and k[6] in club_periods:
                self.model.add(var == 0)

    # ── 7. First Slot Priority (soft → hard) ─────────────────────────────────
    def _first_slot_priority(self) -> None:
        """
        Encourage at least one class in P1 each day for each branch/year/section.
        """
        bys = set(
            (a["branch"], a["year"], a.get("section", "A"))
            for a in self.assignments
        )
        for day in DAYS:
            for branch, year, section in bys:
                slots_p1 = [
                    self.x[k]
                    for k in self.x
                    if k[2] == branch and k[3] == year and k[4] == section
                    and k[5] == day and k[6] == 1
                ]
                if slots_p1:
                    self.model.add(sum(slots_p1) >= 1)
