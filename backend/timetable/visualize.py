# visualize_timetable.py
"""
Reads timetable from DB and prints a nice Day x Time grid for a given
timetable version + batch (section). Optional: show a matplotlib table.
"""

from typing import Dict, Tuple
from collections import defaultdict

# pip install pandas matplotlib if you don't have them
import pandas as pd # pyright: ignore[reportMissingModuleSource]
import matplotlib.pyplot as plt # pyright: ignore[reportMissingModuleSource]

# 👉 adjust this import to where your models live
from .models import (
    SessionLocal,
    Timeslots,
    SubjectOfferings,
    Subjects,
    Faculty,
    Rooms,
    Batches,
)

from .solver import TimetableEntry
# ---------- helpers ----------

DAY_NAMES = {
    0: "Monday",
    1: "Tuesday",
    2: "Wednesday",
    3: "Thursday",
    4: "Friday",
    5: "Saturday",
    6: "Sunday",
}


def build_timetable_dataframe(
    version_id: str,
    batch_id: str,
) -> pd.DataFrame:
    """
    Pull data from DB and return a pandas DataFrame shaped like:

        index = day_name (rows)
        columns = time_label (cols)
        values = string like "L_DS/AG\nR-212"

    You can print this or plot with matplotlib.
    """
    db = SessionLocal()
    try:
        # 1) Load all entries for this version + batch
        entries = (
            db.query(TimetableEntry)
            .filter(
                TimetableEntry.version_id == version_id,
                TimetableEntry.batch_id == batch_id,
            )
            .all()
        )

        if not entries:
            raise ValueError(
                f"No timetable entries found for version_id={version_id}, batch_id={batch_id}"
            )

        # 2) Load supporting data (timeslots, subjects, faculty, rooms)
        timeslots = {ts.id: ts for ts in db.query(Timeslots).all()}

        # SubjectOfferings -> Subjects
        offerings = {off.id: off for off in db.query(SubjectOfferings).all()}
        subjects = {s.code: s for s in db.query(Subjects).all()}

        # Faculty & rooms
        faculties = {f.id: f for f in db.query(Faculty).all()}
        rooms = {r.id: r for r in db.query(Rooms).all()}

        # Optional: get batch name for printing later
        batch_obj = db.query(Batches).filter(Batches.id == batch_id).first()
        batch_name = getattr(batch_obj, "name", batch_id) if batch_obj else batch_id

        # 3) Build rows for DataFrame
        records = []

        for e in entries:
            ts = timeslots.get(e.slot)  # ⚠️ depends how you modeled timeslot
            # If you stored day/slot directly in TimetableEntry, use those:
            day = e.day if hasattr(e, "day") else ts.day
            slot_no = e.slot if hasattr(e, "slot") else ts.slot

            day_name = DAY_NAMES.get(day, str(day))

            # Build a time label for the column (e.g., "09:00-10:00" or "Slot 1")
            if hasattr(ts, "start_time") and hasattr(ts, "end_time") and ts.start_time and ts.end_time:
                time_label = f"{ts.start_time.strftime('%H:%M')}-{ts.end_time.strftime('%H:%M')}"
            else:
                time_label = f"Slot {slot_no}"

            off = offerings.get(e.subject_offering_id)
            subj_code = off.subject_code if off else "UNK"
            subj = subjects.get(subj_code)

            # Short subject display, e.g. "L_DS" like in your photo
            # You can customize this mapping to exactly match your format
            subj_display = subj_code
            if subj and getattr(subj, "name", None):
                subj_display = subj_code  # or f"{subj_code}\n{subj.name}"

            fac = faculties.get(e.faculty_id)
            fac_name = getattr(fac, "name", "") if fac else ""
            # Convert "Dr. Avinash Gupta" -> "AG" style initials
            fac_short = ""
            if fac_name:
                parts = fac_name.split()
                fac_short = "".join(p[0].upper() for p in parts if p)

            room_obj = rooms.get(e.room_id)
            room_code = getattr(room_obj, "code", None) or getattr(room_obj, "room_no", "") or str(e.room_id)

            # Final cell text: like "L_DS/AG\nR-212"
            # if you want L_ prefix, check subject type (theory vs lab) in Subjects
            typ_prefix = "L"  # default lecture
            if subj and getattr(subj, "type", "").lower() == "lab":
                typ_prefix = "P"

            cell_text = f"{typ_prefix}_{subj_code}"
            if fac_short:
                cell_text += f"/{fac_short}"
            if room_code:
                cell_text += f"\n{room_code}"

            records.append(
                {
                    "day_name": day_name,
                    "time_label": time_label,
                    "cell": cell_text,
                }
            )

        # 4) Convert to DataFrame and pivot
        df = pd.DataFrame(records)
        # pivot so rows = days, columns = time slots
        grid = df.pivot_table(
            index="day_name",
            columns="time_label",
            values="cell",
            aggfunc=lambda x: "\n".join(x),  # if multiple, join them
        )

        # sort days in Monday→Friday order if present
        day_order = [DAY_NAMES[d] for d in sorted(set(DAY_NAMES.keys())) if DAY_NAMES[d] in grid.index]
        grid = grid.reindex(day_order).dropna(how="all", axis=0)

        # sort columns by natural order (Slot 1, Slot 2 or time)
        grid = grid.reindex(sorted(grid.columns), axis=1)

        grid.attrs["batch_name"] = batch_name
        grid.attrs["version_id"] = version_id
        return grid

    finally:
        db.close()


# ----------  printing & plotting  ----------

def print_timetable_ascii(grid: pd.DataFrame):
    """
    Print a simple text-based timetable (days x time slots).
    """
    batch_name = grid.attrs.get("batch_name", "")
    version_id = grid.attrs.get("version_id", "")

    print(f"\nTimetable for batch: {batch_name} (version: {version_id})\n")
    print(grid.fillna("").to_string())


def show_timetable_plot(grid: pd.DataFrame):
    """
    Show a matplotlib table that looks like a timetable.
    """
    fig, ax = plt.subplots(figsize=(len(grid.columns) * 1.5, len(grid.index) * 0.8))
    ax.axis("off")

    table = ax.table(
        cellText=grid.fillna("").values,
        rowLabels=grid.index,
        colLabels=grid.columns,
        cellLoc="center",
        loc="center",
    )

    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.2, 1.5)

    batch_name = grid.attrs.get("batch_name", "")
    version_id = grid.attrs.get("version_id", "")

    plt.title(f"Timetable – {batch_name} (version {version_id})")
    plt.tight_layout()
    plt.show()


# ----------  main for quick testing ----------

if __name__ == "__main__":
    # TODO: replace with actual version_id and batch_id from your DB
    VERSION_ID = input("Enter Version id : ")
    BATCH_ID = input("Enter Your Batch : ")

    grid = build_timetable_dataframe(VERSION_ID, BATCH_ID)
    print_timetable_ascii(grid)
    # uncomment if you want the plotted version:
    # show_timetable_plot(grid)
