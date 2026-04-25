# CLAUDE.md - Directive pour Claude CLI / Codex

> Ce fichier est la source de verite pour la session `api-cosium-claude`.
> **vps-master** peut aussi intervenir sur ce projet et doit mettre a jour ce fichier.
> Voir la section "Dernieres interventions vps-master" en bas.

## Memoire persistante inter-sessions

**Au demarrage de CHAQUE session (avant toute action), lire `.claude-memory/MEMORY.md` puis les fichiers qu'il reference.**
Ce dossier est la memoire versionnee du projet (feedback utilisateur, historique sessions, deploiement VPS, etc.). Il est synchronise via `git pull` donc disponible sur toutes les machines (poste local + VPS).
Quand tu apprends quelque chose d'important a memoriser (preference user, decision architecturale, incident resolu), ajoute/mets a jour un fichier dans `.claude-memory/` et reference-le dans `.claude-memory/MEMORY.md`, puis commit.

## Mode de fonctionnement

**Au demarrage, TOUJOURS executer l'ETAPE 0 (health check) puis reprendre la prochaine etape non cochee.**

1. **ETAPE 0 OBLIGATOIRE** : Execute un health check (verification environnement : Docker, services, API, frontend). Si un service echoue, corriger AVANT de continuer.
2. Lis les instructions de l'utilisateur et execute les taches demandees
3. Lis le bloc de contexte (fichiers a lire, specs de reference)
4. Execute chaque sous-tache `- [ ]` dans l'ordre
5. Quand une sous-tache est terminee, coche-la : `- [x]`
6. Quand toutes les sous-taches sont faites, coche l'etape : `## ETAPE X : ... [x]`
7. Fais la **checklist de validation** (voir ci-dessous)
8. **ARRETE-TOI** et affiche un resume : ce qui a ete fait, ce qui a ete verifie, les problemes rencontres
9. Attends que l'utilisateur dise **"continue"** pour passer a l'etape suivante

**Si l'utilisateur te dit "continue" sans autre instruction** : reprends a la prochaine tache non cochee.
**Si l'utilisateur te dit "continue auto"** : enchaine les etapes sans attendre (mode autonome).

### Checklist de validation (obligatoire apres chaque etape)

Avant de marquer une etape comme terminee, verifie TOUT :

