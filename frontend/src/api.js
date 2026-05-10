const BASE = "";

async function call(method, path, { body, auth } = {}) {
  const headers = { "Content-Type": "application/json" };
  if (auth) headers.Authorization = `Bearer ${auth}`;
  const res = await fetch(`${BASE}${path}`, {
    method,
    credentials: "include",
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw Object.assign(new Error(err.detail || `${res.status}`), { status: res.status, body: err });
  }
  return res.json();
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
  event: (token, kind, meta = {}) => call("POST", `/api/test/${token}/event`, { body: { kind, meta } }),
  submit: (token) => call("POST", `/api/test/${token}/submit`),
};

export const managerApi = {
  createInvite: (auth, name, email) => call("POST", `/api/manager/invites`, { body: { name, email }, auth }),
  listCandidates: (auth) => call("GET", `/api/manager/candidates`, { auth }),
  candidateDetail: (auth, id) => call("GET", `/api/manager/candidates/${id}`, { auth }),
  patchCandidate: (auth, id, patch) => call("PATCH", `/api/manager/candidates/${id}`, { body: patch, auth }),
  itemSignedUrl: (auth, id) => call("GET", `/api/manager/items/${id}/signed-url`, { auth }),
};
