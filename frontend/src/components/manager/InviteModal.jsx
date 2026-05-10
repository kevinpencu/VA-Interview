import { useState } from "react";
import { managerApi } from "../../api";

export default function InviteModal({ token, onClose, onCreated }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [result, setResult] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

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

  return (
    <div style={overlayStyle}>
      <div style={modalStyle}>
        {!result ? (
          <>
            <h3 style={{ marginTop: 0 }}>New invite</h3>
            <label className="label">Candidate name (label only)</label>
            <input value={name} onChange={(e) => setName(e.target.value)} style={inputStyle} />
            <label className="label">Candidate email (label only)</label>
            <input value={email} onChange={(e) => setEmail(e.target.value)} type="email" style={inputStyle} />
            {error && <p style={{ color: "var(--accent-bad)" }}>{error}</p>}
            <div style={{ textAlign: "right" }}>
              <button onClick={onClose} style={ghostBtn}>Cancel</button>
              <button onClick={go} disabled={!name || !email || submitting} style={primaryBtn}>
                {submitting ? "…" : "Generate link"}
              </button>
            </div>
          </>
        ) : (
          <>
            <h3 style={{ marginTop: 0 }}>Send this link</h3>
            <p className="muted">Copy and paste it in WhatsApp. The link is single-use.</p>
            <input readOnly value={result.url} onClick={(e) => e.target.select()} style={inputStyle} />
            <div style={{ textAlign: "right" }}>
              <button onClick={onClose} style={primaryBtn}>Done</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const overlayStyle = { position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 };
const modalStyle = { background: "#141414", border: "1px solid #2a2a2a", borderRadius: 8, padding: 24, width: 480 };
const inputStyle = { width: "100%", padding: 10, marginTop: 4, marginBottom: 16, background: "#0a0a0a", color: "#fff", border: "1px solid #2a2a2a", borderRadius: 6 };
const primaryBtn = { padding: "8px 16px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600, marginLeft: 8 };
const ghostBtn = { padding: "8px 16px", background: "transparent", color: "#fff", border: "1px solid #333", borderRadius: 6 };
