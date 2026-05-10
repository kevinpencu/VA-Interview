import { useParams } from "react-router-dom";
import { useTestSession } from "../../hooks/useTestSession.js";
import { useTabBlurLogger } from "../../hooks/useTabBlurLogger.js";
import { candidateApi } from "../../api";
import InvalidLink from "./InvalidLink.jsx";
import Welcome from "./Welcome.jsx";
import Tutorial from "./Tutorial.jsx";
import Quiz from "./Quiz.jsx";
import StepIntro from "./StepIntro.jsx";
import SubmitScreen from "./Submit.jsx";
import TestStep from "./TestStep.jsx";

export default function CandidateRoot() {
  const { token } = useParams();
  const { state, setState, refresh, loading, error } = useTestSession(token);
  const inSession = !["loading", "invalid", "needs_name"].includes(state.state);
  useTabBlurLogger(token, inSession);

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
    case "step_kling_in_progress": {
      if (!state.next_item) return <div style={{ padding: 48 }}>Loading next item…</div>;
      const pool = state.next_item.pool;
      return (
        <TestStep
          token={token}
          pool={pool}
          item={state.next_item}
          progress={state.progress_in_step}
          onAdvance={async (next) => {
            if (next?.test_complete) {
              await candidateApi.submit(token);
              await refresh();
            } else if (next?.step_complete) {
              await refresh();   // server will route to the next step's intro
            } else if (next?.item) {
              // Optimistically update next_item without a full refresh
              setState((s) => ({
                ...s,
                progress_in_step: state.progress_in_step + 1,
                next_item: next.item,
              }));
            } else {
              await refresh();
            }
          }}
        />
      );
    }
    default:
      return <div style={{ padding: 48 }}>State: {state.state} — coming next.</div>;
  }
}
