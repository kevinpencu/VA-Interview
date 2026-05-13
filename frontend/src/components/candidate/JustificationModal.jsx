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
        <div className="eyebrow">Why?</div>
        <h2 style={{ marginTop: 6, marginBottom: 8, fontFamily: "var(--font-display)", fontStyle: "italic", fontSize: 30 }}>
          One sentence
        </h2>
        <p className="muted" style={{ marginBottom: 16, fontSize: "var(--text-sm)" }}>
          Briefly explain your decision. This helps us understand your reasoning.
        </p>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={4}
          autoFocus
          className="input"
          placeholder="e.g. the background is clearly non-American and the song is in Spanish"
          style={{ resize: "vertical", minHeight: 96, fontFamily: "var(--font-sans)" }}
        />
        <div style={{ marginTop: 16, display: "flex", justifyContent: "flex-end" }}>
          <button onClick={go} disabled={submitting || !text.trim()} className="btn btn-primary">
            {submitting ? "Continuing…" : "Continue  →"}
          </button>
        </div>
      </div>
    </div>
  );
}
