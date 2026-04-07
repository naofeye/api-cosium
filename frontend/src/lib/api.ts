import { refreshAccessToken, clearAuthState } from "./auth";
export { API_BASE } from "./config";
import { API_BASE } from "./config";
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
      // Clear the original timeout so it doesn't abort the retry
      clearTimeout(timeout);
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
        throw new Error("Session expirée");
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
      const msg = String(
        (errorBody?.error as Record<string, unknown>)?.message ||
        errorBody?.message ||
        errorBody?.detail ||
        `Erreur API ${response.status}`
      );

      // Dispatch a custom event for global toast handling (skip 401, handled above)
      if (typeof window !== "undefined" && response.status !== 401) {
        window.dispatchEvent(
          new CustomEvent("api-error", {
            detail: { message: msg, status: response.status },
          })
        );
      }

      throw new Error(msg);
    }

    if (response.status === 204) return undefined as T;
    return response.json();
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      const timeoutMsg = "La requête a expiré. Vérifiez votre connexion et réessayez.";
      if (typeof window !== "undefined") {
        window.dispatchEvent(
          new CustomEvent("api-error", { detail: { message: timeoutMsg, status: 0 } })
        );
      }
      throw new Error(timeoutMsg);
    }
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}
