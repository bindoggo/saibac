# backend/llm_optimizer.py
"""
High-level orchestrator:
- Loads timetable version from DB
- Builds a compact JSON + natural-language prompt describing the current timetable and optimization goals
- Calls LLM via llm_client.ask_llm
- Extracts JSON from LLM response and parses assignment list
- Validates via post_validation
- Returns parsed assignments (not yet saved)
"""

import json
import logging
import re
from typing import Dict, Any, List

from .llm_client import ask_llm
from .post_validation import validate_assignments_hard_constraints

logger = logging.getLogger(__name__)

JSON_EXTRACT_RE = re.compile(r"(\{(?:.|\s)*\}|\[(?:.|\s)*\])")  # try to find a JSON object/array in the response


def _extract_json_text(text: str) -> str:
    """
    Heuristic to extract JSON substring from an LLM response.
    """
    if not text:
        return ""
    # first try to find a top-level JSON object/array
    m = JSON_EXTRACT_RE.search(text)
    if m:
        return m.group(1)
    # fallback: try to fix common issues
    # if text looks like lines of "key: value", return as {} to fail later
    return text


def build_optimization_prompt(
    version_meta: Dict[str, Any],
    entries: List[Dict[str, Any]],
    events: Dict[int, Dict],
    timeslots: Dict[int, Dict],
    rooms: Dict[int, Dict],
    faculties: Dict[int, Dict],
    batches: Dict[int, Dict],
    goals: List[str],
) -> str:
    """
    Build a compact prompt. Keep it succinct (LLMs have context limits).
    The prompt asks for a JSON response with a top-level object:
    { "optimized_assignments": [ {event_id, timeslot_id, room_id}, ... ] }
    """

    # Compact representations
    def compact_entries(rows):
        out = []
        for e in rows:
            out.append({
                "event_id": e.get("event_id"),
                "offering": e.get("subject_offering_id") or e.get("offering_id"),
                "batch_id": e.get("batch_id"),
                "faculty_id": e.get("faculty_id"),
                "timeslot_id": e.get("timeslot_id"),
                "room_id": e.get("room_id"),
            })
        return out

    # short summary tables
    summary = {
        "counts": {
            "events": len(events),
            "timeslots": len(timeslots),
            "rooms": len(rooms),
            "faculties": len(faculties),
            "batches": len(batches),
        }
    }

    prompt_lines = [
        "You are an expert timetable optimizer. Input is a valid feasible timetable produced by a constraint solver.",
        "You MUST NOT violate hard constraints. These hard constraints are:",
        "1) No faculty can teach >1 event at the same timeslot.",
        "2) No batch can attend >1 event at the same timeslot.",
        "3) No room double-bookings.",
        "4) Room capacity must be >= batch size.",
        "5) Lab events must be placed in lab rooms.",
        "",
        "Goals to improve (soft constraints) — act on these to improve the timetable:",
    ]
    for g in goals:
        prompt_lines.append(f"- {g}")
        prompt_lines.append("")
        prompt_lines.append("Provide your result as strict JSON only (no commentary) with the schema:")
        prompt_lines.append('{"optimized_assignments":[{"event_id":<int>,"timeslot_id":<int>,"room_id":<int>}, ...]}')
        prompt_lines.append("")
        prompt_lines.append("SUMMARY:")
        prompt_lines.append(json.dumps(summary))
        prompt_lines.append("")
        prompt_lines.append("ENTRIES (current assignments):")
        # include compact entries but avoid extremely long prompt — limit entries if huge
        compact = compact_entries(entries)
        # if too many entries, truncate but inform
        max_include = 400  # conservative
        if len(compact) > max_include:
            prompt_lines.append(f"(showing first {max_include} of {len(compact)} entries)")
            compact = compact[:max_include]
        prompt_lines.append(json.dumps(compact))
        prompt_lines.append("")
        prompt_lines.append("TIMESLOTS (id -> day,slot):")
        # minimal timeslot info
        ts_compact = {tid: {"day": t.get("day"), "slot": t.get("slot")} for tid, t in timeslots.items()}
        prompt_lines.append(json.dumps(ts_compact))
        prompt_lines.append("")
        prompt_lines.append("ROOMS (id -> capacity,type):")
        rooms_compact = {rid: {"capacity": r.get("capacity"), "type": r.get("type")} for rid, r in rooms.items()}
        prompt_lines.append(json.dumps(rooms_compact))
        prompt_lines.append("")
        prompt_lines.append("FACULTIES (id -> max_per_day,unavailable_slots_count):")
        fac_compact = {fid: {"max_per_day": f.get("max_per_day"), "unavailable": len(f.get("unavailable_slots", []))} for fid, f in faculties.items()}
        prompt_lines.append(json.dumps(fac_compact))
        prompt_lines.append("")
        prompt_lines.append("BATCHES (id -> size):")
        bat_compact = {bid: {"size": b.get("size")} for bid, b in batches.items()}
        prompt_lines.append(json.dumps(bat_compact))
        prompt_lines.append("")
        prompt_lines.append("Now propose improvements only by changing timeslot_id and/or room_id for events.")
        prompt_lines.append("Return the full list of assignments (one per event_id).")

        return "\n".join(prompt_lines)


