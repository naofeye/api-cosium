import { refreshAccessToken, clearAuthState } from "./auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api/v1";
const DEFAULT_TIMEOUT_MS = 10000;

export async function fetchJson<T = unknown>(path: string, options?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    ...(options?.headers as Record<string, string>),
  };
  // Set Content-Type for JSON bodies only (not FormData)
  if (options?.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json";
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  try {
    let response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      credentials: "include",
      cache: "no-store",
      signal: controller.signal,
    });

    // On 401, try silent refresh via httpOnly cookie
    if (response.status === 401) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        response = await fetch(`${API_BASE}${path}`, {
          ...options,
          headers,
          credentials: "include",
          cache: "no-store",
        });
      } else {
        clearAuthState();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        throw new Error("Session expiree");
      }
    }

    if (!response.ok) {
      // Try to parse JSON error body; fallback gracefully for non-JSON responses (HTML error pages, gateway errors)
      let errorBody: Record<string, unknown> = {};
      try {
        errorBody = await response.json();
      } catch {
        // Non-JSON response (HTML error page, proxy error, etc.)
      }
      const msg =
        (errorBody?.error as Record<string, unknown>)?.message ||
        errorBody?.message ||
        errorBody?.detail ||
        `Erreur API ${response.status}`;
      throw new Error(String(msg));
    }

    if (response.status === 204) return undefined as T;
    return response.json();
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error("La requete a expire. Verifiez votre connexion et reessayez.");
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}
