import { useState } from "react";
import { candidateApi } from "../../api";

const TUTORIAL = `${import.meta.env.VITE_SUPABASE_URL}/storage/v1/object/public/tutorial`;

const RULES = {
  tiktok: [
    "English audio only — songs and voice-over",
    "American or generic Western style backgrounds — no foreign indoor scenes",
    "Visually interesting — boring static videos are out",
    "Recreatable on Kling — no extreme physics, multiple people, or rapid scene cuts",
    "Not too short or too long (5–30s sweet spot)",
  ],
  nano_banana: [
    "Model identity must match — same face, same body, same bust size as our references",
    "No clear AI artifacts — extra fingers, melted faces, weird hands",
    "Outfit and pose must roughly match the reference scene",
    "Lighting and skin should look like a phone photo, not a studio render",
  ],
  kling: [
    "Realistic motion — no impossible body movements",
    "Face stays consistent through the whole video",
    "No flickering, smearing, or warping",
    "Engaging — not boring or static",
  ],
};

export default function Tutorial({ token, onContinue }) {
  const [submitting, setSubmitting] = useState(false);

  async function ack() {
    setSubmitting(true);
    await candidateApi.tutorialAck(token);
    await onContinue();
  }

  return (
    <div style={{ maxWidth: 760, margin: "32px auto", padding: 16 }}>
      <h1>Read the rules carefully</h1>
      <p className="muted">After this you'll answer 5 quick questions to confirm you understood. If you fail, the test ends.</p>

      {Object.entries(RULES).map(([pool, rules]) => (
        <section key={pool} className="card" style={{ marginTop: 24 }}>
          <h2 style={{ marginTop: 0 }}>{poolName(pool)}</h2>
          <ul>{rules.map((r) => <li key={r}>{r}</li>)}</ul>
          <ExamplesGrid pool={pool} />
        </section>
      ))}

      <button onClick={ack} disabled={submitting}
        style={{ marginTop: 32, padding: "12px 24px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600 }}>
        I've read the rules → continue
      </button>
    </div>
  );
}

function poolName(p) {
  return { tiktok: "TikTok screening", nano_banana: "Nano-banana review", kling: "Kling video review" }[p];
}

function ExamplesGrid({ pool }) {
  // Each pool has up to 4 example images named good_1.jpg, good_2.jpg, bad_1.jpg, bad_2.jpg in tutorial bucket
  const examples = ["good_1.jpg", "good_2.jpg", "bad_1.jpg", "bad_2.jpg"];
  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginTop: 12 }}>
      {examples.map((f) => {
        const isGood = f.startsWith("good");
        return (
          <div key={f} style={{ position: "relative" }}>
            <img src={`${TUTORIAL}/${pool}/${f}`} alt={f} style={{ width: "100%", borderRadius: 6, opacity: 0.95 }} />
            <span style={{
              position: "absolute", top: 6, left: 6, padding: "2px 6px", borderRadius: 3,
              fontSize: 10, fontWeight: 700, background: isGood ? "var(--accent-good)" : "var(--accent-bad)", color: "#000",
            }}>{isGood ? "GOOD" : "BAD"}</span>
          </div>
        );
      })}
    </div>
  );
}
