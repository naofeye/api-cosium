import { expect, test } from "@playwright/test";
import { API_BASE, SEED_EMAIL, SEED_PASSWORD, apiLoginAndInject } from "./helpers";

/**
 * Parcours CRUD clients via l'UI + API :
 * 1. Login seed
 * 2. Création via API (plus rapide que le remplir-un-form) : POST /clients
 * 3. Navigation UI → la liste affiche le client créé
 * 4. Cleanup : soft-delete via API
 *
 * Tester la création UI complète demanderait de remplir un formulaire qui peut
 * évoluer ; l'objectif ici est de valider le chemin listing + cookie auth.
 */

const uniqueSuffix = () => Date.now().toString(36);

test.describe("Clients flow", () => {
  test("login → API create → UI voit le client → API delete", async ({ page, context, request }) => {
    // 1. Login API + injection cookies dans le browser context : plus fiable
    // que uiLogin (qui depend de pressSequentially + react-hook-form +
    // hydration React, parfois flakky en CI).
    const ok = await apiLoginAndInject(context, request, SEED_EMAIL, SEED_PASSWORD);
    expect(ok).toBe(true);

    // 2. Créer un client via API (nom avec suffix unique pour éviter collision)
    const suffix = uniqueSuffix();
    const firstName = `E2E${suffix}`;
    const lastName = `Test${suffix}`;
    const createRes = await request.post(`${API_BASE}/api/v1/clients`, {
      data: { first_name: firstName, last_name: lastName },
      failOnStatusCode: false,
    });
    expect(createRes.status()).toBe(201);
    const created = (await createRes.json()) as { id: number };
    expect(created.id).toBeGreaterThan(0);

    try {
      // 3. Le browser est deja authentifie via les cookies injectes —
      // navigation directe vers /clients (pas besoin de retaper login).

      // Naviguer vers la liste clients et rechercher
      await page.goto("/clients");
      await expect(page.getByRole("heading", { name: /clients/i }).first()).toBeVisible({
        timeout: 10_000,
      });

      // Le client créé doit être visible (soit dans la liste, soit via recherche)
      // On recherche par son prénom unique pour limiter la pagination.
      const searchInput = page.getByPlaceholder(/rechercher/i).first();
      if (await searchInput.isVisible().catch(() => false)) {
        await searchInput.fill(firstName);
        // Debounce 300ms
        await page.waitForTimeout(500);
      }
      await expect(page.getByText(firstName, { exact: false })).toBeVisible({
        timeout: 10_000,
      });
    } finally {
      // 4. Cleanup : soft-delete via API
      await request.delete(`${API_BASE}/api/v1/clients/${created.id}`, {
        failOnStatusCode: false,
      });
    }
  });

  test("logout redirige vers login", async ({ page, context, request }) => {
    const ok = await apiLoginAndInject(context, request, SEED_EMAIL, SEED_PASSWORD);
    expect(ok).toBe(true);

    // Verifier que les cookies sont en place (navigation OK)
    await page.goto("/actions");
    await expect(page).toHaveURL(/\/actions$/, { timeout: 10_000 });

    // Logout via API + clear cookies cote browser
    await request.post(`${API_BASE}/api/v1/auth/logout`, { failOnStatusCode: false });
    await context.clearCookies();

    // Naviguer vers une page protégée → devrait rediriger vers /login
    await page.goto("/clients");
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
  });
});
