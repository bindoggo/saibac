import "./styles.css";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import Layout from "./Layout";

import Login from "./pages/login";
import Dashboard from "./pages/Dashboard";
import FacultyPage from "./pages/Faculty";
import ClassroomsPage from "./pages/Classrooms";
import StudentsPage from "./pages/Students";
import SubjectsPage from "./pages/Subjects";
import OfferingsPage from "./pages/Offerings";
import TimeslotsPage from "./pages/Timeslots";
import TimetablePage from "./pages/Timetable";
import Departments from "./pages/Departments";
import Optimize from "./pages/optimize";

export default function App() {
  return (
    <Router>
      <Routes>

        {/* LOGIN PAGE — no sidebar, no layout */}
        <Route path="/" element={<Login />} />

        {/* ADMIN PAGES — wrapped inside Layout */}
        <Route element={<Layout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/faculty" element={<FacultyPage />} />
          <Route path="/departments" element={<Departments />} />
          <Route path="/classrooms" element={<ClassroomsPage />} />
          <Route path="/students" element={<StudentsPage />} />
          <Route path="/subjects" element={<SubjectsPage />} />
          <Route path="/offerings" element={<OfferingsPage />} />
          <Route path="/timeslots" element={<TimeslotsPage />} />
          <Route path="/timetable" element={<TimetablePage />} />
          <Route path="/optimize" element={<Optimize />} />
        </Route>

      </Routes>
    </Router>
  );
}
