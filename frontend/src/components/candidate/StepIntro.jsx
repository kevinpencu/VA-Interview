import { useState } from "react";
import { candidateApi } from "../../api";

const COPY = {
  tiktok: {
    step: "Step 1 of 3",
    title: "TikTok screening",
    body: "You'll review 30 TikToks. Mark which you would save for recreation. Reject anything in a non-English language, with ugly or non-American backgrounds, that's boring, or that can't be recreated on Kling.",
    button: "Start TikTok review",
  },
  nano_banana: {
    step: "Step 2 of 3",
    title: "Nano-banana review",
    body: "You'll review 30 AI-generated photos of our model based on TikTok frames. Mark which you would actually use to feed Kling. Watch for: identity drift (different face, smaller bust), AI artifacts (weird hands), wrong outfit or pose.",
    button: "Start nano-banana review",
  },
  kling: {
    step: "Step 3 of 3",
    title: "Kling video review",
    body: "You'll review 30 Kling videos. Mark which came out well. Watch for: face inconsistency, flickering, warping, impossible motion, boring or static videos.",
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
    <div className="intro-shell" style={{ textAlign: "center" }}>
      <div className="eyebrow fade-in">{c.step}</div>
      <h1 className="title-display fade-in-1" style={{ fontSize: "clamp(40px, 6vw, 64px)" }}>
        {c.title}
      </h1>
      <p
        className="fade-in-2"
        style={{
          marginTop: 28,
          fontSize: "var(--text-lg)",
          lineHeight: 1.55,
          color: "var(--color-text-soft)",
        }}
      >
        {c.body}
      </p>
      <button
        onClick={go}
        disabled={submitting}
        className="btn btn-primary fade-in-3"
        style={{ marginTop: 40, padding: "14px 32px" }}
      >
        {submitting ? "Loading…" : `${c.button}  →`}
      </button>
    </div>
  );
}
