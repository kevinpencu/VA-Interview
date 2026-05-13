import { useEffect, useState } from "react";
import { candidateApi } from "../../api";

const MANIFEST_URL = `${import.meta.env.VITE_SUPABASE_URL}/storage/v1/object/public/tutorial/manifest.json`;

const PAGES = ["overview", "tiktok", "nano_banana", "kling"];

// Per-filename labels for bad-example tiles. Derived from the lesson filenames
// the seed script uploads. If a filename isn't in this map the tile renders
// without a caption.
const BAD_LABELS = {
  // Bad TikToks
  "non-english.mp4": "Non-English audio",
  "switchestolandscape.MP4": "Switches to landscape mid-clip",
  "toofarback2.mp4": "Girl too far from the camera",
  "uglybackground:non-english.mp4": "Ugly background + non-English audio",
  "weirdmovement2.mp4": "Weird / hard-to-copy movement",
  // Bad Kling
  "cameramoves2.mp4": "Camera moves",
  "clearbug.mp4": "Clear bug / artifact",
  "weirdface6.mp4": "Distorted face",
  "weirdmovement3.mp4": "Robotic / weird movement",
  // Bad NanoBanana
  "differentbackground1.png": "Wrong background",
  "differentbackground2.png": "Wrong background",
  "differentgirl1.jpeg": "Different girl (not our model)",
  "differentgirl2.jpeg": "Different girl (not our model)",
  "differentpose1.jpeg": "Wrong pose",
  "differentpose2.jpeg": "Wrong pose",
  "morph1.jpeg": "Morph (blend of two faces)",
  "morph2.jpeg": "Morph (blend of two faces)",
};

function safeUrl(url) {
  if (!url) return url;
  try {
    return encodeURI(decodeURI(url));
  } catch {
    return encodeURI(url);
  }
}

function labelFor(entry) {
  if (!entry) return null;
  const u = entry.url || entry.generation_url || entry.original_url;
  if (!u) return null;
  try {
    const fn = decodeURIComponent(u.split("?")[0].split("/").pop());
    return BAD_LABELS[fn] || null;
  } catch {
    return null;
  }
}

export default function Tutorial({ token, onContinue }) {
  const [pageIdx, setPageIdx] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [manifest, setManifest] = useState(null);
  const [manifestState, setManifestState] = useState("loading");

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
    return () => { cancelled = true; };
  }, []);

  async function next() {
    if (pageIdx < PAGES.length - 1) {
      setPageIdx(pageIdx + 1);
      window.scrollTo({ top: 0, behavior: "instant" });
      return;
    }
    setSubmitting(true);
    await candidateApi.tutorialAck(token);
    await onContinue();
  }

  function back() {
    if (pageIdx === 0) return;
    setPageIdx(pageIdx - 1);
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  const page = PAGES[pageIdx];
  const isLast = pageIdx === PAGES.length - 1;

  return (
    <div className="wizard">
      <div className="wizard-header fade-in">
        <div>
          <div className="eyebrow">Lesson</div>
          <div style={{ fontSize: 20, marginTop: 4, fontWeight: 600, letterSpacing: "-0.02em" }}>
            Page {pageIdx + 1} <span className="dim" style={{ fontWeight: 400 }}>/ {PAGES.length}</span>
          </div>
        </div>
        <ProgressDots count={PAGES.length} active={pageIdx} />
      </div>

      <div key={page} className="fade-in">
        {page === "overview" && <OverviewPage />}
        {page === "tiktok" && <TikTokPage manifest={manifest} manifestState={manifestState} />}
        {page === "nano_banana" && <NanoBananaPage manifest={manifest} manifestState={manifestState} />}
        {page === "kling" && <KlingPage manifest={manifest} manifestState={manifestState} />}
      </div>

      <NavBar
        pageIdx={pageIdx}
        isLast={isLast}
        submitting={submitting}
        onBack={back}
        onNext={next}
      />
    </div>
  );
}

function ProgressDots({ count, active }) {
  return (
    <div className="dots">
      {Array.from({ length: count }).map((_, i) => (
        <span
          key={i}
          className={`dot ${i === active ? "active" : i < active ? "done" : ""}`}
        />
      ))}
    </div>
  );
}

