# backend/api.py
from typing import List, Optional
from datetime import datetime, time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, validator

from sqlalchemy.orm import Session

from .models import (
    SessionLocal,
    Departments,
    Rooms,
    Faculty,
    Batches,
    Subjects,
    SubjectOfferings,
    FacultyAssignments,
    Timeslots,
)

from .solver import TimetableEntry, TimetableVersion
from .solver import generate_timetable  # your existing solver function

from .llm_optimizer import optimize_timetable_with_llm
from .post_validation import validate_assignments_hard_constraints

router = APIRouter(prefix="/api")


# ---------- DB dependency ----------

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- Pydantic Schemas ----------

class DepartmentCreate(BaseModel):
    code: str
    name: str

class RoomsCreate(BaseModel):
    code: str
    capacity: int
    type: str            # "lab" or "classRooms"
    location: str | None = None

class FacultyCreate(BaseModel):
    name: str
    department_id: str
    max_classes_per_day: int = 4
    active: bool = True


class BatchCreate(BaseModel):
    name: str
    department_id: str
    semester: int
    shift: str = "day"
    size: int


class SubjectCreate(BaseModel):
    code: str | None = None
    title: str | None = None
    name: str | None = None   # optional backward compatibility
    department_id: int | None = None   # <-- changed to int
    type: str = "theory"
    classes_per_week: int = 3


class SubjectOfferingCreate(BaseModel):
    subject_code: str
    batch_id: str
    semester: int
    elective: bool = False


class FacultyAssignmentCreate(BaseModel):
    subject_offering_id: int
    faculty_id: int

class TimeslotCreate(BaseModel):
    day: int        # 0=Mon
    slot: int       # 1,2,3...
    # NOTE: type is Optional[time], not Optional[str]
    start_time: Optional[time] = None  # accepts "09:00", "9", 9, "9:00", etc.
    end_time:   Optional[time] = None

    @validator("start_time", "end_time", pre=True)
    def normalize_time(cls, value):
        if value is None:
            return None

        # if it's already a time object, accept it
        if isinstance(value, time):
            return value

        # if it's a number like 9 or "9"
        try:
            if isinstance(value, int):
                return time(value, 0)
            if isinstance(value, str) and value.isdigit():
                return time(int(value), 0)
        except Exception:
            pass

        # if it's a string with colon "HH:MM"
        if isinstance(value, str):
            try:
                # time.fromisoformat accepts "HH:MM" or "HH:MM:SS"
                return time.fromisoformat(value)
            except Exception:
                raise ValueError(f"Invalid time format: {value!r}. Accepts '9', '09', '9:00', '09:00', or integer hour.")

        # anything else is invalid
        raise ValueError(f"Invalid time type: {type(value)}")



class SolveRequest(BaseModel):
    version_name: Optional[str] = None
    time_limit_seconds: int = 20


# ---------- Departments endpoints ----------

@router.post("/departments")
def create_department(payload: DepartmentCreate, db: Session = Depends(get_db)):
    # optional: check for duplicates
    exists = db.query(Departments).filter(Departments.code == payload.code).first()
    if exists:
        raise HTTPException(status_code=400, detail="Department code already exists")

    dept = Departments(code=payload.code, name=payload.name)
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.get("/departments")
def list_departments(db: Session = Depends(get_db)):
    return db.query(Departments).all()


# ---------- rooms endpoints ----------

@router.post("/rooms")
def create_Rooms(payload: RoomsCreate, db: Session = Depends(get_db)):
    rooms = Rooms(
        code=payload.code,
        capacity=payload.capacity,
        type=payload.type,
        location=payload.location
    )
    db.add(rooms)
    db.commit()
    db.refresh(rooms)
    return rooms


@router.get("/rooms")
def list_Roomss(db: Session = Depends(get_db)):
    return db.query(Rooms).all()


# ---------- Faculty endpoints ----------

