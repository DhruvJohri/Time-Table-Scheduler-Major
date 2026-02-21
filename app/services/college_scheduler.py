"""
College Scheduler — OR-Tools CP-SAT Solver Wrapper
Guide-compliant output: flat list of slot objects with exact guide §4 fields.
"""

import re
from ortools.sat.python import cp_model
from typing import List, Dict, Any, Optional
from datetime import datetime


def _norm_year(year_str: str) -> str:
    """Extract numeric part from any year string format."""
    if not year_str:
        return year_str
    m = re.search(r'(\d+)', str(year_str))
    return m.group(1) if m else str(year_str).strip()


from app.services.constraint_builder import (
    ConstraintBuilder, DAYS, PERIODS
)


class CollegeScheduler:
    """
    Wraps the OR-Tools CP-SAT solver to produce a guide-compliant college timetable.

    Input:
        assignments — list of {teacher_name, subject_name, branch, year, section, lectures_per_week}
        teachers    — list of teacher names
        subjects    — list of subject names
        rooms       — list of {room_name, room_type}
        lab_subjects — subject names that require 2-hr lab blocks

    Output (guide §4 flat array):
        {
          "timetable": [
            { "day", "period", "branch", "year"(int), "section",
              "subject", "faculty", "room", "type" },
            ...
          ],
          "unallocated": ["SubjectName", ...]
        }
    """

    def allocate(
        self,
        assignments:       List[Dict[str, Any]],
        teachers:          List[str],
        subjects:          List[str],
        rooms:             List[Dict[str, str]],
        lab_subjects:      Optional[List[str]] = None,
        cs_split_subjects: Optional[List[str]] = None,
        branch_filter:     Optional[str] = None,
        year_filter:       Optional[str] = None,
        section_filter:    Optional[str] = None,
    ) -> Dict[str, Any]:

        lab_subjects      = lab_subjects or []
        cs_split_subjects = cs_split_subjects or []

        # Apply optional filters
        if branch_filter:
            assignments = [a for a in assignments if a["branch"] == branch_filter]
        if year_filter:
            norm_filter = _norm_year(year_filter)
            assignments = [a for a in assignments if _norm_year(a["year"]) == norm_filter]
        if section_filter:
            assignments = [a for a in assignments if a.get("section", "A") == section_filter]

        if not assignments:
            return {"timetable": [], "unallocated": []}

        branches   = sorted({a["branch"]              for a in assignments})
        years      = sorted({a["year"]                for a in assignments})
        sections   = sorted({a.get("section", "A")    for a in assignments})
        room_names = [r["room_name"] if isinstance(r, dict) else r for r in rooms]

        model = cp_model.CpModel()

        # ── Decision variables ────────────────────────────────────────────────
        # x[(teacher, subject, branch, year, section, day, period, room)] ∈ {0,1}
        x = {}
        for asgn in assignments:
            t   = asgn["teacher_name"]
            s   = asgn["subject_name"]
            br  = asgn["branch"]
            yr  = asgn["year"]
            sec = asgn.get("section", "A")
            for day in DAYS:
                for period in PERIODS:
                    for room in room_names:
                        key = (t, s, br, yr, sec, day, period, room)
                        x[key] = model.new_bool_var(
                            f"x_{t}_{s}_{br}_{yr}_{sec}_{day}_{period}_{room}"
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
            # Fallback: greedy allocation
            return self._greedy_fallback(assignments, room_names, lab_subjects)

        # ── Build flat output (guide §4) ──────────────────────────────────────
        result: List[Dict[str, Any]] = []

        for key, var in x.items():
            if solver.value(var) == 1:
                t, s, br, yr, sec, day, period, room = key

                subj_lower = s.lower()
                if s in lab_subjects:
                    slot_type = "LAB"
                elif "tutorial" in subj_lower:
                    slot_type = "TUTORIAL"
                elif "seminar" in subj_lower:
                    slot_type = "SEMINAR"
                else:
                    slot_type = "LECTURE"

                # Convert year to int (guide §4)
                try:
                    year_int = int(_norm_year(yr))
                except (ValueError, TypeError):
                    year_int = yr

                result.append({
                    "day":     day,
                    "period":  period,
                    "branch":  br,
                    "year":    year_int,
                    "section": sec,
                    "subject": s,
                    "faculty": t,
                    "room":    room,
                    "type":    slot_type,
                })

        # Sort for consistency
        result.sort(key=lambda sl: (
            DAYS.index(sl["day"]) if sl["day"] in DAYS else 99,
            sl["period"]
        ))

        # ── Detect unallocated (guide §10) ────────────────────────────────────
        scheduled_counts: Dict[tuple, int] = {}
        for sl in result:
            key_t = (sl["faculty"], sl["subject"], sl["branch"], str(sl["year"]), sl["section"])
            scheduled_counts[key_t] = scheduled_counts.get(key_t, 0) + 1

        unallocated = []
        for asgn in assignments:
            key_t = (
                asgn["teacher_name"], asgn["subject_name"],
                asgn["branch"], _norm_year(asgn["year"]), asgn.get("section", "A")
            )
            got  = scheduled_counts.get(key_t, 0)
            need = asgn["lectures_per_week"]
            if got < need:
                unallocated.append(asgn["subject_name"])

        return {"timetable": result, "unallocated": list(set(unallocated))}

    # ── Greedy Fallback ───────────────────────────────────────────────────────
    def _greedy_fallback(
        self,
        assignments: List[Dict[str, Any]],
        rooms: List[str],
        lab_subjects: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Round-robin fallback when CP-SAT times out. Returns guide §4 format."""
        lab_subjects = lab_subjects or []
        result: List[Dict[str, Any]] = []
        day_period_room_used:    Dict = {}
        day_period_teacher_used: Dict = {}
        scheduled_counts:        Dict = {}

        room_idx = day_idx = period_idx = 0
        max_loops = len(DAYS) * len(PERIODS) * max(1, len(rooms))

        for asgn in assignments:
            remaining = asgn["lectures_per_week"]
            loops = 0
            while remaining > 0 and loops < max_loops:
                loops += 1
                day     = DAYS[day_idx % len(DAYS)]
                period  = PERIODS[period_idx % len(PERIODS)]
                room    = rooms[room_idx % len(rooms)] if rooms else "TBD"
                teacher = asgn["teacher_name"]
                subject = asgn["subject_name"]
                section = asgn.get("section", "A")

                # Skip Thursday P1/P7 (club periods)
                if day == "Thursday" and period in (1, 7):
                    period_idx += 1
                    continue

                # Skip P1/P2 for labs
                if subject in lab_subjects and period in (1, 2):
                    period_idx += 1
                    continue

                slot_ok = (
                    (day, period, room)    not in day_period_room_used and
                    (day, period, teacher) not in day_period_teacher_used
                )
                if slot_ok:
                    subj_lower = subject.lower()
                    if subject in lab_subjects:
                        slot_type = "LAB"
                    elif "tutorial" in subj_lower:
                        slot_type = "TUTORIAL"
                    elif "seminar" in subj_lower:
                        slot_type = "SEMINAR"
                    else:
                        slot_type = "LECTURE"

                    try:
                        year_int = int(_norm_year(asgn["year"]))
                    except (ValueError, TypeError):
                        year_int = asgn["year"]

                    result.append({
                        "day":     day,
                        "period":  period,
                        "branch":  asgn["branch"],
                        "year":    year_int,
                        "section": section,
                        "subject": subject,
                        "faculty": teacher,
                        "room":    room,
                        "type":    slot_type,
                    })
                    key_t = (teacher, subject, asgn["branch"], _norm_year(asgn["year"]), section)
                    scheduled_counts[key_t] = scheduled_counts.get(key_t, 0) + 1
                    day_period_room_used[(day, period, room)] = True
                    day_period_teacher_used[(day, period, teacher)] = True
                    remaining -= 1

                period_idx += 1
                if period_idx % len(PERIODS) == 0:
                    day_idx  += 1
                    room_idx += 1

        result.sort(key=lambda sl: (
            DAYS.index(sl["day"]) if sl["day"] in DAYS else 99,
            sl["period"]
        ))

        unallocated = []
        for asgn in assignments:
            key_t = (
                asgn["teacher_name"], asgn["subject_name"],
                asgn["branch"], _norm_year(asgn["year"]), asgn.get("section", "A")
            )
            got  = scheduled_counts.get(key_t, 0)
            need = asgn["lectures_per_week"]
            if got < need:
                unallocated.append(asgn["subject_name"])

        return {"timetable": result, "unallocated": list(set(unallocated))}


_scheduler_instance = None

def get_college_scheduler() -> CollegeScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = CollegeScheduler()
    return _scheduler_instance
