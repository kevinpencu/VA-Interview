import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { managerApi } from "../../api";
import ItemReplay from "./ItemReplay.jsx";

const POOL_LABEL = { tiktok: "TikTok", nano_banana: "Nano-banana", kling: "Kling" };

export default function CandidateDetail({ jwt }) {
  const { id } = useParams();
  const [data, setData] = useState(null);
  const [replay, setReplay] = useState(null);
  const [savingNotes, setSavingNotes] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);
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
    setSavedFlash(true);
    setTimeout(() => setSavedFlash(false), 1500);
  }

  if (!data) {
    return (
      <div className="admin-shell">
        <p className="muted">Loading…</p>
      </div>
    );
  }
  const { row, auto_fail_reasons, quiz_correct, quiz_total, tab_switches, steps, free_text_justifications, decisions } = data;
  const recClass = { pass: "badge-pass", borderline: "badge-borderline", fail: "badge-fail" }[row.recommendation] || "badge-neutral";

  return (
    <div className="admin-shell">
      <Link to="/admin" className="label" style={{ display: "inline-flex", alignItems: "center", gap: 6, marginBottom: 16, textDecoration: "none" }}>
        ← Candidates
      </Link>

      <header className="admin-topbar" style={{ marginBottom: 24 }}>
        <div className="left">
          <span className="eyebrow">Candidate</span>
          <h1 style={{ margin: 0 }}>{row.candidate_name || row.invited_label || "—"}</h1>
          <p className="muted mono" style={{ margin: "4px 0 0", fontSize: 13 }}>
            {row.candidate_email || row.invited_label_email || ""}
          </p>
        </div>
        <div className="actions" style={{ alignItems: "center" }}>
          <span className={`badge ${recClass}`} style={{ fontSize: 13, padding: "4px 12px" }}>
            {row.recommendation ? row.recommendation.toUpperCase() : "—"}
          </span>
        </div>
      </header>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12 }}>
        <Stat label="Recommendation" value={row.recommendation ? row.recommendation.toUpperCase() : "—"} />
        <Stat label="Quiz" value={`${quiz_correct} / ${quiz_total}`} />
        <Stat label="Tab switches" value={tab_switches} />
        <Stat label="Total time" value={row.total_time_seconds ? `${Math.round(row.total_time_seconds / 60)} min` : "—"} />
      </div>

      {auto_fail_reasons?.length > 0 && (
        <div style={{
          marginTop: 24,
          padding: 16,
          background: "var(--bad-bg)",
          borderRadius: "var(--r-lg)",
          border: "1px solid var(--bad-border)",
          borderLeft: "3px solid var(--bad)",
        }}>
          <strong style={{ color: "var(--bad)" }}>Auto-fail triggered</strong>
          <ul style={{ marginTop: 8, marginBottom: 0, color: "var(--text-soft)" }}>
            {auto_fail_reasons.map((r) => <li key={r}><code className="mono" style={{ fontSize: 13 }}>{r}</code></li>)}
          </ul>
        </div>
      )}

      <h2>Per-step breakdown</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Step</th>
            <th>Accuracy</th>
            <th>Dupe consistency</th>
            <th>Median dwell</th>
            <th>Duration</th>
          </tr>
        </thead>
        <tbody>
          {steps.map((s) => (
            <tr key={s.pool}>
              <td style={{ fontWeight: 500, color: "var(--text)" }}>{POOL_LABEL[s.pool] || s.pool}</td>
              <td className="mono">{(s.accuracy * 100).toFixed(0)}%</td>
              <td className="mono">
                {s.expected_duplicates === 0 ? <span className="dim">—</span> : `${s.duplicate_consistency} / ${s.expected_duplicates}`}
              </td>
              <td className="mono">{s.median_dwell_ms ? `${(s.median_dwell_ms / 1000).toFixed(1)}s` : "—"}</td>
              <td className="mono">{s.duration_seconds ? `${Math.round(s.duration_seconds / 60)} min` : "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {free_text_justifications.length > 0 && (
        <>
          <h2>Free-text justifications</h2>
          <div style={{ display: "grid", gap: 8 }}>
            {free_text_justifications.map((j, i) => (
              <div key={i} className="card">
                <span className="label">{POOL_LABEL[j.pool] || j.pool}</span>
                <p style={{ margin: "6px 0 0", color: "var(--text)" }}>{j.justification}</p>
              </div>
            ))}
          </div>
        </>
      )}

      <h2>All decisions</h2>
      <table className="table">
        <thead>
          <tr>
            <th>Step</th>
            <th>#</th>
            <th>Their answer</th>
            <th>Correct?</th>
            <th>Dwell</th>
            <th style={{ width: 110 }}></th>
          </tr>
        </thead>
        <tbody>
          {decisions.map((d) => (
            <tr key={d.id} style={!d.is_correct ? { background: "var(--bad-bg)" } : undefined}>
              <td style={{ fontWeight: 500, color: "var(--text)" }}>{POOL_LABEL[d.pool] || d.pool}</td>
              <td className="mono">
                {d.display_index + 1}
                {d.is_duplicate && <span className="dim" title="Duplicate of an earlier item">*</span>}
              </td>
              <td className="mono" style={{ fontWeight: 500 }}>{d.answer ? "Yes" : "No"}</td>
              <td className="mono">
                {d.is_correct
                  ? <span style={{ color: "var(--good)", fontWeight: 600 }}>✓</span>
                  : <span style={{ color: "var(--bad)", fontWeight: 600 }}>✗</span>}
              </td>
              <td className="mono dim">{(d.dwell_ms / 1000).toFixed(1)}s</td>
              <td>
                <button onClick={() => setReplay(d)} className="btn btn-ghost" style={{ padding: "5px 12px", fontSize: 13 }}>
                  Replay
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <h2>Your decision</h2>
      <div style={{ display: "flex", gap: 8 }}>
        <button
          onClick={() => decide("hired")}
          className={row.manager_decision === "hired" ? "btn btn-good" : "btn btn-ghost"}
          style={{ padding: "10px 24px", fontWeight: 600 }}
        >
          {row.manager_decision === "hired" ? "✓ " : ""}Hire
        </button>
        <button
          onClick={() => decide("rejected")}
          className={row.manager_decision === "rejected" ? "btn btn-bad" : "btn btn-ghost"}
          style={{ padding: "10px 24px", fontWeight: 600 }}
        >
          {row.manager_decision === "rejected" ? "✓ " : ""}Reject
        </button>
      </div>

      <h2>Notes</h2>
      <textarea
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={4}
        className="input"
        placeholder="Private notes about this candidate (only visible to you)"
        style={{ resize: "vertical", minHeight: 100 }}
      />
      <div style={{ display: "flex", gap: 8, alignItems: "center", marginTop: 8 }}>
        <button onClick={saveNotes} disabled={savingNotes} className="btn btn-primary" style={{ padding: "8px 18px" }}>
          {savingNotes ? "Saving…" : "Save notes"}
        </button>
        {savedFlash && <span className="muted" style={{ fontSize: 13 }}>✓ Saved</span>}
      </div>

      {replay && <ItemReplay jwt={jwt} decision={replay} onClose={() => setReplay(null)} />}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="card">
      <span className="label">{label}</span>
      <p style={{ margin: "6px 0 0", fontSize: 26, fontWeight: 600, color: "var(--text)", lineHeight: 1.1 }}>{value}</p>
    </div>
  );
}
