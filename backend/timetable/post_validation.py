# backend/post_validation.py
from typing import List, Dict, Tuple, Any
from collections import defaultdict

# We assume SQLAlchemy model objects will be passed in or queriable by the caller.
# The validator works on a list of assignment dicts:
# assignments = [ { "event_id": ..., "timeslot_id": ..., "room_id": ..., "batch_id": ..., "faculty_id": ... }, ... ]
#
# It returns (True, None) if valid, or (False, "error message") if invalid.

def validate_assignments_hard_constraints(
    assignments: List[Dict[str, Any]],
    timeslot_lookup: Dict[int, Dict],
    room_lookup: Dict[int, Dict],
    event_lookup: Dict[int, Dict],
) -> Tuple[bool, str]:
    """
    Very strict checks:
    - every assignment references existing event, timeslot, room
    - no two assignments use same (timeslot, room)
    - no faculty teaches two events in same timeslot
    - no batch attends two events in same timeslot
    - room capacity >= batch size (if event_lookup provides batch size)
    - room type compatibility if event indicates is_lab
    - all event_ids present (optional: check same count)
    """
    # quick existence checks
    for a in assignments:
        if a.get("event_id") not in event_lookup:
            return False, f"Unknown event_id {a.get('event_id')}"
        if a.get("timeslot_id") not in timeslot_lookup:
            return False, f"Unknown timeslot_id {a.get('timeslot_id')}"
        if a.get("room_id") not in room_lookup:
            return False, f"Unknown room_id {a.get('room_id')}"

    # uniqueness checks
    room_ts = set()
    faculty_ts = defaultdict(set)
    batch_ts = defaultdict(set)

    for a in assignments:
        eid = a["event_id"]
        tid = a["timeslot_id"]
        rid = a["room_id"]
        key = (tid, rid)
        if key in room_ts:
            return False, f"Room {rid} double-booked at timeslot {tid}"
        room_ts.add(key)

        ev = event_lookup[eid]
        batch_id = ev.get("batch_id") or a.get("batch_id")
        fac_id = ev.get("faculty_id") or a.get("faculty_id")

        # faculty clash
        if fac_id is not None:
            if tid in faculty_ts[fac_id]:
                return False, f"Faculty {fac_id} has multiple events at timeslot {tid}"
            faculty_ts[fac_id].add(tid)

        # batch clash
        if batch_id is not None:
            if tid in batch_ts[batch_id]:
                return False, f"Batch {batch_id} has multiple events at timeslot {tid}"
            batch_ts[batch_id].add(tid)

        # capacity & room type
        room = room_lookup[rid]
        room_cap = room.get("capacity")
        room_type = room.get("type")
        batch_size = ev.get("batch_size")
        is_lab = ev.get("is_lab", False)
        if batch_size is not None and room_cap is not None and room_cap < batch_size:
            return False, f"Room {rid} capacity ({room_cap}) smaller than batch size ({batch_size}) for event {eid}"
        if is_lab and room_type is not None and room_type != "lab":
            return False, f"Event {eid} requires a lab but room {rid} is type {room_type}"

    # passed checks
    return True, ""
