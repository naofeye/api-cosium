import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config — tests E2E OptiFlow.
 *
 * Prerequisite : API (:8000) + web (:3000) tournent.
 * En local : `docker compose up` puis `npm run test:e2e` depuis `apps/web/`.
 * En CI : workflow `.github/workflows/e2e.yml` orchestre l'ensemble.
 *
 * Les tests utilisent le compte seed `admin@optiflow.com / Admin123` qui existe
 * après startup backend (voir `apps/api/app/seed.py`).
 */

const WEB_BASE_URL = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const API_BASE_URL = process.env.E2E_API_URL ?? "http://localhost:8000";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  expect: { timeout: 5_000 },
  fullyParallel: false, // les tests MFA modifient l'état du user seed
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: WEB_BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
    extraHTTPHeaders: {
      // Les tests qui parlent directement à l'API via request fixture
      // ont besoin de Content-Type JSON par défaut.
      "Accept": "application/json",
    },
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // Expose la baseURL API aux specs via process.env
  globalSetup: undefined,
  metadata: {
    apiBaseUrl: API_BASE_URL,
  },
});
