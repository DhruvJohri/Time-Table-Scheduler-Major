"""
Excel upload parsing and synchronization to SQL models.

Supports .xlsx files without external parser dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import re
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.models import (
    Branch, YearSection, Faculty, Classroom, LabRoom, Subject
)

NS = {
    "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "pkgrel": "http://schemas.openxmlformats.org/package/2006/relationships",
}

BRANCH_ALIASES = {
    "CS": "CSE",
    "CSE": "CSE",
    "COMPUTER SCIENCE": "CSE",
    "ECE": "ECE",
    "EEE": "EEE",
    "ME": "ME",
    "CE": "CE",
    "IT": "IT",
}


@dataclass
class ImportIssue:
    row: int
    message: str


def _norm_text(value: str) -> str:
    return " ".join((value or "").strip().upper().split())


def _normalize_branch(value: str) -> str:
    key = _norm_text(value)
    return BRANCH_ALIASES.get(key, key[:10] if key else "GEN")


def _parse_year(value: str) -> int:
    text = _norm_text(value)
    match = re.search(r"(\d+)", text)
    if not match:
        return 1
    year = int(match.group(1))
    if year < 1:
        return 1
    if year > 4:
        return 4
    return year


def _slug_code(name: str, size: int = 8) -> str:
    tokens = re.findall(r"[A-Z0-9]+", _norm_text(name))
    if not tokens:
        return "SUBJ"
    short = "".join(t[0] for t in tokens if t)[:size]
    return short or tokens[0][:size]


def _col_to_num(col: str) -> int:
    num = 0
    for ch in col:
        if ch.isalpha():
            num = num * 26 + (ord(ch.upper()) - ord("A") + 1)
    return num


def _xlsx_rows_from_bytes(content: bytes) -> List[List[str]]:
    with zipfile.ZipFile(BytesIO(content)) as zf:
        shared: List[str] = []
        if "xl/sharedStrings.xml" in zf.namelist():
            root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in root.findall("main:si", NS):
                shared.append("".join((t.text or "") for t in si.findall(".//main:t", NS)))

        workbook = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
        rid_to_target = {
            rel.attrib["Id"]: rel.attrib["Target"]
            for rel in rels.findall("pkgrel:Relationship", NS)
        }
        first_sheet = workbook.find("main:sheets/main:sheet", NS)
        if first_sheet is None:
            return []
        rel_id = first_sheet.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rid_to_target.get(rel_id, "")
        if not target:
            return []
        if not target.startswith("xl/"):
            target = f"xl/{target}"

        sheet = ET.fromstring(zf.read(target))
        rows: List[List[str]] = []
        for row in sheet.findall(".//main:sheetData/main:row", NS):
            cells: Dict[int, str] = {}
            for cell in row.findall("main:c", NS):
                ref = cell.attrib.get("r", "")
                col = "".join(ch for ch in ref if ch.isalpha())
                idx = _col_to_num(col)
                cell_type = cell.attrib.get("t")
                value_node = cell.find("main:v", NS)
                value = ""
                if cell_type == "s":
                    if value_node is not None and value_node.text is not None:
                        s_idx = int(value_node.text)
                        value = shared[s_idx] if 0 <= s_idx < len(shared) else ""
                elif cell_type == "inlineStr":
                    is_node = cell.find("main:is", NS)
                    if is_node is not None:
                        value = "".join((t.text or "") for t in is_node.findall(".//main:t", NS))
                else:
                    value = value_node.text if value_node is not None and value_node.text is not None else ""
                cells[idx] = (value or "").strip()
            if cells:
                max_col = max(cells.keys())
                rows.append([cells.get(i, "").strip() for i in range(1, max_col + 1)])
        return rows


def _index_headers(headers: List[str]) -> Dict[str, int]:
    index: Dict[str, int] = {}
    for i, name in enumerate(headers):
        index[_norm_text(name)] = i
    return index


def _next_faculty_code(db: Session) -> str:
    i = db.query(Faculty).count() + 1
    while True:
        code = f"F{i:03d}"
        exists = db.query(Faculty).filter(Faculty.employee_id == code).first()
        if not exists:
            return code
        i += 1


def _get_or_create_branch(db: Session, branch_code: str) -> Branch:
    branch = db.query(Branch).filter(Branch.code == branch_code).first()
    if branch:
        return branch
    branch = Branch(code=branch_code, name=branch_code)
    db.add(branch)
    db.flush()
    return branch


def _get_or_create_year_section(db: Session, branch_id: int, year: int, section: str) -> YearSection:
    ys = db.query(YearSection).filter(
        YearSection.branch_id == branch_id,
        YearSection.year == year,
        YearSection.section == section
    ).first()
    if ys:
        return ys
    ys = YearSection(branch_id=branch_id, year=year, section=section)
    db.add(ys)
    db.flush()
    return ys


def _get_or_create_faculty(db: Session, teacher_name: str, dept: str) -> Faculty:
    faculty = db.query(Faculty).filter(Faculty.name == teacher_name).first()
    if faculty:
        if not faculty.department:
            faculty.department = dept
        return faculty
    faculty = Faculty(
        employee_id=_next_faculty_code(db),
        name=teacher_name,
        department=dept,
        is_active=True
    )
    db.add(faculty)
    db.flush()
    return faculty


def _is_lab_room(room: str) -> bool:
    text = _norm_text(room)
    return "LAB" in text or text.startswith("CC")


def _get_or_create_room(db: Session, room_number: str) -> Tuple[Optional[Classroom], Optional[LabRoom]]:
    room = room_number.strip()
    if not room:
        return None, None
    if _is_lab_room(room):
        lab = db.query(LabRoom).filter(LabRoom.room_number == room).first()
        if lab is None:
            lab = LabRoom(
                room_number=room,
                lab_type=room,
                capacity=60,
                building="A",
                is_active=True
            )
            db.add(lab)
            db.flush()
        return None, lab
    classroom = db.query(Classroom).filter(Classroom.room_number == room).first()
    if classroom is None:
        classroom = Classroom(
            room_number=room,
            capacity=80,
            building="A",
            is_active=True
        )
        db.add(classroom)
        db.flush()
    return classroom, None


def _get_or_create_subject(
    db: Session,
    subject_name: str,
    branch_id: int,
    year: int,
    section: str,
    faculty_id: int,
    preferred_code: Optional[str] = None
) -> Subject:
    subject = db.query(Subject).filter(
        Subject.name == subject_name,
        Subject.branch_id == branch_id,
        Subject.year == year,
        Subject.section == section,
        Subject.faculty_id == faculty_id
    ).first()
    if subject:
        subject.is_active = True
        return subject

    base_code = _norm_text(preferred_code) if preferred_code else _slug_code(subject_name)
    base_code = re.sub(r"[^A-Z0-9]", "", base_code)[:20] or _slug_code(subject_name)
    code = base_code
    suffix = 1
    while db.query(Subject).filter(
        Subject.code == code,
        Subject.branch_id == branch_id,
        Subject.year == year,
        Subject.section == section
    ).first():
        suffix += 1
        code = f"{base_code}{suffix}"

    subject = Subject(
        code=code,
        name=subject_name,
        branch_id=branch_id,
        year=year,
        section=section,
        lectures_per_week=0,
        tutorials_per_week=0,
        lab_periods_per_week=0,
        seminar_periods_per_week=0,
        lab_duration=2,
        faculty_id=faculty_id,
        classroom_id=None,
        labroom_id=None,
        is_active=True
    )
    db.add(subject)
    db.flush()
    return subject


def import_master_file(db: Session, content: bytes) -> Dict:
    rows = _xlsx_rows_from_bytes(content)
    if not rows:
        return {"success": False, "message": "No rows found in master file", "issues": []}
    headers = _index_headers(rows[0])
    required = ["TEACHERNAME", "SUBJECTNAME", "YEAR", "BRANCH", "CLASSROOM"]
    missing = [col for col in required if col not in headers]
    if missing:
        return {"success": False, "message": f"Missing required columns: {', '.join(missing)}", "issues": []}

    issues: List[ImportIssue] = []
    processed = 0

    for i, row in enumerate(rows[1:], start=2):
        try:
            teacher = row[headers["TEACHERNAME"]].strip()
            subject_name = row[headers["SUBJECTNAME"]].strip()
            year = _parse_year(row[headers["YEAR"]])
            branch_code = _normalize_branch(row[headers["BRANCH"]])
            room = row[headers["CLASSROOM"]].strip()
            section = row[headers["SECTION"]].strip().upper() if "SECTION" in headers and headers["SECTION"] < len(row) and row[headers["SECTION"]].strip() else "A"

            if not teacher or not subject_name:
                issues.append(ImportIssue(i, "TeacherName/SubjectName is empty"))
                continue

            branch = _get_or_create_branch(db, branch_code)
            _get_or_create_year_section(db, branch.id, year, section)
            faculty = _get_or_create_faculty(db, teacher, dept=branch_code)
            classroom, labroom = _get_or_create_room(db, room)
            preferred_code = row[headers["SUBJECTCODE"]].strip() if "SUBJECTCODE" in headers and headers["SUBJECTCODE"] < len(row) else None
            subject = _get_or_create_subject(
                db, subject_name, branch.id, year, section, faculty.id, preferred_code=preferred_code
            )

            subject.classroom_id = classroom.id if classroom else None
            subject.labroom_id = labroom.id if labroom else None
            subject.lab_duration = 2
            subject.is_active = True

            processed += 1
        except Exception as exc:
            issues.append(ImportIssue(i, str(exc)))

    db.commit()
    return {
        "success": True,
        "message": "Master file synchronized",
        "processed_rows": processed,
        "issues": [issue.__dict__ for issue in issues],
    }


def _subject_type(subject_name: str) -> str:
    value = _norm_text(subject_name)
    if "LAB" in value:
        return "LAB"
    if "TUTORIAL" in value:
        return "TUTORIAL"
    if "SEMINAR" in value:
        return "SEMINAR"
    return "LECTURE"


def import_assignment_file(db: Session, content: bytes) -> Dict:
    rows = _xlsx_rows_from_bytes(content)
    if not rows:
        return {"success": False, "message": "No rows found in assignment file", "issues": []}
    headers = _index_headers(rows[0])
    required = ["TEACHERNAME", "SUBJECTNAME", "YEAR", "BRANCH", "LECTURESPERWEEK"]
    missing = [col for col in required if col not in headers]
    if missing:
        return {"success": False, "message": f"Missing required columns: {', '.join(missing)}", "issues": []}

    parsed_rows: List[Tuple[int, str, str, int, str, str, int]] = []
    issues: List[ImportIssue] = []

    for i, row in enumerate(rows[1:], start=2):
        try:
            teacher = row[headers["TEACHERNAME"]].strip()
            subject_name = row[headers["SUBJECTNAME"]].strip()
            year = _parse_year(row[headers["YEAR"]])
            branch_code = _normalize_branch(row[headers["BRANCH"]])
            section = row[headers["SECTION"]].strip().upper() if "SECTION" in headers and headers["SECTION"] < len(row) and row[headers["SECTION"]].strip() else "A"
            count_raw = row[headers["LECTURESPERWEEK"]].strip()
            count = int(float(count_raw)) if count_raw else 0
            parsed_rows.append((i, teacher, subject_name, year, branch_code, section, count))
        except Exception as exc:
            issues.append(ImportIssue(i, f"Invalid row format: {exc}"))

    touched_sections = set((row[3], row[4], row[5]) for row in parsed_rows)  # (year, branch, section)
    for year, branch_code, section in touched_sections:
        branch = _get_or_create_branch(db, branch_code)
        _get_or_create_year_section(db, branch.id, year, section)
        db.query(Subject).filter(
            Subject.branch_id == branch.id,
            Subject.year == year,
            Subject.section == section
        ).update(
            {
                Subject.lectures_per_week: 0,
                Subject.tutorials_per_week: 0,
                Subject.lab_periods_per_week: 0,
                Subject.seminar_periods_per_week: 0,
                Subject.lab_duration: 2,
                Subject.is_active: True,
            },
            synchronize_session=False
        )

    applied = 0
    for row_num, teacher, subject_name, year, branch_code, section, count in parsed_rows:
        try:
            if count < 0:
                issues.append(ImportIssue(row_num, "LecturesPerWeek cannot be negative"))
                continue

            branch = _get_or_create_branch(db, branch_code)
            _get_or_create_year_section(db, branch.id, year, section)
            faculty = _get_or_create_faculty(db, teacher, dept=branch_code)
            subject = db.query(Subject).filter(
                Subject.name == subject_name,
                Subject.branch_id == branch.id,
                Subject.year == year,
                Subject.section == section
            ).first()

            if subject is None:
                # Keep assignment row but record a warning because master mapping was missing.
                subject = _get_or_create_subject(
                    db, subject_name, branch.id, year, section, faculty.id
                )
                issues.append(ImportIssue(row_num, "Subject not found in master; created fallback subject"))

            subject.faculty_id = faculty.id
            subject.lab_duration = 2
            kind = _subject_type(subject_name)
            if kind == "LAB":
                subject.lab_periods_per_week = count
                if subject.labroom_id is None and subject.classroom_id is not None:
                    # Convert classroom assignment to lab where possible.
                    classroom = db.query(Classroom).filter(Classroom.id == subject.classroom_id).first()
                    if classroom:
                        _, lab = _get_or_create_room(db, classroom.room_number)
                        subject.labroom_id = lab.id if lab else subject.labroom_id
                        subject.classroom_id = None
            elif kind == "TUTORIAL":
                subject.tutorials_per_week = count
            elif kind == "SEMINAR":
                subject.seminar_periods_per_week = count
            else:
                subject.lectures_per_week = count
            applied += 1
        except Exception as exc:
            issues.append(ImportIssue(row_num, f"Failed to apply assignment: {exc}"))

    db.commit()
    return {
        "success": True,
        "message": "Assignment file synchronized",
        "processed_rows": applied,
        "issues": [issue.__dict__ for issue in issues],
    }
