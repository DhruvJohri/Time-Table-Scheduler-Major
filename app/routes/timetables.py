"""
Timetable Routes — Guide-Compliant
POST   /timetable/generate
GET    /timetable
GET    /timetable/{branch}/{year}/{section}
DELETE /timetable/clear
"""

from fastapi import APIRouter, HTTPException, status
from bson.objectid import ObjectId
from datetime import datetime
from typing import List, Optional
import re

from app.schemas import GenerateTimetableRequest
from app.models.database import (
    users_collection,
    timetables_collection,
    master_data_collection,
    assignment_data_collection,
)
from app.services.college_scheduler import get_college_scheduler


router = APIRouter(prefix="/timetable", tags=["timetable"])


# ── Helper: normalise year strings ───────────────────────────────────────────
def _norm_year(year_str: str) -> str:
    """
    Extract numeric part from any year string.
    "3rd Year" → "3",  "Year 3" → "3",  "3" → "3"
    """
    if not year_str:
        return str(year_str)
    m = re.search(r'(\d+)', str(year_str))
    return m.group(1) if m else str(year_str).strip()


# ── Helper: serialise Mongo doc ──────────────────────────────────────────────
def _ser(doc: dict) -> dict:
    """Convert MongoDB document to JSON-serializable dict."""
    out = {}
    for k, v in doc.items():
        if k == "_id":
            out["id"] = str(v)
        elif isinstance(v, ObjectId):
            out[k] = str(v)
        elif isinstance(v, datetime):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = _ser(v)
        elif isinstance(v, list):
            out[k] = [_ser(i) if isinstance(i, dict) else i for i in v]
        else:
            out[k] = v
    return out


