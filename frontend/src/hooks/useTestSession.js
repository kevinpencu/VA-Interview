import { useCallback, useEffect, useState } from "react";
import { candidateApi } from "../api";

export function useTestSession(token) {
  const [state, setState] = useState({ state: "loading", progress_in_step: 0, next_item: null });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const s = await candidateApi.state(token);
      setState(s);
    } catch (e) {
      setError(e);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { refresh(); }, [refresh]);

  return { state, setState, loading, error, refresh };
}
