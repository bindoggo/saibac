// src/pages/Dashboard.jsx
import { useEffect, useState } from "react";

const API = "https://saibac.onrender.com/api";

export default function Dashboard() {
  const [facultyStats, setFacultyStats] = useState({
    total: 0,
    active: 0,
    on_leave: 0,
    avg_hours: 0,
  });

  const [roomCount, setRoomCount] = useState(0);
  const [batchCount, setBatchCount] = useState(0);
  const [subjectCount, setSubjectCount] = useState(0);

  async function load() {
    try {
      const [facRes, roomRes, batchRes, subjRes] = await Promise.all([
        fetch(`${API}/faculty/stats`),
        fetch(`${API}/rooms`),
        fetch(`${API}/batches`),
        fetch(`${API}/subjects`),
      ]);

      setFacultyStats(await facRes.json());
      setRoomCount((await roomRes.json()).length);
      setBatchCount((await batchRes.json()).length);
      setSubjectCount((await subjRes.json()).length);
    } catch (err) {
      console.error("Dashboard load failed:", err);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <div>
      <div className="page-title">Dashboard</div>
      <div className="page-subtitle">Overview of Smart Classroom System</div>

      <div className="card-row" style={{ marginTop: 20 }}>
        <div className="card card-metric">
          <div className="card-metric-label">Total Faculty</div>
          <div className="card-metric-value">{facultyStats.total}</div>
        </div>

        <div className="card card-metric">
          <div className="card-metric-label">Active Faculty</div>
          <div className="card-metric-value">{facultyStats.active}</div>
        </div>

        <div className="card card-metric">
          <div className="card-metric-label">Classrooms</div>
          <div className="card-metric-value">{roomCount}</div>
        </div>

        <div className="card card-metric">
          <div className="card-metric-label">Batches</div>
          <div className="card-metric-value">{batchCount}</div>
        </div>

        <div className="card card-metric">
          <div className="card-metric-label">Subjects</div>
          <div className="card-metric-value">{subjectCount}</div>
        </div>
      </div>

      <div className="card" style={{ marginTop: 20 }}>
        <div style={{ fontWeight: 500 }}>Welcome to SmartClass Scheduler</div>
        <div style={{ marginTop: 10, color: "#9ca3af", fontSize: 14 }}>
          Use the sidebar to manage faculty, students, classrooms, subjects,
          offerings, and generate timetables.
        </div>
      </div>
    </div>
  );
}
