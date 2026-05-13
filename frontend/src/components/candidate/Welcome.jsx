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
      <div className="eyebrow fade-in">VA Interview</div>
      <h1 className="title-display fade-in-1">
        Welcome.<br />
        Let's see <em>how you'd</em><br />judge our content.
      </h1>

      <div className="card-accent fade-in-2" style={{ marginTop: 40 }}>
        <p style={{ marginBottom: 8 }}>
          This takes about <strong>30–45 minutes</strong>. Complete it in one sitting on a desktop browser.
        </p>
        <p style={{ marginBottom: 0, color: "var(--color-text-muted)", fontSize: "var(--text-sm)" }}>
          You can't pause or retake. Make sure your audio is on.
        </p>
      </div>

      <form onSubmit={submit} className="fade-in-3" style={{ marginTop: 40 }}>
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
          <p style={{ color: "var(--color-bad)", marginBottom: 16, fontSize: "var(--text-sm)" }}>
            {error}
          </p>
        )}
        <button
          type="submit"
          className="btn btn-primary"
          disabled={submitting || !name || !email}
          style={{ width: "100%" }}
        >
          {submitting ? "Starting…" : "Begin the test  →"}
        </button>
      </form>
    </div>
  );
}
