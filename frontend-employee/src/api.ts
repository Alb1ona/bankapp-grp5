// API-klient til kunde-API'et.
// - Sender cookies (credentials: 'include') til server-side session.
// - Holder CSRF-token i hukommelsen og sender det i X-CSRF-Token ved ændringer.
import type { ApiError } from "./types";

const API_BASE = (import.meta.env.VITE_API_BASE as string) || "http://localhost:8000";

let csrfToken: string | null = null;

export function setCsrfToken(token: string | null) {
  csrfToken = token;
}

export class ApiException extends Error {
  code: string;
  requestId?: string;
  status: number;
  constructor(status: number, err: ApiError) {
    super(err.message);
    this.status = status;
    this.code = err.code;
    this.requestId = err.request_id;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const mutating = method !== "GET";
  if (mutating && csrfToken) headers["X-CSRF-Token"] = csrfToken;

  const res = await fetch(`${API_BASE}${path}`, {
    method,
    headers,
    credentials: "include",
    body: body ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new ApiException(res.status, data as ApiError);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
};

export { API_BASE };
