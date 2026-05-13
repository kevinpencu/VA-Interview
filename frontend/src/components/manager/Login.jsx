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
    <div className="intro-shell" style={{ maxWidth: 400 }}>
      <div className="eyebrow fade-in">VA Interview · Admin</div>
      <h1 className="title-display fade-in-1" style={{ fontSize: 56 }}>
        <em>Sign in</em>
      </h1>
      <p className="muted fade-in-1" style={{ marginTop: 12, marginBottom: 32 }}>
        Manager access only.
      </p>

      <form onSubmit={submit} className="fade-in-2">
        <div style={{ marginBottom: 16 }}>
          <label className="label" style={{ display: "block", marginBottom: 6 }}>Email</label>
          <input
            className="input"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            type="email"
            required
            placeholder="manager@example.com"
          />
        </div>
        <div style={{ marginBottom: 20 }}>
          <label className="label" style={{ display: "block", marginBottom: 6 }}>Password</label>
          <input
            className="input"
            value={pw}
            onChange={(e) => setPw(e.target.value)}
            type="password"
            required
            placeholder="••••••••"
          />
        </div>
        {error && (
          <p style={{ color: "var(--color-bad)", marginBottom: 16, fontSize: "var(--text-sm)" }}>
            {error}
          </p>
        )}
        <button disabled={submitting} className="btn btn-primary" style={{ width: "100%" }}>
          {submitting ? "Signing in…" : "Sign in  →"}
        </button>
      </form>
    </div>
  );
}