1. `docker compose up --build` demarre sans erreur
2. Aucune erreur Python au demarrage (pas d'import manquant, pas de syntax error)
3. Si des tests existent : `docker compose exec api pytest -v` passe a 100%
4. Les endpoints modifies/crees repondent correctement via Swagger (http://localhost:8000/docs)
5. Le frontend compile sans erreur (`docker compose logs web` ne montre pas d'erreur)

Si un check echoue : corrige avant de cocher l'etape. Ne coche JAMAIS une etape qui ne passe pas la validation.

## Identite du projet

**OptiFlow AI** est une plateforme metier pour opticiens qui se branche sur l'ERP Cosium (cloud, heberge sur c1.cosium.biz). Elle centralise : CRM client, gestion documentaire (GED), devis/ventes, remboursements mutuelles/secu, facturation, paiements, rapprochement bancaire, marketing, et assistants IA.

## Stack technique

- **Backend** : Python 3.12 + FastAPI + SQLAlchemy 2.x + PostgreSQL 16
- **Frontend** : Next.js 15 + React 19 + TypeScript
- **Infra** : Docker Compose (PostgreSQL, Redis 7, MinIO, Mailhog, API, Web)
- **Auth** : JWT (PyJWT) + bcrypt (passlib)
- **Tests** : pytest + httpx (a configurer)
- **Migrations** : Alembic (configure, utilise `alembic upgrade head`)

## Architecture obligatoire

Respecter la separation en couches du backend :
```
backend/app/
  api/              # Routes FastAPI (routers) - PAS de logique metier
  services/         # Logique metier (un service par domaine)
  domain/           # Modeles Pydantic (schemas request/response)
  models/           # Modeles SQLAlchemy (ORM)
  repositories/     # Acces base de donnees
  integrations/     # Connecteurs externes (Cosium, email, SMS, S3)
  core/             # Config, security, logging, exceptions
  db/               # Engine, session, migrations Alembic
```

Frontend : composants reutilisables dans `components/`, logique API dans `lib/`, pages dans `app/`.

## Regles de developpement (Charte)

### Les 9 regles fondamentales

1. **Typage partout** : annotations Python sur toutes les fonctions, TypeScript strict cote front
2. **Validation explicite** : Pydantic models pour toutes les entrees/sorties API
3. **Pas de logique metier dans les routers** : les routes appellent des services
4. **Gestion d'erreurs propre** : exceptions metier custom, pas de HTTPException brut dans les services
5. **Logging structure** : logs JSON avec contexte (user_id, action, entity_type, entity_id)
6. **Tests obligatoires** : chaque service doit avoir ses tests unitaires, chaque endpoint un test d'integration
7. **Migrations versionnees** : Alembic pour toute modification de schema, jamais create_all en prod
8. **Audit trail** : table audit_logs pour toute operation sensible (creation, modification, suppression, paiement)
9. **Integration encapsulee** : chaque API externe derriere un adaptateur (pattern port/adapter), jamais d'appel direct depuis un service

### Patterns obligatoires (exemples)

**Router (api/routers/) — SLIM, pas de logique :**
```python
# BON : le router delegue tout au service
@router.post("/cases", response_model=CaseResponse, status_code=201)
def create_case(
    payload: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> CaseResponse:
    return case_service.create_case(db, payload, current_user.id)

# INTERDIT : logique metier dans le router
@router.post("/cases")
def create_case(payload: dict, db: Session = Depends(get_db)):
    customer = Customer(**payload)  # NON : c'est de la logique metier
    db.add(customer)               # NON : c'est de l'acces BDD
    db.commit()                    # NON : pas dans un router
```

**Service (services/) — logique metier pure :**
```python
# Le service ne connait PAS FastAPI, pas de Request, pas de HTTPException
def create_case(db: Session, payload: CaseCreate, user_id: int) -> CaseResponse:
    customer = client_repo.create(db, payload.first_name, payload.last_name, ...)
    case = case_repo.create(db, customer.id, payload.source)
    audit_service.log_action(db, user_id, "create", "case", case.id)
    logger.info("Case created", case_id=case.id, user_id=user_id)
    return CaseResponse.model_validate(case)
```

**Repository (repositories/) — SQL pur, pas de logique :**
```python
# Le repo ne fait QUE des requetes BDD
def get_by_id(db: Session, case_id: int) -> Case | None:
    return db.query(Case).filter(Case.id == case_id).first()

def create(db: Session, customer_id: int, source: str) -> Case:
    case = Case(customer_id=customer_id, status="draft", source=source)
    db.add(case)
    db.commit()
    db.refresh(case)
    return case
```

**Schema Pydantic (domain/schemas/) — validation stricte :**
```python
class CaseCreate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = None
    email: EmailStr | None = None
    source: str = "manual"

class CaseResponse(BaseModel):
    id: int
    customer_name: str
    status: str
    source: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### Anti-patterns INTERDITS

- **Pas de `dict` en entree/sortie d'endpoint** : toujours un schema Pydantic
- **Pas de `db.query()` dans un router** : toujours via un repository
- **Pas de `HTTPException` dans un service** : lever une exception metier custom
- **Pas de `print()`** : utiliser le logger
- **Pas de `import *`** : imports explicites uniquement
- **Pas de TODO/FIXME laisses dans le code** : corriger immediatement ou creer une issue
- **Pas de secrets en dur** : tout dans .env via settings Pydantic
- **Pas de fichier de plus de 300 lignes** : decouper si ca depasse
- **Pas de fonction de plus de 50 lignes** : extraire en sous-fonctions
- **Pas de copier-coller** : factoriser dans une fonction utilitaire

### Conventions de nommage

- **Fichiers Python** : snake_case (`case_service.py`, `client_repo.py`)
- **Classes** : PascalCase (`CaseService`, `ClientRepository`)
- **Fonctions/variables** : snake_case (`get_case_detail`, `total_amount`)
- **Constantes** : UPPER_SNAKE_CASE (`MAX_PAGE_SIZE = 100`)
- **Endpoints API** : kebab-case dans l'URL (`/api/v1/audit-logs`)
- **Tables SQL** : snake_case pluriel (`cases`, `audit_logs`, `pec_requests`)
- **Fichiers TypeScript** : PascalCase pour les composants (`Navbar.tsx`), camelCase pour les utilitaires (`api.ts`)

### Structure d'un nouveau module (template)

Quand tu crees un nouveau module (ex: "devis"), cree TOUJOURS ces fichiers dans cet ordre :
1. `domain/schemas/devis.py` — schemas Pydantic en premier (ca definit le contrat)
2. `models.py` — ajouter le modele SQLAlchemy + migration Alembic
3. `repositories/devis_repo.py` — acces BDD
4. `services/devis_service.py` — logique metier
5. `api/routers/devis.py` — routes FastAPI
6. Enregistrer le router dans `main.py`
7. `tests/test_devis.py` — tests
8. Frontend pages si applicable

## ⛔ SECURITE COSIUM — LECTURE SEULE (CRITIQUE)

> **REGLE ABSOLUE : OptiFlow ne doit JAMAIS modifier, creer ou supprimer quoi que ce soit dans Cosium.**
> Cosium est l'ERP de production du client. Toute ecriture accidentelle peut corrompre des donnees metier irreversibles.
> La synchronisation est UNIDIRECTIONNELLE : Cosium → OptiFlow uniquement.

### Methodes HTTP AUTORISEES vers Cosium

| Methode | Usage | Autorise ? |
|---------|-------|------------|
| `POST /authenticate/basic` | Obtenir un token d'authentification | ✅ OUI (seul POST autorise) |
| `GET /*` | Lecture de donnees (clients, factures, produits...) | ✅ OUI |
| `PUT /*` | Modification de donnees | ⛔ **INTERDIT** |
| `POST /*` (sauf auth) | Creation de donnees | ⛔ **INTERDIT** |
| `DELETE /*` | Suppression de donnees | ⛔ **INTERDIT** |
| `PATCH /*` | Modification partielle | ⛔ **INTERDIT** |

### Endpoints Cosium AUTORISES (liste exhaustive)

Base URL : `https://c1.cosium.biz/{tenant}/api`
Auth : POST `/{tenant}/api/authenticate/basic` → AccessToken
Format : HAL (application/hal+json)

| API | Endpoint | Methode | Capacite |
|-----|----------|---------|----------|
| Auth | /authenticate/basic | POST | Obtenir un token (seul POST autorise) |
| Customers | /customers | GET | Recherche clients (nom, email, tel, date naissance) |
| Invoices | /invoices | GET | Factures, devis, avoirs (16 types de docs) |
| Invoiced Items | /invoiced-items | GET | Lignes de facture detaillees |
| Products | /products | GET | Catalogue produits (EAN, GTIN) |
| Products | /products/{id}/stock | GET | Stocks par site |
| Products | /products/{id}/latent-sales | GET | Ventes latentes |
| Payment Types | /payment-types | GET | Moyens de paiement |

### Endpoints Cosium INTERDITS (ne JAMAIS implementer)

Ces endpoints existent dans l'API Cosium mais sont **FORMELLEMENT INTERDITS** dans OptiFlow :

- ⛔ `PUT /customers/subscribed-to-email`
- ⛔ `PUT /customers/unsubscribed-from-email`
- ⛔ `PUT /customers/subscribed-to-paper`
- ⛔ `PUT /customers/unsubscribed-from-paper`
- ⛔ `PUT /customers/subscribed-to-sms`
- ⛔ `PUT /customers/unsubscribed-from-sms`
- ⛔ Tout autre endpoint en PUT, POST (sauf auth), DELETE, PATCH

### Regles d'implementation du CosiumClient

```python
# OBLIGATOIRE : Le CosiumClient ne doit implementer QUE ces methodes :
class CosiumClient:
    def authenticate(self, tenant: str, login: str, password: str) -> str:
        """POST /authenticate/basic — SEUL POST autorise"""
        ...

    def get(self, endpoint: str, params: dict | None = None) -> dict:
        """GET generique — SEULE methode de lecture"""
        ...

    # ⛔ INTERDIT : pas de methode put(), post(), delete(), patch()
    # ⛔ INTERDIT : pas de methode generique send() ou request() avec methode variable
    # ⛔ INTERDIT : pas de httpx.put(), httpx.post(), httpx.delete(), httpx.patch() vers Cosium
```

**Verification obligatoire** : Avant de valider l'ETAPE 15, verifier que :
1. Le `CosiumClient` n'a QUE `authenticate()` et `get()` comme methodes
2. Aucun `PUT`, `POST` (sauf auth), `DELETE`, `PATCH` n'est envoye vers `c1.cosium.biz`
3. Les tests mockent le client et verifient qu'aucune ecriture n'est possible
4. Aucun endpoint de l'API OptiFlow ne declenche une ecriture vers Cosium

**IMPORTANT** : CORS desactive sur Cosium. Tous les appels Cosium doivent passer par le backend (proxy), jamais depuis le frontend.

## 🎨 CHARTE FRONTEND — QUALITE PROFESSIONNELLE (CRITIQUE)

> **REGLE ABSOLUE : Le frontend doit etre de qualite professionnelle, intuitif, et concu pour des opticiens qui ne sont PAS des experts informatiques.**
> Chaque ecran doit repondre en moins de 3 secondes aux questions : "Qu'est-ce qui se passe ?", "Qu'est-ce que je dois faire ?", "Quel est l'impact financier/client ?"
> Le design doit inspirer confiance et maitrise immediate, comme un cockpit de pilotage metier — pas comme un ERP dense.

### Stack frontend obligatoire

```
Next.js 15 + React 19 + TypeScript strict
Tailwind CSS (utilitaires)
shadcn/ui (composants de base : Button, Card, Dialog, Table, Badge, etc.)
Lucide React (icones)
Recharts (graphiques)
```

**A installer des l'ETAPE 6** :
```bash
npx shadcn@latest init
npm install tailwindcss @tailwindcss/forms lucide-react recharts
npm install clsx tailwind-merge class-variance-authority
```

### Philosophie UX — Les 10 principes fondamentaux

1. **Clarte avant beaute** : chaque element a une fonction. Pas de decoration inutile, pas d'animation gratuite, pas de bruit visuel. L'information doit sauter aux yeux.

2. **Zero jargon technique** : les labels, boutons, messages d'erreur, etats vides doivent etre rediges en francais clair et humain. Pas de "Error 404 Not Found" mais "Ce dossier n'existe pas ou a ete supprime". Pas de "Submit" mais "Enregistrer" ou "Valider".

3. **Actions visibles sans scroller** : les boutons d'action principaux (Creer, Enregistrer, Envoyer) doivent TOUJOURS etre visibles sans scroller. Utiliser des barres d'actions collantes (`sticky`) en haut ou en bas.

4. **Feedback instantane** : chaque action utilisateur doit produire un retour visible en moins de 200ms. Un clic sur un bouton = spinner + texte de chargement. Un enregistrement reussi = toast de confirmation vert. Une erreur = toast rouge avec message humain.

5. **Etats explicites** : chaque page/composant DOIT gerer 4 etats distincts :
   - **Loading** : skeleton ou spinner avec texte ("Chargement des dossiers...")
   - **Erreur** : message humain + bouton "Reessayer" + lien support si pertinent
   - **Vide** : illustration legere + texte explicatif + bouton d'action ("Aucun dossier. Creer le premier ?")
   - **Donnees** : affichage normal avec pagination si necessaire

6. **Navigation predictible** : l'utilisateur doit TOUJOURS savoir ou il est (breadcrumb), comment revenir en arriere, et ou aller ensuite. Pas de cul-de-sac.

7. **Formulaires intelligents** : validation en temps reel champ par champ (pas juste a la soumission), labels au-dessus des champs (jamais a gauche), placeholder qui donne un exemple concret, messages d'erreur sous le champ fautif en rouge, bouton de soumission desactive tant que le formulaire est invalide.

8. **Donnees financieres lisibles** : les montants en euros TOUJOURS formates (1 234,56 €), les pourcentages avec 1 decimale (85,3%), les dates en format francais (03/04/2026), les statuts en badges colores.

9. **Responsive pragmatique** : desktop first (ecran 1920x1080 = cible principale), mais le layout doit rester utilisable a 1366x768 (ecran laptop). Pas de mobile pour le MVP — c'est un outil de bureau.

10. **Accessibilite de base** : contrastes WCAG AA, navigation clavier possible, attributs aria-label sur les icones sans texte, focus visible sur les elements interactifs.

### Design system — Tokens visuels obligatoires

```typescript
// Utiliser ces tokens dans TOUT le frontend

// COULEURS FONCTIONNELLES (pas decoratives)
const colors = {
  // Actions principales
  primary: "blue-600",       // Boutons principaux, liens actifs
  primaryHover: "blue-700",

  // Etats metier
  success: "emerald-600",    // Paye, complet, valide, accepte
  warning: "amber-500",      // Attention, en attente, bientot en retard
  danger: "red-600",         // En retard, refuse, erreur, bloquant
  info: "sky-500",           // Information neutre, en cours

  // Fond et texte
  bgPage: "gray-50",        // Fond de page
  bgCard: "white",          // Fond des cartes
  bgSidebar: "gray-900",    // Fond sidebar (sombre)
  textPrimary: "gray-900",  // Texte principal
  textSecondary: "gray-500", // Texte secondaire
  textOnDark: "white",      // Texte sur fond sombre
  border: "gray-200",       // Bordures legeres
};

// TYPOGRAPHIE
// - Titres de page : text-2xl font-bold text-gray-900
// - Titres de section : text-lg font-semibold text-gray-800
// - Texte courant : text-sm text-gray-700
// - Labels de formulaire : text-sm font-medium text-gray-700
// - Texte secondaire : text-sm text-gray-500
// - Montants financiers : text-base font-semibold tabular-nums
// - Badges : text-xs font-medium

// ESPACEMENTS
// - Padding de carte : p-6
// - Gap entre cartes : gap-6
// - Padding de page : px-6 py-8
// - Marge entre sections : space-y-8

// OMBRES
// - Cartes : shadow-sm border border-gray-200
// - Modales : shadow-xl
// - Dropdowns : shadow-lg

// ARRONDIS
// - Boutons : rounded-lg
// - Cartes : rounded-xl
// - Badges : rounded-full
// - Inputs : rounded-lg
```

### Layout principal obligatoire

```
┌─────────────────────────────────────────────────────────────────┐
│ ┌──────────┐  ┌──────────────────────────────────────────────┐  │
│ │           │  │  Header : breadcrumb + recherche + notifs   │  │
│ │  SIDEBAR  │  ├──────────────────────────────────────────────┤  │
│ │           │  │                                              │  │
│ │  Logo     │  │              CONTENU PRINCIPAL               │  │
│ │  ─────    │  │                                              │  │
│ │  Actions  │  │  - File d'actions (accueil)                 │  │
│ │  Dashboard│  │  - Dashboard KPIs                           │  │
│ │  Dossiers │  │  - Listes / Details                         │  │
│ │  Clients  │  │  - Formulaires                              │  │
│ │  Devis    │  │  - Rapprochement bancaire                   │  │
│ │  Factures │  │                                              │  │
│ │  PEC      │  │                                              │  │
│ │  Paiements│  ├──────────────────────────────────────────────┤  │
│ │  Relances │  │  Footer sticky : actions contextuelles      │  │
│ │  Marketing│  └──────────────────────────────────────────────┘  │
│ │  ─────    │                                                    │
│ │  Admin    │                                                    │
│ │  IA       │                                                    │
│ └──────────┘                                                    │
└─────────────────────────────────────────────────────────────────┘
```

**Sidebar** : fixe a gauche, largeur 256px, fond sombre (gray-900), texte blanc, icones Lucide, items avec hover (gray-800), item actif avec fond primary + bordure gauche, collapse possible en icones seules (64px) pour gagner de l'espace.

**Header** : hauteur 64px, fond blanc, ombre legere, contient : breadcrumb a gauche, barre de recherche globale au centre, icone notifications (cloche avec badge rouge) + avatar utilisateur a droite.

**Contenu** : fond gray-50, padding px-6 py-8, max-width 1440px centre.

### Composants reutilisables obligatoires

Creer ces composants dans `frontend/src/components/ui/` des l'ETAPE 6. Les reutiliser PARTOUT.

```
components/
  layout/
    Sidebar.tsx          — Navigation laterale avec items, collapse, badge compteurs
    Header.tsx           — Breadcrumb + recherche + notifications + avatar
    PageLayout.tsx       — Wrapper page (titre, description, actions, contenu)
    PageHeader.tsx       — Titre de page + boutons d'action (sticky si formulaire)
  ui/
    Button.tsx           — shadcn/ui, variantes : primary, secondary, danger, ghost, outline
    Card.tsx             — shadcn/ui, avec header optionnel, footer optionnel
    Badge.tsx            — shadcn/ui, couleurs par statut : success, warning, danger, info, default
    DataTable.tsx        — Tableau de donnees avec tri, filtres, pagination, actions par ligne
    EmptyState.tsx       — Illustration + titre + description + bouton CTA
    LoadingState.tsx     — Skeleton loader ou spinner avec texte
    ErrorState.tsx       — Message d'erreur + bouton reessayer
    StatusBadge.tsx      — Badge de statut metier (brouillon, en_cours, paye, refuse, etc.)
    MoneyDisplay.tsx     — Affichage montant formate (1 234,56 €) avec couleur (vert si positif, rouge si negatif)
    DateDisplay.tsx      — Date formatee en francais (03 avr. 2026)
    ConfirmDialog.tsx    — Modale de confirmation pour actions destructives
    Toast.tsx            — Notification temporaire (succes, erreur, info)
    SearchInput.tsx      — Barre de recherche avec debounce (300ms)
    KPICard.tsx          — Card KPI : icone, valeur, label, tendance (+/- %), couleur
    AgingTable.tsx       — Balance agee avec code couleur par tranche
    Timeline.tsx         — Chronologie verticale d'evenements/interactions
    FileUpload.tsx       — Zone drag & drop + bouton parcourir, preview, progression
    Pagination.tsx       — Navigation de pages avec taille de page configurable
  form/
    FormField.tsx        — Wrapper champ (label, input, message erreur, aide)
    Select.tsx           — Select custom avec options, placeholder, validation
    DateRangePicker.tsx  — Selecteur de plage de dates (debut/fin)
    Input.tsx            — Input shadcn/ui enrichi (icone gauche, compteur caracteres)
    Textarea.tsx         — Zone texte multi-lignes avec compteur
  navigation/
    Tabs.tsx             — Onglets navigables (shadcn/ui Tabs, TabsList, TabsTrigger, TabsContent)
    Breadcrumb.tsx       — Fil d'Ariane avec liens cliquables
```

### Patterns de page obligatoires

**Page liste** (clients, dossiers, devis, factures, PEC, paiements, relances) :
```tsx
<PageLayout
  title="Dossiers"
  description="Gestion des dossiers clients"
  actions={<Button onClick={...}>Nouveau dossier</Button>}
>
  {/* Barre de filtres */}
  <div className="flex items-center gap-4 mb-6">
    <SearchInput placeholder="Rechercher un dossier..." onSearch={...} />
    <Select label="Statut" options={statusOptions} />
    <DateRangePicker />
    <Button variant="outline" onClick={exportCSV}>Exporter</Button>
  </div>

  {/* Tableau avec etats */}
  {isLoading ? <LoadingState text="Chargement des dossiers..." /> :
   isError ? <ErrorState message={error.message} onRetry={refetch} /> :
   data.length === 0 ? <EmptyState
     title="Aucun dossier"
     description="Commencez par creer votre premier dossier client."
     action={<Button>Creer un dossier</Button>}
   /> :
   <DataTable columns={columns} data={data} />}

  {/* Pagination */}
  <Pagination total={totalCount} page={page} pageSize={pageSize} />
</PageLayout>
```

**Page detail** (dossier, client, devis, facture) :
```tsx
<PageLayout
  title={`Dossier #${case.id} — ${case.customerName}`}
  breadcrumb={[
    { label: "Dossiers", href: "/cases" },
    { label: `#${case.id}` }
  ]}
  actions={
    <div className="flex gap-2">
      <Button variant="outline">Modifier</Button>
      <Button variant="danger">Supprimer</Button>
    </div>
  }
>
  {/* En-tete avec KPIs rapides */}
  <div className="grid grid-cols-4 gap-4 mb-8">
    <KPICard icon={FileText} label="Documents" value={docCount} />
    <KPICard icon={Euro} label="Total facture" value={totalInvoiced} />
    <KPICard icon={CheckCircle} label="Encaisse" value={totalPaid} color="success" />
    <KPICard icon={AlertCircle} label="Reste du" value={remaining} color="danger" />
  </div>

  {/* Onglets */}
  <Tabs defaultValue="resume">
    <TabsList>
      <TabsTrigger value="resume">Resume</TabsTrigger>
      <TabsTrigger value="documents">Documents ({docCount})</TabsTrigger>
      <TabsTrigger value="finances">Finances</TabsTrigger>
      <TabsTrigger value="historique">Historique</TabsTrigger>
    </TabsList>
    <TabsContent value="resume">...</TabsContent>
    <TabsContent value="documents">...</TabsContent>
    <TabsContent value="finances">...</TabsContent>
    <TabsContent value="historique">...</TabsContent>
  </Tabs>
</PageLayout>
```

**Page formulaire** (creation/edition) :
```tsx
<PageLayout title="Nouveau dossier" breadcrumb={[...]}>
  <form onSubmit={handleSubmit}>
    <Card>
      <CardHeader>
        <CardTitle>Informations client</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Champs en grille 2 colonnes */}
        <div className="grid grid-cols-2 gap-4">
          <FormField label="Nom *" error={errors.lastName}>
            <Input {...register("lastName")} placeholder="Dupont" />
          </FormField>
          <FormField label="Prenom *" error={errors.firstName}>
            <Input {...register("firstName")} placeholder="Jean" />
          </FormField>
        </div>
        {/* ... autres champs */}
      </CardContent>
    </Card>

    {/* Barre d'action sticky en bas */}
    <div className="sticky bottom-0 bg-white border-t p-4 flex justify-end gap-2">
      <Button variant="outline" onClick={cancel}>Annuler</Button>
      <Button type="submit" disabled={!isValid || isSubmitting}>
        {isSubmitting ? "Enregistrement..." : "Creer le dossier"}
      </Button>
    </div>
  </form>
</PageLayout>
```

### Badges de statut metier (couleurs obligatoires)

```typescript
const STATUS_COLORS = {
  // Dossiers
  brouillon: "gray",      // Gris neutre
  en_cours: "blue",        // Bleu info
  complet: "emerald",      // Vert succes
  archive: "gray",         // Gris

  // Devis
  draft: "gray",
  envoye: "blue",
  signe: "emerald",
  refuse: "red",
  expire: "amber",

  // Factures
  a_facturer: "amber",
  facturee: "blue",
  payee: "emerald",
  partiellement_payee: "amber",
  impayee: "red",
  annulee: "gray",

  // PEC
  soumise: "blue",
  en_attente: "amber",
  acceptee: "emerald",
  refusee: "red",
  partielle: "amber",

  // Paiements
  en_attente: "amber",
  recu: "emerald",
  retard: "red",
  rejete: "red",

  // Relances
  planifiee: "gray",
  envoyee: "blue",
  repondue: "emerald",
  echouee: "red",
};
```

### Messages utilisateur (francais, humains, bienveillants)

```typescript
// TOASTS DE SUCCES
"Dossier cree avec succes"
"Document televerse"
"Paiement enregistre"
"Devis envoye au client"
"Relance envoyee"

// TOASTS D'ERREUR
"Impossible de charger les dossiers. Verifiez votre connexion et reessayez."
"Ce client existe deja avec cette adresse email."
"Le montant du paiement depasse le solde restant du."
"Session expiree. Veuillez vous reconnecter."

// ETATS VIDES
"Aucun dossier pour le moment. Creez votre premier dossier client pour commencer."
"Aucun document dans ce dossier. Glissez-deposez vos fichiers ici."
"Pas de paiement en retard. Tout est a jour !"
"Aucune campagne envoyee. Lancez votre premiere campagne marketing."

// CONFIRMATIONS DESTRUCTIVES
"Etes-vous sur de vouloir supprimer ce dossier ? Cette action est irreversible."
"Confirmer l'envoi de la relance a 47 clients ?"
"Anonymiser les donnees de ce client ? Les donnees financieres agregees seront conservees."
```

### Anti-patterns frontend INTERDITS

- **Pas de page blanche** : TOUJOURS un etat loading, erreur ou vide. Jamais un ecran blanc.
- **Pas de message en anglais** : tout en francais. Pas de "Loading...", "Error", "Submit", "Cancel".
- **Pas de tableau sans pagination** : max 25 lignes par page par defaut.
- **Pas de formulaire sans validation** : chaque champ obligatoire marque *, validation temps reel.
- **Pas de bouton sans feedback** : clic = spinner ou desactivation immediate pour eviter le double-clic.
- **Pas de suppression sans confirmation** : modale de confirmation pour TOUTE suppression.
- **Pas de lien mort** : chaque lien de la sidebar doit pointer vers une page fonctionnelle (au minimum une page "a venir").
- **Pas de nombre sans formatage** : montants, pourcentages, dates — TOUJOURS formates.
- **Pas de couleur purement decorative** : chaque couleur a un sens metier (vert=OK, rouge=probleme, ambre=attention).
- **Pas d'icone sans label** : chaque icone seule DOIT avoir un `aria-label` et un tooltip au hover.
- **Pas de console.log en production** : retirer tous les logs de debug avant de valider une etape.
- **Pas de `any` en TypeScript** : typer strictement TOUTES les props, states, et responses API.

### Performance frontend

- **Composants lourds** : utiliser `React.lazy()` + `Suspense` pour les pages avec graphiques (dashboard, analytics)
- **Listes longues** : pagination serveur (pas de chargement de 10000 lignes en memoire)
- **Images** : utiliser `next/image` avec lazy loading pour les avatars et illustrations
- **Recherche** : debounce de 300ms sur les barres de recherche (eviter les requetes a chaque frappe)
- **Cache** : utiliser les headers `Cache-Control` pour les donnees rarement modifiees (document_types, payment_types)

### Specs de reference frontend

- Cadrage frontend : `docs/specs/05_Cadrage_Frontend_Premium_OptiFlow_AI.md`
- Plan ecrans : *(supprime lors du nettoyage — voir docs/specs/ pour les specs restantes)*

---

## Base de donnees cible (~20 tables)

**Tables existantes** : users, customers, cases, documents, payments (5)
**Tables a creer progressivement** :
- ETAPE 3 : audit_logs
- ETAPE 10 : notifications, action_items
- ETAPE 11 : devis, devis_lignes
- ETAPE 12 : factures, facture_lignes
- ETAPE 13 : payer_organizations, payer_contracts, pec_requests, pec_status_history, relances (PEC)
- ETAPE 14 : bank_transactions (+ enrichir payments)
- ETAPE 15 : reminder_plans, reminders, reminder_templates
- ETAPE 16 : marketing_consents, segments, segment_memberships, campaigns, message_logs

Schema complet dans : *(supprime — le schema est defini dans les modeles SQLAlchemy : backend/app/models/)*

## Etat actuel du code

### Backend (backend/app/)
- main.py : setup FastAPI, CORS, seed - FAIT
- api.py : 8 endpoints basiques - FAIT mais a refactorer en routers separes
- models.py : 5 modeles SQLAlchemy - FAIT mais incomplet (manque 5 tables)
- security.py : JWT + bcrypt - FAIT mais manque refresh token
- seed.py : donnees demo - FAIT
- core/config.py : settings Pydantic - FAIT
- db/base.py + session.py : connexion BDD - FAIT

### Frontend (frontend/src/)
- page.tsx : page accueil avec liens - FAIT
- dashboard/page.tsx : 6 KPIs - FAIT
- cases/page.tsx : liste dossiers - FAIT
- cases/[id]/page.tsx : detail dossier - FAIT
- lib/api.ts : fetch wrapper - FAIT
- globals.css : styles basiques - FAIT

### Ce qui MANQUE (critique)
- Aucun test
- Aucun logging
- Pas de validation d'entree (Pydantic schemas)
- Pas de service layer (logique dans les routers)
- Pas de refresh token / RBAC enforce
- Pas d'integration MinIO reelle
- Pas d'integration Cosium
- Pas de migrations Alembic
- Pas de formulaires frontend (login, creation dossier, upload)
- Pas de gestion d'erreurs / loading states frontend

## Documentation de reference

### Specs disponibles (docs/specs/)
- Vision produit : `docs/specs/01_Vision_Produit_OptiFlow_AI.md`
- Cadrage fonctionnel : `docs/specs/02_Cadrage_Metier_Fonctionnel_OptiFlow_AI.md`
- Architecture : `docs/specs/03_Architecture_Logicielle_Technique_OptiFlow_AI.md`
- Cadrage frontend : `docs/specs/05_Cadrage_Frontend_Premium_OptiFlow_AI.md`
- Paiements & rapprochement : `docs/specs/06_Spec_Paiements_Rapprochement_OptiFlow_AI.md`
- Mutuelles & PEC : `docs/specs/07_Spec_Mutuelles_SecuriteSociale_TiersPayant_OptiFlow_AI.md`
- Marketing & CRM : `docs/specs/08_Spec_Marketing_CRM_OptiFlow_AI.md`
- GED & documents : `docs/specs/09_Spec_GED_Cosium_Documents_OptiFlow_AI.md`
- Modele de donnees : `docs/specs/10_Modele_Donnees_Detaille_OptiFlow_AI.md`

*Note : Les specs 13-23, docs/cosium/, et docs/directives/ ont ete supprimes lors du nettoyage. Le code source fait reference.*

## Architecture Multi-tenant — Design pour groupe d'opticiens (ETAPE 22)

> **CRITIQUE** : OptiFlow supporte le modele SaaS multi-tenant : 50+ magasins (tenants) appartenant a 1 groupe (organization).
> Chaque tenant = isolation complete des donnees + credentials Cosium propres + acces utilisateurs granulaires.
> **Strategie** : Shared Database + Row-Level Security (RLS) PostgreSQL + tenant_id partout.

### Principes fondamentaux

1. **Isolation des donnees** : Chaque tenant a son `tenant_id` dans PostgreSQL. RLS policies filtrent automatiquement toutes les queries. **REGLE** : JAMAIS de query sans tenant_id dans le WHERE.
2. **Un seul JWT, multi-tenant** : JWT inclut `tenant_id` + `is_group_admin`. Un user peut appartenir a plusieurs tenants (via `tenant_users`). Switch tenant = nouvel appel `/auth/switch-tenant`.
3. **Cosium par tenant** : Chaque tenant a ses credentials Cosium chiffres (Fernet). Sync = 1 task Celery par tenant, isolee.
4. **Group admin = vue transversale** : Admin groupe voit tous les tenants et stats agregees via `/admin/group-dashboard`.

### Tables d'organisation (non filtrees par RLS)

- `organizations` : le groupe (ex: "OptiDistribution")
- `tenants` : chaque magasin (ex: "Paris Champs-Elysees")
- `tenant_users` : mapping user-tenant avec role (admin/manager/operator/viewer)
- `tenant_cosium_credentials` : credentials Cosium chiffres par tenant

### Flux obligatoire par requete API

1. JWT extrait du header Authorization
2. `TenantContext` cree (tenant_id, user_id, role, is_group_admin)
3. Middleware appelle `SET app.tenant_id = '{tenant_id}'` sur la session PostgreSQL
4. Router passe tenant_ctx aux services → services passent tenant_id aux repos
5. Repos ajoutent `WHERE tenant_id = ?` a TOUTES les queries

### Anti-pattern tenant INTERDIT

```python
# INTERDIT : query sans tenant_id = breach de securite
def get_case(db, case_id):
    return db.query(Case).filter(Case.id == case_id).first()

# OBLIGATOIRE : tenant_id explicite
def get_case(db, case_id, tenant_id):
    return db.query(Case).filter(Case.id == case_id, Case.tenant_id == tenant_id).first()
```

---

## Commandes utiles

```bash
# Demarrer l'environnement complet
docker compose up --build

# API : http://localhost:8000/docs (Swagger)
# Front : http://localhost:3000
# MinIO console : http://localhost:9001 (minioadmin/minioadmin)
# Mailhog : http://localhost:8025

# Login demo
# email: admin@optiflow.local / password: admin123

# Tests (a configurer)
docker compose exec api pytest -v

# Migrations Alembic (a configurer)
docker compose exec api alembic upgrade head
```

---

## Dernieres interventions vps-master

> Cette section est maintenue par la session `vps-master` quand elle intervient sur ce projet.
> La session `api-cosium-claude` doit la lire au demarrage pour savoir ce qui a change.

### 2026-04-25 — Audit VPS + fix OOM + CI

- **Fix OOM api container** : `mem_limit` passe de 768m a 1536m dans `docker-compose.yml`. Le worker Celery `bulk_download_cosium_documents` causait des OOM kills en boucle (652 kills en une nuit). Concurrency deja reduite a 2 (session precedente).
- **Fix CI backend** : 81 tests fails corriges (26 fichiers). Causes : `Tenant.erp_type` sans default, bugs `_parse_date`, RBAC fallback, consent opt-out, CSV import variants, name matching, facture parser regex. Commit `c8c6270`.
- **Fix E2E workflow** : `next.config.ts` ajoute `outputFileTracingRoot` pour monorepo. `e2e.yml` lance le standalone server correctement. `login/page.tsx` retire le `disabled` du bouton (react-hook-form + Playwright incompatibles). Les tests E2E n'ont **jamais passe** — background complet dans `TODO.md` section "E2E Playwright".
- **Sidebar admin** : 6 sous-pages admin exposees en liens directs au lieu d'un seul "Admin". Commit `4d2694a`.
- **Hook auto-deploy** : chaque `git push` sur ce projet fait automatiquement `docker compose up -d --build` via `/home/claude-agent/.claude/hooks/auto-deploy.sh`.
