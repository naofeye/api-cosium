---
name: Unification branches — main seule source de verite depuis 2026-04-19
description: La branche `master` a ete supprimee. `main` est la seule branche canonique (local + remote). Toute action git doit viser `main`.
type: project
originSessionId: 21e0df06-b2a4-4e95-bdf2-27568dbbb888
---
Depuis 2026-04-19, le repo `naofeye/api-cosium` n'a plus qu'une seule branche principale : `main`.

Contexte : jusque-la, deux branches divergeaient (162↑ / 125↓) — `master` suivait le travail actif, `main` etait la default GitHub mais figee au 2026-04-17 (`8c494dd`). Verification faite : `master` contenait deja tout le code de `main` (memes features, SHAs differents suite a un rebase lors de la restructuration monorepo `d0fb9b2`). Force-push `master:main` + suppression de `master` local et remote.

**Etat final (commit `6e000e3`)** :
- `origin/main` = seule branche principale, default branch GitHub
- `master` supprimee partout
- Historique `main` = historique de l'ancien `master` (164 commits au-dessus du merge-base `d0fb9b2`, sessions 2026-04-17 + 2026-04-18 + fix 2026-04-19)
- CI verte (9/9 + CodeQL) confirmee sur le nouveau main apres force-push
- PR Dependabot encore ouvertes (14) — a re-baser ou fermer/re-ouvrir si conflits

**Consequences operationnelles** :
- `git push origin main` (plus jamais `master`)
- Sur le VPS (cf. vps_deployment.md) : `cd /srv/interface-ia/projects/api-cosium && git fetch origin --prune && git reset --hard origin/main` (le VPS suivait probablement master — a verifier/corriger au prochain deploiement)
- Toute nouvelle feature part de `main`
- Les memoires anciennes qui mentionnent `master` referent historiquement a ce qui est maintenant `main`
