// src/pages/Optimize.jsx
import { useEffect, useState } from "react";

const API = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000/api";

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

function normalizeAndSortVersions(raw) {
  if (!raw) return [];
  if (!Array.isArray(raw)) {
    if (raw.data && Array.isArray(raw.data)) raw = raw.data;
    else if (raw.results && Array.isArray(raw.results)) raw = raw.results;
    else return [];
  }
  const copy = raw.slice();
  copy.sort((a, b) => {
    const da = a?.created_at ? new Date(a.created_at).getTime() : 0;
    const db = b?.created_at ? new Date(b.created_at).getTime() : 0;
    return da - db;
  });
  return copy;
}

export default function OptimizePage() {
  const [versions, setVersions] = useState([]); // sorted oldest->newest
  const [selectedVersion, setSelectedVersion] = useState("");
  const [promptText, setPromptText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [newVersion, setNewVersion] = useState(null);
  const [entries, setEntries] = useState([]);
  const [timeslots, setTimeslots] = useState([]);
  const [rooms, setRooms] = useState({});
  const [offerings, setOfferings] = useState({});

  // Load existing timetable versions
  async function loadVersions() {
    try {
      const res = await fetch(`${API}/timetable/versions`);
      const raw = res.ok ? await res.json() : [];
      const sorted = normalizeAndSortVersions(raw);
      setVersions(sorted);
      if (sorted.length) {
        // default to latest (last element)
        setSelectedVersion((prev) => prev || sorted[sorted.length - 1].id);
      } else {
        setSelectedVersion("");
      }
    } catch (err) {
      console.error("Failed to load versions:", err);
      setVersions([]);
      setSelectedVersion("");
    }
  }

  // Load lookup data needed for timetable grid
  async function loadLookups() {
    try {
      const [tsRes, offRes, roomRes] = await Promise.all([
        fetch(`${API}/timeslots`),
        fetch(`${API}/subject-offerings`),
        fetch(`${API}/rooms`)
      ]);

      const ts = tsRes.ok ? await tsRes.json() : [];
      const off = offRes.ok ? await offRes.json() : [];
      const rm = roomRes.ok ? await roomRes.json() : [];

      setTimeslots(Array.isArray(ts) ? ts : []);
      const rmap = {};
      (Array.isArray(rm) ? rm : []).forEach(r => {
        if (r && (r.id !== undefined)) rmap[r.id] = r;
      });
      setRooms(rmap);

      const offmap = {};
      (Array.isArray(off) ? off : []).forEach(o => {
        if (o && (o.id !== undefined)) offmap[o.id] = o;
      });
      setOfferings(offmap);
    } catch (err) {
      console.error("Failed to load lookups:", err);
      setTimeslots([]);
      setRooms({});
      setOfferings({});
    }
  }

  async function loadVersionEntries(versionId) {
    if (!versionId) return setEntries([]);
    try {
      const res = await fetch(`${API}/timetable/version/${versionId}`);
      if (!res.ok) {
        setEntries([]);
        return;
      }
      const data = await res.json();
      setEntries(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load version entries:", err);
      setEntries([]);
    }
  }

  useEffect(() => {
    loadVersions();
    loadLookups();
  }, []);

  // Whenever the selected version changes, load its entries
  useEffect(() => {
    if (selectedVersion) {
      loadVersionEntries(selectedVersion);
    } else {
      setEntries([]);
    }
  }, [selectedVersion]);

  // Also when a new version is created by optimize(), load it
  useEffect(() => {
    if (newVersion) {
      // reload versions and select the new one after refresh
      (async () => {
        await loadVersions();
        setSelectedVersion(newVersion);
        await loadVersionEntries(newVersion);
      })();
    }
  }, [newVersion]);

  // Run optimization
  async function optimize() {
    if (!promptText.trim()) {
      alert("Please enter an optimization prompt.");
      return;
    }

    setLoading(true);
    setError("");
    setNewVersion(null);
    setEntries([]);

    try {
      const res = await fetch(`${API}/timetable/optimize`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          version_id: selectedVersion,
          goals: [promptText.trim()]
        })
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(text);
      }

      const data = await res.json();
      // backend returns { new_version_id: "..." }
      const newId = data?.new_version_id || null;
      setNewVersion(newId);
    } 
    catch (err) {
      console.error(err);
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }

  // Build table
  const maxSlot = Math.max(...(timeslots || []).map(t => t.slot || 0), 8);
  const slots = Array.from({ length: maxSlot }, (_, i) => i + 1);

  const byDaySlot = {};
  (entries || []).forEach(e => {
    const key = `${e.day}-${e.slot}`;
    const off = offerings[e.subject_offering_id];
    const subjCode = off ? off.subject_code : "SUB";
    const roomCode = rooms[e.room_id] ? rooms[e.room_id].code : e.room_id;

    const text = `${subjCode}/${roomCode}`;
    if (!byDaySlot[key]) byDaySlot[key] = [];
    byDaySlot[key].push(text);
  });

  return (
    <div>
      <div className="page-title">LLM Timetable Optimization</div>
      <div className="page-subtitle">
        Select a timetable version → Enter an optimization prompt → View optimized timetable.
      </div>

      {/* ---- Card: Select version ---- */}
      <div className="card" style={{ marginTop: 20 }}>
        <div style={{ fontSize: 18, fontWeight: 500 }}>Select Timetable Version</div>

        <select
          className="select"
          value={selectedVersion}
          onChange={(e) => setSelectedVersion(e.target.value)}
          style={{ marginTop: 12, width: "100%" }}
        >
          <option value="">Select version</option>
          {versions.map((v, idx) => (
            <option key={v.id} value={v.id}>
              {`Version ${idx + 1}`}
            </option>
          ))}
        </select>
      </div>

      {/* ---- Card: Optimization prompt ---- */}
      <div className="card" style={{ marginTop: 20 }}>
        <div style={{ fontSize: 18, fontWeight: 500 }}>Optimization Prompt</div>
        <div style={{ color: "#9ca3af", fontSize: 13, marginTop: 6 }}>
          Example: "Reduce load on batch 1", "Balance faculty schedule", "Avoid last slot".
        </div>

        <textarea
          className="input"
          style={{ marginTop: 12, width: "100%", minHeight: 70 }}
          placeholder="Describe what you want the AI to improve..."
          value={promptText}
          onChange={(e) => setPromptText(e.target.value)}
        />

        <button
          className="button-primary"
          style={{ marginTop: 12, width: 150 }}
          onClick={optimize}
          disabled={loading}
        >
          {loading ? "Optimizing..." : "Optimize"}
        </button>

        {error && (
          <div style={{ color: "#f87171", marginTop: 12 }}>
            <b>Error:</b> {error}
          </div>
        )}
      </div>

      {/* ---- Optimized version ---- */}
      {newVersion && (
        <div className="card" style={{ marginTop: 20 }}>
          <div style={{ fontSize: 18, fontWeight: 500 }}>Optimized Version Created</div>
          <div style={{ marginTop: 8 }}>
            New version ID: <b>{newVersion}</b>
          </div>
        </div>
      )}

      {/* ---- Show optimized timetable ---- */}
      {entries.length > 0 && (
        <div className="card" style={{ marginTop: 20 }}>
          <div style={{ fontSize: 18, fontWeight: 500, marginBottom: 8 }}>
            Optimized Timetable
          </div>

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr>
                  <th style={{ textAlign: "left", padding: 8 }}>Day</th>
                  {slots.map(s => (
                    <th
                      key={s}
                      style={{ textAlign: "center", padding: 8, minWidth: "11ch" }}
                    >
                      Slot {s}
                    </th>
                  ))}
                </tr>
              </thead>

              <tbody>
                {DAY_NAMES.map((day, dIdx) => (
                  <tr key={dIdx}>
                    <td style={{ padding: 8, color: "#e5e7eb" }}>{day}</td>
                    {slots.map(slot => {
                      const key = `${dIdx}-${slot}`;
                      const arr = byDaySlot[key] || [];
                      const txt = arr.join(", ");

                      return (
                        <td
                          key={slot}
                          style={{
                            borderTop: "1px solid #111827",
                            padding: 8,
                            textAlign: "center",
                            whiteSpace: "nowrap",
                            overflow: "hidden",
                            textOverflow: "ellipsis",
                            minWidth: "11ch"
                          }}
                          title={txt}
                        >
                          {txt}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
