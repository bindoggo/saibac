# timetable_solver.py
"""
Single-file timetable solver:
- Uses existing SQLAlchemy models for your college DB
- Defines TimetableVersion and TimetableEntry (if not already present)
- Retrieves data, solves timetable, and writes results back to DB.

Requirements:
- ortools (pip install ortools)
- SQLAlchemy models file (models.py) with:
  - Base (class Base(DeclarativeBase): pass)
  - engine
  - SessionLocal
  - Rooms, Faculty, Batches, Subjects, SubjectOfferings, FacultyAssignments, Timeslots
"""

import uuid
from datetime import datetime
from collections import defaultdict

from ortools.sat.python import cp_model

from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, Session

# 👉 adjust this import to match your actual models module
from .models import (
    Base,
    engine,
    SessionLocal,
    Rooms,
    Faculty,
    Batches,
    Subjects,
    SubjectOfferings,
    FacultyAssignments,
    Timeslots,
    # if you already have these, you can remove their definitions below
    TimetableVersion,
    TimetableEntry,
)

# ==========================
# 2) Helper functions
# ==========================

def gen_id() -> str:
    return str(uuid.uuid4())


# ==========================
# 3) Main solver function
# ==========================

def generate_timetable(version_name: str | None = None, time_limit_seconds: int = 30) -> dict:
    """
    1. Open DB session
    2. Load data from DB
    3. Build CP-SAT model and solve
    4. Create TimetableVersion + TimetableEntries
    5. Commit and return summary
    """

    db: Session = SessionLocal()

    try:
        # --------------------
        # 3.1 Load data from DB
        # --------------------

        rooms_db = db.query(Rooms).all()
        timeslots_db = db.query(Timeslots).order_by(Timeslots.day, Timeslots.slot).all()
        offerings_db = db.query(SubjectOfferings).all()
        subjects_db = {s.code: s for s in db.query(Subjects).all()}
        batches_db = {b.id: b for b in db.query(Batches).all()}
        assignments_db = db.query(FacultyAssignments).all()
        faculty_db = {f.id: f for f in db.query(Faculty).all()}

        # 👉 IMPORTANT:
        # Check your models.py and ensure these attribute names exist:
        # - Rooms.capacity (maybe room.cap or room_capacity)
        # - Rooms.type ('lab'/'theory'; maybe room.room_type)
        # - Timeslots.day, Timeslots.slot
        # - Subjects.classes_per_week, Subjects.type
        # - Batches.size
        # If they are different, change lines below accordingly.

        if not rooms_db or not timeslots_db or not offerings_db:
            return {
                "success": False,
                "reason": "insufficient_data",
                "message": "Need rooms, timeslots, and subject_offerings in DB.",
            }

        # offering_id -> faculty_id (assume exactly one assignment; if multiple, we pick first)
        offering_to_faculty: dict[str, str] = {}
        for fa in assignments_db:
            off_id = str(fa.subject_offering_id)
            fac_id = str(fa.faculty_id)
            if off_id not in offering_to_faculty:
                offering_to_faculty[off_id] = fac_id

        # --------------------
        # 3.2 Build "events" = each required class
        # --------------------
        # For each offering, create 'classes_per_week' identical event instances.

        events = []  # list of dict: {idx, offering_id, batch_id, faculty_id, subject_type, batch_size}
        event_idx = 0

        for off in offerings_db:
            off_id = str(off.id)
            subj = subjects_db.get(off.subject_code)
            if subj is None:
                # subject missing, skip this offering
                continue

            batch = batches_db.get(off.batch_id)
            if batch is None:
                continue

            classes_per_week = int(subj.classes_per_week or 1)
            subject_type = (subj.type or "theory").lower()
            batch_size = int(batch.size or 0)
            faculty_id = offering_to_faculty.get(off_id)

            if not faculty_id:
                # if no faculty assigned, skip this offering (or you can raise error)
                # to enforce all offerings have a faculty, change this behavior.
                continue

            for _ in range(classes_per_week):
                events.append({
                    "idx": event_idx,
                    "offering_id": off_id,
                    "batch_id": str(off.batch_id),
                    "faculty_id": faculty_id,
                    "subject_type": subject_type,
                    "batch_size": batch_size,
                })
                event_idx += 1

        if not events:
            return {
                "success": False,
                "reason": "no_events",
                "message": "No schedulable events (check offerings and faculty_assignments).",
            }

        # Quick precheck: total events <= room * timeslots
        total_instances = len(events)
        total_room_slots = len(rooms_db) * len(timeslots_db)

        if total_instances > total_room_slots:
            return {
                "success": False,
                "reason": "precheck_failed",
                "message": f"Required classes {total_instances} > available room slots {total_room_slots}.",
            }

        # --------------------
        # 3.3 Build CP-SAT model
        # --------------------
        model = cp_model.CpModel()

        # Indices
        room_index = {i: r for i, r in enumerate(rooms_db)}
        timeslot_index = {i: t for i, t in enumerate(timeslots_db)}

        # Decision variables: x[e_idx, t_idx, r_idx] = 1 if event e in timeslot t in room r
        x = {}  # (e_idx, t_idx, r_idx) -> BoolVar

        # Build variables with pre-filtering
        for e in events:
            e_idx = e["idx"]
            subj_type = e["subject_type"]
            batch_size = e["batch_size"]

            for t_idx, ts in enumerate(timeslots_db):
                day = ts.day
                slot = ts.slot

                # For now, we don't consider unavailability or fixed slots in this simpler version
                for r_idx, room in enumerate(rooms_db):
                    # capacity
                    # 👉 change room.capacity to the correct attribute if needed
                    if room.capacity is not None and room.capacity < batch_size:
                        continue
                    # lab room check
                    # 👉 change room.type if needed (e.g., room.room_type)
                    room_type = (room.type or "").lower()
                    if subj_type == "lab" and room_type != "lab":
                        continue

                    var = model.NewBoolVar(f"x_e{e_idx}_t{t_idx}_r{r_idx}")
                    x[(e_idx, t_idx, r_idx)] = var

        # Hard constraints

        # (1) Each event must be scheduled exactly once
        for e in events:
            e_idx = e["idx"]
            vars_for_e = [v for (i, t, r), v in x.items() if i == e_idx]
            if not vars_for_e:
                return {
                    "success": False,
                    "reason": "no_domain_for_event",
                    "message": f"No feasible room/timeslot for event (offering {e['offering_id']}).",
                }
            model.Add(sum(vars_for_e) == 1)

        # (2) Rooms non-overlap per timeslot: at most one event in each room per timeslot
        for t_idx, ts in enumerate(timeslots_db):
            for r_idx, room in enumerate(rooms_db):
                vars_here = [v for (i, t, r), v in x.items() if t == t_idx and r == r_idx]
                if vars_here:
                    model.Add(sum(vars_here) <= 1)

        # (3) Batches non-overlap: a batch cannot have two classes in same timeslot
        batches_set = set(e["batch_id"] for e in events)
        for b in batches_set:
            e_idxs_for_batch = [e["idx"] for e in events if e["batch_id"] == b]
            for t_idx, ts in enumerate(timeslots_db):
                vars_here = [v for (i, t, r), v in x.items() if i in e_idxs_for_batch and t == t_idx]
                if vars_here:
                    model.Add(sum(vars_here) <= 1)

        # (4) Faculty non-overlap: a faculty cannot teach two classes in same timeslot
        faculties_set = set(e["faculty_id"] for e in events)
        for f_id in faculties_set:
            e_idxs_for_fac = [e["idx"] for e in events if e["faculty_id"] == f_id]
            for t_idx, ts in enumerate(timeslots_db):
                vars_here = [v for (i, t, r), v in x.items() if i in e_idxs_for_fac and t == t_idx]
                if vars_here:
                    model.Add(sum(vars_here) <= 1)

        # Objective: minimize wasted seats
        obj_terms = []
        for (i, t, r), var in x.items():
            room = room_index[r]
            batch_size = events[i]["batch_size"]
            # 👉 adjust room.capacity if needed
            cap = int(room.capacity or 0)
            waste = max(0, cap - batch_size)
            if waste > 0:
                obj_terms.append(waste * var)

        if obj_terms:
            model.Minimize(sum(obj_terms))

        # --------------------
        # 3.4 Solve
        # --------------------
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = time_limit_seconds
        solver.parameters.num_search_workers = 8

        status = solver.Solve(model)
        status_name = solver.StatusName(status)

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return {
                "success": False,
                "reason": "no_solution",
                "message": f"Solver status: {status_name}",
            }

        # --------------------
        # 3.5 Write timetable to DB
        # --------------------

        version = TimetableVersion()
        version.id = gen_id()
        version.name = version_name or f"auto_{datetime.utcnow().isoformat()}"
        version.status = "draft"
        db.add(version)
        db.flush()  # ensure version.id set

        created_entries = 0
        sample_entries = []

        for (i, t, r), var in x.items():
            if solver.Value(var):
                e = events[i]
                ts = timeslot_index[t]
                room = room_index[r]

                entry = TimetableEntry()
                entry.id = gen_id()
                entry.version_id = version.id
                entry.subject_offering_id = e["offering_id"]
                entry.faculty_id = e["faculty_id"]
                entry.batch_id = e["batch_id"]
                entry.room_id = str(room.id)
                entry.day = ts.day
                entry.slot = ts.slot

                db.add(entry)
                created_entries += 1

                if len(sample_entries) < 20:
                    sample_entries.append({
                        "subject_offering_id": entry.subject_offering_id,
                        "faculty_id": entry.faculty_id,
                        "batch_id": entry.batch_id,
                        "room_id": entry.room_id,
                        "day": entry.day,
                        "slot": entry.slot,
                    })

        db.commit()

        return {
            "success": True,
            "version_id": version.id,
            "entries_count": created_entries,
            "sample_entries": sample_entries,
            "solver_status": status_name,
        }

    finally:
        db.close()


# ==========================
# 4) Run directly for testing
# ==========================

if __name__ == "__main__":
    result = generate_timetable(version_name="test_run", time_limit_seconds=20)
    print(result)
