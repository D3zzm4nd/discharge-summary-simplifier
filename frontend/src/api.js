const API = import.meta.env.VITE_API || "http://localhost:8000";
let token = null;                       // kept in memory only
export const setToken = (t) => (token = t);

export async function api(path, { method = "GET", json, form } = {}) {
  const headers = token ? { Authorization: `Bearer ${token}` } : {};
  if (json) headers["Content-Type"] = "application/json";
  const res = await fetch(API + path, { method, headers, body: json ? JSON.stringify(json) : form });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Something went wrong. Please try again.");
  return body;
}
