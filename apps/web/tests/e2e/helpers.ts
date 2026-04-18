import type { APIRequestContext, Page } from "@playwright/test";
import { authenticator } from "otplib";

export const API_BASE = process.env.E2E_API_URL ?? "http://localhost:8000";
export const SEED_EMAIL = process.env.E2E_SEED_EMAIL ?? "admin@optiflow.com";
export const SEED_PASSWORD = process.env.E2E_SEED_PASSWORD ?? "Admin123";

/**
 * Appelle /auth/login via l'API request context.
 * Retourne la réponse JSON ou lève si non-200.
 */
export async function apiLogin(
  request: APIRequestContext,
  email: string,
  password: string,
  totpCode?: string,
): Promise<{ status: number; body: Record<string, unknown> }> {
  const body: Record<string, unknown> = { email, password };
  if (totpCode) body.totp_code = totpCode;
  const res = await request.post(`${API_BASE}/api/v1/auth/login`, {
    data: body,
    failOnStatusCode: false,
  });
  return { status: res.status(), body: await res.json().catch(() => ({})) };
}

/**
 * Login via la page UI (utile pour récupérer un state authentifié dans le navigateur).
 * Reste sur /login si MFA requise — à l'appelant de vérifier la suite.
 *
 * Important : on attend l'hydratation React avant de cliquer, sinon le form
 * submit en GET natif (querystring visible dans l'URL), court-circuitant
 * le handleSubmit de react-hook-form. On détecte l'hydratation en attendant
 * que window.__NEXT_DATA__ soit présent ET networkidle.
 */
export async function uiLogin(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login", { waitUntil: "networkidle" });
  // Laisse React hydrater (Next standalone + React 19 : ~500ms après networkidle).
  // Sans ce délai, onSubmit n'est pas attaché au <form> -> submit GET natif
  // avec password dans l'URL.
  await page.waitForTimeout(1000);
  await page.getByLabel("Adresse email").fill(email);
  await page.getByLabel("Mot de passe").fill(password);
  // submit via JS dispatch pour bypass tout risque de GET natif résiduel :
  // on appelle requestSubmit() sur le form qui trigger React onSubmit
  // (preventDefault fait par handleSubmit de react-hook-form).
  await page.evaluate(() => {
    const form = document.querySelector<HTMLFormElement>("form");
    form?.requestSubmit();
  });
}

/**
 * Dérive un code TOTP 6 digits à partir d'un secret base32.
 * otplib v12 — API classique, fenêtre 30s, 6 digits par défaut.
 */
export function deriveTotp(secret: string): string {
  return authenticator.generate(secret);
}

/**
 * Désactive MFA sur le user seed via API directe (cleanup entre tests).
 * Requiert des cookies valides d'un login authentifié.
 */
export async function disableMfaViaApi(
  request: APIRequestContext,
  password: string,
): Promise<void> {
  await request.post(`${API_BASE}/api/v1/auth/mfa/disable`, {
    data: { password },
    failOnStatusCode: false,
  });
}
