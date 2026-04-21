---
name: Toujours commit ET push apres changements
description: Apres une serie de modifications sur le repo, il faut committer ET pousser vers le remote (pas seulement commit local).
type: feedback
originSessionId: eb44105e-6380-4e79-8930-65f88994dc42
---
Apres toute serie de modifications (audit, refactor, fix, feature) qui se termine par un commit local, l'utilisateur veut aussi que les commits soient pushes vers le remote.

**Why:** L'utilisateur a fait un rappel explicite "mets en memoire commit et push" apres une session de 10 passes ou j'avais committe en local mais pas pushe. Le commit seul ne suffit pas pour synchroniser avec le remote (et donc avec d'autres environnements : VPS, CI, collegues).

**How to apply:**
- Quand une serie de changements se termine naturellement (fin de chantier, fin de session, apres "c'est bon", etc.), faire `git push` apres `git commit`.
- Pour les commits successifs d'une meme session de travail, grouper les push en fin de serie pour eviter de pusher des etats intermediaires instables.
- Si un push pourrait poser probleme (branche protegee, force-push, merge conflicts), demander confirmation avant.
