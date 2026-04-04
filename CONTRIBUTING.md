# Contribuer a OptiFlow AI

## Architecture en couches

```
Router (api/routers/)  →  Service (services/)  →  Repository (repositories/)
        ↓                        ↓                         ↓
   Pas de logique         Logique metier          Acces BDD pur
   Pas de db.query        Pas de HTTPException    Pas de logique
   response_model=        Exceptions custom       commit/refresh
```

## Creer un nouveau module

Exemple : module "prescriptions"

1. `domain/schemas/prescriptions.py` — schemas Pydantic (contrat API)
2. `models/prescription.py` — modele SQLAlchemy + migration Alembic
3. `repositories/prescription_repo.py` — CRUD BDD
4. `services/prescription_service.py` — logique metier
5. `api/routers/prescriptions.py` — routes FastAPI
6. Enregistrer le router dans `main.py`
7. `tests/test_prescriptions.py` — tests
8. Frontend si applicable

## Conventions de nommage

| Element | Convention | Exemple |
|---------|-----------|---------|
| Fichiers Python | snake_case | `case_service.py` |
| Classes | PascalCase | `CaseService` |
| Fonctions/variables | snake_case | `get_case_detail` |
| Constantes | UPPER_SNAKE | `MAX_PAGE_SIZE` |
| Endpoints API | kebab-case | `/api/v1/audit-logs` |
| Tables SQL | snake_case pluriel | `pec_requests` |
| Composants React | PascalCase | `StatusBadge.tsx` |

## Creer une migration

```bash
docker compose exec api alembic revision --autogenerate -m "add_prescriptions_table"
docker compose exec api alembic upgrade head
```

## Exceptions metier

```python
# Dans les services — jamais HTTPException
from app.core.exceptions import NotFoundError, BusinessError, ValidationError, ForbiddenError

raise NotFoundError("prescription", prescription_id)  # → 404
raise BusinessError("Ce devis est deja facture")       # → 400
raise ValidationError("montant", "Doit etre positif")  # → 422
raise ForbiddenError("Acces refuse")                   # → 403
```

## Regles Cosium

**LECTURE SEULE** : le CosiumConnector n'a que `authenticate()` et `get_*()`.
Aucun PUT/POST(sauf auth)/DELETE/PATCH vers c1.cosium.biz.

## Auth httpOnly

L'authentification utilise des cookies httpOnly pour stocker le JWT.
Le flow est le suivant :

1. `POST /api/v1/auth/login` retourne un cookie `optiflow_token` (httpOnly, SameSite=Lax, Secure en prod)
2. Chaque requete suivante envoie automatiquement le cookie via le navigateur
3. Le backend lit le token depuis le cookie (`request.cookies.get("optiflow_token")`)
4. Fallback : si le header `Authorization: Bearer <token>` est present, il est utilise en priorite (utile pour les tests et clients non-navigateur)
5. `POST /api/v1/auth/refresh` genere un nouveau access token et met a jour le cookie
6. `POST /api/v1/auth/logout` supprime le cookie (max_age=0)

Avantage : le token n'est jamais accessible en JavaScript (protection XSS).

## Encryption

Les credentials Cosium de chaque tenant sont chiffres en base avec Fernet (symmetric encryption).

- Cle de chiffrement : `ENCRYPTION_KEY` dans `.env` (generee via `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- Module : `app/core/encryption.py` expose `encrypt_value()` et `decrypt_value()`
- Usage : les champs `cosium_login` et `cosium_password` dans `tenant_cosium_credentials` sont chiffres avant stockage et dechiffres a la lecture
- Si `ENCRYPTION_KEY` est vide, les fonctions retournent la valeur en clair (mode dev uniquement)

## Lint et format

```bash
# Backend
ruff check app/ --fix && ruff format app/

# Frontend
npx prettier --write "src/**/*.{ts,tsx}" && npx tsc --noEmit
```
