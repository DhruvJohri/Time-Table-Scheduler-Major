"""
Export Routes - JSON, CSV, PDF, Share
(MySQL + SQLAlchemy Version)
"""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from io import StringIO, BytesIO
from datetime import datetime
from weasyprint import HTML
import csv
import json
import os

from app.database import get_db
from app.models.models import TimetableEntry, TimetableVersion

router = APIRouter(prefix="/api/export", tags=["export"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# ==================================================
# GET TIMETABLE VERSION
# ==================================================
def get_timetable_version(db: Session, version_id: int | None):
    if version_id:
        version = db.query(TimetableVersion).filter(
            TimetableVersion.id == version_id
        ).first()
    else:
        version = db.query(TimetableVersion).filter(
            TimetableVersion.is_active == True
        ).order_by(TimetableVersion.created_at.desc()).first()

    if not version:
        raise HTTPException(status_code=404, detail="Timetable version not found")

    return version


# ==================================================
# JSON EXPORT
# ==================================================
@router.get("/json")
def export_json(version_id: int | None = None, db: Session = Depends(get_db)):

    version = get_timetable_version(db, version_id)

    entries = db.query(TimetableEntry).filter(
        TimetableEntry.version_id == version.id
    ).all()

    data = []

    for e in entries:
        data.append({
            "day": e.day_of_week.value,
            "period": e.period_number,
            "subject": e.subject.name if e.subject else None,
            "faculty": e.faculty.name if e.faculty else None,
            "room": e.classroom.room_number if e.classroom else (
                e.labroom.room_number if e.labroom else None
            ),
            "type": e.session_type.value
        })

    json_content = json.dumps(data, indent=2)

    return StreamingResponse(
        iter([json_content]),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=timetable.json"}
    )


# ==================================================
# CSV EXPORT
# ==================================================
@router.get("/csv")
def export_csv(version_id: int | None = None, db: Session = Depends(get_db)):

    version = get_timetable_version(db, version_id)

    entries = db.query(TimetableEntry).filter(
        TimetableEntry.version_id == version.id
    ).all()

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["Day", "Period", "Subject", "Faculty", "Room", "Type"])

    for e in entries:
        writer.writerow([
            e.day_of_week.value,
            e.period_number,
            e.subject.name if e.subject else "",
            e.faculty.name if e.faculty else "",
            e.classroom.room_number if e.classroom else (
                e.labroom.room_number if e.labroom else ""
            ),
            e.session_type.value
        ])

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=timetable.csv"}
    )


# ==================================================
# PDF EXPORT (GRID FORMAT)
# ==================================================
@router.get("/pdf")
def export_pdf(version_id: int | None = None, db: Session = Depends(get_db)):

    version = get_timetable_version(db, version_id)

    entries = db.query(TimetableEntry).filter(
        TimetableEntry.version_id == version.id
    ).all()

    html_content = _generate_grid_html(entries, version)

    pdf_io = BytesIO()
    HTML(string=html_content).write_pdf(pdf_io)
    pdf_io.seek(0)

    return StreamingResponse(
        pdf_io,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=timetable.pdf"}
    )


# ==================================================
# SHARE LINK
# ==================================================
@router.get("/share")
def get_share_link(version_id: int | None = None, db: Session = Depends(get_db)):

    version = get_timetable_version(db, version_id)

    return {
        "shareUrl": f"{FRONTEND_URL}/share/{version.id}",
        "versionId": version.id,
        "createdAt": version.created_at.isoformat() if version.created_at else None
    }


# ==================================================
# GRID HTML GENERATOR
# ==================================================
def _generate_grid_html(entries, version):

    days = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]
    periods = [1, 2, 3, 4, 5, 6, 7]

    grid = {day: {p: None for p in periods} for day in days}

    for e in entries:
        day = e.day_of_week.value
        period = e.period_number
        if day in grid and period in grid[day]:
            grid[day][period] = e

    rows_html = ""

    for day in days:
        row = f"<tr><td class='day'>{day}</td>"
        for p in periods:
            cell = grid[day][p]
            if cell:
                room = cell.classroom.room_number if cell.classroom else (
                    cell.labroom.room_number if cell.labroom else ""
                )

                row += f"""
                <td>
                    <strong>{cell.subject.name if cell.subject else ""}</strong><br>
                    {cell.faculty.name if cell.faculty else ""}<br>
                    {room}<br>
                    <small>{cell.session_type.value}</small>
                </td>
                """
            else:
                row += "<td>-</td>"
        row += "</tr>"
        rows_html += row

    return f"""
    <html>
    <head>
        <style>
            @page {{
                size: A4 landscape;
                margin: 15mm;
            }}
            body {{
                font-family: Arial;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                table-layout: fixed;
            }}
            th, td {{
                border: 1px solid black;
                padding: 6px;
                text-align: center;
                font-size: 11px;
            }}
            th {{
                background: #1e3a8a;
                color: white;
            }}
            .day {{
                font-weight: bold;
                background: #f3f4f6;
            }}
        </style>
    </head>
    <body>

        <h2 style="text-align:center;">
            Timetable Version {version.id}
        </h2>

        <table>
            <thead>
                <tr>
                    <th>Day</th>
                    {"".join([f"<th>P{p}</th>" for p in periods])}
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

    </body>
    </html>
    """