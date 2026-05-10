import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { managerApi } from "../../api";
import ItemReplay from "./ItemReplay.jsx";

export default function CandidateDetail({ jwt }) {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [replay, setReplay] = useState(null);
  const [savingNotes, setSavingNotes] = useState(false);
  const [notes, setNotes] = useState("");

  const load = useCallback(async () => {
    const d = await managerApi.candidateDetail(jwt, id);
    setData(d);
    setNotes(d.manager_notes || "");
  }, [jwt, id]);
  useEffect(() => { load(); }, [load]);

  async function decide(decision) {
    await managerApi.patchCandidate(jwt, id, { manager_decision: decision });
    await load();
  }
  async function saveNotes() {
    setSavingNotes(true);
    await managerApi.patchCandidate(jwt, id, { manager_notes: notes });
    setSavingNotes(false);
  }

  if (!data) return <div style={{ padding: 32 }}>Loading…</div>;
  const { row, auto_fail_reasons, quiz_correct, quiz_total, tab_switches, steps, free_text_justifications, decisions } = data;

  return (
    <div style={{ maxWidth: 1100, margin: "32px auto", padding: 16 }}>
      <h1>{row.candidate_name || row.invited_label}</h1>
      <p className="muted">{row.candidate_email || row.invited_label_email}</p>

      <div style={{ display: "flex", gap: 24, marginTop: 16 }}>
        <Stat label="Recommendation" value={row.recommendation?.toUpperCase() || "—"} />
        <Stat label="Quiz" value={`${quiz_correct}/${quiz_total}`} />
        <Stat label="Tab switches" value={tab_switches} />
        <Stat label="Total time" value={row.total_time_seconds ? `${Math.round(row.total_time_seconds / 60)}m` : "—"} />
      </div>

      {auto_fail_reasons?.length > 0 && (
        <div style={{ marginTop: 24, padding: 16, background: "#3a1f1f", borderRadius: 8, border: "1px solid #5a2a2a" }}>
          <strong>Auto-fail reasons</strong>
          <ul style={{ marginBottom: 0 }}>
            {auto_fail_reasons.map((r) => <li key={r}>{r}</li>)}
          </ul>
        </div>
      )}

      <h2 style={{ marginTop: 32 }}>Per-step</h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr style={{ borderBottom: "1px solid #2a2a2a", textAlign: "left" }}>
          <th style={th}>Step</th><th style={th}>Accuracy</th><th style={th}>Obvious bad caught</th>
          <th style={th}>Obvious good caught</th><th style={th}>Dupe consistency</th>
          <th style={th}>Median dwell</th><th style={th}>Duration</th>
        </tr></thead>
        <tbody>
          {steps.map((s) => (
            <tr key={s.pool} style={{ borderBottom: "1px solid #1a1a1a" }}>
              <td style={td}>{s.pool}</td>
              <td style={td}>{(s.accuracy * 100).toFixed(0)}%</td>
              <td style={td}>{s.obvious_bad_caught}/4</td>
              <td style={td}>{s.obvious_good_caught}/4</td>
              <td style={td}>{s.duplicate_consistency}/2</td>
              <td style={td}>{s.median_dwell_ms ? `${(s.median_dwell_ms / 1000).toFixed(1)}s` : "—"}</td>
              <td style={td}>{s.duration_seconds ? `${Math.round(s.duration_seconds / 60)}m` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {free_text_justifications.length > 0 && (
        <>
          <h2 style={{ marginTop: 32 }}>Free-text justifications</h2>
          {free_text_justifications.map((j, i) => (
            <div key={i} className="card" style={{ marginTop: 8 }}>
              <span className="label">{j.pool}</span>
              <p style={{ margin: "4px 0" }}>{j.justification}</p>
            </div>
          ))}
        </>
      )}

      <h2 style={{ marginTop: 32 }}>All decisions</h2>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead><tr style={{ borderBottom: "1px solid #2a2a2a", textAlign: "left" }}>
          <th style={th}>Pool</th><th style={th}>#</th><th style={th}>Type</th>
          <th style={th}>Their answer</th><th style={th}>Correct?</th><th style={th}>Dwell</th><th></th>
        </tr></thead>
        <tbody>
          {decisions.map((d) => (
            <tr key={d.id} style={{ borderBottom: "1px solid #1a1a1a", background: !d.is_correct ? "#1f0d0d" : "transparent" }}>
              <td style={td}>{d.pool}</td>
              <td style={td}>{d.display_index + 1}{d.is_duplicate ? "*" : ""}</td>
              <td style={td}>{d.anchor_kind || "normal"}</td>
              <td style={td}>{d.answer ? "Yes" : "No"}</td>
              <td style={td}>{d.is_correct ? "✓" : "✗"}</td>
              <td style={td}>{(d.dwell_ms / 1000).toFixed(1)}s</td>
              <td style={td}><button onClick={() => setReplay(d)} style={{ padding: "4px 10px", background: "transparent", border: "1px solid #333", color: "#fff", borderRadius: 4 }}>Replay</button></td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2 style={{ marginTop: 32 }}>Manager decision</h2>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={() => decide("hired")} style={{ padding: "8px 16px", background: row.manager_decision === "hired" ? "#22c55e" : "transparent", color: row.manager_decision === "hired" ? "#000" : "#fff", border: "1px solid #333", borderRadius: 6 }}>Hire</button>
        <button onClick={() => decide("rejected")} style={{ padding: "8px 16px", background: row.manager_decision === "rejected" ? "#ef4444" : "transparent", color: row.manager_decision === "rejected" ? "#000" : "#fff", border: "1px solid #333", borderRadius: 6 }}>Reject</button>
      </div>

      <h2 style={{ marginTop: 32 }}>Notes</h2>
      <textarea value={notes} onChange={(e) => setNotes(e.target.value)} rows={4}
        style={{ width: "100%", padding: 10, background: "#0a0a0a", color: "#fff", border: "1px solid #2a2a2a", borderRadius: 6 }} />
      <button onClick={saveNotes} disabled={savingNotes}
        style={{ marginTop: 8, padding: "8px 16px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600 }}>
        {savingNotes ? "Saving…" : "Save notes"}
      </button>

      {replay && <ItemReplay jwt={jwt} decision={replay} onClose={() => setReplay(null)} />}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="card" style={{ minWidth: 120 }}>
      <span className="label">{label}</span>
      <p style={{ margin: 0, fontSize: 22, fontWeight: 600 }}>{value}</p>
    </div>
  );
}
const th = { padding: "10px 8px", fontSize: 11, textTransform: "uppercase", color: "#888" };
const td = { padding: "10px 8px" };