@router.post("/faculty")
def create_faculty(payload: FacultyCreate, db: Session = Depends(get_db)):
    fac = Faculty(
        name=payload.name,
        department_id=payload.department_id,
        max_classes_per_day=payload.max_classes_per_day,
        active=payload.active,
    )
    db.add(fac)
    db.commit()
    db.refresh(fac)
    return fac


@router.get("/faculty")
def list_faculty(db: Session = Depends(get_db)):
    return db.query(Faculty).all()


@router.get("/faculty/stats")
def faculty_stats(db: Session = Depends(get_db)):
    total = db.query(Faculty).count()
    active = db.query(Faculty).filter(Faculty.active == True).count()
    # on_leave could be a flag; for now assume `active=False`
    on_leave = total - active
    # very simple avg load: entries per faculty in latest version
    latest_version = (
        db.query(TimetableVersion)
        .order_by(TimetableVersion.created_at.desc())
        .first()
    )
    avg_hours = 0
    if latest_version:
        entries = (
            db.query(TimetableEntry.faculty_id)
            .filter(TimetableEntry.version_id == latest_version.id)
            .all()
        )
        if entries:
            # assume 1 entry = 1 hour
            avg_hours = len(entries) / max(active, 1)
    return {
        "total": total,
        "active": active,
        "on_leave": on_leave,
        "avg_hours": avg_hours,
    }


# ---------- Batches endpoints (Students) ----------

@router.post("/batches")
def create_batch(payload: BatchCreate, db: Session = Depends(get_db)):
    b = Batches(
        name=payload.name,
        department_id=payload.department_id,
        semester=payload.semester,
        shift=payload.shift,
        size=payload.size,
    )
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@router.get("/batches")
def list_batches(db: Session = Depends(get_db)):
    return db.query(Batches).all()


# ---------- Subjects endpoints ----------

@router.post("/subjects")
def create_subject(payload: SubjectCreate, db: Session = Depends(get_db)):
    # ensure minimal data
    if not payload.code:
        raise HTTPException(status_code=400, detail="Missing subject code")

    # prefer title, fallback to name or code
    title_val = payload.title or payload.name or payload.code

    # Validate department_id if present. If None, allow nullable in DB (or require depending on your schema).
    if payload.department_id is not None:
        dept = db.query(Departments).filter(Departments.id == payload.department_id).first()
        if not dept:
            raise HTTPException(status_code=400, detail=f"Department with id {payload.department_id} not found")

    # duplicate check on code
    exists = db.query(Subjects).filter(Subjects.code == payload.code).first()
    if exists:
        raise HTTPException(status_code=400, detail="Subjects code already exists")

    subj = Subjects(
        code=payload.code,
        title=title_val,
        department_id=payload.department_id,
        type=payload.type,
        classes_per_week=payload.classes_per_week,
    )
    db.add(subj)
    db.commit()
    db.refresh(subj)
    return subj

@router.get("/subjects")
def list_subjects(db: Session = Depends(get_db)):
    return db.query(Subjects).all()


# ---------- Offerings & assignments ----------

@router.post("/subject-offerings")
def create_offering(payload: SubjectOfferingCreate, db: Session = Depends(get_db)):
    off = SubjectOfferings(
        subject_code=payload.subject_code,
        batch_id=payload.batch_id,
        semester=payload.semester,
        elective=payload.elective,
    )
    db.add(off)
    db.commit()
    db.refresh(off)
    return off


@router.get("/subject-offerings")
def list_offerings(db: Session = Depends(get_db)):
    return db.query(SubjectOfferings).all()


@router.post("/faculty-assignments")
def create_assignment(payload: FacultyAssignmentCreate, db: Session = Depends(get_db)):
    fa = FacultyAssignments(
        subject_offering_id=payload.subject_offering_id,
        faculty_id=payload.faculty_id,
    )
    db.add(fa)
    db.commit()
    db.refresh(fa)
    return fa


@router.get("/faculty-assignments")
def list_assignments(db: Session = Depends(get_db)):
    return db.query(FacultyAssignments).all()


