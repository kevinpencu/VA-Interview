import { Navigate, Route, Routes } from "react-router-dom";
import CandidateRoot from "./components/candidate/Root.jsx";
import ManagerRoot from "./components/manager/Root.jsx";
import "./styles.css";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/admin" replace />} />
      <Route path="/test/:token/*" element={<CandidateRoot />} />
      <Route path="/admin/*" element={<ManagerRoot />} />
      <Route path="*" element={<div style={{ padding: 32 }}>Not found</div>} />
    </Routes>
  );
}