function NavBar({ pageIdx, isLast, submitting, onBack, onNext }) {
  return (
    <div className="wizard-nav">
      <button onClick={onBack} disabled={pageIdx === 0} className="btn btn-ghost">← Back</button>
      <button onClick={onNext} disabled={submitting} className="btn btn-primary">
        {submitting ? "Loading…" : isLast ? "Continue to quiz →" : "Next →"}
      </button>
    </div>
  );
}

// =====================================================================
// Page 1 — Job overview
// =====================================================================

function OverviewPage() {
  return (
    <article>
      <h1 style={{ marginTop: 0 }}>The job, in plain terms</h1>
      <p>You'll help create AI videos of our model to post on Instagram Reels. We don't film her — every frame is generated by AI, using real TikToks as the blueprint.</p>
      <p>The pipeline is three steps:</p>

      <section className="card" style={{ marginTop: 16 }}>
        <h2 style={{ marginTop: 0 }}>Step 1 — Pick a TikTok to recreate</h2>
        <p style={{ marginBottom: 0 }}>
          Scroll TikTok and find dance or lip-sync videos by other girls. When one fits our criteria, save it.
          <strong> Most videos won't qualify</strong> — you're being picky on purpose.
        </p>
      </section>

      <section className="card" style={{ marginTop: 12 }}>
        <h2 style={{ marginTop: 0 }}>Step 2 — Generate the first frame with Nano Banana</h2>
        <p style={{ marginBottom: 0 }}>
          Nano Banana is an AI image generator. We feed it the first frame of the TikTok plus reference photos of our model.
          Nano Banana swaps the girl in the frame with our model — same pose, same outfit, same background.
        </p>
      </section>

      <section className="card" style={{ marginTop: 12 }}>
        <h2 style={{ marginTop: 0 }}>Step 3 — Generate the video with Kling</h2>
        <p style={{ marginBottom: 0 }}>
          Kling is an AI video generator. We feed it the original TikTok plus the Nano-banana frame. Kling produces a new
          video that copies the original's motion but with our model as the subject.
        </p>
      </section>

      <p style={{ marginTop: 24 }}>
        You don't need to know the technical details — you'll learn those after you're hired. For now, just understand the goal:{" "}
        <strong>recreate TikTok dances with our model using AI</strong>. Your job is to judge the work at each step.
      </p>

      <section className="card" style={{ marginTop: 16, background: "var(--bg-subtle)", border: "1px solid var(--border)" }}>
        <h2 style={{ marginTop: 0 }}>What this test looks like</h2>
        <p>After this lesson you'll answer a <strong>5-question comprehension check</strong>. You need 4 of 5 correct to continue — fail it and the test ends.</p>
        <p>Then you'll review three sets of 30 items, one per step:</p>
        <ul>
          <li>30 TikToks — <strong>would you save these?</strong></li>
          <li>30 Nano-banana generations — <strong>would you use these to feed Kling?</strong></li>
          <li>30 Kling videos — <strong>are these good enough to post?</strong></li>
        </ul>
        <p style={{ marginBottom: 0 }}>
          You can't go back to a previous answer once you click. Read the next three pages carefully — each one explains exactly what to look for.
        </p>
      </section>
    </article>
  );
}

// =====================================================================
// Page 2 — TikTok screening
// =====================================================================

