// src/pages/Departments.jsx
import { useEffect, useState } from "react";
const API = process.env.REACT_APP_API_BASE_URL || "http://localhost:8000/api";

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState([]);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);

  async function load() {
    try {
      const res = await fetch(`${API}/departments`);
      const data = await res.json();
      setDepartments(data || []);
    } catch (err) {
      console.error("Failed to load departments", err);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleAdd(e) {
    e.preventDefault();
    if (!code.trim() || !name.trim()) {
      alert("Both code and name are required");
      return;
    }
    setLoading(true);
    try {
      await fetch(`${API}/departments`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: code.trim(), name: name.trim() }),
      });
      setCode("");
      setName("");
      await load();
    } catch (err) {
      console.error("Failed to create department", err);
      alert("Failed to create department. Check console.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="page-title">Departments</div>
      <div className="page-subtitle">Create and manage departments</div>

      <div className="card" style={{ marginTop: 16 }}>
        <form onSubmit={handleAdd}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <div style={{ fontWeight: 500 }}>Add Department</div>
            <button className="button-primary" disabled={loading}>
              {loading ? "Saving..." : "+ Add"}
            </button>
          </div>

          <div className="form-row" style={{ marginTop: 12 }}>
            <label style={{ minWidth: 180 }}>
              Code (short)
              <input
                className="input"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="e.g. CSE"
              />
            </label>

            <label style={{ flex: 1 }}>
              Full Name
              <input
                className="input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Computer Science & Engineering"
              />
            </label>
          </div>
        </form>
      </div>

      <div className="card list" style={{ marginTop: 16 }}>
        {departments.length === 0 ? (
          <div className="list-row" style={{ justifyContent: "center", color: "#6b7280" }}>
            No departments yet.
          </div>
        ) : (
          departments.map((d) => (
            <div key={d.code ?? d.id} className="list-row">
              <div>
                <div style={{ fontWeight: 500 }}>{d.code} — {d.name}</div>
                <div style={{ fontSize: 12, color: "#9ca3af" }}>{d.id}</div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