# ---------- Timeslots ----------

@router.post("/timeslots")
def create_timeslot(payload: TimeslotCreate, db: Session = Depends(get_db)):
    ts = Timeslots(
        day=payload.day,
        slot=payload.slot,
        start_time=payload.start_time,
        end_time=payload.end_time,
    )
    db.add(ts)
    db.commit()
    db.refresh(ts)
    return ts


@router.get("/timeslots")
def list_timeslots(db: Session = Depends(get_db)):
    return db.query(Timeslots).all()


# ---------- Timetable generation & view ----------

@router.post("/timetable/generate")
def generate(req: SolveRequest):
    result = generate_timetable(
        version_name=req.version_name or "web_ui",
        time_limit_seconds=req.time_limit_seconds,
    )
    return result


@router.get("/timetable/versions")
def list_versions(db: Session = Depends(get_db)):
    return (
        db.query(TimetableVersion)
        .order_by(TimetableVersion.created_at.desc())
        .all()
    )


@router.get("/timetable/batch/{version_id}/{batch_id}")
def timetable_by_batch(version_id: str, batch_id: str, db: Session = Depends(get_db)):
    entries = (
        db.query(TimetableEntry)
        .filter(
            TimetableEntry.version_id == version_id,
            TimetableEntry.batch_id == batch_id,
        )
        .all()
    )
    return entries


@router.get("/timetable/faculty/{version_id}/{faculty_id}")
def timetable_by_faculty(version_id: str, faculty_id: str, db: Session = Depends(get_db)):
    entries = (
        db.query(TimetableEntry)
        .filter(
            TimetableEntry.version_id == version_id,
            TimetableEntry.faculty_id == faculty_id,
        )
        .all()
    )
    return entries

