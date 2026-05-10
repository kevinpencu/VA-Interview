import { useEffect, useRef, useState } from "react";
import { candidateApi } from "../../api";
import JustificationModal from "./JustificationModal.jsx";

const COPY = {
  tiktok: {
    question: "Would you save this TikTok for recreation?",
    yes: { label: "Yes, save this", sub: "Worth recreating" },
    no:  { label: "No, skip", sub: "Wrong language / boring / can't recreate" },
    type: "video",
  },
  nano_banana: {
    question: "Would you use this generation to feed Kling?",
    yes: { label: "Yes, use this", sub: "Identity matches, no AI artifacts" },
    no:  { label: "No, reject", sub: "Wrong identity / artifacts / off-prompt" },
    type: "image",
  },
  kling: {
    question: "Did this Kling video come out well?",
    yes: { label: "Good", sub: "Realistic motion, consistent face" },
    no:  { label: "Bad", sub: "Flicker / warp / inconsistent / boring" },
    type: "video",
  },
};

export default function TestStep({ token, pool, item, progress, onAdvance }) {
  const c = COPY[pool];
  const [shownAt] = useState(() => new Date().toISOString());
  const startMs = useRef(performance.now());
  const [submitting, setSubmitting] = useState(false);
  const [pendingJustification, setPendingJustification] = useState(null); // { decisionId } when needed
  const [pendingAdvance, setPendingAdvance] = useState(null);

  async function answer(value) {
    if (submitting || pendingJustification) return;
    setSubmitting(true);
    const dwell = Math.round(performance.now() - startMs.current);
    try {
      const res = await candidateApi.decision(token, {
        item_id: item.id, answer: value, dwell_ms: dwell, shown_at: shownAt,
      });
      if (res.needs_justification) {
        setPendingJustification({ decisionId: res.decision_id });
        setPendingAdvance(() => async () => {
          await onAdvance(res.next);
        });
      } else {
        await onAdvance(res.next);
      }
    } finally {
      setSubmitting(false);
    }
  }

  useEffect(() => {
    function onKey(e) {
      if (pendingJustification) return;
      if (e.key === "ArrowRight") answer(true);
      if (e.key === "ArrowLeft") answer(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [pendingJustification, item.id]);

  useEffect(() => {
    function onBeforeUnload(e) {
      e.preventDefault();
      e.returnValue = "";
      return "";
    }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, []);

  async function submitJustification(text) {
    await candidateApi.justification(token, pendingJustification.decisionId, text);
    setPendingJustification(null);
    if (pendingAdvance) await pendingAdvance();
  }

  return (
    <div style={{ maxWidth: 880, margin: "32px auto", padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
        <span className="label">Step {stepNumber(pool)} — {stepName(pool)}</span>
        <span className="label">{progress + 1} / 30</span>
      </div>
      <div style={{ display: "flex", gap: 24, alignItems: "stretch", background: "#0d0d0d", padding: 24, borderRadius: 8 }}>
        <div style={{ flexShrink: 0 }}>
          {c.type === "video" ? (
            <video
              key={item.id}
              src={item.storage_url}
              controls autoPlay
              style={{ width: 240, aspectRatio: "9/16", borderRadius: 6, background: "#000" }}
            />
          ) : (
            <img
              src={item.storage_url}
              alt=""
              style={{ width: 320, borderRadius: 6 }}
            />
          )}
        </div>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", gap: 12 }}>
          <p style={{ fontSize: 16, color: "#bbb", margin: 0 }}>{c.question}</p>
          <button onClick={() => answer(true)} disabled={submitting}
            style={btnStyle("good")}>
            <span style={{ fontWeight: 600 }}>{c.yes.label}</span>
            <span className="muted" style={{ display: "block", fontSize: 11, marginTop: 4 }}>{c.yes.sub}</span>
          </button>
          <button onClick={() => answer(false)} disabled={submitting}
            style={btnStyle("bad")}>
            <span style={{ fontWeight: 600 }}>{c.no.label}</span>
            <span className="muted" style={{ display: "block", fontSize: 11, marginTop: 4 }}>{c.no.sub}</span>
          </button>
          <span className="label" style={{ marginTop: 8 }}>← reject  /  → accept</span>
        </div>
      </div>
      {pendingJustification && (
        <JustificationModal onSubmit={submitJustification} onCancel={() => {}} />
      )}
    </div>
  );
}

function stepName(p) { return { tiktok: "TikTok review", nano_banana: "Nano-banana review", kling: "Kling video review" }[p]; }
function stepNumber(p) { return { tiktok: 1, nano_banana: 2, kling: 3 }[p]; }
function btnStyle(kind) {
  const palette = kind === "good"
    ? { bg: "#1f3a1f", color: "#b5f5b5", border: "#2a5a2a" }
    : { bg: "#3a1f1f", color: "#f5b5b5", border: "#5a2a2a" };
  return {
    padding: "16px 18px", background: palette.bg, color: palette.color,
    border: `1px solid ${palette.border}`, borderRadius: 6,
    textAlign: "left", fontSize: 14,
  };
}
