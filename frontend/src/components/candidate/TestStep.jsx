import { useEffect, useRef, useState } from "react";
import { candidateApi } from "../../api";
import JustificationModal from "./JustificationModal.jsx";

const COPY = {
  tiktok: {
    name: "TikTok screening",
    short: "TikTok",
    question: "Would you save this TikTok?",
    yes: { label: "Yes, save it", sub: "Worth recreating" },
    no:  { label: "No, skip", sub: "Wrong language / boring / can't recreate" },
    type: "video",
    rejectIf: [
      <><strong>Non-English</strong> audio or song</>,
      <><strong>Ugly or non-American</strong> background</>,
      <>Girl moves <strong>too far from the camera</strong></>,
      <><strong>Weird or hard-to-copy</strong> dance moves</>,
      <>Phone <strong>flips to landscape</strong> mid-video</>,
    ],
  },
  nano_banana: {
    name: "Nano-banana review",
    short: "Nano-banana",
    question: "Would you use this generation?",
    yes: { label: "Yes, use it", sub: "Identity matches, no artifacts" },
    no:  { label: "No, reject", sub: "Wrong identity / artifacts / off-prompt" },
    type: "pair",
    rejectIf: [
      <><strong>Different girl</strong> — not our model</>,
      <><strong>Morph</strong> — blend of our model and another face</>,
      <><strong>Wrong pose</strong> vs. the original frame</>,
      <><strong>Wrong background or outfit</strong></>,
      <><strong>Shrunken bust</strong> — must match her references</>,
      <><strong>AI artifacts</strong> — weird hands, extra fingers, melted features</>,
    ],
  },
  kling: {
    name: "Kling review",
    short: "Kling",
    question: "Did this come out well?",
    yes: { label: "Good", sub: "Real motion, consistent face" },
    no:  { label: "Bad", sub: "Flicker / warp / inconsistent / boring" },
    type: "video",
    rejectIf: [
      <>Any <strong>visible bugs, artifacts, or glitches</strong></>,
      <>Face <strong>distorts, morphs, or flickers</strong> mid-clip</>,
      <><strong>Robotic or impossible</strong> body movement</>,
      <>Camera <strong>pans or zooms</strong> on its own</>,
      <>Looks <strong>clearly AI-generated</strong> or unreal</>,
    ],
  },
};

function requestFullscreen(el) {
  if (!el) return;
  if (el.requestFullscreen) return el.requestFullscreen();
  if (el.webkitRequestFullscreen) return el.webkitRequestFullscreen();
  if (el.webkitEnterFullscreen) return el.webkitEnterFullscreen();
}

function stepNumber(p) { return { tiktok: 1, nano_banana: 2, kling: 3 }[p]; }