@router.post("/timetable/optimize")
def optimize_timetable_api(version_id: Optional[str] = None, goals: Optional[list] = None, db: Session = Depends(get_db)):
    """
    Trigger LLM optimization.
    - version_id: existing version to optimize (if not provided, uses latest).
    - goals: optional list of strings describing soft goals (e.g. ["reduce faculty daily load", "avoid back-to-back classes"]).
    Returns new timetable version metadata on success.
    """
    # find source version
    if version_id:
        src_ver = db.query(TimetableVersion).filter(TimetableVersion.id == version_id).first()
        if not src_ver:
            raise HTTPException(status_code=404, detail="version not found")
    else:
        src_ver = db.query(TimetableVersion).order_by(TimetableVersion.created_at.desc()).first()
        if not src_ver:
            raise HTTPException(status_code=404, detail="no timetable versions found to optimize")

    # load current entries for that version
    entries = db.query(TimetableEntry).filter(TimetableEntry.version_id == src_ver.id).all()
    # build lookups
    current_entries = []
    event_ids = set()
    for e in entries:
        current_entries.append({
            "event_id": getattr(e, "event_id", None) or getattr(e, "subject_offering_id", None) or None,
            "subject_offering_id": getattr(e, "subject_offering_id", None),
            "batch_id": getattr(e, "batch_id", None),
            "faculty_id": getattr(e, "faculty_id", None),
            "timeslot_id": getattr(e, "timeslot_id", None),
            "Rooms_id": getattr(e, "Rooms_id", None),
        })
        if getattr(e, "event_id", None):
            event_ids.add(e.event_id)
        elif getattr(e, "subject_offering_id", None):
            event_ids.add(e.subject_offering_id)

    # load events_lookup: we need batch_size, is_lab, faculty_id -> derive from SubjectOfferings/Subjects/Batches/Faculty
    events_lookup = {}
    for row in current_entries:
        eid = int(row["event_id"])
        # Prefer to query subject offering row to fetch metadata# compute the id value first (prefer subject_offering_id from the row, otherwise use eid)
        so_id = row.get("subject_offering_id") or eid
        off = db.query(SubjectOfferings).filter(SubjectOfferings.id == so_id).first()

        if not off:
            # fallback: minimal
            events_lookup[eid] = {
                "batch_id": row.get("batch_id"),
                "faculty_id": row.get("faculty_id"),
                "is_lab": False,
                "batch_size": None,
            }
            continue
        # gather batch size
        b = db.query(Batches).filter(Batches.id == off.batch_id).first()
        batch_size = b.size if b else None
        # deduce lab flag from Subjects (if available)
        subj = getattr(off, "subject", None)
        # sometimes relationship not present; try fetching
        if not subj:
            try:
                subj = db.query(Subjects).filter(Subjects.code == off.subject_code).first()
            except Exception:
                subj = None
        is_lab = getattr(subj, "type", None) == "lab" if subj else False
        events_lookup[eid] = {
            "batch_id": off.batch_id,
            "faculty_id": None,  # we'll set below if faculty assignment exists in db
            "is_lab": is_lab,
            "batch_size": batch_size,
        }
        # try to find faculty assignment
        fa = db.query(FacultyAssignments).filter(FacultyAssignments.subject_offering_id == off.id).first()
        if fa:
            events_lookup[eid]["faculty_id"] = fa.faculty_id

    # timeslot lookup
    timeslot_objs = db.query(Timeslots).all()
    timeslot_lookup = {ts.id: {"day": ts.day, "slot": ts.slot} for ts in timeslot_objs}
    # rooms lookup
    Rooms_objs = db.query(Rooms).all()
    Rooms_lookup = {r.id: {"capacity": r.capacity, "type": r.type} for r in Rooms_objs}
    # faculties lookup
    faculty_objs = db.query(Faculty).all()
    faculty_lookup = {}
    for f in faculty_objs:
        # if you have a faculty unavailability table, fetch those as a set of timeslot ids
        faculty_lookup[f.id] = {"max_per_day": getattr(f, "max_classes_per_day", None), "unavailable_slots": set()}

    # batches lookup
    batch_objs = db.query(Batches).all()
    batch_lookup = {b.id: {"size": getattr(b, "size", None)} for b in batch_objs}

    # collect goals
    if not goals:
        goals = [
            "Minimize days with no free period for batches (aim one free per day if possible)",
            "Reduce back-to-back classes for batches where possible",
            "Balance daily load for faculty; avoid >4 classes in a day where possible",
        ]

    # call optimizer
    try:
        optimized_assignments = optimize_timetable_with_llm(
            version_meta={"id": src_ver.id, "name": src_ver.name},
            current_entries=current_entries,
            events_lookup=events_lookup,
            timeslots=timeslot_lookup,
            rooms=Rooms_lookup,
            faculties=faculty_lookup,
            batches=batch_lookup,
            goals=goals,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"LLM optimization failed: {exc}")

    # Validate strictly using post_validation
    valid, msg = validate_assignments_hard_constraints(optimized_assignments, timeslot_lookup, Rooms_lookup, events_lookup)
    if not valid:
        raise HTTPException(status_code=400, detail=f"Optimization violated hard constraints: {msg}")

    # Persist as a new TimetableVersion + TimetableEntry rows
    new_version = TimetableVersion(name=(src_ver.name or "version") + "-llm-opt", created_at=datetime.utcnow())
    db.add(new_version)
    db.commit()
    db.refresh(new_version)

    # insert entries
    for a in optimized_assignments:
        # create TimetableEntry - adapt field names to your model
        te = TimetableEntry(
            version_id=new_version.id,
            subject_offering_id=a.get("event_id"),  # if your timetable uses subject_offering_id name
            batch_id=events_lookup[a["event_id"]]["batch_id"],
            faculty_id=events_lookup[a["event_id"]].get("faculty_id"),
            timeslot_id=a["timeslot_id"],
            Rooms_id=a["Rooms_id"],
            day=timeslot_lookup[a["timeslot_id"]]["day"],
            slot=timeslot_lookup[a["timeslot_id"]]["slot"],
        )
        db.add(te)
    db.commit()

    return {"status": "ok", "new_version_id": new_version.id}