import { useEffect, useState } from "react";
import { managerApi } from "../../api";

export default function ItemReplay({ jwt, decision, onClose }) {
  const [url, setUrl] = useState(null);

  useEffect(() => {
    managerApi.itemSignedUrl(jwt, decision.item_id).then((r) => setUrl(r.url));
  }, [jwt, decision.item_id]);

  const isVideo = decision.pool !== "nano_banana";

  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.85)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100 }}>
      <div style={{ background: "#141414", border: "1px solid #2a2a2a", borderRadius: 8, padding: 24, maxWidth: 720 }}>
        <button onClick={onClose} style={{ float: "right", background: "transparent", color: "#fff", border: "none", fontSize: 18 }}>×</button>
        <h3 style={{ marginTop: 0 }}>{decision.pool} — item #{decision.display_index + 1}</h3>
        <p className="muted">
          Candidate said: <strong>{decision.answer ? "Yes" : "No"}</strong> ·
          Correct answer: <strong>{decision.is_correct ? "(matches)" : "(opposite)"}</strong> ·
          Type: <strong>{decision.anchor_kind || "normal"}</strong>
        </p>
        {url ? (
          isVideo ? <video src={url} controls style={{ maxWidth: "100%" }} /> :
                    <img src={url} alt="" style={{ maxWidth: "100%" }} />
        ) : "Loading…"}
        {decision.justification && <p style={{ marginTop: 12 }}><em>"{decision.justification}"</em></p>}
      </div>
    </div>
  );
}
