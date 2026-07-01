/**
 * Centralized API fetch helper.
 *
 * All frontend API calls should go through `apiFetch` to ensure the JWT
 * auth token is consistently attached. Replaces ad-hoc fetch() calls
 * that were missing the Authorization header.
 */

export function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = localStorage.getItem("cs599_token");
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

/**
 * Fetch wrapper that auto-attaches JWT auth headers.
 * Usage: const res = await apiFetch("/api/providers", { method: "GET" });
 */
export async function apiFetch(
  endpoint: string,
  options: RequestInit = {}
): Promise<Response> {
  const headers: Record<string, string> = { ...getAuthHeaders() };
  // Merge caller-provided headers
  if (options.headers) {
    Object.assign(headers, options.headers);
  }
  // FormData: let browser set Content-Type (multipart boundary),
  // remove our default application/json — otherwise FastAPI 422s
  if (options.body instanceof FormData) {
    delete headers["Content-Type"];
  }
  return fetch(endpoint, { ...options, headers });
}
