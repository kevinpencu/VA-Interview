import { useCallback, useEffect, useState } from "react";
import { candidateApi } from "../api";

export function useTestSession(token) {
  const [state, setState] = useState({ state: "loading", progress_in_step: 0, next_item: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async (attempt = 0) => {
    setLoading(true);
    setError(null);
    try {
      const s = await candidateApi.state(token);
      setState(s);
    } catch (e) {
      // Transient network or 5xx errors (redeploy mid-flight, brief outage) —
      // retry with backoff instead of showing the candidate "Link unavailable".
      const transient = !e.status || e.status >= 500;
      if (transient && attempt < 4) {
        const backoff = 600 * Math.pow(2, attempt);
        setTimeout(() => refresh(attempt + 1), backoff);
        return;
      }
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { refresh(); }, [refresh]);

  return { state, setState, loading, error, refresh };
}
