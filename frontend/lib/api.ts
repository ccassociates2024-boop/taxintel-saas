const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type User = { id: string; email: string; full_name: string; role: string };
export type Client = { id: string; full_name: string; pan: string; email?: string; phone?: string; residential_status: string; client_type: string };

export function getToken() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("taxintel_token") || "";
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (!(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${API_URL}${path}`, { ...init, headers, cache: "no-store" });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(payload.detail || "Request failed");
  }
  return response.json();
}

export async function auth(path: "login" | "register", payload: object) {
  return api<{ access_token: string; user: User }>(`/api/v1/auth/${path}`, {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

