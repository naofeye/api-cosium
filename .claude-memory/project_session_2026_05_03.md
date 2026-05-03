---
name: Session 2026-05-03 — Sweep autonome ambitieux 24/48h (9 livrables)
description: 5 commits pushes sur main, 4 migrations Alembic, 1 page Coming Soon livree (API publique), +38 tests backend (2327), 0 regression. CI verte 8524276.
type: project
---

## Resume

Mission "tu as 24/48h, plan ambitieux, polish + nice-to-have inclus".
3 audits Explore parallele (backend, frontend, infra/CI), plan structure
9 blocs (A-I), 5 commits, 4 migrations.

## Livrables (9)

1. `7129f36` — API publique REST v1 (Coming Soon T3 2026 -> reel)
2. `d758b9f` — Devis signature electronique eIDAS Simple (clickwrap)
3. `360754b` — Token revocation per-user (logout-everywhere) + db.query repo + N+1 fix
4. `8524276` — impact_score action_items + Prometheus exporters + alertmanager + docs
5. `81c09d4` — WEBHOOKS.md + redirect /webhooks + beat schedule orphans

## Migrations Alembic (4)

- `c6d7e8f9a1b2` users.token_version
- `d7e8f9a1b2c3` api_tokens
- `e8f9a1b2c3d4` devis signature fields
- `f9a1b2c3d4e5` action_items.impact_score

## Patterns documentes / consolides

1. **API publique pattern** : token Bearer + scopes + secret affiche une
   seule fois + UI admin masque le reste. Reutilise pour webhooks (memes
   patterns, tres reutilisables).

2. **Signature electronique eIDAS Simple** : suffisant legalement pour
   < 1500 EUR. Capture IP/UA + texte consent + horodatage. Public token
   single-use. V2 envisageable : signature dessinee canvas, eIDAS qualifiee
   via DocuSign/CertEurope.

3. **impact_score deterministe** : algorithme local (pas d'API IA), base
   priority + log10(montant) + recency. Tri primary dans repo. Pattern
   reutilisable pour autres listes prioriees (notifications, events).

4. **Pre-prod validation script** : pattern bash + check exhaustif des
   prerequis env. Reutilise pour autres projets Pattern B (booking-optisante,
   scraper-project, etc.).

## Reste backlog

- Cosium client async (B1) : gros refacto cascade dans 8+ services. P3
  jusqu'a observation OOM/latence en prod.
- Splits >300L : tous sous seuil 400L, deprioritized
- Tests E2E settings + operations-batch (P2)
- mypy strict progressif (P3)
- DIFFERE-PROD action Nabil : TLS, passwords prod, Sentry DSN, rotation Cosium

## Couts cache estimes

5h+ travail concentre. Sandbox /srv ro toujours contournee via
`docker run --user 1002:1002` pour writes + git ops via alpine/git.