function TikTokPage({ manifest, manifestState }) {
  return (
    <article>
      <h1 style={{ marginTop: 0 }}>Step 1 — Picking the right TikTok</h1>
      <p>
        On the job you'll scroll TikTok looking for dance or lip-sync videos by <strong>American girls</strong>.
        Most of what you scroll past won't qualify. Be selective.
      </p>

      <h2 style={{ marginTop: 24 }}>What makes a TikTok worth saving</h2>
      <ul>
        <li><strong>English audio.</strong> The song or voice-over must be in English.</li>
        <li><strong>American-style background.</strong> Usually her bedroom or apartment — typical American girl setting, not a foreign indoor scene.</li>
        <li><strong>The girl stays mostly in place.</strong> She doesn't wander far from the camera or move back and forth a lot.</li>
        <li><strong>The dance is simple enough.</strong> Kling can't reproduce hard choreography, especially weird torso movements.</li>
      </ul>

      <h3 style={{ marginTop: 20 }}>Good examples</h3>
      <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>Easier dance, girl stays put, English audio, clean American background.</p>
      <ExamplesGrid items={manifest?.tiktok?.good} state={manifestState} side="good" showLabels={false} />

      <h2 style={{ marginTop: 32 }}>What gets rejected</h2>
      <ul>
        <li><strong>Non-English audio</strong></li>
        <li><strong>Ugly or non-American background</strong></li>
        <li><strong>Girl moves too far back from the camera</strong></li>
        <li><strong>Weird or hard-to-recreate dance moves</strong></li>
        <li><strong>The phone flips to landscape mid-video</strong> — this glitches Kling</li>
      </ul>

      <h3 style={{ marginTop: 20 }}>Bad examples — one of each failure mode</h3>
      <ExamplesGrid items={manifest?.tiktok?.bad} state={manifestState} side="bad" showLabels={true} />
    </article>
  );
}

// =====================================================================
// Page 3 — Nano-banana review
// =====================================================================

function NanoBananaPage({ manifest, manifestState }) {
  const refs = manifest?.model_reference || [];
  return (
    <article>
      <h1 style={{ marginTop: 0 }}>Step 2 — Judging a Nano-banana generation</h1>
      <p>
        After we pick a TikTok, we send its first frame plus reference photos of our model into Nano Banana.
        The output should be the same frame but with <strong>our model</strong> instead of the original girl.
        Your job is to confirm Nano Banana did it right.
      </p>

      {refs.length > 0 && (
        <section className="card-accent" style={{ marginTop: 24 }}>
          <div className="eyebrow">Reference</div>
          <h2 style={{ marginTop: 4 }}>
            This is our model
          </h2>
          <p className="muted" style={{ marginTop: 8, fontSize: "var(--text-sm)", marginBottom: 16 }}>
            Memorize her face, body, and especially her bust size. Every generation you accept needs to look like the same person.
          </p>
          <div style={{
            display: "grid",
            gridTemplateColumns: `repeat(${Math.min(refs.length, 4)}, 1fr)`,
            gap: 12,
          }}>
            {refs.map((r, i) => (
              <img
                key={i}
                src={safeUrl(r.url)}
                alt=""
                loading="lazy"
                style={{
                  width: "100%",
                  borderRadius: "var(--r-md)",
                  display: "block",
                  border: "1px solid var(--border)",
                }}
              />
            ))}
          </div>
        </section>
      )}

      <h2 style={{ marginTop: 24 }}>What to compare, in order of priority</h2>
      <ol>
        <li><strong>Identity.</strong> The face and body should clearly be our model — not a different girl, not a half-and-half morph of our model and the original.</li>
        <li><strong>Bust size.</strong> Nano Banana often shrinks the bust. It must match our model's reference photos — consistency across our content matters.</li>
        <li><strong>Pose.</strong> Same body position as the original frame.</li>
        <li><strong>Outfit and background.</strong> Identical to the original frame.</li>
      </ol>

      <h3 style={{ marginTop: 20 }}>Good examples</h3>
      <p className="muted" style={{ marginTop: 0, fontSize: 13 }}>Left of each pair: the original TikTok frame. Right: Nano Banana's generation. Everything matches — same model, right bust size, same pose, same outfit, same background.</p>
      <ExamplesGrid items={manifest?.nano_banana?.good} state={manifestState} side="good" showLabels={false} />

      <h2 style={{ marginTop: 32 }}>What gets rejected</h2>
      <ul>
        <li><strong>Different girl</strong> — Nano Banana generated someone who isn't our model</li>
        <li><strong>Morph</strong> — the result looks like a blend of our model and the original girl</li>
        <li><strong>Wrong pose</strong> — body position drifted from the original frame</li>
        <li><strong>Wrong background</strong> — Nano Banana invented or swapped the setting</li>
        <li><strong>Shrunken bust</strong> — body proportions don't match our model's references</li>
      </ul>

      <h3 style={{ marginTop: 20 }}>Bad examples — grouped by failure mode</h3>
      <ExamplesGrid items={manifest?.nano_banana?.bad} state={manifestState} side="bad" showLabels={true} />
    </article>
  );
}

