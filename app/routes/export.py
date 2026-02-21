"""
Export Routes — PDF only
GET /api/export/{timetable_id}/pdf  🔒 (auth required)
"""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from bson.objectid import ObjectId
from io import BytesIO
from datetime import datetime
from app.models.database import timetables_collection
import os

# ── PDF export ─────────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Spacer, Paragraph
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

pt: float = 1.0

router = APIRouter(prefix="/api/export", tags=["export"])

DAYS      = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
DAY_SHORT = {"Monday":"MON","Tuesday":"TUE","Wednesday":"WED",
             "Thursday":"THU","Friday":"FRI","Saturday":"SAT"}

COL_DEFS = [
    ("period", 1, "8:00\n9:00"),
    ("period", 2, "9:00\n10:00"),
    ("sep",    None, "BREAK"),
    ("period", 3, "10:15\n11:15"),
    ("period", 4, "11:15\n12:15"),
    ("sep",    None, "LUNCH"),
    ("period", 5, "13:00\n14:00"),
    ("period", 6, "14:00\n15:00"),
    ("period", 7, "15:15\n16:15"),
]

# ─────────────────────────────────────────────────────────────────────────────
# Route
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{timetable_id}/pdf")
async def export_pdf(
    timetable_id: str,
):
    """Export timetable as landscape A4 PDF. Requires: Authorization: Bearer <token>"""
    try:
        doc = timetables_collection.find_one({"_id": ObjectId(timetable_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Timetable not found")
        pdf_bytes = _generate_pdf_timetable(doc)
        return StreamingResponse(
            BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=timetable-{timetable_id}.pdf"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# PDF GENERATOR — Day + Branch sub-rows × Period columns
# ─────────────────────────────────────────────────────────────────────────────

_DARK  = colors.HexColor("#1e1b4b")
_MID   = colors.HexColor("#1e293b")
_SEP   = colors.HexColor("#0f172a")
_LIGHT = colors.HexColor("#e2e8f0")
_GREY  = colors.HexColor("#64748b")
_ALT   = colors.HexColor("#111827")
_ACC   = colors.HexColor("#6366f1")
_WHITE = colors.white

_BRANCH_TINT = {
    "CS": colors.HexColor("#dbeafe"),  "EC": colors.HexColor("#d1fae5"),
    "ME": colors.HexColor("#fef3c7"),  "CE": colors.HexColor("#ede9fe"),
    "EE": colors.HexColor("#ffedd5"),  "IT": colors.HexColor("#fce7f3"),
    "CH": colors.HexColor("#f0fdf4"),
}
_BRANCH_BORDER = {
    "CS": colors.HexColor("#3b82f6"),  "EC": colors.HexColor("#10b981"),
    "ME": colors.HexColor("#f59e0b"),  "CE": colors.HexColor("#8b5cf6"),
    "EE": colors.HexColor("#f97316"),  "IT": colors.HexColor("#ec4899"),
    "CH": colors.HexColor("#22c55e"),
}
_DEF_TINT   = colors.HexColor("#f1f5f9")
_DEF_BORDER = colors.HexColor("#94a3b8")


def _branch_tint(branch):
    key = (branch or "").upper()[:2]
    return _BRANCH_TINT.get(key, _DEF_TINT)


def _branch_bdr(branch):
    key = (branch or "").upper()[:2]
    return _BRANCH_BORDER.get(key, _DEF_BORDER)


def _collect_sections(timetable_data: dict):
    sec_set = set()
    for slots in timetable_data.values():
        for s in (slots if isinstance(slots, list) else []):
            if not s.get("is_free"):
                sec_set.add(f"{s.get('branch','')}|{s.get('year','')}")
    return sorted(sec_set, key=lambda k: (k.split("|")[0], k.split("|")[1]))


def _build_slot_map(timetable_data: dict, sections):
    m = {day: {sec: {} for sec in sections} for day in DAYS}
    for day, slots in timetable_data.items():
        if day not in m:
            continue
        for s in (slots if isinstance(slots, list) else []):
            if s.get("is_free"):
                continue
            sec = f"{s.get('branch','')}|{s.get('year','')}"
            if sec in m[day]:
                m[day][sec][s.get("period")] = s
    return m


def _generate_pdf_timetable(timetable: dict) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=24*pt, rightMargin=24*pt,
        topMargin=28*pt,  bottomMargin=20*pt,
    )

    styles = getSampleStyleSheet()
    title_st = ParagraphStyle("T", parent=styles["Title"],
                              fontSize=10, textColor=_LIGHT,
                              alignment=TA_CENTER, spaceAfter=2, leading=13)
    sub_st   = ParagraphStyle("S", parent=styles["Normal"],
                              fontSize=7, textColor=_GREY,
                              alignment=TA_CENTER, spaceAfter=6)
    cell_st  = ParagraphStyle("C", parent=styles["Normal"],
                              fontSize=6, textColor=colors.HexColor("#1e293b"),
                              leading=8, alignment=TA_CENTER)
    hdr_st   = ParagraphStyle("H", parent=styles["Normal"],
                              fontSize=6, textColor=_LIGHT,
                              leading=8, alignment=TA_CENTER, fontName="Helvetica-Bold")
    day_st   = ParagraphStyle("D", parent=styles["Normal"],
                              fontSize=7, textColor=_ACC,
                              fontName="Helvetica-Bold", alignment=TA_CENTER)
    sec_st   = ParagraphStyle("SE", parent=styles["Normal"],
                              fontSize=6, textColor=_LIGHT,
                              fontName="Helvetica-Bold", alignment=TA_CENTER)
    sep_st   = ParagraphStyle("SP", parent=styles["Normal"],
                              fontSize=6, textColor=_GREY,
                              alignment=TA_CENTER)

    branch  = timetable.get("branch", "All Branches")
    year    = timetable.get("year",   "All Years")
    version = timetable.get("version", 1)
    tt_data = timetable.get("timetable", {})

    sections = _collect_sections(tt_data)
    if not sections:
        sections = ["—|—"]

    slot_map = _build_slot_map(tt_data, sections)

    W_DAY  = 30
    W_SEC  = 36
    W_SEP  = 18
    W_USED  = W_DAY + W_SEC + 2*W_SEP
    W_AVAIL = 794 - W_USED
    W_PER  = round(W_AVAIL / 7, 1)

    col_widths = [W_DAY, W_SEC]
    for ctype, _, _ in COL_DEFS:
        col_widths.append(W_SEP if ctype == "sep" else W_PER)

    hdr_row = [Paragraph("DAY", hdr_st), Paragraph("SECTION", hdr_st)]
    for ctype, _, lbl in COL_DEFS:
        hdr_row.append(Paragraph(lbl, hdr_st))

    table_rows = [hdr_row]
    style_cmds = []
    cur_row    = 1

    for di, day in enumerate(DAYS):
        day_start = cur_row
        for si, sec_key in enumerate(sections):
            sec_br, sec_yr = sec_key.split("|")
            tint_c = _branch_tint(sec_br)

            row_cells = []
            row_cells.append(Paragraph(DAY_SHORT.get(day, day[:3]), day_st) if si == 0 else "")
            sec_label = f"{sec_br}" + (f"\nY{sec_yr}" if sec_yr else "")
            row_cells.append(Paragraph(sec_label, sec_st))

            for ctype, period_num, _ in COL_DEFS:
                if ctype == "sep":
                    row_cells.append("")
                else:
                    slot = slot_map.get(day, {}).get(sec_key, {}).get(period_num)
                    if slot:
                        subj = slot.get("subject", "")
                        tchr = slot.get("teacher", "")
                        room = slot.get("room", "")
                        lab  = " [LAB]" if slot.get("is_lab") else ""
                        txt  = f"<b>{subj}{lab}</b><br/>{tchr}<br/>{room}"
                        row_cells.append(Paragraph(txt, cell_st))
                        col_idx = 2 + [i for i, c in enumerate(COL_DEFS) if c[1] == period_num][0]
                        style_cmds.append(
                            ("BACKGROUND", (col_idx, cur_row), (col_idx, cur_row), tint_c)
                        )
                    else:
                        row_cells.append(Paragraph("—", sep_st))

            table_rows.append(row_cells)
            style_cmds.append(("BACKGROUND", (1, cur_row), (1, cur_row), _ALT))
            cur_row += 1

        day_end = cur_row - 1
        style_cmds.append(("SPAN",       (0, day_start), (0, day_end)))
        style_cmds.append(("BACKGROUND", (0, day_start), (0, day_end), _MID))
        style_cmds.append(("LINEBELOW",  (0, day_end),   (-1, day_end), 1.2, colors.HexColor("#334155")))

    for ci, (ctype, _, _) in enumerate(COL_DEFS):
        if ctype == "sep":
            real_col = 2 + ci
            style_cmds.append(("BACKGROUND", (real_col, 0), (real_col, -1), _SEP))
            style_cmds.append(("TEXTCOLOR",  (real_col, 0), (real_col, -1), _GREY))
            style_cmds.append(("FONTSIZE",   (real_col, 1), (real_col, -1), 5))

    base_style = TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0),  _DARK),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  _LIGHT),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  6),
        ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",        (0, 0), (-1, 0),  "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, 0),  4),
        ("BOTTOMPADDING", (0, 0), (-1, 0),  4),
        ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, -1), 6),
        ("ALIGN",         (0, 1), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 1), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 2),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#334155")),
        ("BACKGROUND",    (0, 1), (0, -1),  _MID),
        ("VALIGN",        (0, 1), (0, -1),  "MIDDLE"),
    ])
    for cmd in style_cmds:
        base_style.add(*cmd)

    tbl = Table(table_rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(base_style)

    story = [
        Paragraph("SHRI RAM MURTI SMARAK COLLEGE OF ENGINEERING AND TECHNOLOGY", title_st),
        Paragraph(
            f"TIME TABLE  ·  B.Tech"
            + (f"  ·  {branch}" if branch and branch != "All Branches" else "")
            + (f"  ·  Year {year}" if year and year != "All Years" else "")
            + f"  ·  v{version}",
            sub_st,
        ),
        tbl,
        Spacer(1, 6),
    ]

    doc.build(story)
    return buf.getvalue()
