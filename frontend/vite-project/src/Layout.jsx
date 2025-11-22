import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useEffect } from "react";

export default function Layout() {
  const navigate = useNavigate();

  // protect routes
  useEffect(() => {
    if (!localStorage.getItem("logged_in")) {
      navigate("/");
    }
  }, []);

  return (
    <div className="app-shell">

      {/* Sidebar */}
      <div className="sidebar">
        
        <nav className="sidebar-nav">
          <NavLink to="/dashboard" className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}>Dashboard</NavLink>
          <NavLink to="/timetable" className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}>Timetable</NavLink>
          <NavLink to="/faculty" className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}>Faculty</NavLink>
          <NavLink to="/classrooms" className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}>Classrooms</NavLink>
          <NavLink to="/students" className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}>Students</NavLink>
          <NavLink to="/subjects" className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}>Subjects</NavLink>
          <NavLink to="/offerings" className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}>Offerings</NavLink>
          <NavLink to="/departments" className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}>Departments</NavLink>
          <NavLink to="/timeslots" className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}>Timeslots</NavLink>
          <NavLink to="/optimize" className={({ isActive }) => "sidebar-link" + (isActive ? " active" : "")}>Optimize</NavLink>
        </nav>

        <div className="User" style={{ fontSize: 15, marginTop: "auto", textAlign: "center" }}>
          Admin User
        </div>
      </div>

      {/* Main Area */}
      <main className="main">
        <header className="topbar">
          <div style={{ fontSize: 23, color: "var(--accent)", textAlign: "center" }}>
            Smart Classroom & Timetable Scheduler
          </div>
          <div style={{ fontSize: 12, color: "#9ca3af" }}>
            {new Date().toLocaleString()}
          </div>
        </header>

        {/* Route outlet */}
        <div className="content">
          <Outlet />
        </div>
      </main>

    </div>
  );
}
