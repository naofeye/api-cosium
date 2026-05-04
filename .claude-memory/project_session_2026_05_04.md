---
name: Session 2026-05-04 all-inclusive — fix mypy + purge secrets + CI guard
description: Apres les 3 commits Codex review (2d1881a SSRF + d3f22fb M2-M9+N4 + 61b199c M1+M8+N1+N2), 4 commits all-inclusive vps-master pour finaliser la CI verte et patcher un leak accidentel.
type: project
---

## Mission

"all inclusive" continuation autonome. Sortir une CI verte apres les
3 commits Codex review du 2026-05-03 qui ont laisse 2 erreurs mypy.

## 4 commits

- `065024c` fix(mypy) : typing devis_signature_service valid_until check
  apres commit Codex M3. CI bloquante depuis 24h, 2 erreurs operator/
  arg-type sur datetime | None narrowing manquant.
- `f75671a` fix(security) : purge .env.bak files leaked in 065024c
  ⚠️ POSTGRES_PASSWORD + S3_SECRET_KEY + JWT_SECRET + ENCRYPTION_KEY
  exposes accidentellement par git add -A qui a inclus 2 fichiers
  .env.bak generes par setup.sh. Retire du HEAD via git rm --cached
  + .env.bak* + .env.bak + .env.test ajoutes au .gitignore.
- `a701133` ci(security) : add .env.bak* check to gitignore-check job
  pour catcher pattern automatiquement en CI au prochain push.
- (final) docs+memory : REVIEW.md status table + memoire snapshot

## Status REVIEW.md Codex 2026-05-03

11/14 items resolus, 1 partial (CVE rotation 2026-06-15), 1 wontfix
(CSP Next.js limit), 1 ACTION NABIL (rotation secrets compromis).

## Patterns documentes

1. **Pre-commit hooks par-pass docker** : git via `docker run alpine/git`
   ne lance pas les pre-commit hooks (gitleaks, ruff, etc). Defense en
   profondeur necessaire en CI (gitignore-check + pip-audit + scan trivy).

2. **Mypy strict apres modifs Codex** : 7 modules pilots strict =>
   nouvelle modif typing-incompatible bloque la CI immediatement.
   Cycle vertueux : Codex fait un fix, mypy strict catch un type bug,
   on raffine. Bon retour sur investissement.

3. **Setup.sh genere des .env.bak-** : risque secret leak via `git add -A`.
   Pattern .env.bak* dans .gitignore + check CI = double rempart.

## Action urgente Nabil

**Rotation des 4 secrets compromis** dans le commit 065024c (et son enfant
f75671a) :
1. JWT_SECRET (regenerable, invalide tous tokens existants)
2. ENCRYPTION_KEY (NECESSITE re-encrypt Tier 1 PII customer + cosium cookies)
3. S3_SECRET_KEY MinIO
4. POSTGRES_PASSWORD

Voir `docs/COSIUM_CREDS_ROTATION.md` pour la procedure complete.

Puis `git filter-repo` ou `BFG Repo-Cleaner` pour purger les 2 commits
de l'historique GitHub (les secrets restent visibles dans la blame
history actuellement).
