import { useState } from "react";

export default function JustificationModal({ onSubmit, onCancel }) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function go() {
    setSubmitting(true);
    await onSubmit(text.trim());
    setSubmitting(false);
  }

  return (
    <div style={{
      position: "fixed", inset: 0, background: "rgba(0,0,0,0.7)",
      display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100,
    }}>
      <div style={{ background: "#141414", border: "1px solid #2a2a2a", borderRadius: 8, padding: 24, width: 480 }}>
        <h3 style={{ marginTop: 0 }}>One sentence — why?</h3>
        <p className="muted" style={{ marginTop: 0 }}>
          Briefly explain your decision. This helps us understand your reasoning.
        </p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          autoFocus
          style={{ width: "100%", padding: 10, background: "#0a0a0a", color: "#fff", border: "1px solid #2a2a2a", borderRadius: 6 }}
        />
        <div style={{ marginTop: 16, textAlign: "right" }}>
          <button onClick={go} disabled={submitting || !text.trim()}
            style={{ padding: "10px 20px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600 }}>
            {submitting ? "…" : "Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