# ── POST /timetable/generate ─────────────────────────────────────────────────
@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_timetable(request: GenerateTimetableRequest):
    """
    Generate a college timetable using OR-Tools CP-SAT.
    Returns only { status, message | unallocated } — no timetable payload.
    Frontend must call GET /timetable/{branch}/{year}/{section} to retrieve data.
    """
    # 1. Resolve admin
    try:
        admin = users_collection.find_one({"_id": ObjectId(request.admin_id)})
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid admin_id format.")
    if not admin:
        raise HTTPException(status_code=404, detail="Admin profile not found.")

    admin_email = admin["email"]

    # 2. Load latest master data
    master = master_data_collection.find_one(
        {"admin_email": admin_email},
        sort=[("created_at", -1)]
    )
    if not master:
        raise HTTPException(
            status_code=400,
            detail="No master data found. Upload Master Data Excel first."
        )

    # 3. Load latest assignment data
    asgn_doc = assignment_data_collection.find_one(
        {"admin_email": admin_email},
        sort=[("created_at", -1)]
    )
    if not asgn_doc:
        raise HTTPException(
            status_code=400,
            detail="No assignment data found. Upload Assignment Data Excel first."
        )

    assignments = asgn_doc.get("assignments", [])

    # Apply filters
    if request.branch:
        assignments = [a for a in assignments if a["branch"] == request.branch]
    if request.year:
        req_year_norm = _norm_year(request.year)
        assignments = [a for a in assignments if _norm_year(a["year"]) == req_year_norm]
    if request.section:
        assignments = [a for a in assignments if a.get("section", "A") == request.section]

    if not assignments:
        raise HTTPException(
            status_code=400,
            detail="No assignments match the selected Branch/Year/Section filter."
        )

    # 4. Extract master lists
    teachers   = master.get("teachers", [])
    subjects   = master.get("subjects", [])
    classrooms = master.get("classrooms", [])

    records = master.get("records", [])
    if not teachers:
        teachers = sorted({r["teacher_name"] for r in records})
    if not teachers:
        teachers = sorted({a["teacher_name"] for a in assignments})
    if not subjects:
        subjects = sorted({r["subject_name"] for r in records})
    if not subjects:
        subjects = sorted({a["subject_name"] for a in assignments})
    if not classrooms:
        classrooms = sorted({r["classroom"] for r in records if r.get("classroom")})
    if not classrooms:
        classrooms = ["R101"]

    rooms        = [{"room_name": c, "room_type": "lecture"} for c in classrooms]
    lab_subjects = [s for s in subjects if "lab" in s.lower()]

    # 5. Run solver
    try:
        scheduler = get_college_scheduler()
        solver_result = scheduler.allocate(
            assignments=assignments,
            teachers=teachers,
            subjects=subjects,
            rooms=rooms,
            lab_subjects=lab_subjects,
            branch_filter=request.branch,
            year_filter=request.year,
            section_filter=request.section,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Solver error: {exc}")

    flat_timetable = solver_result.get("timetable", [])
    unallocated    = solver_result.get("unallocated", [])
    sched_status   = "partial" if unallocated else "success"

    # 6. Versioning labels
    branches = sorted({a["branch"]              for a in assignments})
    years    = sorted({_norm_year(a["year"])     for a in assignments})
    secs     = sorted({a.get("section", "A")    for a in assignments})

    branch_label  = request.branch  or ",".join(branches)
    year_label    = _norm_year(request.year) if request.year else ",".join(years)
    section_label = request.section or ",".join(secs)

    existing = timetables_collection.count_documents({
        "admin_id": request.admin_id,
        "branch":   branch_label,
        "year":     year_label,
        "section":  section_label,
    })
    version = existing + 1

    start_date = request.start_date or datetime.utcnow().strftime("%Y-%m-%d")
    label = (
        f"v{version} — {branch_label} / "
        f"Year {year_label} / Sec {section_label} — {start_date}"
    )

    # 7. Store flat array in MongoDB
    doc = {
        "admin_id":   request.admin_id,
        "branch":     branch_label,
        "year":       year_label,
        "section":    section_label,
        "version":    version,
        "label":      label,
        "timetable":  flat_timetable,   # flat list of guide §4 slots
        "created_at": datetime.utcnow(),
    }
    timetables_collection.insert_one(doc)

    # 8. Return status + timetable slots directly (most reliable for frontend)
    response = {
        "status":    sched_status,
        "timetable": flat_timetable,
    }
    if sched_status == "partial":
        response["unallocated"] = unallocated
    else:
        response["message"] = "Timetable generated"
    return response


# ── GET /timetable — flat array of ALL stored entries ────────────────────────
@router.get("", response_model=list)
async def get_all_timetables():
    """
    Return flat array of ALL timetable slot entries from all stored documents.
    """
    all_slots: List[dict] = []
    cursor = timetables_collection.find({}, sort=[("created_at", -1)])
    for doc in cursor:
        slots = doc.get("timetable", [])
        if isinstance(slots, list):
            all_slots.extend(slots)
    return all_slots


# ── GET /timetable/{branch}/{year}/{section} ──────────────────────────────────
@router.get("/{branch}/{year}/{section}", response_model=list)
async def get_timetable_by_section(branch: str, year: str, section: str):
    """
    Return flat array of slots for the MOST RECENT timetable matching
    branch / year / section.
    """
    norm_yr = _norm_year(year)

    # Find most recent matching document
    doc = timetables_collection.find_one(
        {
            "branch":  branch,
            "year":    norm_yr,
            "section": section,
        },
        sort=[("created_at", -1)]
    )

    # Fallback: match without section (older docs may not have it)
    if not doc:
        doc = timetables_collection.find_one(
            {"branch": branch, "year": norm_yr},
            sort=[("created_at", -1)]
        )

    if not doc:
        raise HTTPException(
            status_code=404,
            detail=f"No timetable found for {branch} / Year {year} / Section {section}."
        )

    slots = doc.get("timetable", [])
    if not isinstance(slots, list):
        raise HTTPException(status_code=500, detail="Timetable data is malformed.")

    # Filter flat list by section
    filtered = [
        s for s in slots
        if str(s.get("section", "A")) == section
    ]

    # If nothing matched section filter, return all slots (older format)
    if not filtered and slots:
        filtered = slots

    return filtered


# ── DELETE /timetable/clear — delete ALL timetables ──────────────────────────
@router.delete("/clear", status_code=status.HTTP_200_OK)
async def clear_all_timetables():
    """
    Delete ALL stored timetables.
    Guide §5: 'DELETE /timetable/clear — Frontend button: Reset Timetable'
    """
    result = timetables_collection.delete_many({})
    return {
        "message": "All timetables cleared",
        "deleted": result.deleted_count,
    }


# ── GET /timetable/id/{timetable_id} — fetch one by MongoDB _id (history) ────
@router.get("/id/{timetable_id}", response_model=dict)
async def get_timetable_by_id(timetable_id: str):
    """Get a single complete timetable document by its MongoDB ID (for version history)."""
    try:
        doc = timetables_collection.find_one({"_id": ObjectId(timetable_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timetable ID.")
    if not doc:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    return _ser(doc)


# ── GET /timetable/versions/{admin_id} — version list (history panel) ────────
@router.get("/versions/{admin_id}", response_model=list)
async def get_timetable_versions(admin_id: str):
    """List version summaries for an admin's timetables (for History Panel)."""
    cursor = timetables_collection.find(
        {"admin_id": admin_id},
        {"timetable": 0}
    ).sort("created_at", -1)

    versions = []
    for doc in cursor:
        created = doc.get("created_at")
        versions.append({
            "id":         str(doc["_id"]),
            "version":    doc.get("version", 1),
            "label":      doc.get("label", f"v{doc.get('version', 1)}"),
            "branch":     doc.get("branch", ""),
            "year":       doc.get("year", ""),
            "section":    doc.get("section", "A"),
            "created_at": created.isoformat() if isinstance(created, datetime) else str(created or ""),
        })
    return versions


# ── DELETE /timetable/id/{timetable_id} — delete one version ─────────────────
@router.delete("/id/{timetable_id}", status_code=status.HTTP_200_OK)
async def delete_timetable_by_id(timetable_id: str):
    """Delete a single timetable version by its MongoDB ID."""
    try:
        result = timetables_collection.delete_one({"_id": ObjectId(timetable_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timetable ID.")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    return {"message": "Timetable deleted"}
