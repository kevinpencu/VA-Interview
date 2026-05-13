import { useState } from "react";
import { candidateApi } from "../../api";

const QUIZ = [
  {
    q: "Which of the following is NOT a reason to reject a TikTok?",
    options: [
      "Non-English audio",
      "Ugly background",
      "Trending in the United States",
      "Clearly impossible to recreate on Kling",
    ],
  },
  {
    q: "A nano-banana generation comes back with a clearly smaller bust than our reference photos. You should:",
    options: [
      "Approve it — it's close enough",
      "Reject it",
      "Approve it and add a note",
      "Approve it if the rest of the image looks good",
    ],
  },
  {
    q: "A Kling video shows the model's face flickering for 1 second mid-clip. You should:",
    options: [
      "Approve — the rest is fine",
      "Approve if it's only a small section",
      "Reject — face must stay consistent",
      "Approve if you can crop it out",
    ],
  },
  {
    q: "How many TikToks, nano-banana images, and Kling videos will you review in this test?",
    options: ["10 of each", "20 of each", "30 of each", "50 of each"],
  },
  {
    q: "Can you go back to a previous answer once you've clicked?",
    options: ["Yes, anytime", "Yes, within the same step", "Only if you refresh", "No, never"],
  },
];

export default function Quiz({ token, onPass, onFail }) {
  const [answers, setAnswers] = useState(Array(QUIZ.length).fill(null));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  function set(qIdx, optIdx) {
    setAnswers((prev) => prev.map((v, i) => (i === qIdx ? optIdx : v)));
  }

  async function submit() {
    setSubmitting(true);
    setError(null);
    try {
      const res = await candidateApi.quiz(token, answers);
      if (res.passed) await onPass();
      else await onFail();
    } catch (e) {
      setError(e.message);
    } finally {
      setSubmitting(false);
    }
  }

  const allAnswered = answers.every((a) => a !== null);

  return (
    <div className="wizard">
      <div className="eyebrow fade-in">Quick check</div>
      <h1 className="fade-in-1" style={{ fontSize: 48, marginBottom: 8 }}>
        Did you read the rules?
      </h1>
      <p className="muted fade-in-1" style={{ marginBottom: 32 }}>
        Five questions. Get at least four right to continue — fail and the test ends.
      </p>

      {QUIZ.map((q, qi) => (
        <div key={qi} className="card fade-in-2" style={{ marginTop: 16 }}>
          <div style={{ display: "flex", gap: 12, alignItems: "baseline", marginBottom: 14 }}>
            <span className="mono" style={{ color: "var(--color-accent)", fontSize: 13, minWidth: 22 }}>
              {String(qi + 1).padStart(2, "0")}
            </span>
            <p style={{ margin: 0, fontSize: "var(--text-lg)", color: "var(--color-text)" }}>{q.q}</p>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            {q.options.map((opt, oi) => {
              const checked = answers[qi] === oi;
              return (
                <label
                  key={oi}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 12,
                    padding: "12px 14px",
                    borderRadius: 6,
                    border: `1px solid ${checked ? "var(--color-accent-dim)" : "var(--color-border)"}`,
                    background: checked ? "var(--color-accent-glow)" : "transparent",
                    color: checked ? "var(--color-text)" : "var(--color-text-soft)",
                    cursor: "pointer",
                    transition: "border-color 120ms ease, background 120ms ease, color 120ms ease",
                  }}
                >
                  <input
                    type="radio"
                    name={`q-${qi}`}
                    checked={checked}
                    onChange={() => set(qi, oi)}
                    style={{ accentColor: "var(--color-accent)" }}
                  />
                  <span>{opt}</span>
                </label>
              );
            })}
          </div>
        </div>
      ))}

      {error && <p style={{ color: "var(--color-bad)", marginTop: 16 }}>{error}</p>}

      <button
        onClick={submit}
        disabled={!allAnswered || submitting}
        className="btn btn-primary fade-in-3"
        style={{ marginTop: 32, padding: "14px 28px" }}
      >
        {submitting ? "Submitting…" : "Submit answers  →"}
      </button>
    </div>
  );
}
