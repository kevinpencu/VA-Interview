import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { managerApi } from "../../api";
import InviteModal from "./InviteModal.jsx";

export default function Dashboard({ jwt }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showInvite, setShowInvite] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setRows(await managerApi.listCandidates(jwt));
    setLoading(false);
  }, [jwt]);

  useEffect(() => { load(); }, [load]);

  return (
    <div style={{ maxWidth: 1100, margin: "32px auto", padding: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h1 style={{ margin: 0 }}>Candidates</h1>
        <button onClick={() => setShowInvite(true)}
          style={{ padding: "8px 16px", background: "#fff", color: "#000", border: "none", borderRadius: 6, fontWeight: 600 }}>
          + New invite
        </button>
      </div>
      {loading ? <p>Loading…</p> : (
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 24 }}>
          <thead>
            <tr style={{ textAlign: "left", borderBottom: "1px solid #2a2a2a" }}>
              <th style={th}>Name</th>
              <th style={th}>Status</th>
              <th style={th}>Recommendation</th>
              <th style={th}>Manager</th>
              <th style={th}>Total time</th>
              <th style={th}>Invited</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} style={{ borderBottom: "1px solid #1a1a1a" }}>
                <td style={td}>
                  <Link to={`/admin/candidates/${r.id}`}>{r.candidate_name || r.invited_label || "—"}</Link>
                  <div className="muted" style={{ fontSize: 11 }}>{r.candidate_email || r.invited_label_email || ""}</div>
                </td>
                <td style={td}>{statusOf(r)}</td>
                <td style={td}><RecBadge rec={r.recommendation} /></td>
                <td style={td}>{r.manager_decision || "—"}</td>
                <td style={td}>{r.total_time_seconds ? `${Math.round(r.total_time_seconds / 60)}m` : "—"}</td>
                <td style={td}>{new Date(r.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {showInvite && (
        <InviteModal
          token={jwt}
          onClose={() => setShowInvite(false)}
          onCreated={load}
        />
      )}
    </div>
  );
}

function statusOf(r) {
  if (r.submitted_at) return "Submitted";
  if (r.started_at) return "In progress";
  return "Invited";
}

function RecBadge({ rec }) {
  if (!rec) return <span className="muted">—</span>;
  const color = { pass: "#22c55e", borderline: "#f59e0b", fail: "#ef4444" }[rec];
  return (
    <span style={{ background: color, color: "#000", padding: "2px 8px", borderRadius: 999, fontSize: 12, fontWeight: 700 }}>
      {rec.toUpperCase()}
    </span>
  );
}

const th = { padding: "12px 8px", fontSize: 11, textTransform: "uppercase", color: "#888", letterSpacing: 0.05 };
const td = { padding: "12px 8px" };
