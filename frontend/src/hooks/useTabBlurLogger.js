import { useEffect } from "react";
import { candidateApi } from "../api";

export function useTabBlurLogger(token, enabled) {
  useEffect(() => {
    if (!enabled) return;
    function onVis() {
      const kind = document.visibilityState === "hidden" ? "tab_blur" : "tab_focus";
      candidateApi.event(token, kind).catch(() => {});
    }
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [token, enabled]);
}
