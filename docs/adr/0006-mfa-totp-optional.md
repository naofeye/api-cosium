# ADR 0006 — MFA TOTP optionnel par compte

**Date** : 2026-04-16
**Statut** : Accepté
**Contexte audit** : Passe 7 post-audit (voir `TODO.md` section P1 Sécurité/comptes)

## Contexte

L'audit OWASP a identifié l'absence de MFA comme gap P1 : la compromission d'un mot de passe admin donne un accès total. Les comptes opticien et admin accèdent à des données sensibles (clients, factures, mutuelles, dossiers médicaux partiels).

## Options considérées

1. **MFA obligatoire globale** : force tous les users à activer TOTP.
   - ➕ sécurité maximale
   - ➖ friction UX, blocage déploiement, rollout complexe
2. **MFA optionnelle par user** : l'user choisit d'activer
   - ➕ adoption progressive, pas de blocage
   - ➖ adoption volontaire faible sans incentive
3. **MFA forcée pour rôle admin** : seul les admins doivent activer
   - ➕ équilibre sécurité/UX, cible les comptes à risque
   - ➖ nécessite migration + blocage des admins actuels sans MFA

## Décision

**Option 2 : MFA optionnelle par user, enrôlement auto-service**.

Raisons :
- Déploiement immédiat sans blocage production
- Adoption mesurable via métrique `optiflow_users_mfa_enabled`
- Si adoption insuffisante → évolution vers option 3 via config tenant (à venir)

## Implémentation

- **Modèle** : `User.totp_secret_enc`, `totp_enabled`, `totp_last_used_at` (migration `u6v7w8x9y0z1`)
- **Secret** : chiffré Fernet via `app.core.encryption.encrypt`
- **Library** : `pyotp==2.9.0`, fenêtre acceptée ±30 s (`valid_window=1`)
- **Endpoints** :
  - `GET /api/v1/auth/mfa/status` → `{enabled: bool}`
  - `POST /api/v1/auth/mfa/setup` → `{secret, otpauth_uri, issuer}` (génère, n'active pas)
  - `POST /api/v1/auth/mfa/enable` `{code}` → active si code valide
  - `POST /api/v1/auth/mfa/disable` `{password}` → désactive (nécessite password)
- **Login** : `LoginRequest.totp_code?` requis si `user.totp_enabled=True`, sinon inchangé

## Conséquences

✅ Gap OWASP A07 fermé pour les users qui activent
✅ Observabilité : métrique Prometheus `optiflow_users_mfa_enabled`
✅ Rotation / recovery : `/mfa/disable` nécessite password → protection basique. Backup codes prévus en v2.
⚠️ Si user perd son authenticator sans backup, seul l'admin peut réinitialiser (manuel pour l'instant).

## À venir

- **Backup codes** (10 codes one-shot pour recovery)
- **MFA forcée rôle admin** (option 3) une fois adoption suffisante
- **Anti-brute-force** sur `/mfa/enable` et login MFA (lockout dédié)
