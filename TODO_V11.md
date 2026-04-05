# TODO V11 — OptiFlow AI : En attendant Cosium — Le dernier mile

> **Etat** : 7 commits, 306 tests backend, 70 frontend, 126 endpoints, 25+ features.
> Cosium en attente (activation OIDC/Direct Access Grant requise).
> Cette V11 optimise ce qu'on a deja et ajoute ce qui manque pour etre impeccable.

---

## PHASE 1 : ADAPTER LE CONNECTEUR COSIUM POUR OIDC (Etapes 1-2)

> Cosium utilise Keycloak OIDC, pas /authenticate/basic. On doit adapter le client
> pour etre pret le jour ou Cosium active l'acces.

### ETAPE 1 : Refactorer CosiumClient pour supporter OIDC [ ]

> Le client actuel POST sur `/authenticate/basic`. Cosium utilise en fait Keycloak
> avec `grant_type=password` sur `https://id.neox-it.org/auth/realms/general/protocol/openid-connect/token`.

- [ ] Modifier `integrations/cosium/client.py` :
  - Ajouter un mode d'auth `oidc` en alternative a `basic`
  - La methode `authenticate()` detecte le mode :
    - Si `settings.cosium_oidc_token_url` est configure → mode OIDC (Keycloak)
    - Sinon → mode basic (ancien, pour compatibilite)
  - En mode OIDC :
    ```python
    response = self._client.post(settings.cosium_oidc_token_url, data={
        "grant_type": "password",
        "client_id": settings.cosium_oidc_client_id,
        "username": login,
        "password": password,
    })
    self.token = response.json()["access_token"]
    ```
  - Le header d'API passe de `AccessToken {token}` a `Bearer {token}` en mode OIDC
- [ ] Ajouter dans `config.py` :
  ```python
  cosium_oidc_token_url: str = ""  # ex: https://id.neox-it.org/auth/realms/general/protocol/openid-connect/token
  cosium_oidc_client_id: str = ""  # ex: 594d43b0-7361-4adf-a0d9-72ad5c7c5731
  ```
- [ ] Ajouter dans `.env.example` : `COSIUM_OIDC_TOKEN_URL=` et `COSIUM_OIDC_CLIENT_ID=`
- [ ] Tests : mock OIDC token endpoint → verifie que le token est obtenu et utilise en Bearer

---

### ETAPE 2 : Script de test Cosium interactif [ ]

> Creer un script standalone qui teste la connexion Cosium etape par etape.

- [ ] Creer `scripts/test_cosium.py` :
  - Lit les credentials depuis `.env`
  - Teste l'auth (basic ou OIDC selon la config)
  - Fetche 5 clients et les affiche
  - Fetche 3 factures et les affiche
  - Affiche un resume : "Connexion OK, X clients, Y factures disponibles"
  - Usage : `docker compose exec api python scripts/test_cosium.py`
- [ ] Documenter dans le README la section "Connexion Cosium"

---

## PHASE 2 : DECOUPER LES DERNIERS GROS FICHIERS (Etapes 3-4)

### ETAPE 3 : Decouper les 3 fichiers frontend > 300 lignes [ ]

> `clients/[id]` (352), `admin` (348), `rapprochement` (343)

- [ ] `clients/[id]/page.tsx` (352 lignes) : extraire le bloc avatar + upload dans un composant `components/AvatarUpload.tsx`
- [ ] `admin/page.tsx` (348 lignes) : extraire le graphique d'activite dans `admin/components/ActivityChart.tsx` et la section sante dans `admin/components/HealthStatus.tsx`
- [ ] `rapprochement/page.tsx` (343 lignes) : extraire les sections drag-drop existantes dans un composant `rapprochement/components/ManualReconciliation.tsx`
- [ ] Objectif : 0 fichier frontend > 300 lignes

---

### ETAPE 4 : Decouper les 3 fichiers backend > 300 lignes [ ]

> `seed_demo.py` (435), `pdf_service.py` (372), `reminder_repo.py` (350)

- [ ] `pdf_service.py` (372) : extraire les helpers communs (`_build_header`, `_build_customer_block`, `_build_lines_table`, `_build_totals`) dans `pdf_helpers.py`
- [ ] `reminder_repo.py` (350) : extraire les fonctions `get_all_overdue`, `get_overdue_payments`, `get_overdue_pec` dans `reminder_overdue_repo.py`
- [ ] `seed_demo.py` : acceptable (script one-shot, pas du code metier)
- [ ] Objectif : 0 fichier backend metier > 300 lignes (hors seed)

---

## PHASE 3 : TESTS FRONTEND (Etapes 5-6)

> 33 pages, 0 test de page. 10 fichiers de test sur des composants basiques.

### ETAPE 5 : Tests des 5 pages les plus critiques [ ]

- [ ] `tests/pages/login.test.tsx` :
  - Rendu du formulaire (email, password, bouton)
  - Bouton desactive si champs vides
  - Appel API mock sur submit
  - Message d'erreur si login echoue
- [ ] `tests/pages/dashboard.test.tsx` :
  - Rendu des KPI cards
  - Affichage du date picker
  - LoadingState pendant le chargement
- [ ] `tests/pages/clients.test.tsx` :
  - Rendu de la liste
  - Bouton "Nouveau client" present
  - Boutons "Importer CSV" et "Exporter CSV" presents
  - Bouton "Doublons" present
