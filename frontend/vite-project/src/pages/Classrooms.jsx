// src/pages/Classrooms.jsx
import { useEffect, useState } from "react";
const API = "https://saibac.onrender.com/api";
export default function ClassroomsPage() {
  const [rooms, setRooms] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [form, setForm] = useState({
    code: "",
    capacity: "",
    type: "theory",
    location: "",
    department_id: "",
  });

  async function load() {
    const [rRes, dRes] = await Promise.all([
      fetch(`${API}/rooms`),
      fetch(`${API}/departments`),
    ]);
    setRooms(await rRes.json());
    setDepartments(await dRes.json());
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    await fetch(`${API}/rooms`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        ...form,
        capacity: Number(form.capacity),
      }),
    });
    setForm({ code: "", capacity: "", type: "theory", location: "", department_id: "" });
    load();
  }

  return (
    <div>
      <div className="page-title">Classrooms</div>
      <div className="page-subtitle">Manage classrooms and labs</div>

      <div className="card" style={{ marginTop: 16 }}>
        <form onSubmit={handleSubmit}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontWeight: 500 }}>Add Classroom</div>
            <button className="button-primary">+ Add</button>
          </div>
          <div className="form-row">
            <label>
              Code
              <input
                className="input"
                value={form.code}
                onChange={(e) => setForm((f) => ({ ...f, code: e.target.value }))}
              />
            </label>
            <label>
              Capacity
              <input
                className="input"
                type="number"
                value={form.capacity}
                onChange={(e) => setForm((f) => ({ ...f, capacity: e.target.value }))}
              />
            </label>
            <label>
              Type
              <select
                className="select"
                value={form.type}
                onChange={(e) => setForm((f) => ({ ...f, type: e.target.value }))}
              >
                <option value="theory">Theory</option>
                <option value="lab">Lab</option>
              </select>
            </label>
            <label>
              Department
              <select
                className="select"
                value={form.department_id}
                onChange={(e) => setForm((f) => ({ ...f, department_id: e.target.value }))}
              >
                <option value="">Shared / General</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </label>
            <label style={{ flex: 1 }}>
              Location
              <input
                className="input"
                value={form.location}
                onChange={(e) => setForm((f) => ({ ...f, location: e.target.value }))}
              />
            </label>
          </div>
        </form>
      </div>

      <div className="card list" style={{ marginTop: 16 }}>
        {rooms.map((r) => (
          <div key={r.id} className="list-row">
            <div>
              <div style={{ fontWeight: 500 }}>{r.code}</div>
              <div style={{ fontSize: 12, color: "#9ca3af" }}>
                {r.type?.toUpperCase()} • {r.location || "No location"}
              </div>
            </div>
            <div style={{ fontSize: 12 }}>
              <div className="badge">{r.capacity} seats</div>
            </div>
          </div>
        ))}
        {rooms.length === 0 && (
          <div className="list-row" style={{ justifyContent: "center", color: "#6b7280" }}>
            No classrooms yet.
          </div>
        )}
      </div>
    </div>
  );
}
