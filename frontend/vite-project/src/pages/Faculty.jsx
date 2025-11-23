// src/pages/Faculty.jsx
import { useEffect, useState } from "react";

const API = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000/api";

export default function FacultyPage() {
  const [stats, setStats] = useState({ total: 0, active: 0, on_leave: 0, avg_hours: 0 });
  const [faculty, setFaculty] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [filterDept, setFilterDept] = useState("all");
  const [form, setForm] = useState({
    name: "",
    department_id: "",
    max_classes_per_day: 4,
  });
  const [loading, setLoading] = useState(false);

  async function loadData() {
    const [statsRes, facultyRes, deptRes] = await Promise.all([
      fetch(`${API}/faculty/stats`),
      fetch(`${API}/faculty`),
      fetch(`${API}/departments`),
    ]);
    setStats(await statsRes.json());
    setFaculty(await facultyRes.json());
    setDepartments(await deptRes.json());
  }

  useEffect(() => {
    loadData();
  }, []);

  const filtered = faculty.filter((f) => filterDept === "all" || f.department_id === filterDept);

  async function handleAddFaculty(e) {
    e.preventDefault();
    if (!form.name || !form.department_id) return;
    setLoading(true);
    await fetch(`${API}/faculty`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...form, active: true }),
    });
    setLoading(false);
    setForm({ name: "", department_id: "", max_classes_per_day: 4 });
    loadData();
  }

  return (
    <div>
      <div className="page-title">Faculty Management</div>
      <div className="page-subtitle">Manage faculty members, workload, and schedules</div>

      <div className="card-row">
        <div className="card card-metric">
          <div className="card-metric-label">Total Faculty</div>
          <div className="card-metric-value">{stats.total}</div>
          <div className="card-metric-tag">All departments</div>
        </div>
        <div className="card card-metric">
          <div className="card-metric-label">Active</div>
          <div className="card-metric-value">{stats.active}</div>
        </div>
        <div className="card card-metric">
          <div className="card-metric-label">On Leave</div>
          <div className="card-metric-value">{stats.on_leave}</div>
        </div>
        <div className="card card-metric">
          <div className="card-metric-label">Avg Hours / Week</div>
          <div className="card-metric-value">{stats.avg_hours.toFixed(1)}</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <form onSubmit={handleAddFaculty}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontWeight: 500 }}>Add Faculty</div>
            <button className="button-primary" disabled={loading}>
              {loading ? "Saving..." : "+ Add Faculty"}
            </button>
          </div>
          <div className="form-row">
            <label>
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
              Max classes / day
              <input
                className="input"
                type="number"
                min={1}
                max={8}
                value={form.max_classes_per_day}
                onChange={(e) => setForm((f) => ({ ...f, max_classes_per_day: Number(e.target.value) }))}
              />
            </label>
          </div>
        </form>
      </div>

      <div className="card-row" style={{ marginTop: 16, alignItems: "flex-start" }}>
        <div className="card" style={{ flex: 2 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
            <div style={{ fontWeight: 500 }}>Faculty Members</div>
            <select
              className="select"
              value={filterDept}
              onChange={(e) => setFilterDept(e.target.value)}
            >
              <option value="all">All Departments</option>
              {departments.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name}
                </option>
              ))}
            </select>
          </div>

          <div className="list">
            {filtered.map((f) => {
              const initials = f.name
                .split(" ")
                .filter(Boolean)
                .map((p) => p[0].toUpperCase())
                .slice(0, 3)
                .join("");
              return (
                <div key={f.id} className="list-row">
                  <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                    <div
                      style={{
                        width: 36,
                        height: 36,
                        borderRadius: 999,
                        background: "#0f766e",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontSize: 12,
                        fontWeight: 600,
                      }}
                    >
                      {initials}
                    </div>
                    <div>
                      <div style={{ fontWeight: 500 }}>{f.name}</div>
                      <div style={{ fontSize: 12, color: "#9ca3af" }}>
                        {departments.find((d) => d.id === f.department_id)?.name || "—"}
                      </div>
                    </div>
                  </div>
                  <div style={{ fontSize: 12, textAlign: "right" }}>
                    <div className="badge">Max {f.max_classes_per_day} / day</div>
                  </div>
                </div>
              );
            })}
            {filtered.length === 0 && (
              <div className="list-row" style={{ justifyContent: "center", color: "#6b7280" }}>
                No faculty yet. Add someone above.
              </div>
            )}
          </div>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <div style={{ fontWeight: 500, marginBottom: 8 }}>Weekly Workload (simple)</div>
          <div style={{ fontSize: 12, color: "#9ca3af" }}>
            This can be enhanced later using timetable entries.
          </div>
        </div>
      </div>
    </div>
  );
}
