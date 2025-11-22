// src/pages/Students.jsx
import { useEffect, useState } from "react";
const API = "http://localhost:8000/api";

export default function StudentsPage() {
  const [batches, setBatches] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [form, setForm] = useState({
    name: "",
    department_id: "",
    semester: 3,
    shift: "day",
    size: "",
  });

  async function load() {
    const [bRes, dRes] = await Promise.all([
      fetch(`${API}/batches`),
      fetch(`${API}/departments`),
    ]);
    setBatches(await bRes.json());
    setDepartments(await dRes.json());
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    await fetch(`${API}/batches`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, size: Number(form.size), semester: Number(form.semester) }),
    });
    setForm({ name: "", department_id: "", semester: 3, shift: "day", size: "" });
    load();
  }

  return (
    <div>
      <div className="page-title">Student Batches</div>
      <div className="page-subtitle">Manage sections and batch sizes</div>

      <div className="card" style={{ marginTop: 16 }}>
        <form onSubmit={handleSubmit}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontWeight: 500 }}>Add Batch</div>
            <button className="button-primary">+ Add Batch</button>
          </div>
          <div className="form-row">
            <label>
              Batch Name
              <input
                className="input"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </label>
            <label>
              Department
              <select
                className="select"
                value={form.department_id}
                onChange={(e) => setForm((f) => ({ ...f, department_id: e.target.value }))}
              >
                <option value="">Select department</option>
                {departments.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Semester
              <input
                className="input"
                type="number"
                value={form.semester}
                onChange={(e) => setForm((f) => ({ ...f, semester: e.target.value }))}
              />
            </label>
            <label>
              Shift
              <select
                className="select"
                value={form.shift}
                onChange={(e) => setForm((f) => ({ ...f, shift: e.target.value }))}
              >
                <option value="day">Day</option>
                <option value="evening">Evening</option>
              </select>
            </label>
            <label>
              Size
              <input
                className="input"
                type="number"
                value={form.size}
                onChange={(e) => setForm((f) => ({ ...f, size: e.target.value }))}
              />
            </label>
          </div>
        </form>
      </div>

      <div className="card list" style={{ marginTop: 16 }}>
        {batches.map((b) => (
          <div key={b.id} className="list-row">
            <div>
              <div style={{ fontWeight: 500 }}>{b.name}</div>
              <div style={{ fontSize: 12, color: "#9ca3af" }}>
                Semester {b.semester} • {b.shift.toUpperCase()}
              </div>
            </div>
            <div style={{ fontSize: 12 }}>
              <div className="badge">{b.size} students</div>
            </div>
          </div>
        ))}
        {batches.length === 0 && (
          <div className="list-row" style={{ justifyContent: "center", color: "#6b7280" }}>
            No batches defined.
          </div>
        )}
      </div>
    </div>
  );
}
