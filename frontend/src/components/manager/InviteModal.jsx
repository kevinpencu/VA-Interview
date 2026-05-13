import { useState } from "react";
import { managerApi } from "../../api";

export default function InviteModal({ token, onClose, onCreated }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [copied, setCopied] = useState(false);

  async function go() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await managerApi.createInvite(token, name, email);
      setResult(res);
      onCreated();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function copyUrl() {
    try {
      await navigator.clipboard.writeText(result.url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (e) {
      // fallback handled via click-to-select
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        {!result ? (
          <>
            <div className="eyebrow">New candidate</div>
            <h2 style={{ marginTop: 4, marginBottom: 18 }}>
              Generate an invite
            </h2>
            <div style={{ marginBottom: 14 }}>
              <label className="label" style={{ display: "block", marginBottom: 6 }}>Candidate name <span className="dim">(label only)</span></label>
              <input className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="Jane Doe" />
            </div>
            <div style={{ marginBottom: 18 }}>
              <label className="label" style={{ display: "block", marginBottom: 6 }}>Candidate email <span className="dim">(label only)</span></label>
              <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} type="email" placeholder="jane@example.com" />
            </div>
            {error && <p style={{ color: "var(--bad)", fontSize: "var(--text-sm)", marginBottom: 12 }}>{error}</p>}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={onClose} className="btn btn-ghost">Cancel</button>
              <button onClick={go} disabled={!name || !email || submitting} className="btn btn-primary">
                {submitting ? "Creating…" : "Generate link"}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="eyebrow">Invite ready</div>
            <h2 style={{ marginTop: 4, marginBottom: 8 }}>
              Send this link
            </h2>
            <p className="muted" style={{ marginBottom: 16, fontSize: "var(--text-sm)" }}>
              Single-use. Once they click, no one else can.
            </p>
            <input
              className="input mono"
              readOnly
              value={result.url}
              onClick={(e) => e.target.select()}
              style={{ fontSize: 12, marginBottom: 16 }}
            />
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
              <button onClick={copyUrl} className="btn btn-ghost">{copied ? "✓ Copied" : "Copy"}</button>
              <button onClick={onClose} className="btn btn-primary">Done</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
