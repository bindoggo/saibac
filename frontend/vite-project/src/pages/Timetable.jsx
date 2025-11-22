// src/pages/Timetable.jsx
import { useEffect, useState } from "react";
const API = "http://localhost:8000/api";

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

function makeEmptyGrid(days, slots) {
  const grid = {};
  for (let d = 0; d < days; d++) {
    grid[d] = {};
    for (let s = 1; s <= slots; s++) {
      grid[d][s] = "";
    }
  }
  return grid;
}

export default function TimetablePage() {
  const [versions, setVersions] = useState([]); // sorted ascending by created_at
  const [batches, setBatches] = useState([]);
  const [faculty, setFaculty] = useState([]);
  const [offerings, setOfferings] = useState([]);
  const [rooms, setRooms] = useState([]);
  const [timeslots, setTimeslots] = useState([]);

  const [selectedVersion, setSelectedVersion] = useState("");
  const [mode, setMode] = useState("batch"); // "batch" or "faculty"
  const [selectedBatch, setSelectedBatch] = useState("");
  const [selectedFaculty, setSelectedFaculty] = useState("");
  const [entries, setEntries] = useState([]);
  const [grid, setGrid] = useState(null);
  const [maxSlot, setMaxSlot] = useState(8);
  const [loading, setLoading] = useState(false);

  // helper maps
  const offeringById = Object.fromEntries(offerings.map((o) => [o.id, o]));
  const roomById = Object.fromEntries(rooms.map((r) => [String(r.id), r]));
  const subjectByCode = {}; // not used heavily but kept if needed

  // helper to normalize and sort versions by created_at ascending
  function normalizeAndSortVersions(rawVersions) {
    if (!Array.isArray(rawVersions)) {
      // Try common wrappers
      if (rawVersions && Array.isArray(rawVersions.data)) return normalizeAndSortVersions(rawVersions.data);
      if (rawVersions && Array.isArray(rawVersions.results)) return normalizeAndSortVersions(rawVersions.results);
      return [];
    }
    // copy and sort by created_at asc, fallback to id if missing
    const copy = rawVersions.slice();
    copy.sort((a, b) => {
      const da = a?.created_at ? new Date(a.created_at).getTime() : 0;
      const db = b?.created_at ? new Date(b.created_at).getTime() : 0;
      return da - db;
    });
    return copy;
  }

  useEffect(() => {
    async function loadBase() {
      try {
        const [vRes, bRes, fRes, offRes, roomRes, tsRes] = await Promise.all([
          fetch(`${API}/timetable/versions`),
          fetch(`${API}/batches`),
          fetch(`${API}/faculty`),
          fetch(`${API}/subject-offerings`),
          fetch(`${API}/rooms`),
          fetch(`${API}/timeslots`),
        ]);

        // parse safely
        const [vRaw, b, f, offs, r, ts] = await Promise.all([
          vRes.ok ? vRes.json() : [],
          bRes.ok ? bRes.json() : [],
          fRes.ok ? fRes.json() : [],
          offRes.ok ? offRes.json() : [],
          roomRes.ok ? roomRes.json() : [],
          tsRes.ok ? tsRes.json() : [],
        ]);

        const sortedVersions = normalizeAndSortVersions(vRaw);
        setVersions(sortedVersions);

        setBatches(Array.isArray(b) ? b : []);
        setFaculty(Array.isArray(f) ? f : []);
        setOfferings(Array.isArray(offs) ? offs : []);
        setRooms(Array.isArray(r) ? r : []);
        setTimeslots(Array.isArray(ts) ? ts : []);

        // default to latest version (last in sorted array)
        if (sortedVersions.length) {
          const latest = sortedVersions[sortedVersions.length - 1];
          setSelectedVersion(latest.id);
        }
        // compute max slot from timeslots if provided
        if (ts && ts.length) {
          const smax = ts.reduce((mx, t) => Math.max(mx, t.slot || 0), 0);
          if (smax > 0) setMaxSlot(smax);
        }
      } catch (err) {
        console.error("Failed to load base data:", err);
      }
    }
    loadBase();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // whenever entries / supporting data change, rebuild grid
    buildGrid();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entries, offerings, rooms, maxSlot]);

  async function handleGenerate() {
    setLoading(true);
    try {
      await fetch(`${API}/timetable/generate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      // refresh versions and notify user
      const vRes = await fetch(`${API}/timetable/versions`);
      const vRaw = vRes.ok ? await vRes.json() : [];
      const sorted = normalizeAndSortVersions(vRaw);
      setVersions(sorted);
      if (sorted.length) setSelectedVersion(sorted[sorted.length - 1].id);
      alert("Timetable generated");
    } catch (err) {
      console.error("Generate failed", err);
      alert("Failed to run solver. Check backend.");
    } finally {
      setLoading(false);
    }
  }

  async function loadEntries() {
    if (!selectedVersion) return;
    if (mode === "batch" && !selectedBatch) return;
    if (mode === "faculty" && !selectedFaculty) return;

    try {
      const url =
        mode === "batch"
          ? `${API}/timetable/batch/${selectedVersion}/${selectedBatch}`
          : `${API}/timetable/faculty/${selectedVersion}/${selectedFaculty}`;
      const res = await fetch(url);
      const data = res.ok ? await res.json() : [];
      // data should be array of TimetableEntry objects with day and slot fields
      setEntries(data || []);

      // update maxSlot from returned entries if larger
      const smax = (data || []).reduce((mx, e) => Math.max(mx, e.slot || 0), 0);
      if (smax > 0) setMaxSlot((m) => Math.max(m, smax));
    } catch (err) {
      console.error("Failed to load entries:", err);
    }
  }

  useEffect(() => {
    loadEntries();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedVersion, selectedBatch, selectedFaculty, mode]);

  function buildGrid() {
    // grid: days (0..6) x slots (1..maxSlot) -> cell text
    const days = 7; // always show Mon..Sun; you can change to 6 for Mon..Sat
    const g = makeEmptyGrid(days, maxSlot);

    // Each entry expected:
    // { subject_offering_id, room_id, day, slot, faculty_id, ... }
    for (const e of entries) {
      const d = Number(e.day ?? 0);
      const s = Number(e.slot ?? 1);

      // resolve subject code from offering -> offerings endpoint should have subject_code
      let subjCode = "";
      if (e.subject_offering_id) {
        const off =
          offeringById[e.subject_offering_id] ||
          offerings.find((o) => String(o.id) === String(e.subject_offering_id));
        if (off) subjCode = off.subject_code || off.subject_code?.toString() || "";
      }

      // resolve room code
      const room =
        roomById[String(e.room_id)] || rooms.find((r) => String(r.id) === String(e.room_id));
      const roomCode = room ? room.code || room.room_no || room.id : e.room_id || "";

      const text = subjCode ? `${subjCode}/${roomCode}` : `${roomCode}`;

      // place into grid; if multiple entries collide, join with comma (shouldn't happen)
      if (!g[d]) g[d] = {};
      if (!g[d][s]) g[d][s] = text;
      else if (g[d][s] === "") g[d][s] = text;
      else g[d][s] = `${g[d][s]}, ${text}`; // fallback
    }

    setGrid(g);
  }

  // Render helpers
  const slotHeaders = Array.from({ length: maxSlot }, (_, i) => i + 1);

  return (
    <div>
      <div className="page-title">Timetable</div>
      <div className="page-subtitle">Generate and inspect schedules</div>

      <div className="card-row" style={{ marginTop: 16 }}>
        <div className="card" style={{ flex: 1 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div>
              <div style={{ fontWeight: 500 }}>Generate Timetable</div>
              <div style={{ fontSize: 12, color: "#9ca3af" }}>
                Runs the solver on current data and stores a new version.
              </div>
            </div>
            <button className="button-primary" onClick={handleGenerate} disabled={loading}>
              {loading ? "Generating..." : "Run Solver"}
            </button>
          </div>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <div style={{ fontWeight: 500 }}>Select Version & View Mode</div>
          <div className="form-row">
            <label>
              Version
              <select
                className="select"
                value={selectedVersion}
                onChange={(e) => setSelectedVersion(e.target.value)}
              >
                <option value="">Select version</option>
                {versions.map((v, idx) => (
                  <option key={v.id} value={v.id}>
                    {`Version ${idx + 1}`}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Mode
              <select
                className="select"
                value={mode}
                onChange={(e) => setMode(e.target.value)}
              >
                <option value="batch">By Batch</option>
                <option value="faculty">By Faculty</option>
              </select>
            </label>

            {mode === "batch" ? (
              <label>
                Batch
                <select
                  className="select"
                  value={selectedBatch}
                  onChange={(e) => setSelectedBatch(e.target.value)}
                >
                  <option value="">Select batch</option>
                  {batches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name}
                    </option>
                  ))}
                </select>
              </label>
            ) : (
              <label>
                Faculty
                <select
                  className="select"
                  value={selectedFaculty}
                  onChange={(e) => setSelectedFaculty(e.target.value)}
                >
                  <option value="">Select faculty</option>
                  {faculty.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div style={{ fontWeight: 500, marginBottom: 8 }}>Timetable Grid</div>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead>
              <tr>
                <th style={{ textAlign: "left", padding: 6, minWidth: 120 }}>Day</th>
                {slotHeaders.map((s) => (
                  <th
                    key={s}
                    style={{
                      textAlign: "center",
                      padding: 6,
                      minWidth: "11ch", // make slot wide enough for ~11 chars
                      whiteSpace: "nowrap",
                    }}
                  >
                    Slot {s}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 6 }, (_, d) => d).map((dayIdx) => {
                const dayName = DAY_NAMES[dayIdx] || `Day ${dayIdx}`;
                return (
                  <tr key={dayIdx}>
                    <td style={{ padding: 6, color: "#e5e7eb", width: 140 }}>{dayName}</td>
                    {slotHeaders.map((s) => {
                      const val = grid && grid[dayIdx] ? grid[dayIdx][s] || "" : "";
                      return (
                        <td
                          key={s}
                          style={{
                            padding: "10px 6px",
                            borderTop: "1px solid #111827",
                            textAlign: "center",
                            color: "#9ca3af",
                            minWidth: "11ch",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            fontFamily: "monospace",
                          }}
                          title={val}
                        >
                          {val}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {(!entries || entries.length === 0) && (
          <div style={{ marginTop: 12, fontSize: 12, color: "#6b7280" }}>
            No entries loaded. Select a version and batch/faculty.
          </div>
        )}
      </div>
    </div>
  );
}
