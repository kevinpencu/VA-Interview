import { useParams } from "react-router-dom";
import { useTestSession } from "../../hooks/useTestSession.js";
import InvalidLink from "./InvalidLink.jsx";
import Welcome from "./Welcome.jsx";
import Tutorial from "./Tutorial.jsx";
import Quiz from "./Quiz.jsx";
import StepIntro from "./StepIntro.jsx";
import SubmitScreen from "./Submit.jsx";

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
    case "needs_tutorial":
      return <Tutorial token={token} onContinue={refresh} />;
    case "needs_quiz":
      return <Quiz token={token} onPass={refresh} onFail={refresh} />;
    case "step_tiktok_intro":
      return <StepIntro token={token} pool="tiktok" onContinue={refresh} />;
    case "step_nano_banana_intro":
      return <StepIntro token={token} pool="nano_banana" onContinue={refresh} />;
    case "step_kling_intro":
      return <StepIntro token={token} pool="kling" onContinue={refresh} />;
    case "submitted":
      return <SubmitScreen />;
    case "step_tiktok_in_progress":
    case "step_nano_banana_in_progress":
    case "step_kling_in_progress":
      return <div style={{ padding: 48 }}>Step screen — implemented in Task 18.</div>;
    default:
      return <div style={{ padding: 48 }}>State: {state.state} — coming next.</div>;
  }
}
