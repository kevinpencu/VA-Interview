import { useState } from "react";
import { supabase } from "../../lib/supabase.js";

export default function Login({ onLogin }) {
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  async function submit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    const { error } = await supabase.auth.signInWithPassword({ email, password: pw });
    setSubmitting(false);
    if (error) return setError(error.message);
    await onLogin();
  }

  return (
    <div style={{ maxWidth: 360, margin: "120px auto", padding: 16 }}>
      <h1>Manager login</h1>
      <form onSubmit={submit}>
        <label className="label">Email</label>
        <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" required
          style={inputStyle} />
        <label className="label">Password</label>
        <input value={pw} onChange={(e) => setPw(e.target.value)} type="password" required
          style={inputStyle} />
        {error && <p style={{ color: "var(--accent-bad)" }}>{error}</p>}
        <button disabled={submitting}
          style={{ padding: "12px 24px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600, marginTop: 8 }}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}

const inputStyle = {
  width: "100%", padding: 10, marginTop: 4, marginBottom: 16,
  background: "#141414", color: "#fff", border: "1px solid #333", borderRadius: 6,
};
