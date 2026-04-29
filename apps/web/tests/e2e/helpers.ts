import type { APIRequestContext, BrowserContext, Page } from "@playwright/test";
import { authenticator } from "otplib";

// En CI, nginx unifie API+Web sur le meme origin (port 80) pour que les
// cookies httpOnly/SameSite=Strict fonctionnent dans le navigateur Playwright.
// En local sans nginx, fallback sur le port API direct.
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
 * Login direct via API + injection des cookies dans le browser context.
 * Approche fiable pour authentifier le browser SANS dependre du clavier
 * virtuel ni de l'hydration React. Utiliser pour les tests qui ont besoin
 * d'etre authentifies pour leur setup mais ne testent pas le formulaire.
 *
 * Apres l'appel, le browser est connecte : les pages goto sont autorisees.
 * Retourne false si MFA requis ou login echoue.
 */
export async function apiLoginAndInject(
  context: BrowserContext,
  request: APIRequestContext,
  email: string,
  password: string,
  totpCode?: string,
): Promise<boolean> {
  const body: Record<string, unknown> = { email, password };
  if (totpCode) body.totp_code = totpCode;
  const res = await request.post(`${API_BASE}/api/v1/auth/login`, {
    data: body,
    failOnStatusCode: false,
  });
  if (res.status() !== 200) return false;
  // Recupere les cookies poses par l'API et les injecte dans le browser context.
  // Le browser sera authentifie pour toutes les navigations suivantes.
  const reqStorage = await request.storageState();
  await context.addCookies(reqStorage.cookies);
  return true;
}

/**
 * Login via la page UI (utile pour TESTER le formulaire lui-meme).
 * Reste sur /login si MFA requise — à l'appelant de vérifier la suite.
 *
 * react-hook-form's register() uses an internal store updated only via
 * its onChange handler. Playwright's fill() doesn't reliably trigger it.
 * pressSequentially with un delay fires individual key events that React's
 * event delegation picks up, updating the internal form state correctly.
 *
 * Pour les tests qui ne testent PAS le formulaire mais ont juste besoin
 * d'etre authentifies, preferer `apiLoginAndInject` (plus fiable).
 */
export async function uiLogin(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login");
  // Attendre que React hydrate (Next.js 16 Suspense) avant de taper.
  await page.waitForLoadState("networkidle");
  const emailField = page.getByLabel("Adresse email");
  await emailField.click();
  await emailField.pressSequentially(email, { delay: 30 });
  const pwField = page.getByLabel("Mot de passe");
  await pwField.click();
  await pwField.pressSequentially(password, { delay: 30 });
  await page.getByRole("button", { name: /se connecter/i }).click();
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
