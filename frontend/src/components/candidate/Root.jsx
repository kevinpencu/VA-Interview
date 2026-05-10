import { useParams } from "react-router-dom";
import { useTestSession } from "../../hooks/useTestSession.js";
import InvalidLink from "./InvalidLink.jsx";
import Welcome from "./Welcome.jsx";

export default function CandidateRoot() {
  const { token } = useParams();
  const { state, refresh, loading, error } = useTestSession(token);

  if (loading) return <div style={{ padding: 48 }}>Loading…</div>;
  if (error) return <InvalidLink />;

  switch (state.state) {
    case "invalid":
      return <InvalidLink />;
    case "session_in_use":
      return (
        <div style={{ padding: 48, textAlign: "center" }}>
          <h1>Test in progress in another window</h1>
          <p className="muted">Close other tabs/windows showing this link, then refresh.</p>
        </div>
      );
    case "needs_name":
      return <Welcome token={token} onStarted={refresh} />;
    default:
      // Other states wired in later tasks
      return <div style={{ padding: 48 }}>State: {state.state} — coming next.</div>;
  }
}
