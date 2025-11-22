// src/pages/Subjects.jsx
import { useEffect, useState } from "react";
const API = "http://localhost:8000/api";

export default function SubjectsPage() {
  const [subjects, setSubjects] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [form, setForm] = useState({
    code: "",
    name: "",
    department_id: "",
    type: "theory",
    classes_per_week: 3,
  });

  async function load() {
    const [sRes, dRes] = await Promise.all([
      fetch(`${API}/subjects`),
      fetch(`${API}/departments`),
    ]);
    setSubjects(await sRes.json());
    setDepartments(await dRes.json());
  }

  useEffect(() => {
    load();
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    await fetch(`${API}/subjects`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, classes_per_week: Number(form.classes_per_week) }),
    });
    setForm({ code: "", name: "", department_id: "", type: "theory", classes_per_week: 3 });
    load();
  }

  return (
    <div>
      <div className="page-title">Subjects</div>
      <div className="page-subtitle">Define subjects per department</div>

      <div className="card" style={{ marginTop: 16 }}>
        <form onSubmit={handleSubmit}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontWeight: 500 }}>Add Subject</div>
            <button className="button-primary">+ Add Subject</button>
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
            <label style={{ flex: 1 }}>
              Name
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
              Classes / week
              <input
                className="input"
                type="number"
                value={form.classes_per_week}
                onChange={(e) => setForm((f) => ({ ...f, classes_per_week: e.target.value }))}
              />
            </label>
          </div>
        </form>
      </div>

      <div className="card list" style={{ marginTop: 16 }}>
        {subjects.map((s) => (
          <div key={s.code} className="list-row">
            <div>
              <div style={{ fontWeight: 500 }}>{s.code} – {s.name}</div>
              <div style={{ fontSize: 12, color: "#9ca3af" }}>
                {s.type.toUpperCase()} • {s.classes_per_week} / week
              </div>
            </div>
          </div>
        ))}
        {subjects.length === 0 && (
          <div className="list-row" style={{ justifyContent: "center", color: "#6b7280" }}>
            No subjects yet.
          </div>
        )}
      </div>
    </div>
  );
}
