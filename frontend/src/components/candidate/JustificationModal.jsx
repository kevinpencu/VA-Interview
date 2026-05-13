import { useState } from "react";

export default function JustificationModal({ onSubmit }) {
  const [text, setText] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function go() {
    setSubmitting(true);
    await onSubmit(text.trim());
    setSubmitting(false);
  }

  return (
    <div className="modal-overlay">
      <div className="modal">
        <div className="eyebrow">Quick justification</div>
        <h2 style={{ marginTop: 4, marginBottom: 6 }}>One sentence — why?</h2>
        <p className="muted" style={{ marginBottom: 16, fontSize: "var(--text-sm)" }}>
          Briefly explain your decision. This helps us understand your reasoning.
        </p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          autoFocus
          className="input"
          placeholder="e.g. the background is non-American and the song is in Spanish"
          style={{ resize: "vertical", minHeight: 96 }}
        />
        <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end" }}>
          <button onClick={go} disabled={submitting || !text.trim()} className="btn btn-primary">
            {submitting ? "Continuing…" : "Continue"}
          </button>
        </div>
      </div>
    </div>
  );
}
