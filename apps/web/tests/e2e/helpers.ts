import type { APIRequestContext, Page } from "@playwright/test";
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
 * Login via la page UI (utile pour récupérer un state authentifié dans le navigateur).
 * Reste sur /login si MFA requise — à l'appelant de vérifier la suite.
 *
 * Utilise click + type (pas fill) pour simuler une frappe clavier réelle.
 * react-hook-form register() écoute les events React synthétiques — seule
 * une interaction clavier complète (focus → keydown → input → keyup)
 * garantit que watch() voit les nouvelles valeurs en CI.
 * Tab entre les champs déclenche onBlur (revalidation).
 */
export async function uiLogin(page: Page, email: string, password: string): Promise<void> {
  await page.goto("/login");

  const emailField = page.getByLabel("Adresse email");
  await emailField.click();
  await emailField.pressSequentially(email, { delay: 30 });

  // Tab to password field — triggers blur/validation on email
  await page.keyboard.press("Tab");
  await page.getByLabel("Mot de passe").pressSequentially(password, { delay: 30 });

  // Tab away from password to trigger blur, then wait for react-hook-form
  await page.keyboard.press("Tab");
  await page.waitForTimeout(300);

  // Submit — prefer click if enabled, otherwise Enter on form
  const submitBtn = page.getByRole("button", { name: /se connecter/i });
  const isEnabled = await submitBtn.isEnabled().catch(() => false);
  if (isEnabled) {
    await submitBtn.click();
  } else {
    // Enter from any field submits the form via handleSubmit
    await page.keyboard.press("Enter");
  }
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
