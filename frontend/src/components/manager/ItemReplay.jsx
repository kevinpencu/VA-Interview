import { useEffect, useState } from "react";
import { managerApi } from "../../api";

export default function ItemReplay({ jwt, decision, onClose }) {
  const [url, setUrl] = useState(null);

  useEffect(() => {
    managerApi.itemSignedUrl(jwt, decision.item_id).then((r) => setUrl(r.url));
  }, [jwt, decision.item_id]);

  useEffect(() => {
    function onKey(e) { if (e.key === "Escape") onClose(); }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const isVideo = decision.pool !== "nano_banana";

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "auto",
          maxWidth: "min(720px, 92vw)",
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          padding: 0,
        }}
      >
        <header style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "16px 20px",
          borderBottom: "1px solid var(--border)",
        }}>
          <div>
            <div className="label" style={{ marginBottom: 2 }}>
              {decision.pool} · item {decision.display_index + 1}
            </div>
            <div style={{ fontSize: 14, color: "var(--text-soft)" }}>
              Candidate said <strong>{decision.answer ? "Yes" : "No"}</strong>{" "}
              <span className="dim">·</span>{" "}
              <span className={decision.is_correct ? "" : ""} style={{ color: decision.is_correct ? "var(--good)" : "var(--bad)", fontWeight: 500 }}>
                {decision.is_correct ? "Correct" : "Wrong"}
              </span>
            </div>
          </div>
          <button onClick={onClose} className="btn btn-ghost" style={{ padding: "6px 12px" }}>
            Close · Esc
          </button>
        </header>

        <div style={{
          padding: 16,
          overflow: "auto",
          background: "#000",
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          minHeight: 200,
        }}>
          {url ? (
            isVideo
              ? <video src={url} controls autoPlay style={{ maxWidth: "100%", maxHeight: "70vh", display: "block", borderRadius: 6 }} />
              : <img src={url} alt="" style={{ maxWidth: "100%", maxHeight: "70vh", display: "block", borderRadius: 6 }} />
          ) : (
            <span className="muted">Loading…</span>
          )}
        </div>

        {decision.justification && (
          <div style={{ padding: "12px 20px", borderTop: "1px solid var(--border)", background: "var(--bg-subtle)" }}>
            <span className="label" style={{ marginRight: 8 }}>Their reasoning</span>
            <span style={{ color: "var(--text-soft)" }}>"{decision.justification}"</span>
          </div>
        )}
      </div>
    </div>
  );
}
