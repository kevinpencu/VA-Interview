import { useEffect, useState } from "react";
import { Route, Routes } from "react-router-dom";
import { supabase } from "../../lib/supabase.js";
import Login from "./Login.jsx";
import Dashboard from "./Dashboard.jsx";
import CandidateDetail from "./CandidateDetail.jsx";

export default function ManagerRoot() {
  const [session, setSession] = useState(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => { setSession(data.session); setLoaded(true); });
    const { data: sub } = supabase.auth.onAuthStateChange((_e, s) => setSession(s));
    return () => sub.subscription.unsubscribe();
  }, []);

  if (!loaded) return <div style={{ padding: 48 }}>…</div>;
  if (!session) return <Login onLogin={() => {/* state listener will pick it up */}} />;

  const jwt = session.access_token;
  return (
    <Routes>
      <Route path="" element={<Dashboard jwt={jwt} />} />
      <Route path="candidates/:id" element={<CandidateDetail jwt={jwt} />} />
    </Routes>
  );
}
