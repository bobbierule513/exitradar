/**
 * Single API client for all frontend HTTP calls.
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    "X-Demo-User": "00000000-0000-4000-8000-000000000001",
    ...(options.headers || {}),
  };
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch (err) {
    const error = new Error("Backend unreachable. Is the API running on " + API_BASE + "?");
    error.code = "NETWORK";
    throw error;
  }
  if (!res.ok) {
    let message = res.statusText;
    try {
      const body = await res.json();
      message = body.error || body.detail || message;
    } catch {
      /* ignore */
    }
    const error = new Error(typeof message === "string" ? message : JSON.stringify(message));
    error.status = res.status;
    throw error;
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("text/csv")) return res.text();
  return res.json();
}

export const api = {
  health: () => request("/health"),
  workspaces: () => request("/api/v1/workspaces"),
  commandCenter: (workspaceId, thesisId) =>
    request(
      `/api/v1/workspaces/${workspaceId}/command-center` +
        (thesisId ? `?thesis_id=${encodeURIComponent(thesisId)}` : "")
    ),
  theses: (workspaceId) =>
    request(`/api/v1/theses?workspace_id=${encodeURIComponent(workspaceId)}`),
  getThesis: (id) => request(`/api/v1/theses/${id}`),
  createThesis: (body) =>
    request("/api/v1/theses", { method: "POST", body: JSON.stringify(body) }),
  searchJobs: (body) =>
    request("/api/v1/search-jobs", { method: "POST", body: JSON.stringify(body) }),
  getSearchJob: (id) => request(`/api/v1/search-jobs/${id}`),
  companies: (workspaceId) =>
    request(
      `/api/v1/companies` +
        (workspaceId ? `?workspace_id=${encodeURIComponent(workspaceId)}` : "")
    ),
  getCompany: (id) => request(`/api/v1/companies/${id}`),
  evidence: (id) => request(`/api/v1/companies/${id}/evidence`),
  signals: (id) => request(`/api/v1/companies/${id}/signals`),
  timeline: (id) => request(`/api/v1/companies/${id}/timeline`),
  opportunities: (thesisId) => request(`/api/v1/theses/${thesisId}/opportunities`),
  opportunity: (companyId, thesisId) =>
    request(`/api/v1/companies/${companyId}/opportunities/${thesisId}`),
  recommendation: (companyId, thesisId) =>
    request(
      `/api/v1/companies/${companyId}/recommendation` +
        (thesisId ? `?thesis_id=${encodeURIComponent(thesisId)}` : "")
    ),
  outreach: (companyId, body) =>
    request(`/api/v1/companies/${companyId}/outreach`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  listOutreach: (companyId) => request(`/api/v1/companies/${companyId}/outreach`),
  pipeline: (companyId, body) =>
    request(`/api/v1/companies/${companyId}/pipeline`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  activity: (companyId, body) =>
    request(`/api/v1/companies/${companyId}/activities`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  dealBrief: (companyId, thesisId) =>
    request(`/api/v1/companies/${companyId}/deal-brief?thesis_id=${encodeURIComponent(thesisId)}`, {
      method: "POST",
    }),
  createExport: (body) =>
    request("/api/v1/exports", { method: "POST", body: JSON.stringify(body) }),
  getExport: (id, format = "json") =>
    request(`/api/v1/exports/${id}?format=${format}`),
  getCadence: (workspaceId, thesisId) =>
    request(
      `/api/v1/workspaces/${workspaceId}/cadence` +
        (thesisId ? `?thesis_id=${encodeURIComponent(thesisId)}` : "")
    ),
  patchCadence: (workspaceId, body) =>
    request(`/api/v1/workspaces/${workspaceId}/cadence`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  bookOfWork: (thesisId, week) =>
    request(
      `/api/v1/theses/${thesisId}/book-of-work` +
        (week ? `?week=${encodeURIComponent(week)}` : "")
    ),
  generateBookOfWork: (thesisId, body = {}) =>
    request(`/api/v1/theses/${thesisId}/book-of-work`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  completeBookSlot: (slotId, body = {}) =>
    request(`/api/v1/book-of-work/slots/${slotId}/complete`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  skipBookSlot: (slotId, body = {}) =>
    request(`/api/v1/book-of-work/slots/${slotId}/skip`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
};

