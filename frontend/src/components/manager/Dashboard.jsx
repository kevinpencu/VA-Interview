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
    <div className="admin-shell">
      <header className="admin-topbar fade-in">
        <div className="left">
          <span className="eyebrow">VA Interview · Admin</span>
          <h1 className="title-display" style={{ fontSize: 44, margin: 0 }}>
            <em>Candidates</em>
          </h1>
        </div>
        <div className="actions">
          <button
            className="btn btn-ghost"
            title="Open a fresh candidate session in a new tab. Doesn't appear in the candidates list."
            onClick={async () => {
              const { token } = await managerApi.createPreviewInvite(jwt);
              window.open(`${window.location.origin}/test/${token}`, "_blank", "noopener");
            }}
          >
            ⛶ &nbsp;Preview as candidate
          </button>
          <button className="btn btn-primary" onClick={() => setShowInvite(true)}>
            + New invite
          </button>
        </div>
      </header>

      {loading ? (
        <p className="muted">Loading…</p>
      ) : rows.length === 0 ? (
        <div className="card-elevated fade-in-1" style={{ textAlign: "center", padding: 64 }}>
          <h2 style={{ marginBottom: 8 }}>No candidates yet</h2>
          <p className="muted" style={{ marginBottom: 24 }}>
            Generate an invite and share it with your first candidate.
          </p>
          <button className="btn btn-primary" onClick={() => setShowInvite(true)}>
            + Create first invite
          </button>
        </div>
      ) : (
        <table className="table fade-in-1">
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Status</th>
              <th>Recommendation</th>
              <th>Manager</th>
              <th>Total time</th>
              <th>Invited</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>
                  <Link
                    to={`/admin/candidates/${r.id}`}
                    style={{ color: "var(--color-text)", borderBottom: "1px solid var(--color-border-strong)" }}
                  >
                    {r.candidate_name || r.invited_label || "—"}
                  </Link>
                  <div className="muted mono" style={{ fontSize: 11, marginTop: 2 }}>
                    {r.candidate_email || r.invited_label_email || ""}
                  </div>
                </td>
                <td><StatusPill row={r} /></td>
                <td><RecBadge rec={r.recommendation} /></td>
                <td className="muted">{r.manager_decision || "—"}</td>
                <td className="mono dim" style={{ fontSize: 13 }}>
                  {r.total_time_seconds ? `${Math.round(r.total_time_seconds / 60)}m` : "—"}
                </td>
                <td className="dim" style={{ fontSize: 13 }}>
                  {new Date(r.created_at).toLocaleDateString(undefined, {
                    month: "short", day: "numeric",
                  })}
                </td>
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

function StatusPill({ row }) {
  if (row.submitted_at) return <span className="badge badge-neutral">Submitted</span>;
  if (row.started_at) return <span className="badge badge-borderline">In progress</span>;
  return <span className="badge badge-neutral">Invited</span>;
}

function RecBadge({ rec }) {
  if (!rec) return <span className="dim">—</span>;
  const klass = { pass: "badge-pass", borderline: "badge-borderline", fail: "badge-fail" }[rec];
  return <span className={`badge ${klass}`}>{rec}</span>;
}
