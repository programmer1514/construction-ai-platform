// Thin API client. Every call either resolves to { data, meta } or throws an ApiError with a friendly message.
const BASE = import.meta.env.VITE_API_URL || "";
const TIMEOUT_MS = 90000;

export class ApiError extends Error {
  constructor(message, code = "error", status = 0) {
    super(message);
    this.code = code;
    this.status = status;
  }
}

async function request(path, options = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  let res;
  try {
    res = await fetch(BASE + path, { ...options, signal: ctrl.signal });
  } catch (e) {
    if (e?.name === "AbortError") throw new ApiError("The request took too long. Please try again.", "timeout");
    throw new ApiError("Cannot reach the server. Make sure the backend is running (uvicorn on port 8000).", "network");
  } finally {
    clearTimeout(timer);
  }

  let body = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON response */
  }

  if (!res.ok) {
    throw new ApiError(body?.error?.message || `Request failed (HTTP ${res.status}).`, body?.error?.code || `http_${res.status}`, res.status);
  }
  if (!body || typeof body !== "object" || body.data == null || typeof body.data !== "object") {
    throw new ApiError("The server sent an unexpected response.", "bad_response", res.status);
  }
  return { data: body.data, meta: body.meta || null };
}

export const postJson = (path, payload) =>
  request(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });

export const postForm = (path, formData) => request(path, { method: "POST", body: formData });

export async function getHealth() {
  try {
    const res = await fetch(BASE + "/api/health");
    return res.ok ? await res.json() : null;
  } catch {
    return null;
  }
}
