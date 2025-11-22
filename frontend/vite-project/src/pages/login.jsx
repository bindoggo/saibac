import React, { useState } from "react";
import { Shield, User, GraduationCap, ChevronRight, BookOpen } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const navigate = useNavigate();
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(false);

  const roles = [
    { id: "admin", title: "Administrator", desc: "Full system access and management", icon: Shield, color: "#0D7377" },
    { id: "faculty", title: "Faculty Member", desc: "Manage courses and view schedules", icon: User, color: "#14FFEC" },
    { id: "student", title: "Student", desc: "View timetables and manage preferences", icon: GraduationCap, color: "#8B5CF6" }
  ];

  function handleContinue() {
    if (!selected) return;

    setLoading(true);

    if (selected === "admin") {
      localStorage.setItem("logged_in", "yes");

      // apply theme for admin
      const el = document.getElementById("root");
      if (el) el.className = "root";

      setTimeout(() => {
        navigate("/dashboard");
        setLoading(false);
      }, 300);
    } else {
      setTimeout(() => setLoading(false), 300);
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(to bottom right, #141414, #1f1f1f, #0D7377)",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        padding: "20px",
      }}
    >
      <div style={{ width: "100%", maxWidth: "480px" }}>

        {/* Logo + App Name */}
        <div style={{ textAlign: "center", marginBottom: "40px" }}>
          <div
            style={{
              width: "70px",
              height: "70px",
              background: "#14FFEC",
              margin: "0 auto 20px",
              borderRadius: "20px",
              display: "flex",
              justifyContent: "center",
              alignItems: "center",
              boxShadow: "0 4px 20px rgba(20, 255, 236, 0.25)",
            }}
          >
            <BookOpen size={36} color="#111" />
          </div>

          <h1 style={{ fontSize: "34px", fontWeight: "bold", color: "white" }}>Smart AI</h1>
          <p style={{ color: "#CCCCCC", marginTop: "4px" }}>Classroom & Timetable Scheduler</p>
        </div>

        {/* Card */}
        <div
          style={{
            background: "#262626",
            borderRadius: "18px",
            border: "1px solid #444",
            boxShadow: "0 6px 30px rgba(0,0,0,0.4)",
            padding: "30px",
          }}
        >
          <h2 style={{ textAlign: "center", color: "white", fontSize: "20px", marginBottom: "20px" }}>
            Select Your Role
          </h2>

          {/* Role Buttons */}
          <div style={{ display: "flex", flexDirection: "column", gap: "15px", marginBottom: "20px" }}>
            {roles.map((r) => {
              const Icon = r.icon;
              const active = selected === r.id;

              return (
                <button
                  key={r.id}
                  onClick={() => setSelected(r.id)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    width: "100%",
                    padding: "16px",
                    borderRadius: "14px",
                    border: active ? "2px solid #14FFEC" : "2px solid #444",
                    background: active ? "rgba(20,255,236,0.08)" : "#1A1A1A",
                    transition: "0.2s",
                    cursor: "pointer",
                  }}
                >
                  <div
                    style={{
                      width: "48px",
                      height: "48px",
                      background: r.color,
                      borderRadius: "12px",
                      display: "flex",
                      justifyContent: "center",
                      alignItems: "center",
                    }}
                  >
                    <Icon size={26} color="white" />
                  </div>

                  <div style={{ flex: 1, marginLeft: "15px" }}>
                    <div style={{ color: "white", fontWeight: 600, marginBottom: "3px" }}>{r.title}</div>
                    <div style={{ color: "#BBBBBB", fontSize: "14px" }}>{r.desc}</div>
                  </div>

                  <ChevronRight size={20} color={active ? "#14FFEC" : "#666"} />
                </button>
              );
            })}
          </div>

          {/* Continue Button */}
          <button
            onClick={handleContinue}
            disabled={!selected || loading}
            style={{
              width: "100%",
              padding: "14px",
              borderRadius: "12px",
              background: selected ? "#14FFEC" : "#555",
              color: selected ? "#111" : "#888",
              fontWeight: 600,
              cursor: selected ? "pointer" : "not-allowed",
              transition: "0.2s",
              marginBottom: "8px",
            }}
          >
            {loading ? "Processing..." : "Continue"}
          </button>

          <p style={{ fontSize: "12px", textAlign: "center", color: "#888" }}>
            Demo Mode — Click any role to explore the system
          </p>
        </div>
      </div>
    </div>
  );
}
