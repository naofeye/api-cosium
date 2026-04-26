# Authentification Cosium — 3 modes

Base URL : `https://c1.cosium.biz/{tenant}/api`

> **⚠️ RAPPEL SÉCURITÉ** : OptiFlow ne fait que **GET** (lecture) sur Cosium. Le seul `POST` autorisé est `/authenticate/basic`. Voir [CLAUDE.md](../CLAUDE.md) pour les règles complètes.

## Mode 1 — Basic Auth (recommandé serveur)

Utilise login + password Cosium pour obtenir un AccessToken.

```python
# apps/api/app/integrations/cosium/client.py
def authenticate(self, tenant: str, login: str, password: str) -> str:
    resp = self.http.post(
        f"/{tenant}/api/authenticate/basic",
        json={"login": login, "password": password},
    )
    return resp.json()["AccessToken"]
```

**Variables .env** :
```
COSIUM_BASE_URL=https://c1.cosium.biz
COSIUM_TENANT=mon-tenant
COSIUM_LOGIN=optiflow-user
COSIUM_PASSWORD=<secret>
```

**Usage** : pour les tasks Celery de sync (pas de session utilisateur).

## Mode 2 — OIDC (Keycloak password grant)

Si Cosium fédère avec un IdP qui expose un endpoint OIDC token (ex: Keycloak).
Le code (`apps/api/app/integrations/cosium/client.py::_authenticate_oidc`) implémente un **password grant**, pas un `client_credentials`.

```python
# Implémentation réelle : password grant (login + password Cosium)
def _authenticate_oidc(self, login: str, password: str) -> str:
    resp = self._client.post(
        settings.cosium_oidc_token_url,
        data={
            "grant_type": "password",
            "client_id": settings.cosium_oidc_client_id,
            "username": login,
            "password": password,
        },
    )
    return resp.json()["access_token"]
```

**Variables .env** :
```
COSIUM_OIDC_TOKEN_URL=https://<keycloak-host>/realms/<realm>/protocol/openid-connect/token
COSIUM_OIDC_CLIENT_ID=<client-id-public>
COSIUM_LOGIN=<login Cosium>
COSIUM_PASSWORD=<password Cosium>
```

**Note** : aucun `client_secret` n'est utilisé (client OIDC public). Si un déploiement Cosium impose `client_credentials` ou `confidential client`, ajouter le champ `cosium_oidc_client_secret` dans `core/config.py` et adapter `_authenticate_oidc()`.

**Usage** : environnements qui imposent OIDC plutôt que `/authenticate/basic`.

## Mode 3 — Cookie (interactif, exceptionnel)

Récupère les cookies `access_token` + `device-credential` du navigateur après login manuel.

**Usage** : dev local / debug quand Basic Auth n'est pas disponible. **Jamais en prod.**

```
COSIUM_ACCESS_TOKEN=<cookie access_token>
COSIUM_DEVICE_CREDENTIAL=<cookie device-credential>
```

## Refresh & expiration

- AccessToken Cosium : durée ~4h (à confirmer avec Cosium)
- OptiFlow garde le token en mémoire worker, refresh automatique sur 401
- Pas de cache Redis partagé (éviter fuites cross-tenant)

## Switch tenant multi-magasin

Chaque tenant OptiFlow a ses propres credentials Cosium dans `tenant_cosium_credentials` (chiffrés Fernet) :

```python
creds = tenant_cosium_credentials_repo.get(db, tenant_id)
login = decrypt(creds.login_encrypted)
password = decrypt(creds.password_encrypted)
token = cosium.authenticate(creds.tenant_slug, login, password)
```

## Rotation des credentials

Procédure (docs/RUNBOOK.md pour les détails) :
1. Créer un nouveau user dans Cosium
2. `UPDATE tenant_cosium_credentials SET login_encrypted=..., password_encrypted=...`
3. Déclencher sync manuelle pour vérifier
4. Désactiver l'ancien user côté Cosium

## Endpoints autorisés (rappel)

| API | Méthode | Endpoint |
|-----|---------|----------|
| Auth | POST | `/authenticate/basic` |
| Customers | GET | `/customers` |
| Invoices | GET | `/invoices`, `/invoiced-items` |
| Products | GET | `/products`, `/products/{id}/stock`, `/products/{id}/latent-sales` |
| Payment Types | GET | `/payment-types` |

Tout le reste (PUT, POST hors auth, DELETE, PATCH) est **INTERDIT**.
