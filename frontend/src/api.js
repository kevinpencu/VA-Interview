const BASE = "";

/** Sleep helper. */
function sleep(ms) { return new Promise((r) => setTimeout(r, ms)); }

/**
 * Fetch wrapper with automatic retry on transient errors.
 *
 * Retries on:
 *   - Network errors (fetch throws, browser offline, DNS, etc.)
 *   - 5xx server errors (Railway redeploy, container restart, Supabase blip)
 *   - Per-request timeout (12s)
 *
 * Does NOT retry on 4xx — those are client errors we should surface immediately.
 *
 * Backoff: 400ms, 800ms, 1.6s, 3.2s, 6.4s (≈12s total) before throwing.
 */
async function call(method, path, opts = {}) {
  const { body, auth, retries = 5, timeoutMs = 12000 } = opts;
  const headers = { "Content-Type": "application/json" };
  if (auth) headers.Authorization = `Bearer ${auth}`;

  let lastErr;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const ac = new AbortController();
    const timer = setTimeout(() => ac.abort(), timeoutMs);
    let res;
    try {
      res = await fetch(`${BASE}${path}`, {
        method,
        credentials: "include",
        headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: ac.signal,
      });
    } catch (e) {
      // Network error, abort, DNS fail, browser offline, etc.
      clearTimeout(timer);
      lastErr = e;
      if (attempt < retries) {
        await sleep(400 * Math.pow(2, attempt));
        continue;
      }
      throw e;
    }
    clearTimeout(timer);

    if (res.status >= 500 && attempt < retries) {
      // Backend transient (redeploy mid-flight, 502, 504, 503...) — retry.
      await sleep(400 * Math.pow(2, attempt));
      continue;
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw Object.assign(new Error(err.detail || `${res.status}`), { status: res.status, body: err });
    }
    return res.json();
  }
  throw lastErr;
}

export const candidateApi = {
  state: (token) => call("GET", `/api/test/${token}/state`),
  start: (token, name, email) => call("POST", `/api/test/${token}/start`, { body: { name, email } }),
  tutorialAck: (token) => call("POST", `/api/test/${token}/tutorial-acknowledged`),
  quiz: (token, answers) => call("POST", `/api/test/${token}/quiz`, { body: { answers } }),
  stepIntroAck: (token, pool) => call("POST", `/api/test/${token}/step/${pool}/intro-acknowledged`),
  decision: (token, payload) => call("POST", `/api/test/${token}/decision`, { body: payload }),
  justification: (token, decisionId, text) =>
    call("POST", `/api/test/${token}/justification`, { body: { decision_id: decisionId, justification: text } }),
  // Events are best-effort. Don't retry tab_blur events — they're not load-bearing.
  event: (token, kind, meta = {}) => call("POST", `/api/test/${token}/event`, { body: { kind, meta }, retries: 0 }),
  submit: (token) => call("POST", `/api/test/${token}/submit`),
};

export const managerApi = {
  createInvite: (auth, name, email) => call("POST", `/api/manager/invites`, { body: { name, email }, auth }),
  createPreviewInvite: (auth) => call("POST", `/api/manager/preview-invite`, { auth }),
  listCandidates: (auth) => call("GET", `/api/manager/candidates`, { auth }),
  candidateDetail: (auth, id) => call("GET", `/api/manager/candidates/${id}`, { auth }),
  patchCandidate: (auth, id, patch) => call("PATCH", `/api/manager/candidates/${id}`, { body: patch, auth }),
  deleteCandidate: (auth, id) => call("DELETE", `/api/manager/candidates/${id}`, { auth }),
  itemSignedUrl: (auth, id) => call("GET", `/api/manager/items/${id}/signed-url`, { auth }),
};
