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
    <div style={{ maxWidth: 720, margin: "32px auto", padding: 16 }}>
      <h1>Comprehension check</h1>
      <p className="muted">Answer all 5 questions. You need at least 4 correct to continue.</p>
      {QUIZ.map((q, qi) => (
        <div key={qi} className="card" style={{ marginTop: 16 }}>
          <p style={{ marginTop: 0, fontWeight: 600 }}>{qi + 1}. {q.q}</p>
          {q.options.map((opt, oi) => (
            <label key={oi} style={{ display: "block", padding: "6px 0" }}>
              <input
                type="radio"
                name={`q-${qi}`}
                checked={answers[qi] === oi}
                onChange={() => set(qi, oi)}
                style={{ marginRight: 8 }}
              />
              {opt}
            </label>
          ))}
        </div>
      ))}
      {error && <p style={{ color: "var(--accent-bad)" }}>{error}</p>}
      <button onClick={submit} disabled={!allAnswered || submitting}
        style={{ marginTop: 24, padding: "12px 24px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600 }}>
        {submitting ? "Submitting…" : "Submit answers"}
      </button>
    </div>
  );
}
