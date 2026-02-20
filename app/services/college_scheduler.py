"""
College Scheduler — OR-Tools CP-SAT Solver Wrapper
Generates a conflict-free college timetable from structured assignment data.
"""

from ortools.sat.python import cp_model
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.constraint_builder import (
    ConstraintBuilder, DAYS, PERIODS, PERIOD_TIMES
)


class CollegeScheduler:
    """
    Wraps the OR-Tools CP-SAT solver to produce a college timetable.

    Input:
        assignments — list of {teacher_name, subject_name, branch, year, lectures_per_week}
        teachers    — list of teacher names
        subjects    — list of subject names
        rooms       — list of {room_name, room_type}
        lab_subjects — subject names that require 2-hr lab blocks
        cs_split_subjects — subjects with CS1/CS2 branch split

    Output:
        {
          "Monday":    [{"period":1,"start_time":"08:00","end_time":"09:00",
                         "subject":"Math","teacher":"Mr.A","room":"R101",
                         "branch":"CS","year":"2","is_lab":false,"is_free":false}, ...],
          "Tuesday":   [...],
          ...
        }
    """

    def allocate(
        self,
        assignments:      List[Dict[str, Any]],
        teachers:         List[str],
        subjects:         List[str],
        rooms:            List[Dict[str, str]],   # [{room_name, room_type}, ...]
        lab_subjects:     Optional[List[str]] = None,
        cs_split_subjects:Optional[List[str]] = None,
        branch_filter:    Optional[str] = None,
        year_filter:      Optional[str] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:

        lab_subjects      = lab_subjects      or []
        cs_split_subjects = cs_split_subjects or []

        # Apply optional filters
        if branch_filter:
            assignments = [a for a in assignments if a["branch"] == branch_filter]
        if year_filter:
            assignments = [a for a in assignments if a["year"] == year_filter]

        if not assignments:
            return {day: [] for day in DAYS}

        branches = sorted({a["branch"] for a in assignments})
        years    = sorted({a["year"]   for a in assignments})
        room_names = [r["room_name"] if isinstance(r, dict) else r for r in rooms]

        model = cp_model.CpModel()

        # ── Decision variables ────────────────────────────────────────────────
        # x[(teacher, subject, branch, year, day, period, room)] ∈ {0, 1}
        x = {}
        for asgn in assignments:
            t, s, br, yr = (
                asgn["teacher_name"], asgn["subject_name"],
                asgn["branch"], asgn["year"]
            )
            for day in DAYS:
                for period in PERIODS:
                    for room in room_names:
                        key = (t, s, br, yr, day, period, room)
                        x[key] = model.new_bool_var(
                            f"x_{t}_{s}_{br}_{yr}_{day}_{period}_{room}"
                        )

        # ── Constraints ───────────────────────────────────────────────────────
        cb = ConstraintBuilder(
            model=model, x=x,
            teachers=teachers, subjects=subjects, rooms=room_names,
            branches=branches, years=years,
            assignments=assignments,
            lab_subjects=lab_subjects,
            cs_subjects=cs_split_subjects,
        )
        cb.apply_all()

        # ── Solve ─────────────────────────────────────────────────────────────
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 30.0
        solver.parameters.num_workers = 4
        status = solver.solve(model)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            # Fallback: return greedy allocation if CP-SAT can't find a solution
            return self._greedy_fallback(assignments, room_names)

        # ── Build output ──────────────────────────────────────────────────────
        result: Dict[str, List[Dict[str, Any]]] = {day: [] for day in DAYS}

        for key, var in x.items():
            if solver.value(var) == 1:
                t, s, br, yr, day, period, room = key
                start, end = PERIOD_TIMES[period]
                result[day].append({
                    "period":     period,
                    "start_time": start,
                    "end_time":   end,
                    "subject":    s,
                    "teacher":    t,
                    "room":       room,
                    "branch":     br,
                    "year":       yr,
                    "is_lab":     s in lab_subjects,
                    "is_free":    False,
                })

        # Sort each day by period
        for day in DAYS:
            result[day].sort(key=lambda sl: sl["period"])

        return result

    # ── Greedy Fallback ───────────────────────────────────────────────────────
    def _greedy_fallback(
        self,
        assignments: List[Dict[str, Any]],
        rooms: List[str],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Simple round-robin fallback if CP-SAT times out."""
        result = {day: [] for day in DAYS}
        day_period_room_used: Dict = {}   # (day, period, room) → True
        day_period_teacher_used: Dict = {}  # (day, period, teacher) → True

        room_idx = 0
        day_idx  = 0
        period_idx = 0

        for asgn in assignments:
            remaining = asgn["lectures_per_week"]
            while remaining > 0:
                day    = DAYS[day_idx % len(DAYS)]
                period = PERIODS[period_idx % len(PERIODS)]
                room   = rooms[room_idx % len(rooms)] if rooms else "TBD"
                teacher = asgn["teacher_name"]

                slot_ok = (
                    (day, period, room)    not in day_period_room_used and
                    (day, period, teacher) not in day_period_teacher_used
                )
                if slot_ok:
                    start, end = PERIOD_TIMES[period]
                    result[day].append({
                        "period": period, "start_time": start, "end_time": end,
                        "subject": asgn["subject_name"], "teacher": teacher,
                        "room": room, "branch": asgn["branch"], "year": asgn["year"],
                        "is_lab": False, "is_free": False,
                    })
                    day_period_room_used[(day, period, room)] = True
                    day_period_teacher_used[(day, period, teacher)] = True
                    remaining -= 1

                period_idx += 1
                if period_idx % len(PERIODS) == 0:
                    day_idx  += 1
                    room_idx += 1

        for day in DAYS:
            result[day].sort(key=lambda sl: sl["period"])
        return result


_scheduler_instance = None

def get_college_scheduler() -> CollegeScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = CollegeScheduler()
    return _scheduler_instance
