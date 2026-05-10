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
    <div style={{ maxWidth: 480, margin: "80px auto", padding: 16 }}>
      <h1>VA Interview Test</h1>
      <p className="muted">
        This test takes about 30–45 minutes. You must complete it in one sitting on a desktop browser.
        You cannot pause or retake. Make sure you have audio enabled.
      </p>
      <form onSubmit={submit} style={{ marginTop: 24 }}>
        <label className="label">Full name</label>
        <input
          required
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ width: "100%", padding: 10, marginTop: 4, marginBottom: 16, background: "#141414", color: "#fff", border: "1px solid #333", borderRadius: 6 }}
        />
        <label className="label">Email</label>
        <input
          required type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          style={{ width: "100%", padding: 10, marginTop: 4, marginBottom: 16, background: "#141414", color: "#fff", border: "1px solid #333", borderRadius: 6 }}
        />
        {error && <p style={{ color: "var(--accent-bad)" }}>{error}</p>}
        <button
          disabled={submitting || !name || !email}
          style={{ padding: "12px 24px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600 }}
        >
          {submitting ? "Starting..." : "Start test"}
        </button>
      </form>
    </div>
  );
}
