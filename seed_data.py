"""
Seed data script to populate the database with sample college data.
Run this before generating a timetable.
"""

from app.models.database import SessionLocal, init_db
from app.models.models import (
    Branch, YearSection, Faculty, Classroom, LabRoom,
    Subject, ConstraintConfig
)


def seed_database():
    """Populate database with sample data."""
    
    # Initialize tables
    init_db()
    
    db = SessionLocal()
    
    try:
        # Check if data already exists
        if db.query(Branch).count() > 0:
            print("Database already seeded. Skipping...")
            return
        
        # Create Branches
        branches_data = [
            ("CSE", "Computer Science & Engineering"),
            ("ECE", "Electronics & Communication Engineering"),
            ("ME", "Mechanical Engineering"),
            ("CE", "Civil Engineering"),
        ]
        
        branches = {}
        for code, name in branches_data:
            branch = Branch(code=code, name=name)
            db.add(branch)
            branches[code] = branch
        
        db.flush()
        
        # Create Year-Sections
        year_sections = {}
        for branch in branches.values():
            for year in [1, 2, 3, 4]:
                for section in ["A", "B", "C"]:
                    ys = YearSection(branch_id=branch.id, year=year, section=section)
                    db.add(ys)
                    year_sections[f"{branch.code}-{year}-{section}"] = ys
        
        db.flush()
        
        # Create Faculty
        faculty_data = [
            ("F001", "Dr. Rajesh Kumar", "CSE"),
            ("F002", "Prof. Priya Sharma", "CSE"),
            ("F003", "Dr. Amit Patel", "CSE"),
            ("F004", "Dr. Neha Singh", "ECE"),
            ("F005", "Prof. Vikram Gupta", "ECE"),
            ("F006", "Dr. Arjun Reddy", "ME"),
            ("F007", "Prof. Deepak Nair", "ME"),
            ("F008", "Dr. Shikha Verma", "CE"),
            ("F009", "Prof. Ravi Chopra", "CE"),
        ]
        
        faculty_map = {}
        for emp_id, name, dept in faculty_data:
            faculty = Faculty(employee_id=emp_id, name=name, department=dept)
            db.add(faculty)
            faculty_map[emp_id] = faculty
        
        db.flush()
        
        # Create Classrooms
        classroom_data = [
            ("LH-101", 60, "A"),
            ("LH-102", 60, "A"),
            ("LH-103", 50, "A"),
            ("LH-201", 60, "B"),
            ("LH-202", 50, "B"),
            ("LH-301", 45, "C"),
            ("LH-302", 45, "C"),
        ]
        
        classrooms = {}
        for room_num, capacity, building in classroom_data:
            classroom = Classroom(room_number=room_num, capacity=capacity, building=building)
            db.add(classroom)
            classrooms[room_num] = classroom
        
        db.flush()
        
        # Create Lab Rooms
        labroom_data = [
            ("LAB-101", "DSA Lab", 30, "A"),
            ("LAB-102", "CN Lab", 30, "A"),
            ("LAB-103", "DBMS Lab", 30, "B"),
            ("LAB-104", "Web Dev Lab", 25, "B"),
            ("LAB-201", "Electronics Lab", 30, "C"),
            ("LAB-202", "CAD Lab", 25, "C"),
        ]
        
        labrooms = {}
        for room_num, lab_type, capacity, building in labroom_data:
            labroom = LabRoom(room_number=room_num, lab_type=lab_type, capacity=capacity, building=building)
            db.add(labroom)
            labrooms[room_num] = labroom
        
        db.flush()
        
        # Create Subjects for CSE Year 3
        cse_3_subjects = [
            ("DS201", "Data Structures", faculty_map["F001"], classrooms["LH-101"], labrooms["LAB-101"], 3, 1, 2, 0),
            ("DBMS201", "Database Management", faculty_map["F002"], classrooms["LH-102"], labrooms["LAB-103"], 3, 1, 2, 0),
            ("CN201", "Computer Networks", faculty_map["F003"], classrooms["LH-103"], labrooms["LAB-102"], 3, 1, 2, 0),
            ("OS201", "Operating Systems", faculty_map["F001"], classrooms["LH-101"], None, 3, 1, 0, 1),
            ("ADA201", "Algorithm Design", faculty_map["F002"], classrooms["LH-202"], None, 2, 1, 0, 0),
        ]
        
        for code, name, faculty, classroom, labroom, lec, tut, lab, sem in cse_3_subjects:
            subject = Subject(
                code=code,
                name=name,
                branch_id=branches["CSE"].id,
                year=3,
                section="A",
                lectures_per_week=lec,
                tutorials_per_week=tut,
                lab_periods_per_week=lab,
                seminar_periods_per_week=sem,
                lab_duration=2,
                faculty_id=faculty.id,
                classroom_id=classroom.id,
                labroom_id=labroom.id if labroom else None
            )
            db.add(subject)
        
        # Create Subjects for CSE Year 3 Section B
        for code, name, faculty, classroom, labroom, lec, tut, lab, sem in cse_3_subjects:
            subject = Subject(
                code=f"{code}B",
                name=f"{name} (Section B)",
                branch_id=branches["CSE"].id,
                year=3,
                section="B",
                lectures_per_week=lec,
                tutorials_per_week=tut,
                lab_periods_per_week=lab,
                seminar_periods_per_week=sem,
                lab_duration=2,
                faculty_id=faculty.id,
                classroom_id=classrooms["LH-201"],
                labroom_id=labroom.id if labroom else None
            )
            db.add(subject)
        
        # Create Subjects for ECE Year 2
        ece_2_subjects = [
            ("EC201", "Circuit Analysis", faculty_map["F004"], classrooms["LH-201"], None, 3, 1, 0, 0),
            ("EM201", "Electromagnetics", faculty_map["F005"], classrooms["LH-202"], labrooms["LAB-201"], 3, 1, 2, 0),
            ("EC202", "Digital Electronics", faculty_map["F004"], classrooms["LH-301"], labrooms["LAB-202"], 3, 1, 2, 0),
        ]
        
        for code, name, faculty, classroom, labroom, lec, tut, lab, sem in ece_2_subjects:
            subject = Subject(
                code=code,
                name=name,
                branch_id=branches["ECE"].id,
                year=2,
                section="A",
                lectures_per_week=lec,
                tutorials_per_week=tut,
                lab_periods_per_week=lab,
                seminar_periods_per_week=sem,
                lab_duration=2,
                faculty_id=faculty.id,
                classroom_id=classroom.id,
                labroom_id=labroom.id if labroom else None
            )
            db.add(subject)
        
        # Create Constraint Configuration
        config = ConstraintConfig(
            college_start_time="08:00",
            college_end_time="16:10",
            periods_per_day=7,
            normal_period_duration=50,
            thursday_period_duration=50,
            tea_break_after_period=2,
            tea_break_duration=20,
            lunch_after_period=4,
            lunch_duration=60,
            min_lab_duration=2,
            max_lab_duration=3
        )
        db.add(config)
        
        # Commit all changes
        db.commit()
        print("Database seeded successfully!")
        print(f"  - {len(branches)} branches created")
        print(f"  - {db.query(YearSection).count()} year-sections created")
        print(f"  - {db.query(Faculty).count()} faculty members created")
        print(f"  - {db.query(Classroom).count()} classrooms created")
        print(f"  - {db.query(LabRoom).count()} lab rooms created")
        print(f"  - {db.query(Subject).count()} subjects created")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {str(e)}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
