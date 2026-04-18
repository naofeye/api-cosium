import { expect, test } from "@playwright/test";
import { API_BASE, SEED_EMAIL, SEED_PASSWORD, apiLogin, deriveTotp, uiLogin } from "./helpers";

/**
 * Flow MFA complet via l'API puis UI :
 * 1. Login sans MFA → succès
 * 2. Setup MFA : appel /auth/mfa/setup → récupère secret
 * 3. Dérive TOTP avec otplib
 * 4. Active MFA : POST /auth/mfa/enable
 * 5. Login API avec seulement email/pass → 401 MFA_CODE_REQUIRED
 * 6. Login API avec TOTP → 200
 * 7. UI : login email+pass affiche le formulaire TOTP, code valide → /actions
 * 8. Cleanup : désactive MFA pour laisser le user seed dans l'état initial
 */

test.describe.configure({ mode: "serial" });

test.describe("MFA flow", () => {
  let totpSecret: string | null = null;

  test.afterAll(async ({ request }) => {
    // Cleanup : s'assurer que MFA est désactivé sur le user seed
    if (!totpSecret) return;
    const loginCode = deriveTotp(totpSecret);
    const login = await apiLogin(request, SEED_EMAIL, SEED_PASSWORD, loginCode);
    if (login.status === 200) {
      await request.post(`${API_BASE}/api/v1/auth/mfa/disable`, {
        data: { password: SEED_PASSWORD },
        failOnStatusCode: false,
      });
    }
  });

  test("enroll + verify + login avec TOTP", async ({ request }) => {
    // 1. Login sans MFA (baseline)
    const initial = await apiLogin(request, SEED_EMAIL, SEED_PASSWORD);
    expect(initial.status).toBe(200);

    // 2. Setup MFA (cookies transmis via request context)
    const setupRes = await request.post(`${API_BASE}/api/v1/auth/mfa/setup`);
    expect(setupRes.status()).toBe(200);
    const setupBody = (await setupRes.json()) as { secret: string; otpauth_uri: string };
    expect(setupBody.secret).toBeTruthy();
    expect(setupBody.otpauth_uri).toMatch(/^otpauth:\/\//);
    totpSecret = setupBody.secret;

    // 3. Dérive TOTP
    const code = deriveTotp(totpSecret);
    expect(code).toMatch(/^\d{6}$/);

    // 4. Active MFA
    const enable = await request.post(`${API_BASE}/api/v1/auth/mfa/enable`, {
      data: { code },
    });
    expect(enable.status()).toBe(204);

    // 5. Login sans TOTP → 401 avec marker MFA_CODE_REQUIRED
    const noCode = await apiLogin(request, SEED_EMAIL, SEED_PASSWORD);
    expect(noCode.status).toBe(401);
    const errorMsg = (noCode.body as { error?: { message?: string } })?.error?.message;
    expect(errorMsg).toBe("MFA_CODE_REQUIRED");

    // 6. Login avec TOTP dérivé → 200
    const withCode = deriveTotp(totpSecret);
    const withTotp = await apiLogin(request, SEED_EMAIL, SEED_PASSWORD, withCode);
    expect(withTotp.status).toBe(200);
  });

  test("UI : login affiche le champ TOTP quand MFA active", async ({ page, request }) => {
    test.skip(!totpSecret, "Depend du test enroll precedent");

    await uiLogin(page, SEED_EMAIL, SEED_PASSWORD);

    // Reste sur /login avec le formulaire TOTP
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByLabel(/code totp/i)).toBeVisible({ timeout: 10_000 });

    // Entre le code dérivé
    const code = deriveTotp(totpSecret!);
    await page.getByLabel(/code totp/i).fill(code);
    await page.getByRole("button", { name: /valider le code/i }).click();

    await expect(page).toHaveURL(/\/actions$/, { timeout: 10_000 });

    // Re-auth via API pour le afterAll cleanup
    await apiLogin(request, SEED_EMAIL, SEED_PASSWORD, deriveTotp(totpSecret!));
  });
});
