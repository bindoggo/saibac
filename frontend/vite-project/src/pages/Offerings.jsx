// src/pages/Offerings.jsx
import { useEffect, useState } from "react";
const API = "https://saibac.onrender.com/api";

export default function OfferingsPage() {
  const [batches, setBatches] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [offerings, setOfferings] = useState([]);
  const [faculty, setFaculty] = useState([]);
  const [assignments, setAssignments] = useState([]);

  const [offForm, setOffForm] = useState({
    subject_code: "",
    batch_id: "",
    semester: "",
    elective: false,
  });

  const [assignForm, setAssignForm] = useState({
    subject_offering_id: "",
    faculty_id: "",
  });

  async function load() {
    const [bRes, sRes, oRes, fRes, aRes] = await Promise.all([
      fetch(`${API}/batches`),
      fetch(`${API}/subjects`),
      fetch(`${API}/subject-offerings`),
      fetch(`${API}/faculty`),
      fetch(`${API}/faculty-assignments`),
    ]);
    setBatches(await bRes.json());
    setSubjects(await sRes.json());
    const offs = await oRes.json();
    setOfferings(offs);
    setFaculty(await fRes.json());
    setAssignments(await aRes.json());
    if (offs.length && !assignForm.subject_offering_id) {
      setAssignForm((f) => ({ ...f, subject_offering_id: offs[0].id }));
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleAddOffering(e) {
    e.preventDefault();
    await fetch(`${API}/subject-offerings`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...offForm, semester: Number(offForm.semester) }),
    });
    setOffForm({ subject_code: "", batch_id: "", semester: "", elective: false });
    load();
  }

  async function handleAddAssignment(e) {
    e.preventDefault();
    await fetch(`${API}/faculty-assignments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(assignForm),
    });
    load();
  }

  return (
    <div>
      <div className="page-title">Offerings & Faculty Assignments</div>
      <div className="page-subtitle">Which batch studies which subject, taught by whom</div>

      <div className="card-row" style={{ marginTop: 16, alignItems: "flex-start" }}>
        <div className="card" style={{ flex: 1 }}>
          <form onSubmit={handleAddOffering}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 500 }}>Add Subject Offering</div>
              <button className="button-primary">+ Add Offering</button>
            </div>
            <div className="form-row">
              <label>
                Subject
                <select
                  className="select"
                  value={offForm.subject_code}
                  onChange={(e) => setOffForm((f) => ({ ...f, subject_code: e.target.value }))}
                >
                  <option value="">Select subject</option>
                  {subjects.map((s) => (
                    <option key={s.code} value={s.code}>
                      {s.code} – {s.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Batch
                <select
                  className="select"
                  value={offForm.batch_id}
                  onChange={(e) => setOffForm((f) => ({ ...f, batch_id: e.target.value }))}
                >
                  <option value="">Select batch</option>
                  {batches.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Semester
                <input
                  className="input"
                  type="number"
                  value={offForm.semester}
                  onChange={(e) => setOffForm((f) => ({ ...f, semester: e.target.value }))}
                />
              </label>
              <label>
                Elective?
                <select
                  className="select"
                  value={String(offForm.elective)}
                  onChange={(e) => setOffForm((f) => ({ ...f, elective: e.target.value === "true" }))}
                >
                  <option value="false">No</option>
                  <option value="true">Yes</option>
                </select>
              </label>
            </div>
          </form>
        </div>

        <div className="card" style={{ flex: 1 }}>
          <form onSubmit={handleAddAssignment}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div style={{ fontWeight: 500 }}>Assign Faculty</div>
              <button className="button-primary">+ Assign</button>
            </div>
            <div className="form-row">
              <label>
                Offering
                <select
                  className="select"
                  value={assignForm.subject_offering_id}
                  onChange={(e) => setAssignForm((f) => ({ ...f, subject_offering_id: e.target.value }))}
                >
                  <option value="">Select offering</option>
                  {offerings.map((o) => {
                    const subj = subjects.find((s) => s.code === o.subject_code);
                    const batch = batches.find((b) => b.id === o.batch_id);
                    return (
                      <option key={o.id} value={o.id}>
                        {subj?.code} – {batch?.name}
                      </option>
                    );
                  })}
                </select>
              </label>
              <label>
                Faculty
                <select
                  className="select"
                  value={assignForm.faculty_id}
                  onChange={(e) => setAssignForm((f) => ({ ...f, faculty_id: e.target.value }))}
                >
                  <option value="">Select faculty</option>
                  {faculty.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </form>
        </div>
      </div>

      <div className="card list" style={{ marginTop: 16 }}>
        {offerings.map((o) => {
          const subj = subjects.find((s) => s.code === o.subject_code);
          const batch = batches.find((b) => b.id === o.batch_id);
          const assigned = assignments.filter((a) => a.subject_offering_id === o.id);
          return (
            <div key={o.id} className="list-row">
              <div>
                <div style={{ fontWeight: 500 }}>
                  {subj?.code} – {subj?.name}
                </div>
                <div style={{ fontSize: 12, color: "#9ca3af" }}>
                  Batch {batch?.name} • Sem {o.semester} • {o.elective ? "Elective" : "Core"}
                </div>
              </div>
              <div style={{ fontSize: 12, textAlign: "right" }}>
                {assigned.length === 0 && <div className="badge">No faculty assigned</div>}
                {assigned.map((a) => {
                  const f = faculty.find((ff) => ff.id === a.faculty_id);
                  return <div key={a.id} className="badge">{f?.name || "Unknown"}</div>;
                })}
              </div>
            </div>
          );
        })}
        {offerings.length === 0 && (
          <div className="list-row" style={{ justifyContent: "center", color: "#6b7280" }}>
            No offerings yet.
          </div>
        )}
      </div>
    </div>
  );
}
