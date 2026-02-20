"""
Export Routes - JSON, CSV, PDF
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from bson.objectid import ObjectId
from io import StringIO, BytesIO
import csv, json
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
from reportlab.lib.enums import TA_CENTER, TA_LEFT

pt: float = 1.0

router = APIRouter(prefix="/api/export", tags=["export"])

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

DAYS         = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
DAY_SHORT    = {"Monday":"MON","Tuesday":"TUE","Wednesday":"WED",
                "Thursday":"THU","Friday":"FRI","Saturday":"SAT"}
# Ordered column definitions: (type, period_number_or_None, header_label)
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
PERIOD_COLS = [c[1] for c in COL_DEFS if c[0] == "period"]


# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{timetable_id}/json")
async def export_json(timetable_id: str):
    try:
        doc = timetables_collection.find_one({"_id": ObjectId(timetable_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Timetable not found")
        doc["_id"] = str(doc.get("_id"))
        def _dt(o):
            if isinstance(o, datetime): return o.isoformat()
            raise TypeError(type(o))
        return StreamingResponse(iter([json.dumps(doc, default=_dt, indent=2)]),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=timetable-{timetable_id}.json"})
    except HTTPException: raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{timetable_id}/pdf")
async def export_pdf(timetable_id: str):
    """Export timetable as landscape A4 PDF matching the UI grid layout."""
    try:
        doc = timetables_collection.find_one({"_id": ObjectId(timetable_id)})
        if not doc:
            raise HTTPException(status_code=404, detail="Timetable not found")
        pdf_bytes = _generate_pdf_timetable(doc)
        return StreamingResponse(BytesIO(pdf_bytes), media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=timetable-{timetable_id}.pdf"})
    except HTTPException: raise
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

# Branch accent colours (background tint for occupied cells)
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
    """Return sorted list of 'branch|year' section keys found in the data."""
    sec_set = set()
    for slots in timetable_data.values():
        for s in (slots if isinstance(slots, list) else []):
            if not s.get("is_free"):
                sec_set.add(f"{s.get('branch','')}|{s.get('year','')}")
    return sorted(sec_set, key=lambda k: (k.split("|")[0], k.split("|")[1]))


def _build_slot_map(timetable_data: dict, sections):
    """
    Build map: day → section_key → period → slot_dict
    """
    m = {day: {sec: {} for sec in sections} for day in DAYS}
    for day, slots in timetable_data.items():
        if day not in m: continue
        for s in (slots if isinstance(slots, list) else []):
            if s.get("is_free"): continue
            sec = f"{s.get('branch','')}|{s.get('year','')}"
            if sec in m[day]:
                m[day][sec][s.get("period")] = s
    return m


def _generate_pdf_timetable(timetable: dict) -> bytes:
    """
    Build a landscape A4 PDF that mirrors the UI grid:
      Row structure  : one sub-row per Branch+Year section, grouped by Day
      Column structure: DAY | SECTION | P1 | P2 | BREAK | P3 | P4 | LUNCH | P5 | P6 | P7
    """
    buf = BytesIO()
    # Landscape A4 ≈ 842 × 595 pt
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
    n_sec    = len(sections)

    # ── Column widths ─────────────────────────────────────────────
    # Total usable ≈ 794 pt (842 - 48 margins)
    # DAY=30, SEC=36, BREAK=18, LUNCH=18, each period=(794-30-36-36)/7 ≈ 99
    W_DAY  = 30
    W_SEC  = 36
    W_SEP  = 18
    W_USED  = W_DAY + W_SEC + 2*W_SEP
    W_AVAIL = 794 - W_USED
    W_PER  = round(W_AVAIL / 7, 1)

    col_widths = []
    col_widths.append(W_DAY)   # DAY
    col_widths.append(W_SEC)   # SECTION
    for ctype, _, _ in COL_DEFS:
        col_widths.append(W_SEP if ctype=="sep" else W_PER)

    # ── Table header row ──────────────────────────────────────────
    hdr_row = [Paragraph("DAY", hdr_st), Paragraph("SECTION", hdr_st)]
    for ctype, _, lbl in COL_DEFS:
        hdr_row.append(Paragraph(lbl, hdr_st))

    table_rows   = [hdr_row]
    style_cmds   = []
    cur_row      = 1          # row index (0 = header)

    # ── Data rows (one sub-row per section, grouped by day) ───────
    for di, day in enumerate(DAYS):
        day_start = cur_row
        for si, sec_key in enumerate(sections):
            sec_br, sec_yr = sec_key.split("|")
            bdr_c  = _branch_bdr(sec_br)
            tint_c = _branch_tint(sec_br)

            row_cells = []

            # DAY cell — only on first section row, spans all section rows
            if si == 0:
                row_cells.append(Paragraph(DAY_SHORT.get(day, day[:3]), day_st))
            else:
                row_cells.append("")

            # SECTION cell
            sec_label = f"{sec_br}"
            if sec_yr:
                sec_label += f"\nY{sec_yr}"
            row_cells.append(Paragraph(sec_label, sec_st))

            # Period / separator cells
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
                        # Occupied cell background tint
                        col_idx = 2 + [i for i,c in enumerate(COL_DEFS) if c[1]==period_num][0]
                        style_cmds.append(
                            ("BACKGROUND", (col_idx, cur_row), (col_idx, cur_row), tint_c)
                        )
                    else:
                        row_cells.append(Paragraph("—", sep_st))

            table_rows.append(row_cells)

            # Section background (dark)
            style_cmds.append(("BACKGROUND", (1, cur_row), (1, cur_row), _ALT))

            cur_row += 1

        day_end = cur_row - 1

        # Merge DAY cell across all section rows for this day
        style_cmds.append(("SPAN",       (0, day_start), (0, day_end)))
        style_cmds.append(("BACKGROUND", (0, day_start), (0, day_end), _MID))
        style_cmds.append(("LINEBELOW",  (0, day_end),   (-1, day_end), 1.2, colors.HexColor("#334155")))

    # ── Separator column styling ──────────────────────────────────
    for ci, (ctype, _, _) in enumerate(COL_DEFS):
        if ctype == "sep":
            real_col = 2 + ci
            style_cmds.append(("BACKGROUND", (real_col, 0), (real_col, -1), _SEP))
            style_cmds.append(("TEXTCOLOR",  (real_col, 0), (real_col, -1), _GREY))
            style_cmds.append(("FONTSIZE",   (real_col, 1), (real_col, -1), 5))

    # ── Global table style ────────────────────────────────────────
    base_style = TableStyle([
        # Header row
        ("BACKGROUND",   (0, 0), (-1, 0),  _DARK),
        ("TEXTCOLOR",    (0, 0), (-1, 0),  _LIGHT),
        ("FONTNAME",     (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0),  6),
        ("ALIGN",        (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",       (0, 0), (-1, 0),  "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, 0),  4),
        ("BOTTOMPADDING",(0, 0), (-1, 0),  4),
        # Body
        ("FONTNAME",     (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, -1), 6),
        ("ALIGN",        (0, 1), (-1, -1), "CENTER"),
        ("VALIGN",       (0, 1), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 1), (-1, -1), 2),
        ("BOTTOMPADDING",(0, 1), (-1, -1), 2),
        # Grid
        ("GRID",         (0, 0), (-1, -1), 0.3, colors.HexColor("#334155")),
        # Day col
        ("BACKGROUND",   (0, 1), (0, -1),  _MID),
        ("VALIGN",       (0, 1), (0, -1),  "MIDDLE"),
    ])
    for cmd in style_cmds:
        base_style.add(*cmd)

    tbl = Table(table_rows, colWidths=col_widths, repeatRows=1)
    tbl.setStyle(base_style)

    # ── Page header ───────────────────────────────────────────────
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