export default function TestStep({ token, pool, item, progress, onAdvance }) {
  const c = COPY[pool];
  const [shownAt] = useState(() => new Date().toISOString());
  const startMs = useRef(performance.now());
  const [submitting, setSubmitting] = useState(false);
  const [pendingJustification, setPendingJustification] = useState(null);
  const [pendingAdvance, setPendingAdvance] = useState(null);

  useEffect(() => {
    startMs.current = performance.now();
  }, [item.id]);

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
        setPendingAdvance(() => async () => { await onAdvance(res.next); });
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
      const tag = e.target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA") return;
      if (e.key === "ArrowRight") { e.preventDefault(); answer(true); }
      if (e.key === "ArrowLeft")  { e.preventDefault(); answer(false); }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pendingJustification, item.id]);

  // Suppress accidental navigation away mid-test
  useEffect(() => {
    function onBeforeUnload(e) { e.preventDefault(); e.returnValue = ""; }
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, []);

  async function submitJustification(text) {
    await candidateApi.justification(token, pendingJustification.decisionId, text);
    setPendingJustification(null);
    if (pendingAdvance) await pendingAdvance();
  }

  const isPair = c.type === "pair";

  return (
    <div className="test-step">
      <header className="test-step-header">
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <span className="label">Step {stepNumber(pool)} of 3</span>
          <span style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.02em" }}>
            {c.name}
          </span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "flex-end" }}>
          <span className="label">Progress</span>
          <span className="mono" style={{ fontSize: 20, color: "var(--text)", letterSpacing: "0", fontWeight: 500 }}>
            {String(progress + 1).padStart(2, "0")}
            <span className="dim" style={{ margin: "0 4px" }}>/</span>
            30
          </span>
        </div>
      </header>

      <div className={`test-step-body ${isPair ? "layout-pair" : "layout-video"}`} key={item.id}>
        {isPair ? <NanoBananaContent item={item} /> : <VideoContent item={item} />}

        {isPair ? (
          <div className="pair-actions-row fade-in-1">
            <div className="actions-col">
              <h2 className="question">{c.question}</h2>
              <button className="answer-btn good" onClick={() => answer(true)} disabled={submitting}>
                <span className="answer-main">{c.yes.label}</span>
                <span className="answer-sub">{c.yes.sub}</span>
              </button>
              <button className="answer-btn bad" onClick={() => answer(false)} disabled={submitting}>
                <span className="answer-main">{c.no.label}</span>
                <span className="answer-sub">{c.no.sub}</span>
              </button>
              <div className="keyboard-hint">
                <kbd>←</kbd> reject &nbsp;·&nbsp; <kbd>→</kbd> accept
              </div>
            </div>
            <div className="reject-checklist">
              <span className="reject-label">Reject if you see</span>
              <ul>
                {c.rejectIf.map((entry, i) => <li key={i}>{entry}</li>)}
              </ul>
            </div>
          </div>
        ) : (
          <div className="actions-col fade-in-1">
            <h2 className="question">{c.question}</h2>

            <button
              className="answer-btn good"
              onClick={() => answer(true)}
              disabled={submitting}
            >
              <span className="answer-main">{c.yes.label}</span>
              <span className="answer-sub">{c.yes.sub}</span>
            </button>

            <button
              className="answer-btn bad"
              onClick={() => answer(false)}
              disabled={submitting}
            >
              <span className="answer-main">{c.no.label}</span>
              <span className="answer-sub">{c.no.sub}</span>
            </button>

            <div className="reject-checklist">
              <span className="reject-label">Reject if you see</span>
              <ul>
                {c.rejectIf.map((entry, i) => <li key={i}>{entry}</li>)}
              </ul>
          </div>

            <div className="keyboard-hint">
              <kbd>←</kbd> reject &nbsp;·&nbsp; <kbd>→</kbd> accept
            </div>
          </div>
        )}
      </div>

      {pendingJustification && (
        <JustificationModal onSubmit={submitJustification} onCancel={() => {}} />
      )}
    </div>
  );
}

/* --- Video content (TikTok / Kling) ---------------------------- */

function VideoContent({ item }) {
  const ref = useRef(null);
  return (
    <div className="media-block fade-in">
      <div className="media-frame aspect-9-16">
        <video ref={ref} src={item.storage_url} controls autoPlay playsInline />
      </div>
      <div className="fullscreen-bar">
        <button className="btn-icon" onClick={() => requestFullscreen(ref.current)}>
          ⛶ &nbsp;Fullscreen
        </button>
      </div>
    </div>
  );
}

/* --- Nano-banana content — original + AI side-by-side --------- */

function NanoBananaContent({ item }) {
  const [lightbox, setLightbox] = useState(null);

  useEffect(() => {
    if (!lightbox) return;
    function onEsc(e) { if (e.key === "Escape") setLightbox(null); }
    window.addEventListener("keydown", onEsc);
    return () => window.removeEventListener("keydown", onEsc);
  }, [lightbox]);

  return (
    <div className="media-block fade-in">
      <div className="nb-pair-row">
        <NBImage
          src={item.reference_url}
          label="Original TikTok frame"
          onZoom={() => setLightbox({ src: item.reference_url, label: "Original TikTok frame" })}
        />
        <NBImage
          src={item.storage_url}
          label="Nano-banana generation"
          accent
          onZoom={() => setLightbox({ src: item.storage_url, label: "Nano-banana generation" })}
        />
      </div>

      {lightbox && (
        <div className="lightbox" onClick={() => setLightbox(null)}>
          <div className="lightbox-content" onClick={(e) => e.stopPropagation()}>
            <span className="label" style={{ alignSelf: "flex-start", color: "#FFFFFF" }}>{lightbox.label}</span>
            <img src={lightbox.src} alt="" />
          </div>
          <button className="lightbox-close" onClick={() => setLightbox(null)}>Esc · Close</button>
        </div>
      )}
    </div>
  );
}

function NBImage({ src, label, onZoom }) {
  return (
    <div className="nb-side">
      <div className="nb-caption">
        <span className="label">{label}</span>
        <button className="btn-icon" onClick={onZoom} aria-label="Open fullscreen">⛶ Fullscreen</button>
      </div>
      <div className="media-frame">
        <img src={src} alt="" onClick={onZoom} style={{ cursor: "zoom-in" }} />
      </div>
    </div>
  );
}
