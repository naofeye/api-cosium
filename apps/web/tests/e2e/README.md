# Tests E2E Playwright

Tests end-to-end du frontend OptiFlow via un vrai navigateur (Chromium).

## Prérequis

- API backend joignable sur `http://localhost:8000`
- Frontend joignable sur `http://localhost:3000`
- Compte seed `admin@optiflow.com / Admin123` présent en BDD (créé au startup via `seed.py`)

## Lancer en local

```bash
# 1. Démarrer la stack (depuis la racine du repo)
docker compose up -d

# 2. Installer les navigateurs Playwright une fois
cd apps/web
npx playwright install chromium

# 3. Lancer les tests
npm run test:e2e

# Mode UI (debugger visuel)
npm run test:e2e:ui

# Lancer un seul spec
npx playwright test tests/e2e/login.spec.ts
```

## Variables d'environnement

| Variable | Défaut | Usage |
|---|---|---|
| `E2E_BASE_URL` | `http://localhost:3000` | URL frontend |
| `E2E_API_URL` | `http://localhost:8000` | URL backend |
| `E2E_SEED_EMAIL` | `admin@optiflow.com` | User de test |
| `E2E_SEED_PASSWORD` | `Admin123` | Password user de test |

## Specs

- **`login.spec.ts`** — parcours UI login (valide / invalide), vérif API 401 / 200
- **`mfa.spec.ts`** — enrôle MFA via API, dérive TOTP avec `otplib`, valide login UI + API avec code. Cleanup auto (désactive MFA à la fin)
- **`clients.spec.ts`** — login, créer un client via API, vérifier visible dans la liste UI, cleanup via DELETE

## Points d'attention

- **MFA cleanup** : le test MFA désactive MFA à la fin. Si le test crashe au milieu, le user seed peut rester en état MFA actif ; désactiver manuellement via SQL ou POST `/auth/mfa/disable`.
- **Sérialisation** : `fullyParallel: false` + `mode: "serial"` sur MFA — les tests touchent le même user seed.
- **CI** : `.github/workflows/e2e.yml` tourne sur push master + PR touchant `apps/web|apps/api`, plus `workflow_dispatch`. Utilise nginx comme reverse proxy sur port 80 : `/api/*` → backend `:8000`, `/*` → frontend `:3000`. Même origin garantit que les cookies httpOnly SameSite=Strict sont consommés par les fetch client-side. `NEXT_PUBLIC_API_BASE_URL=/api/v1` (relatif) pour que le frontend tape le proxy.
- **Local** : `docker compose up` fonctionne intégralement car nginx proxy tout sur un seul origin.

## Ajouter un test

1. Crée un fichier `*.spec.ts` dans ce dossier
2. Importe les helpers : `import { SEED_EMAIL, SEED_PASSWORD, apiLogin, uiLogin } from "./helpers";`
3. Utilise `test.describe.configure({ mode: "serial" })` si tes tests modifient le user seed
4. Nettoie ce que tu crées (clients, devis, etc.) dans un bloc `finally` ou `afterAll`
