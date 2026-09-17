const BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

async function j(method, path, body) {
  const res = await fetch(BASE + path, {
    method,
    headers: body ? { "content-type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = "";
    try { detail = (await res.json()).detail || ""; } catch {}
    throw new Error(`${res.status} ${detail || res.statusText}`);
  }
  const text = await res.text();
  return text ? JSON.parse(text) : null;
}

export const api = {
  base: BASE,
  scenarios: () => j("GET", "/scenarios"),
  loadScenario: (id) => j("POST", `/scenarios/${id}/load`),
  events: (q) => j("GET", `/events${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  report: (id) => j("GET", `/events/${id}/report`),
  analyze: (id) => j("POST", `/events/${id}/analyze`),
  approve: (id) => j("POST", `/events/${id}/approve`),
  simulate: (id) => j("POST", `/events/${id}/simulate`),
  revise: (id, instruction) => j("POST", `/events/${id}/revise`, { instruction }),
  reviseDecision: (rid, decision) => j("POST", `/revisions/${rid}/decision`, { decision }),
  claimEvidence: (cid) => j("GET", `/claims/${cid}/evidence`),
  annotate: (cid, note) => j("POST", `/claims/${cid}/annotations`, { note }),
  suggestionDecision: (sid, decision) => j("POST", `/suggestions/${sid}/decision`, { decision }),
  addReport: (id, r) => j("POST", `/events/${id}/reports`, r),
  history: (q) => j("GET", `/reports${q ? `?q=${encodeURIComponent(q)}` : ""}`),
  downloadUrl: (gid) => `${BASE}/reports/${gid}/download`,
};