- [ ] `tests/pages/cases-new.test.tsx` :
  - Rendu du formulaire
  - Validation (nom vide → erreur)
  - Submit mock
- [ ] `tests/pages/search.test.tsx` :
  - GlobalSearch : pas d'appel API si < 2 chars
  - Resultats affiches (mock SWR)

---

### ETAPE 6 : Tests des composants avances [ ]

- [ ] `tests/components/DarkModeToggle.test.tsx` : toggle fonctionne, persist localStorage
- [ ] `tests/components/DraggableTransaction.test.tsx` : draggable attribute, dataTransfer set
- [ ] `tests/components/DroppablePayment.test.tsx` : onMatch called on drop
- [ ] `tests/components/ExportCsv.test.tsx` : exporte un blob CSV correct
- [ ] Objectif : 100+ tests frontend

---

## PHASE 4 : POLISH UX (Etapes 7-9)

### ETAPE 7 : Templates email HTML professionnels [ ]

> Les emails (relances, reset password) sont du HTML brut inline.

- [ ] Creer `backend/app/templates/` avec des templates Jinja2 :
  - `password_reset.html` : email style, logo OptiFlow, bouton "Reinitialiser", footer
  - `relance_client.html` : email professionnel avec montant, date, lien de paiement
  - `welcome.html` : email de bienvenue apres inscription
- [ ] Ajouter `jinja2` dans `requirements.txt`
- [ ] Modifier `email_sender.py` : ajouter `render_template(template_name, context)` qui charge et rend le template
- [ ] Utiliser les templates dans `auth_service.py` (reset) et `reminder_service.py` (relances)
- [ ] Verifier dans Mailhog : les emails sont beaux et formattes

---

### ETAPE 8 : Page de statistiques avancees [ ]

> Le dashboard montre les KPIs du magasin. Il manque une page de stats detaillees.

- [ ] Creer `frontend/src/app/statistiques/page.tsx` :
  - Graphique CA mensuel (12 derniers mois) — Recharts LineChart
  - Graphique nombre de devis vs factures par mois — BarChart
  - Top 10 clients par CA — tableau trie
  - Taux de conversion devis → facture par mois — LineChart
  - Repartition des modes de paiement — PieChart
- [ ] Backend : creer `GET /api/v1/analytics/advanced` qui retourne ces donnees agregees
- [ ] Ajouter "Statistiques" dans la sidebar

---

### ETAPE 9 : Page d'aide et support [ ]

> Un SaaS doit avoir une page d'aide minimale.

- [ ] Creer `frontend/src/app/aide/page.tsx` :
  - FAQ (5-10 questions frequentes avec accordeons)
  - Guide de demarrage rapide (les 5 premieres etapes)
  - Lien vers la documentation technique (README/CONTRIBUTING)
  - Formulaire de contact support (email via `fetchJson` → backend envoie a une adresse support)
  - Raccourcis clavier (Ctrl+K, Ctrl+N, Escape)
- [ ] Ajouter "Aide" dans la sidebar (icone HelpCircle)

---

## PHASE 5 : SECURITE ET DEPS (Etapes 10-11)

### ETAPE 10 : Mettre a jour les deps vulnerables [ ]

> pip audit a identifie des vulns dans cryptography, pyjwt, python-multipart, starlette.

- [ ] Mettre a jour dans `requirements.txt` :
  - `cryptography>=46.0.6` (CVE-2026-26007, CVE-2026-34073)
  - `PyJWT>=2.12.0` (CVE-2026-32597)
  - `python-multipart>=0.0.22` (CVE-2026-24486)
  - `starlette>=0.49.1` (CVE-2025-62727)
- [ ] `docker compose exec api pip install -r requirements.txt`
- [ ] `pytest -q` → tout passe encore
- [ ] Re-run `pip audit` → 0 vulns

---

### ETAPE 11 : Consolidation finale [ ]

- [ ] Fusionner TODO V1-V10 en un seul `docs/HISTORIQUE_TODO.md` (archive)
- [ ] Garder TODO_V11.md comme reference active
- [ ] Mettre a jour `CHANGELOG.md` avec v1.3.0
- [ ] Mettre a jour `README.md` avec les nouvelles features (import CSV, doublons, dark mode, SSE, drag-drop)
- [ ] Tag Git : `git tag v1.3.0 -m "OptiFlow AI v1.3.0"`
- [ ] Verification finale :
  - `pytest -q` → 310+ pass
  - `vitest run` → 100+ pass
  - `ruff check` + `tsc --noEmit` → 0 erreur
  - 0 fichier > 300 lignes (hors seed)
  - Login + Dashboard + Recherche + PDF + Dark mode + SSE → tout OK

---

## Checkpoints

### Apres PHASE 1 (Etapes 1-2) :
- [ ] Connecteur Cosium pret pour OIDC ET basic
- [ ] Script de test Cosium standalone

### Apres PHASE 2 (Etapes 3-4) :
- [ ] 0 fichier metier > 300 lignes

### Apres PHASE 3 (Etapes 5-6) :
- [ ] 100+ tests frontend

### Apres PHASE 4 (Etapes 7-9) :
- [ ] Emails HTML professionnels
- [ ] Page statistiques avancees
- [ ] Page aide et support

### Apres PHASE 5 (Etapes 10-11) :
- [ ] 0 vulnerabilite connue dans les deps
- [ ] Tag v1.3.0
- [ ] **Pret pour le test Cosium reel des que les credentials OIDC sont actives**