// =====================================================================
// Page 4 — Kling video review
// =====================================================================

function KlingPage({ manifest, manifestState }) {
  return (
    <article>
      <h1 style={{ marginTop: 0 }}>Step 3 — Judging the final Kling video</h1>
      <p>
        Once Nano Banana gives us a good first frame, we send it plus the original TikTok to Kling, which generates the
        actual video. Your job is to decide if the result is clean enough to post on Instagram.
      </p>

      <h2 style={{ marginTop: 24 }}>What makes a good Kling video</h2>
      <p>The video should look <strong>real</strong> — not AI-generated, not robotic. Specifically:</p>
      <ul>
        <li><strong>No visible bugs or artifacts.</strong></li>
        <li><strong>Face stays consistent.</strong> Our model's face doesn't morph, distort, or flicker mid-clip.</li>
        <li><strong>Movement looks natural.</strong> No robot-stiff motion, no impossible body bending.</li>
        <li><strong>Camera is static.</strong> It doesn't pan or zoom — Kling shouldn't add motion that wasn't in the original.</li>
      </ul>

      <h3 style={{ marginTop: 20 }}>Good examples</h3>
      <ExamplesGrid items={manifest?.kling?.good} state={manifestState} side="good" showLabels={false} />

      <h2 style={{ marginTop: 32 }}>What gets rejected</h2>
      <ul>
        <li><strong>Clear bugs</strong> — visible artifacts, glitches, distortion</li>
        <li><strong>Weird or distorted face</strong> — face morphs, melts, or flickers</li>
        <li><strong>Robotic motion</strong> — stiff or impossible body movement</li>
        <li><strong>Camera moves</strong> — pan, zoom, or other motion Kling added on its own</li>
      </ul>

      <h3 style={{ marginTop: 20 }}>Bad examples — one of each</h3>
      <ExamplesGrid items={manifest?.kling?.bad} state={manifestState} side="bad" showLabels={true} />

      <section className="card" style={{ marginTop: 40, background: "var(--bg-subtle)", border: "1px solid var(--border)" }}>
        <h2 style={{ marginTop: 0 }}>Before you continue</h2>
        <p>
          When you click <strong>Continue to quiz</strong>, you'll answer 5 multiple-choice questions to confirm you understood the rules.
          You need <strong>4 of 5 correct</strong> to proceed. Fail it and the test ends — there's no retry.
        </p>
        <p style={{ marginBottom: 0 }}>
          <strong>Take your time on this lesson.</strong> Use the Back button to re-read anything you're unsure about. Don't continue until you're ready.
        </p>
      </section>
    </article>
  );
}

// =====================================================================
// Shared rendering
// =====================================================================

function ExamplesGrid({ items, state, side, showLabels }) {
  if (state === "loading") {
    return <p className="muted" style={{ marginTop: 12, fontSize: 13 }}>Loading examples…</p>;
  }
  if (state === "error" || !items || items.length === 0) {
    return null;
  }

  return (
    <div className="example-grid">
      {items.map((entry, i) => (
        <ExampleCell key={i} entry={entry} side={side} showLabel={showLabels} />
      ))}
    </div>
  );
}

function ExampleCell({ entry, side, showLabel }) {
  const isGood = side === "good";
  const label = showLabel ? labelFor(entry) : null;
  return (
    <div className="example-tile">
      <span className={`example-badge ${isGood ? "good" : "bad"}`}>{isGood ? "GOOD" : "BAD"}</span>
      <ExampleMedia entry={entry} />
      {label && <div className="example-caption">{label}</div>}
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
      />
    );
  }
  if (entry.type === "image") {
    return <img src={safeUrl(entry.url)} alt="" loading="lazy" />;
  }
  if (entry.type === "pair") {
    return (
      <div className="example-pair">
        <div className="pair-side">
          <img src={safeUrl(entry.original_url)} alt="" loading="lazy" />
          <span className="pair-tag">ORIGINAL</span>
        </div>
        <div className="pair-side">
          <img src={safeUrl(entry.generation_url)} alt="" loading="lazy" />
          <span className="pair-tag">AI</span>
        </div>
      </div>
    );
  }
  return null;
}
