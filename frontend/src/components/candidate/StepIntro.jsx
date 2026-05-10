import { useState } from "react";
import { candidateApi } from "../../api";

const COPY = {
  tiktok: {
    title: "Step 1 of 3 — TikTok screening",
    body: "You'll review 30 TikToks. Mark which you would save for recreation. Reject anything in a non-English language, with ugly or non-American backgrounds, that's boring, or that can't be recreated on Kling.",
    button: "Start TikTok review",
  },
  nano_banana: {
    title: "Step 2 of 3 — Nano-banana review",
    body: "You'll review 30 AI-generated photos of our model based on TikTok frames. Mark which you would actually use to feed Kling. Watch for: identity drift (different face, smaller bust), AI artifacts (weird hands), wrong outfit/pose.",
    button: "Start nano-banana review",
  },
  kling: {
    title: "Step 3 of 3 — Kling video review",
    body: "You'll review 30 Kling videos. Mark which came out well. Watch for: face inconsistency, flickering, warping, impossible motion, boring/static videos.",
    button: "Start Kling review",
  },
};

export default function StepIntro({ token, pool, onContinue }) {
  const [submitting, setSubmitting] = useState(false);
  const c = COPY[pool];

  async function go() {
    setSubmitting(true);
    await candidateApi.stepIntroAck(token, pool);
    await onContinue();
  }

  return (
    <div style={{ maxWidth: 640, margin: "80px auto", padding: 16, textAlign: "center" }}>
      <h1>{c.title}</h1>
      <p style={{ fontSize: 16, lineHeight: 1.6 }}>{c.body}</p>
      <button onClick={go} disabled={submitting}
        style={{ marginTop: 32, padding: "14px 32px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600, fontSize: 15 }}>
        {submitting ? "Loading…" : c.button}
      </button>
    </div>
  );
}
