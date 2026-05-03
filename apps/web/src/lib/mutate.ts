import { fetchJson } from "./api";

/**
 * Helper de mutation idempotente : ajoute automatiquement un en-tete
 * `X-Idempotency-Key` aux POST/PUT/PATCH/DELETE.
 *
 * Codex M1 (REVIEW.md 2026-05-03) : les creations financieres (devis,
 * facture, avoir) faisaient `fetchJson(...)` sans cle d'idempotence,
 * donc un double clic / retry navigateur creait des doublons. Le backend
 * supporte deja l'idempotence via `app.core.idempotency` (cf docs/specs)
 * mais ne l'active que si l'en-tete est present.
 *
 * Le helper genere automatiquement un UUID si aucune cle n'est fournie.
 * Pour les formulaires ou un retry doit etre dedupe (clic + perte reseau
 * + reclic), passer un `idempotencyKey` stable lie a la soumission :
 *
 *     // Pattern stable : la cle vit autant que le composant.
 *     const idemKey = useRef(crypto.randomUUID()).current;
 *     await mutateJson("/devis", {
 *       method: "POST", body: JSON.stringify(data), idempotencyKey: idemKey,
 *     });
 */
export interface MutateOptions {
  method: "POST" | "PUT" | "PATCH" | "DELETE";
  body?: BodyInit;
  /**
   * Optionnel. Si absent, le helper genere un UUID v4 au moment de l'appel.
   * Pour qu'un retry soit dedupe par le backend, il faut passer la MEME
   * cle aux deux appels (cf pattern useRef ci-dessus).
   */
  idempotencyKey?: string;
  headers?: Record<string, string>;
}

function makeKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback (vieux browsers / SSR sans crypto.randomUUID)
  return `${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

export async function mutateJson<T = unknown>(
  path: string,
  options: MutateOptions,
): Promise<T> {
  const key = options.idempotencyKey ?? makeKey();
  return fetchJson<T>(path, {
    method: options.method,
    body: options.body,
    headers: {
      ...(options.headers ?? {}),
      "X-Idempotency-Key": key,
    },
  });
}
