---
name: Éviter les tunnels CI / debug long
description: Le user a été frustré par un tunnel Playwright (6 fix successifs, 90 min). Préfère cycles courts, locaux, prévisibles, avec 0 risque CI long.
type: feedback
originSessionId: 78e8037f-0ea8-4de6-a636-c3826a097607
---
**Règle** : éviter les chantiers qui débouchent sur des boucles de debug CI longues. Préférer des tâches à cycle court, validables localement, avec résultat prévisible.

**Why** : session 2026-04-18, la mise en place des tests E2E Playwright a produit 6 commits correctifs d'affilée (cookies cross-origin → nginx reverse proxy → hydration React → submit GET natif → form gating → skip tests UI). À chaque fix, le CI E2E prenait 3-5 min et révélait le problème suivant. L'user a dit explicitement : « tu tournes depuis des heures et je ne comprends pas ce que tu fais [...] propose un plan précis, ce qui bloque, quelles sont les options ». Finalement revert de 5 commits + `workflow_dispatch` only pour débloquer.

**How to apply** :
- Quand on démarre un chantier, se poser la question : « combien de boucles CI au pire ? ». Si > 2, proposer une alternative à cycle court.
- Pour des setups complexes (E2E, CI infra, migrations risquées), préférer `workflow_dispatch` + tester localement avec Docker d'abord.
- Si un diagnostic prend > 3 fix successifs sans converger : s'arrêter, faire un point clair au user avec options explicites (A/B/C rollback vs continuer vs alternative), demander décision.
- Privilégier les chantiers purement locaux : TS check, vitest, ruff, unit tests — le feedback est < 30 s et le risque prod est nul.
- Ne pas annoncer une série de 5 items dans le plan si chacun peut potentiellement partir en tunnel.
