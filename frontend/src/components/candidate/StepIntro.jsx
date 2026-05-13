import { useState } from "react";
import { candidateApi } from "../../api";

const COPY = {
  tiktok: {
    step: "Step 1 of 3",
    title: "TikTok screening",
    body: "You'll review 30 TikToks. Mark which you'd save for recreation. Reject anything in a non-English language, with ugly or non-American backgrounds, that's boring, or that can't be recreated on Kling.",
    button: "Start TikTok review",
  },
  nano_banana: {
    step: "Step 2 of 3",
    title: "Nano-banana review",
    body: "You'll review 30 AI-generated photos of our model. Mark which you'd actually use to feed Kling. Watch for: identity drift, smaller bust, AI artifacts, wrong outfit or pose.",
    button: "Start nano-banana review",
  },
  kling: {
    step: "Step 3 of 3",
    title: "Kling video review",
    body: "You'll review 30 Kling videos. Mark which came out well. Watch for: face inconsistency, flickering, warping, impossible motion, boring or static clips.",
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
    <div className="intro-shell" style={{ textAlign: "left" }}>
      <div className="eyebrow fade-in">{c.step}</div>
      <h1 className="intro-title fade-in-1">{c.title}</h1>
      <p
        className="fade-in-2"
        style={{ marginTop: 20, fontSize: "var(--text-lg)", lineHeight: 1.55, color: "var(--text-soft)" }}
      >
        {c.body}
      </p>
      <button
        onClick={go}
        disabled={submitting}
        className="btn btn-primary fade-in-3"
        style={{ marginTop: 32, padding: "12px 24px" }}
      >
        {submitting ? "Loading…" : c.button}
      </button>
    </div>
  );
}
