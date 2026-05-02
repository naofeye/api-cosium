import Cookies from "js-cookie";

export const CSRF_COOKIE_NAME = "optiflow_csrf";
export const CSRF_HEADER_NAME = "X-CSRF-Token";

const SAFE_METHODS = new Set(["GET", "HEAD", "OPTIONS", "TRACE"]);

/**
 * Construit le header CSRF a injecter sur une mutation.
 *
 * Lit le cookie `optiflow_csrf` (pose par le backend au login/refresh) et
 * retourne `{"X-CSRF-Token": <valeur>}` si la methode est mutante.
 *
 * Retourne `{}` pour GET/HEAD/OPTIONS et quand le cookie est absent (la
 * session n'est pas etablie ou backend en mode legacy sans CSRF).
 */
export function csrfHeaders(method: string): Record<string, string> {
  if (SAFE_METHODS.has(method.toUpperCase())) {
    return {};
  }
  const token = Cookies.get(CSRF_COOKIE_NAME);
  if (!token) {
    return {};
  }
  return { [CSRF_HEADER_NAME]: token };
}
