import { expect, test } from "@playwright/test";
import { SEED_EMAIL, SEED_PASSWORD, apiLogin, uiLogin } from "./helpers";

/**
 * Parcours login UI :
 * - page chargée avec champs email + password
 * - login valide → redirection /actions
 * - login invalide → message d'erreur rouge, reste sur /login
 */

test.describe("Login UI", () => {
  test("affiche le formulaire de login", async ({ page }) => {
    await page.goto("/login");

    await expect(page.getByRole("heading", { name: "OptiFlow AI" })).toBeVisible();
    await expect(page.getByLabel("Adresse email")).toBeVisible();
    await expect(page.getByLabel("Mot de passe")).toBeVisible();
    await expect(page.getByRole("button", { name: /se connecter/i })).toBeVisible();
  });

  test("login valide redirige vers /actions", async ({ page }) => {
    await uiLogin(page, SEED_EMAIL, SEED_PASSWORD);
    await expect(page).toHaveURL(/\/actions$/, { timeout: 10_000 });
  });

  test("mauvais mot de passe affiche l'erreur", async ({ page }) => {
    await uiLogin(page, SEED_EMAIL, "MauvaisMotDePasse1!");
    await expect(page).toHaveURL(/\/login$/);
    const alert = page.locator(".bg-red-50");
    await expect(alert).toBeVisible();
  });

  test("mot de passe oublie : le lien pointe vers /forgot-password", async ({ page }) => {
    await page.goto("/login");
    const link = page.getByRole("link", { name: /mot de passe oubli/i });
    await expect(link).toHaveAttribute("href", "/forgot-password");
  });
});

test.describe("Login API direct", () => {
  test("rejette credentials invalides avec 401", async ({ request }) => {
    const { status, body } = await apiLogin(request, SEED_EMAIL, "WrongPassword123!");
    expect(status).toBe(401);
    expect(body).toHaveProperty("error");
  });

  test("accepte credentials seed", async ({ request }) => {
    const { status, body } = await apiLogin(request, SEED_EMAIL, SEED_PASSWORD);
    expect(status).toBe(200);
    expect(body).toHaveProperty("role");
  });
});
