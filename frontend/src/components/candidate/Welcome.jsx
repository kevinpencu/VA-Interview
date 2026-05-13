import { useState } from "react";
import { candidateApi } from "../../api";

export default function Welcome({ token, onStarted }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await candidateApi.start(token, name, email);
      await onStarted();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="intro-shell">
      <div className="eyebrow fade-in">VA Interview · Hiring test</div>
      <h1 className="intro-title fade-in-1">Welcome.</h1>
      <p className="fade-in-1" style={{ marginTop: 16, fontSize: "var(--text-lg)", color: "var(--text-soft)" }}>
        We'll walk you through what the job is, then test you on it.
      </p>

      <div className="card fade-in-2" style={{ marginTop: 32 }}>
        <ul style={{ margin: 0, paddingLeft: 18 }}>
          <li><strong>30–45 minutes</strong>, one sitting, desktop only.</li>
          <li>You <strong>can't pause or retake</strong>. Don't start unless you're ready.</li>
          <li>Make sure your <strong>audio is on</strong>.</li>
        </ul>
      </div>

      <form onSubmit={submit} className="fade-in-3" style={{ marginTop: 32 }}>
        <div style={{ marginBottom: 18 }}>
          <label className="label" style={{ display: "block", marginBottom: 6 }}>Full name</label>
          <input
            className="input"
            required
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="As it appears on your résumé"
          />
        </div>
        <div style={{ marginBottom: 24 }}>
          <label className="label" style={{ display: "block", marginBottom: 6 }}>Email</label>
          <input
            className="input"
            required
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
          />
        </div>
        {error && (
          <p style={{ color: "var(--bad)", marginBottom: 16, fontSize: "var(--text-sm)" }}>{error}</p>
        )}
        <button
          type="submit"
          className="btn btn-primary"
          disabled={submitting || !name || !email}
          style={{ width: "100%", padding: "12px 24px" }}
        >
          {submitting ? "Starting…" : "Begin the test"}
        </button>
      </form>
    </div>
  );
}
