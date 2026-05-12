import { useEffect, useState } from "react";
import { candidateApi } from "../../api";

const MANIFEST_URL = `${import.meta.env.VITE_SUPABASE_URL}/storage/v1/object/public/tutorial/manifest.json`;

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

// Percent-encode the path portion of a public storage URL. The seed script
// preserves filenames verbatim (spaces, colons, etc.) so the manifest may
// contain unencoded URLs; encodeURI handles spaces + special chars without
// touching the scheme/host.
function safeUrl(url) {
  if (!url) return url;
  try {
    return encodeURI(decodeURI(url));
  } catch {
    return encodeURI(url);
  }
}

export default function Tutorial({ token, onContinue }) {
  const [submitting, setSubmitting] = useState(false);
  const [manifest, setManifest] = useState(null);
  const [manifestState, setManifestState] = useState("loading"); // loading | ok | error

  useEffect(() => {
    let cancelled = false;
    fetch(MANIFEST_URL, { cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error(`manifest fetch failed: ${r.status}`);
        return r.json();
      })
      .then((m) => {
        if (cancelled) return;
        setManifest(m);
        setManifestState("ok");
      })
      .catch(() => {
        if (cancelled) return;
        setManifestState("error");
      });
    return () => {
      cancelled = true;
    };
  }, []);

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
          <ExamplesGrid pool={pool} manifest={manifest} state={manifestState} />
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

function ExamplesGrid({ pool, manifest, state }) {
  if (state === "loading") {
    return <p className="muted" style={{ marginTop: 12, fontSize: 13 }}>Loading examples…</p>;
  }
  if (state === "error" || !manifest || !manifest[pool]) {
    return null; // fail quiet — rules still render above
  }

  const good = manifest[pool].good || [];
  const bad = manifest[pool].bad || [];
  const entries = [
    ...good.map((e, i) => ({ ...e, _side: "good", _key: `g${i}` })),
    ...bad.map((e, i) => ({ ...e, _side: "bad", _key: `b${i}` })),
  ];

  if (entries.length === 0) return null;

  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
      gap: 8,
      marginTop: 12,
    }}>
      {entries.map((e) => (
        <ExampleCell key={e._key} entry={e} isGood={e._side === "good"} />
      ))}
    </div>
  );
}

function ExampleCell({ entry, isGood }) {
  return (
    <div style={{ position: "relative" }}>
      <ExampleMedia entry={entry} />
      <span style={{
        position: "absolute", top: 6, left: 6, padding: "2px 6px", borderRadius: 3,
        fontSize: 10, fontWeight: 700, background: isGood ? "var(--accent-good)" : "var(--accent-bad)", color: "#000",
        pointerEvents: "none",
      }}>{isGood ? "GOOD" : "BAD"}</span>
    </div>
  );
}

function ExampleMedia({ entry }) {
  if (entry.type === "video") {
    return (
      <video
        src={safeUrl(entry.url)}
        controls
        muted
        preload="metadata"
        playsInline
        style={{ width: "100%", borderRadius: 6, background: "#000", display: "block" }}
      />
    );
  }
  if (entry.type === "image") {
    return (
      <img
        src={safeUrl(entry.url)}
        alt=""
        loading="lazy"
        style={{ width: "100%", borderRadius: 6, opacity: 0.95, display: "block" }}
      />
    );
  }
  if (entry.type === "pair") {
    return (
      <div style={{ display: "flex", gap: 4 }}>
        <figure style={{ margin: 0, flex: 1, minWidth: 0 }}>
          <img
            src={safeUrl(entry.original_url)}
            alt=""
            loading="lazy"
            style={{ width: "100%", borderRadius: 6, display: "block" }}
          />
          <figcaption style={{ fontSize: 9, textAlign: "center", marginTop: 2, opacity: 0.7 }}>Original</figcaption>
        </figure>
        <figure style={{ margin: 0, flex: 1, minWidth: 0 }}>
          <img
            src={safeUrl(entry.generation_url)}
            alt=""
            loading="lazy"
            style={{ width: "100%", borderRadius: 6, display: "block" }}
          />
          <figcaption style={{ fontSize: 9, textAlign: "center", marginTop: 2, opacity: 0.7 }}>AI</figcaption>
        </figure>
      </div>
    );
  }
  return null;
}
