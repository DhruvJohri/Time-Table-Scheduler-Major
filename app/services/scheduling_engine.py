"""
Intelligent Scheduling Engine - Core timetable generation logic
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import random


class SchedulingEngine:
    """
    Core scheduling engine that generates optimized timetables
    based on user profile and preferences.
    """

    @staticmethod
    def time_to_minutes(time_str: str) -> int:
        """Convert HH:MM format to minutes from midnight"""
        hours, minutes = map(int, time_str.split(":"))
        return hours * 60 + minutes

    @staticmethod
    def minutes_to_time(minutes: int) -> str:
        """Convert minutes from midnight to HH:MM format"""
        hours = (minutes // 60) % 24
        mins = minutes % 60
        return f"{hours:02d}:{mins:02d}"

    @staticmethod
    def add_minutes(time_str: str, minutes_to_add: int) -> str:
        """Add minutes to a time string"""
        total_minutes = SchedulingEngine.time_to_minutes(time_str) + minutes_to_add
        return SchedulingEngine.minutes_to_time(total_minutes)

    @staticmethod
    def get_day_name(date_str: Optional[str] = None) -> str:
        """Get day name from date string"""
        if not date_str:
            date_obj = datetime.now()
        else:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return days[date_obj.weekday()]

    @staticmethod
    def get_energy_level(time_str: str, productivity_type: str) -> str:
        """Determine energy level based on time and productivity type"""
        hour = SchedulingEngine.time_to_minutes(time_str) // 60

        if productivity_type == "morning_person":
            if 6 <= hour <= 10:
                return "high"
            elif 10 < hour <= 14:
                return "medium"
            else:
                return "low"
        elif productivity_type == "night_owl":
            if 20 <= hour <= 23:
                return "high"
            elif 14 < hour <= 18:
                return "medium"
            else:
                return "low"
        else:  # balanced
            if (8 <= hour <= 11) or (14 <= hour <= 17):
                return "high"
            elif (11 < hour <= 14) or (17 < hour <= 20):
                return "medium"
            else:
                return "low"

    @staticmethod
    def calculate_total_hours(blocks: List[Dict], block_type: str) -> float:
        """Calculate total hours for a specific activity type"""
        total = 0
        for block in blocks:
            if block.get("type") == block_type:
                start_min = SchedulingEngine.time_to_minutes(block.get("start", "00:00"))
                end_min = SchedulingEngine.time_to_minutes(block.get("end", "00:00"))
                duration_hours = (end_min - start_min) / 60
                total += duration_hours
        return round(total, 2)

    @staticmethod
    def insert_fixed_activities(blocks: List[Dict], user_profile: Dict) -> None:
        """Insert fixed activities (meals, work, exercise) into timetable"""
        
        # Lunch
        blocks.append({
            "start": user_profile.get("lunch_time_preference", "12:30"),
            "end": SchedulingEngine.add_minutes(user_profile.get("lunch_time_preference", "12:30"), 60),
            "type": "meal",
            "title": "Lunch",
            "is_fixed": True
        })

        # Tea/Snack
        blocks.append({
            "start": user_profile.get("tea_time_preference", "15:00"),
            "end": SchedulingEngine.add_minutes(user_profile.get("tea_time_preference", "15:00"), 30),
            "type": "meal",
            "title": "Tea/Snack",
            "is_fixed": True
        })

        # Exercise
        if user_profile.get("exercise_time"):
            blocks.append({
                "start": user_profile.get("exercise_time"),
                "end": SchedulingEngine.add_minutes(
                    user_profile.get("exercise_time"),
                    user_profile.get("exercise_duration", 45)
                ),
                "type": "exercise",
                "is_fixed": True
            })

        # Work/College hours
        if user_profile.get("work_start_time") and user_profile.get("work_end_time"):
            blocks.append({
                "start": user_profile.get("work_start_time"),
                "end": user_profile.get("work_end_time"),
                "type": "work",
                "title": "Work/College",
                "is_fixed": True
            })

    @staticmethod
    def get_remaining_slots(blocks: List[Dict], wake_up: int, sleep_time: int) -> List[Dict]:
        """Calculate remaining time slots after fixed activities"""
        sorted_blocks = sorted(blocks, key=lambda b: SchedulingEngine.time_to_minutes(b.get("start", "00:00")))
        slots = []
        current_time = wake_up

        for block in sorted_blocks:
            block_start = SchedulingEngine.time_to_minutes(block.get("start", "00:00"))
            if block_start > current_time:
                slots.append({
                    "start": current_time,
                    "end": block_start,
                    "duration": block_start - current_time
                })
            current_time = max(current_time, SchedulingEngine.time_to_minutes(block.get("end", "00:00")))

        if current_time < sleep_time:
            slots.append({
                "start": current_time,
                "end": sleep_time,
                "duration": sleep_time - current_time
            })

        return slots

    @staticmethod
    def distribute_study_blocks(
        blocks: List[Dict],
        user_profile: Dict,
        available_slots: List[Dict],
        wake_up: int
    ) -> None:
        """Distribute study subjects across available time slots"""
        
        subjects = user_profile.get("subjects", [])
        sorted_subjects = sorted(subjects, key=lambda s: s.get("priority", 5))

        slot_index = 0

        for subject in sorted_subjects:
            daily_minutes = int(subject.get("daily_hours", 2) * 60)
            remaining_minutes = daily_minutes

            while remaining_minutes > 0 and slot_index < len(available_slots):
                slot = available_slots[slot_index]
                # Calculate block duration: prefer 60-90 min blocks, respect slot size
                slot_available = min(slot["duration"], 120)
                block_duration = min(
                    remaining_minutes,  # Don't exceed required study time
                    min(90, max(45, slot_available))  # Prefer 45-90 min blocks
                )

                if block_duration >= 45:
                    block_start = SchedulingEngine.minutes_to_time(slot["start"])
                    end_time = SchedulingEngine.add_minutes(block_start, int(block_duration))
                    blocks.append({
                        "start": block_start,
                        "end": end_time,
                        "type": "study",
                        "subject": subject.get("name"),
                        "priority": subject.get("priority"),
                        "energy_level": SchedulingEngine.get_energy_level(
                            block_start,
                            user_profile.get("productivity_type", "balanced")
                        )
                    })

                    remaining_minutes -= int(block_duration)
                    slot["start"] += int(block_duration)
                    slot["duration"] -= int(block_duration)

                    if slot["duration"] < 45:
                        slot_index += 1
                else:
                    slot_index += 1

    @staticmethod
    def insert_breaks(blocks: List[Dict]) -> None:
        """Insert breaks between study blocks strategically"""
        study_blocks = [
            b for b in blocks if b.get("type") == "study"
        ]
        study_blocks.sort(key=lambda b: SchedulingEngine.time_to_minutes(b.get("start", "00:00")))

        for i in range(len(study_blocks) - 1):
            current_block = study_blocks[i]
            next_block = study_blocks[i + 1]

            gap = (
                SchedulingEngine.time_to_minutes(next_block.get("start", "00:00")) -
                SchedulingEngine.time_to_minutes(current_block.get("end", "00:00"))
            )

            if gap >= 10:
                blocks.append({
                    "start": current_block.get("end"),
                    "end": SchedulingEngine.add_minutes(current_block.get("end"), min(15, gap)),
                    "type": "break"
                })

    @staticmethod
    def add_free_time(
        blocks: List[Dict],
        user_profile: Dict,
        available_slots: List[Dict],
        sleep_time: int
    ) -> None:
        """Add free time blocks to the timetable"""
        free_time_minutes = int(user_profile.get("free_time_required", 2) * 60)
        remaining_free_time = free_time_minutes

        for slot in available_slots:
            if remaining_free_time <= 0:
                break

            duration = min(remaining_free_time, slot["duration"] // 2)
            if duration >= 30:
                free_start = SchedulingEngine.minutes_to_time(slot["start"] + slot["duration"] // 2)
                blocks.append({
                    "start": free_start,
                    "end": SchedulingEngine.add_minutes(free_start, int(duration)),
                    "type": "free_time"
                })
                remaining_free_time -= int(duration)

    @staticmethod
    def generate_daily_timetable(user_profile: Dict, date: Optional[str] = None) -> Dict:
        """Generate a daily timetable"""
        blocks = []
        
        wake_up_minutes = SchedulingEngine.time_to_minutes(user_profile.get("wake_up_time", "06:00"))
        sleep_time_minutes = SchedulingEngine.time_to_minutes(user_profile.get("sleep_time", "23:00"))

        # Insert fixed activities
        SchedulingEngine.insert_fixed_activities(blocks, user_profile)

        # Get remaining available slots
        remaining_slots = SchedulingEngine.get_remaining_slots(blocks, wake_up_minutes, sleep_time_minutes)

        # Distribute study blocks
        SchedulingEngine.distribute_study_blocks(blocks, user_profile, remaining_slots, wake_up_minutes)

        # Insert breaks
        SchedulingEngine.insert_breaks(blocks)

        # Add free time
        SchedulingEngine.add_free_time(blocks, user_profile, remaining_slots, sleep_time_minutes)

        # Add sleep
        blocks.append({
            "start": user_profile.get("sleep_time", "23:00"),
            "end": user_profile.get("wake_up_time", "06:00"),
            "type": "sleep"
        })

        # Sort blocks by time
        blocks.sort(key=lambda b: SchedulingEngine.time_to_minutes(b.get("start", "00:00")))

        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        return {
            "date": date,
            "day": SchedulingEngine.get_day_name(date),
            "blocks": blocks,
            "total_study_hours": SchedulingEngine.calculate_total_hours(blocks, "study"),
            "total_work_hours": SchedulingEngine.calculate_total_hours(blocks, "work")
        }

    @staticmethod
    def generate_weekly_timetable(user_profile: Dict, start_date: str) -> Dict:
        """Generate a weekly timetable"""
        days = []
        start = datetime.strptime(start_date, "%Y-%m-%d")

        for i in range(7):
            current_date = start + timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")
            is_weekend = current_date.weekday() >= 5

            if is_weekend:
                day_timetable = SchedulingEngine.generate_weekend_timetable(user_profile, date_str)
            else:
                day_timetable = SchedulingEngine.generate_daily_timetable(user_profile, date_str)

            days.append(day_timetable)

        week_end = start + timedelta(days=6)

        return {
            "week_start": start_date,
            "week_end": week_end.strftime("%Y-%m-%d"),
            "days": days,
            "summary": SchedulingEngine.calculate_weekly_summary(days)
        }

    @staticmethod
    def generate_weekend_timetable(user_profile: Dict, date: str) -> Dict:
        """Generate weekend-optimized timetable (more relaxed)"""
        blocks = []

        # Meditation
        blocks.append({
            "start": "07:00",
            "end": "07:30",
            "type": "meditation"
        })

        # Exercise (longer on weekends)
        if user_profile.get("exercise_time"):
            blocks.append({
                "start": user_profile.get("exercise_time"),
                "end": SchedulingEngine.add_minutes(
                    user_profile.get("exercise_time"),
                    user_profile.get("exercise_duration", 60)
                ),
                "type": "exercise"
            })

        # Meals
        blocks.append({
            "start": user_profile.get("lunch_time_preference", "12:30"),
            "end": SchedulingEngine.add_minutes(user_profile.get("lunch_time_preference", "12:30"), 60),
            "type": "meal",
            "title": "Lunch"
        })

        blocks.append({
            "start": user_profile.get("tea_time_preference", "15:00"),
            "end": SchedulingEngine.add_minutes(user_profile.get("tea_time_preference", "15:00"), 30),
            "type": "meal",
            "title": "Tea/Snack"
        })

        # Light study (half the weekday amount)
        subjects = user_profile.get("subjects", [])[:2]
        study_start = "09:00"

        for subject in subjects:
            duration = max(30, int(subject.get("daily_hours", 2) / 2 * 60))
            blocks.append({
                "start": study_start,
                "end": SchedulingEngine.add_minutes(study_start, duration),
                "type": "study",
                "subject": subject.get("name"),
                "priority": subject.get("priority")
            })
            study_start = SchedulingEngine.add_minutes(study_start, duration + 30)

        # Leisure time
        blocks.append({
            "start": "15:00",
            "end": "18:00",
            "type": "free_time",
            "title": "Leisure / Hobby"
        })

        # Dinner
        blocks.append({
            "start": "19:00",
            "end": "19:45",
            "type": "meal",
            "title": "Dinner"
        })

        # Sleep
        blocks.append({
            "start": user_profile.get("sleep_time", "23:00"),
            "end": user_profile.get("wake_up_time", "06:00"),
            "type": "sleep"
        })

        blocks.sort(key=lambda b: SchedulingEngine.time_to_minutes(b.get("start", "00:00")))

        return {
            "date": date,
            "day": SchedulingEngine.get_day_name(date),
            "blocks": blocks,
            "total_study_hours": SchedulingEngine.calculate_total_hours(blocks, "study")
        }

    @staticmethod
    def calculate_weekly_summary(days: List[Dict]) -> Dict:
        """Calculate weekly summary statistics"""
        subject_distribution = {}
        total_study_hours = 0
        total_work_hours = 0

        for day in days:
            total_study_hours += day.get("total_study_hours", 0)
            total_work_hours += day.get("total_work_hours", 0)

            for block in day.get("blocks", []):
                if block.get("type") == "study" and block.get("subject"):
                    start_min = SchedulingEngine.time_to_minutes(block.get("start", "00:00"))
                    end_min = SchedulingEngine.time_to_minutes(block.get("end", "00:00"))
                    hours = (end_min - start_min) / 60
                    subject = block.get("subject")
                    subject_distribution[subject] = subject_distribution.get(subject, 0) + hours

        return {
            "total_study_hours": round(total_study_hours, 2),
            "total_work_hours": round(total_work_hours, 2),
            "subject_distribution": {k: round(v, 2) for k, v in subject_distribution.items()}
        }

    @staticmethod
    def apply_optimization(
        timetable: List[Dict],
        optimization: str
    ) -> List[Dict]:
        """Apply AI optimization modifications to timetable"""
        # Normalize input - ensure timetable is always a list of days
        if not isinstance(timetable, list):
            timetable = [timetable]
        
        modified = []
        for day in timetable:
            if isinstance(day, dict):
                modified.append(dict(day))
            else:
                modified.append(day)

        if optimization == "reduce_stress":
            return SchedulingEngine._reduce_stress(modified)
        elif optimization == "more_focus":
            return SchedulingEngine._add_more_focus(modified)
        elif optimization == "add_revision":
            return SchedulingEngine._add_revision_slots(modified)
        elif optimization == "weekend_relax":
            return SchedulingEngine._weekend_relax_mode(modified)

        return modified

    @staticmethod
    def _reduce_stress(timetable: List[Dict]) -> List[Dict]:
        """Reduce stress: shorter study blocks, more breaks"""
        for day in timetable:
            if "blocks" not in day:
                continue
                
            new_blocks = []
            for block in day.get("blocks", []):
                block_copy = dict(block)
                if block_copy.get("type") == "study":
                    start_min = SchedulingEngine.time_to_minutes(block_copy.get("start", "00:00"))
                    end_min = SchedulingEngine.time_to_minutes(block_copy.get("end", "00:00"))
                    duration = end_min - start_min

                    # Split longer blocks: if > 2 hours, reduce to 90 mins
                    if duration > 120:
                        block_copy["end"] = SchedulingEngine.add_minutes(block_copy.get("start"), 90)
                        # Add a break after the study block
                        new_blocks.append(block_copy)
                        new_blocks.append({
                            "start": block_copy["end"],
                            "end": SchedulingEngine.add_minutes(block_copy["end"], 15),
                            "type": "break"
                        })
                        continue
                
                new_blocks.append(block_copy)
            day["blocks"] = new_blocks

        return timetable

    @staticmethod
    def _add_more_focus(timetable: List[Dict]) -> List[Dict]:
        """More focus: longer study blocks, minimal distractions"""
        for day in timetable:
            if "blocks" not in day:
                continue
            
            new_blocks = []
            for block in day.get("blocks", []):
                # Skip only non-essential free time, keep meals and breaks
                if block.get("type") == "free_time" and block.get("title") != "Leisure / Hobby":
                    continue
                    
                block_copy = dict(block)
                if block_copy.get("type") == "study":
                    block_copy["energy_level"] = "high"
                new_blocks.append(block_copy)
            day["blocks"] = new_blocks

        return timetable

    @staticmethod
    def _add_revision_slots(timetable: List[Dict]) -> List[Dict]:
        """Add revision slots for studied subjects"""
        for day in timetable:
            if "blocks" not in day:
                continue
                
            studied_subjects = set()
            blocks = day.get("blocks", [])
            occupied_times = set()

            for block in blocks:
                if block.get("type") == "study" and block.get("subject"):
                    studied_subjects.add(block.get("subject"))
                # Track occupied time slots for conflict avoidance
                start_min = SchedulingEngine.time_to_minutes(block.get("start", "00:00"))
                end_min = SchedulingEngine.time_to_minutes(block.get("end", "00:00"))
                for minute in range(start_min, end_min):
                    occupied_times.add(minute)

            # Find available slot for revision (after 16:00, avoid conflicts)
            revision_start_min = SchedulingEngine.time_to_minutes("16:00")
            revision_end_min = SchedulingEngine.time_to_minutes("20:00")
            
            for subject in studied_subjects:
                # Find first available 30-min slot
                found_slot = False
                for minute in range(revision_start_min, revision_end_min - 30):
                    if not any(m in occupied_times for m in range(minute, minute + 30)):
                        blocks.append({
                            "start": SchedulingEngine.minutes_to_time(minute),
                            "end": SchedulingEngine.minutes_to_time(minute + 30),
                            "type": "revision",
                            "subject": subject
                        })
                        # Mark as occupied
                        for m in range(minute, minute + 30):
                            occupied_times.add(m)
                        found_slot = True
                        break

            day["blocks"] = sorted(
                blocks,
                key=lambda b: SchedulingEngine.time_to_minutes(b.get("start", "00:00"))
            )

        return timetable

    @staticmethod
    def _weekend_relax_mode(timetable: List[Dict]) -> List[Dict]:
        """Weekend relax: reduce overall workload"""
        for day in timetable:
            if "blocks" not in day:
                continue
                
            new_blocks = []
            for block in day.get("blocks", []):
                block_copy = dict(block)
                if block_copy.get("type") == "study":
                    start_min = SchedulingEngine.time_to_minutes(block_copy.get("start", "00:00"))
                    end_min = SchedulingEngine.time_to_minutes(block_copy.get("end", "00:00"))
                    duration = end_min - start_min

                    # Reduce study duration on weekends: max 45 mins per block
                    if duration > 60:
                        block_copy["end"] = SchedulingEngine.add_minutes(block_copy.get("start"), 45)
                
                new_blocks.append(block_copy)
            day["blocks"] = new_blocks

        return timetable


# Singleton instance
_engine = SchedulingEngine()


def get_scheduling_engine() -> SchedulingEngine:
    """Get scheduling engine instance"""
    return _engine
