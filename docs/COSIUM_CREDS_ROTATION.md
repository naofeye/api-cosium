# Rotation credentials Cosium — Runbook

> Action critique : un credential Cosium fuite peut donner acces aux donnees
> medicales et financieres de tous les clients de tous les magasins du tenant.
> A executer **avant la mise en production grand public** ou en cas
> d'incident security.

## Contexte

OptiFlow se connecte a Cosium en lecture seule via 3 modes d'auth :
1. **Basic** (login + password) : compte historique `AFAOUSSI` actuellement
   en `.env` (clear text). **A revoquer.**
2. **Cookie session** (`access_token` + `device-credential`) : par tenant,
   stockes chiffres (Fernet) dans `tenants.cosium_cookie_*_enc`.
3. **OIDC** (Keycloak) : pas encore deploye en prod.

Cible apres rotation : passer de Basic global vers Cookie par tenant
(deja partiellement implemente, finalisation lors du go-live).

## Prerequis

- Acces root au VPS (pour redemarrage containers)
- Credentials Nabil au compte Cosium principal pour generer un nouveau compte
- Acces GitHub admin du repo `naofeye/api-cosium` (force-push autorise)
- Backup recent (`/srv/backups/postgres/...`) au cas ou
- Calendrier : eviter heure ouvree (sync Cosium quotidienne 6h UTC)

## Etapes

### 1. Generer le nouveau compte Cosium

Contacter le fournisseur Cosium pour :
- **Revoquer** le compte `AFAOUSSI` (login actuel)
- **Creer** un nouveau compte avec un nom non-personnel (ex:
  `optiflow-prod-2026`) avec les memes droits read-only
- Recuperer login + password initial

### 2. Mettre a jour la BDD avec les nouveaux cookies

Methode 1 — UI admin :
1. Login sur https://cosium.ia.coging.com avec compte Nabil
2. Aller sur `/admin/cosium-cookies`
3. Pour chaque tenant : reinjecter les cookies frais depuis le portail Cosium

Methode 2 — script :
```bash
docker compose exec api python -c "
from app.db.session import SessionLocal
from app.core.encryption import encrypt
from app.repositories import onboarding_repo

db = SessionLocal()
for tenant in onboarding_repo.get_active_cosium_tenants(db):
    print(f'{tenant.slug}: cosium_cookie_*_enc actuels')
    # Reinjecter via le client cosium puis encrypt(new_token)
"
```

### 3. Purger les anciens credentials du repo

Les credentials sont actuellement dans :
- `.env` (clear text, gitignored mais peut etre dans l'historique)
- Code dur historique (verifier `git log -p -- .env`)

**Verification git history** :
```bash
git log --all --oneline -- '.env' | head
git log -p --all -S 'AFAOUSSI' | head -50
```

Si trouve dans l'historique :
```bash
# DESTRUCTIF : recrit l'historique. Sauvegarder une copie du repo ailleurs avant.
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch .env" \
  --prune-empty --tag-name-filter cat -- --all

# Force-push (DEMANDER NABIL avant d'executer)
git push origin --force --all
git push origin --force --tags

# Purger le reflog local
git reflog expire --expire=now --all
git gc --prune=now --aggressive
```

### 4. Mettre a jour `.env` local + `.env.prod`

```bash
# .env (dev local)
COSIUM_LOGIN=optiflow-prod-2026
COSIUM_PASSWORD='<nouveau password>'

# .env.prod (VPS, stocke chiffre via secrets)
# Ne PAS commit cette valeur. Utiliser docker secrets ou Vault.
```

### 5. Redemarrer les containers

```bash
docker compose down api worker beat
docker compose up -d --build api worker beat
docker compose logs api --tail 50  # Verifier "cosium_authenticated"
```

### 6. Verifier la sync

```bash
# Lancer un sync test
curl -H "Authorization: Bearer $TOKEN" -X POST \
  https://cosium.ia.coging.com/api/v1/sync/cosium

# Verifier le resultat dans /admin/cosium-test (UI)
```

### 7. Audit logs

Les logs Cosium (date d'auth, IP source, requests faites) sont visibles dans :
- Console Cosium fournisseur (acces Nabil)
- Sentry si configure (OptiFlow loggue les `cosium_*` events)
- `/admin/audit` filtre `entity_type=cosium_credential`

## Rollback

Si le nouveau compte ne fonctionne pas :
1. Reactiver l'ancien compte cote Cosium (si pas deja revoqué)
2. Restaurer `.env` precedent depuis backup
3. `docker compose up -d --build api worker beat`
4. Verifier sync OK

## Plan apres rotation

- [ ] Mettre a jour `docs/RUNBOOK.md` avec date rotation + nouveau login
- [ ] Mettre a jour `docs/PRODUCTION_CHECKLIST.md` (item DIFFERE-PROD #6 marque resolu)
- [ ] Configurer rotation periodique (ex: tous les 6 mois) dans calendar
- [ ] Envisager passer a OIDC (Keycloak) plus tard pour eviter password partage

## Securite long-terme

V2 envisageables :
- **Vault HashiCorp** ou **Doppler** pour stocker creds hors `.env`
- **Rotation automatique** via Celery beat (necessite API rotation cote Cosium)
- **Audit access logs** Cosium streamingvers Loki/Grafana
- **2FA** sur le compte Cosium principal Nabil

## References

- Charte Cosium read-only : `CLAUDE.md` section "SECURITE COSIUM"
- ADR-0006 : MFA TOTP optionnel (peut s'appliquer a la 2FA Cosium account)
- Hooks Cosium HAL : `apps/api/app/integrations/cosium/client.py`
