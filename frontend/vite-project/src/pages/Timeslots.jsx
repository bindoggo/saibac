// src/pages/Timeslots.jsx
import { useEffect, useState } from "react";
const API = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000/api";

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

export default function TimeslotsPage() {
  const [timeslots, setTimeslots] = useState([]);
  const [form, setForm] = useState({
    day: 0,
    slot: 1,
    start_time: "",
    end_time: "",
  });

  async function load() {
    const res = await fetch(`${API}/timeslots`);
    setTimeslots(await res.json());
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    await fetch(`${API}/timeslots`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...form,
        day: Number(form.day),
        slot: Number(form.slot),
      }),
    });
    setForm({ day: 0, slot: 1, start_time: "", end_time: "" });
    load();
  }

  return (
    <div>
      <div className="page-title">Timeslots</div>
      <div className="page-subtitle">Define period grid used by the scheduler</div>

      <div className="card" style={{ marginTop: 16 }}>
        <form onSubmit={handleSubmit}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontWeight: 500 }}>Add Timeslot</div>
            <button className="button-primary">+ Add</button>
          </div>
          <div className="form-row">
            <label>
              Day
              <select
                className="select"
                value={form.day}
                onChange={(e) => setForm((f) => ({ ...f, day: e.target.value }))}
              >
                {DAY_NAMES.map((n, idx) => (
                  <option key={idx} value={idx}>
                    {n}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Slot #
              <input
                className="input"
                type="number"
                min={1}
                value={form.slot}
                onChange={(e) => setForm((f) => ({ ...f, slot: e.target.value }))}
              />
            </label>
            <label>
              Start time
              <input
                className="input"
                placeholder="09:00"
                value={form.start_time}
                onChange={(e) => setForm((f) => ({ ...f, start_time: e.target.value }))}
              />
            </label>
            <label>
              End time
              <input
                className="input"
                placeholder="10:00"
                value={form.end_time}
                onChange={(e) => setForm((f) => ({ ...f, end_time: e.target.value }))}
              />
            </label>
          </div>
        </form>
      </div>

      <div className="card list" style={{ marginTop: 16 }}>
        {timeslots
          .sort((a, b) => (a.day - b.day) || (a.slot - b.slot))
          .map((ts) => (
            <div key={ts.id} className="list-row">
              <div>
                <div style={{ fontWeight: 500 }}>
                  {DAY_NAMES[ts.day]} – Slot {ts.slot}
                </div>
                <div style={{ fontSize: 12, color: "#9ca3af" }}>
                  {ts.start_time || "?"} – {ts.end_time || "?"}
                </div>
              </div>
            </div>
          ))}
        {timeslots.length === 0 && (
          <div className="list-row" style={{ justifyContent: "center", color: "#6b7280" }}>
            No timeslots defined.
          </div>
        )}
      </div>
    </div>
  );
}
