from fastapi import APIRouter, HTTPException, status, Query, Depends
from bson.objectid import ObjectId
from datetime import datetime
from typing import Optional

from app.schemas import GenerateTimetableRequest
from app.models.database import (
    users_collection,
    timetables_collection,
    master_data_collection,
    assignment_data_collection,
)
from app.services.college_scheduler import get_college_scheduler
from app.dependencies import get_current_admin

router = APIRouter(prefix="/api/timetables", tags=["timetables"])


# ── Helper: serialise Mongo doc to plain JSON-safe dict ───────────────────────
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


# ── POST /generate  (🔒 auth required) ───────────────────────────────────────
@router.post("/generate", status_code=status.HTTP_201_CREATED)
async def generate_timetable(
    request: GenerateTimetableRequest,
    _admin=Depends(get_current_admin),
):
    """
    Generate a college timetable using OR-Tools CP-SAT.
    Reads master + assignment data from MongoDB, runs solver, stores result.
    Requires: Authorization: Bearer <token>
    """
    # 1. Verify admin
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
    if request.branch:
        assignments = [a for a in assignments if a["branch"] == request.branch]
    if request.year:
        assignments = [a for a in assignments if a["year"] == request.year]

    if not assignments:
        raise HTTPException(
            status_code=400,
            detail="No assignments match the selected Branch/Year filter."
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

    rooms = [{"room_name": c, "room_type": "lecture"} for c in classrooms]
    lab_subjects = [s for s in subjects if "lab" in s.lower()]

    # 5. Versioning
    branches = sorted({a["branch"] for a in assignments})
    years    = sorted({a["year"]   for a in assignments})
    branch_label = request.branch or ",".join(branches)
    year_label   = request.year   or ",".join(years)

    existing = timetables_collection.count_documents({
        "admin_id": request.admin_id,
        "branch":   branch_label,
        "year":     year_label,
    })
    version = existing + 1

    # 6. Run solver
    try:
        scheduler = get_college_scheduler()
        timetable = scheduler.allocate(
            assignments=assignments,
            teachers=teachers,
            subjects=subjects,
            rooms=rooms,
            lab_subjects=lab_subjects,
            branch_filter=request.branch,
            year_filter=request.year,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Solver error: {exc}")

    # 7. Store
    start_date = request.start_date or datetime.utcnow().strftime("%Y-%m-%d")
    label = f"v{version} — {branch_label} / Year {year_label} — {start_date}"

    doc = {
        "admin_id":   request.admin_id,
        "branch":     branch_label,
        "year":       year_label,
        "version":    version,
        "label":      label,
        "timetable":  timetable,
        "created_at": datetime.utcnow(),
    }
    result = timetables_collection.insert_one(doc)
    doc["id"] = str(result.inserted_id)
    doc.pop("_id", None)
    doc["created_at"] = doc["created_at"].isoformat()
    return doc


# ── GET /user/{user_id}/versions  (public read) ───────────────────────────────
@router.get("/user/{user_id}/versions", response_model=list)
async def get_timetable_versions(
    user_id: str,
    branch: Optional[str] = Query(None),
    year:   Optional[str] = Query(None),
):
    """List version summaries for a user's timetables, optionally filtered by branch/year."""
    query: dict = {"admin_id": user_id}
    if branch:
        query["branch"] = branch
    if year:
        query["year"] = year

    cursor = timetables_collection.find(
        query,
        {"timetable": 0}
    ).sort("created_at", -1)

    versions = []
    for doc in cursor:
        created = doc.get("created_at")
        versions.append({
            "id":         str(doc["_id"]),
            "version":    doc.get("version", 1),
            "label":      doc.get("label", f"v{doc.get('version',1)}"),
            "branch":     doc.get("branch", ""),
            "year":       doc.get("year", ""),
            "created_at": created.isoformat() if isinstance(created, datetime) else str(created or ""),
        })
    return versions


# ── GET /user/{user_id}  (public read) ───────────────────────────────────────
@router.get("/user/{user_id}", response_model=list)
async def get_user_timetables(
    user_id: str,
    branch: Optional[str] = Query(None),
    year:   Optional[str] = Query(None),
):
    """Get all timetables for a user, optionally filtered by branch/year."""
    query: dict = {"admin_id": user_id}
    if branch:
        query["branch"] = branch
    if year:
        query["year"] = year

    timetables = list(
        timetables_collection.find(query).sort("created_at", -1)
    )
    return [_ser(t) for t in timetables]


# ── GET /{timetable_id}  (public read) ───────────────────────────────────────
@router.get("/{timetable_id}", response_model=dict)
async def get_timetable(timetable_id: str):
    """Get a single timetable by ID."""
    try:
        doc = timetables_collection.find_one({"_id": ObjectId(timetable_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timetable ID.")
    if not doc:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    return _ser(doc)


# ── DELETE /{timetable_id}  (🔒 auth required) ───────────────────────────────
@router.delete("/{timetable_id}", status_code=status.HTTP_200_OK)
async def delete_timetable(
    timetable_id: str,
    _admin=Depends(get_current_admin),
):
    """Delete a timetable. Requires: Authorization: Bearer <token>"""
    try:
        result = timetables_collection.delete_one({"_id": ObjectId(timetable_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid timetable ID.")
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Timetable not found.")
    return {"message": "Timetable deleted"}