def parse_llm_assignments(text: str) -> List[Dict[str, int]]:
    """
    Extract JSON and parse the optimized_assignments array.
    """
    raw = _extract_json_text(text)
    try:
        j = json.loads(raw)
    except Exception:
        # Sometimes the LLM nests JSON under other keys; try to find substring
        # fallback: raise
        raise ValueError("Failed to parse JSON from LLM output. Raw output: " + text[:2000])

    # Try expected keys
    if "optimized_assignments" in j:
        arr = j["optimized_assignments"]
    elif "optimized_timetable" in j and "entries" in j["optimized_timetable"]:
        arr = j["optimized_timetable"]["entries"]
    elif isinstance(j, list):
        arr = j
    else:
        # try to find any array of objects with event_id
        arr = None
        for v in j.values():
            if isinstance(v, list):
                # crude check
                if len(v) and isinstance(v[0], dict) and "event_id" in v[0]:
                    arr = v
                    break
        if arr is None:
            raise ValueError("Could not find optimized_assignments in LLM JSON")

    # normalize entries to have ints
    out = []
    for it in arr:
        if not isinstance(it, dict) or "event_id" not in it:
            continue
        out.append({
            "event_id": int(it["event_id"]),
            "timeslot_id": int(it["timeslot_id"]),
            "room_id": int(it["room_id"]),
        })
    return out


def optimize_timetable_with_llm(
    # all args are plain Python objects (dictionaries / lists) collected by caller
    version_meta: Dict[str, Any],
    current_entries: List[Dict[str, Any]],
    events_lookup: Dict[int, Dict],
    timeslots: Dict[int, Dict],
    rooms: Dict[int, Dict],
    faculties: Dict[int, Dict],
    batches: Dict[int, Dict],
    goals: List[str],
    llm_max_tokens: int = 1024,
) -> List[Dict[str, int]]:
    """
    Returns optimized assignments as a list of {"event_id", "timeslot_id", "room_id"}.
    May raise exceptions on parse/validation failures.
    """
    prompt = build_optimization_prompt(version_meta, current_entries, events_lookup, timeslots, rooms, faculties, batches, goals)
    logger.info("Calling LLM for timetable optimization (prompt len=%d chars)", len(prompt))
    llm_text = ask_llm(prompt, max_tokens=llm_max_tokens, temperature=0.1)
    logger.debug("LLM returned: %s", llm_text[:1500])

    # parse JSON
    optimized = parse_llm_assignments(llm_text)

    # validate internal consistency quickly (caller will run strict validation)
    if len(optimized) != len(events_lookup):
        logger.warning("LLM returned %d assignments but we expected %d events", len(optimized), len(events_lookup))

    return optimized
