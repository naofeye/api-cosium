# PLAN V12 — Intelligence Documentaire, Liaison Client Totale & Assistance PEC

> **Directive pour Claude CLI / Codex**
> Ce fichier est le plan d'implémentation complet de la V12 d'OptiFlow AI.
> Chaque étape contient le contexte, les fichiers à modifier, les specs, et les critères de validation.
> Respecter CLAUDE.md à la lettre (architecture en couches, tests, logging, validation Pydantic, etc.)

---

## CONTEXTE & DIAGNOSTIC

### Problème n°1 : Liaison factures→clients à 53%

**Cause racine** : L'adapter Cosium (`integrations/cosium/adapter.py` ligne 90) extrait `customerId` depuis le body JSON des factures, mais Cosium ne fournit pas systématiquement ce champ dans l'endpoint `/invoices`. En revanche, **les factures contiennent un lien HAL `_links.customer.href`** (format `/customers/{id}`) qui est IGNORÉ par le code actuel.

**Preuve** : Le code des prescriptions (`adapter.py` lignes 217-224) extrait déjà correctement `_links.customer.href` avec le pattern `rsplit("/customers/", 1)[-1]`. Il suffit d'appliquer le même pattern aux factures.

**Impact** : 47% des factures n'ont pas de `customer_id` → la vue 360 client est incomplète, les KPIs financiers par client sont faux, et la PEC ne peut pas s'appuyer sur l'historique facturation.

### Problème n°2 : Zéro extraction documentaire

Les documents Cosium sont téléchargés dans MinIO (`cosium_document_sync.py`) mais **aucune extraction de contenu n'est faite**. Ce sont des blobs binaires inexploitables. Pas d'OCR, pas de parsing PDF, pas d'extraction de texte structuré.

**Impact** : Impossible d'extraire automatiquement les données d'une ordonnance scannée, d'un devis PDF, d'une attestation mutuelle, etc.

### Problème n°3 : PEC manuelle et déconnectée

Le module PEC actuel (`services/pec_service.py`) est un workflow de suivi de statut (soumise→en_attente→acceptée/refusée). Il ne contient **aucune intelligence** :
- Pas de pré-remplissage depuis le devis (part_secu, part_mutuelle, montants)
- Pas de lien vers les prescriptions optiques
- Pas de lien vers les documents justificatifs
- Pas de détection d'incohérences
- Pas de fiche d'assistance structurée
- Pas de liaison directe client→mutuelle

### Problème n°4 : Pas de lien client→mutuelle

Il n'existe **aucune table** `client_mutuelle` ou équivalent. La mutuelle d'un client n'est connue qu'indirectement via :
- `part_mutuelle` dans les devis (montant, pas l'organisme)
- `share_private_insurance` dans les factures Cosium (montant, pas l'organisme)
- `CosiumThirdPartyPayment` (montant mutuelle, pas l'organisme)
- Potentiellement dans les documents scannés (attestation mutuelle)

---

## VISION PRODUIT

Transformer le module PEC en un **assistant intelligent de préparation de prise en charge** qui :

1. **Lie 100% des données à un client** (factures, documents, prescriptions, paiements)
2. **Extrait le contenu des documents** (OCR + parsing structuré)
3. **Consolide automatiquement** les informations depuis toutes les sources
4. **Détecte les incohérences** entre sources (devis vs ordonnance vs documents)
5. **Produit une fiche PEC prête à l'emploi** pour la saisie sur le portail OCAM
6. **Signale les données manquantes** avec niveau de confiance par champ
7. **Garde la main à l'humain** : rien n'est validé automatiquement

---

## ARCHITECTURE DES ÉTAPES

```
ÉTAPE 1 : Liaison client totale (factures, paiements, documents)
ÉTAPE 2 : Détection et liaison mutuelle par client
ÉTAPE 3 : Infrastructure OCR et extraction documentaire
ÉTAPE 4 : Parsers spécialisés (ordonnance, devis, attestation mutuelle)
ÉTAPE 5 : Moteur de consolidation multi-sources
ÉTAPE 6 : Détection d'incohérences et alertes
ÉTAPE 7 : Modèle de données PEC enrichi
ÉTAPE 8 : Service d'assistance PEC (agrégation + fiche)
ÉTAPE 9 : Frontend — Onglet PEC dans la fiche client
ÉTAPE 10 : Frontend — Fiche d'assistance PEC interactive
ÉTAPE 11 : Tests E2E et validation métier
ÉTAPE 12 : Évolutions multi-OCAM et intelligence avancée
```

---

## ÉTAPE 1 : Liaison client totale [ ]

**Objectif** : Passer de 53% à ~95%+ de factures liées à un client. Appliquer le même traitement aux paiements et documents orphelins.

### Contexte fichiers à lire
- `backend/app/integrations/cosium/adapter.py` (le problème : lignes 71-94)
- `backend/app/integrations/cosium/cosium_connector.py` (méthode `_map_invoices`)
- `backend/app/services/erp_sync_invoices.py` (le matching actuel)
- `backend/app/services/erp_sync_service.py` (fonctions `_normalize_name`, `_match_customer_by_name`)
- `backend/app/integrations/erp_models.py` (modèle `ERPInvoice`)

### Sous-tâches

- [ ] **1.1** Modifier `cosium_invoice_to_optiflow()` dans `adapter.py` pour extraire `_links.customer.href` en plus de `customerId`. Pattern identique aux prescriptions (lignes 217-224 du même fichier) :
  ```python
  # Ajouter dans cosium_invoice_to_optiflow() :
  customer_cosium_id = str(data.get("customerId", ""))
  if not customer_cosium_id:
      cust_href = data.get("_links", {}).get("customer", {}).get("href", "")
      if "/customers/" in cust_href:
          try:
              customer_cosium_id = str(int(cust_href.rsplit("/customers/", 1)[-1].split("?")[0]))
          except (ValueError, IndexError):
              pass
  ```

- [ ] **1.2** Même correction pour `cosium_payment_to_optiflow()` : extraire le customer depuis `_links.customer.href` des paiements (actuellement seul `_links.accounting-document` est extrait pour l'invoice, pas le customer)

- [ ] **1.3** Ajouter un champ `customer_cosium_id` dans le modèle `CosiumPayment` s'il n'existe pas déjà, et une FK `customer_id` (nullable) pour le lien direct

- [ ] **1.4** Dans `erp_sync_invoices.py`, améliorer le matching par nom avec un **fuzzy matching Levenshtein** en dernier recours (seuil de distance ≤ 2 caractères, ratio ≥ 85%) pour les cas où le nom est légèrement différent. Utiliser `thefuzz` (anciennement `fuzzywuzzy`) ou `rapidfuzz` (plus rapide, pas de dépendance C) :
  ```bash
  pip install rapidfuzz
  ```
  Ajouter dans `requirements.txt`.

- [ ] **1.5** Créer un script de **re-liaison rétroactive** (`scripts/relink_orphan_invoices.py`) qui re-parcourt toutes les `cosium_invoices` avec `customer_id IS NULL` et tente de les relier avec la nouvelle logique (_links + fuzzy). Ce script doit être exécutable via un endpoint admin protégé ET en CLI.

- [ ] **1.6** Même re-liaison pour les `cosium_payments` orphelins

- [ ] **1.7** Ajouter un endpoint admin `GET /api/v1/admin/data-quality` qui retourne les stats de liaison :
  ```json
  {
    "invoices": {"total": 5000, "linked": 4750, "orphan": 250, "link_rate": 95.0},
    "payments": {"total": 8000, "linked": 7800, "orphan": 200, "link_rate": 97.5},
    "documents": {"total": 1200, "linked": 1150, "orphan": 50, "link_rate": 95.8}
  }
  ```

- [ ] **1.8** Tests : au moins 10 tests couvrant les cas de matching (HAL link présent, absent, fuzzy match, homonymes, noms composés, accents, titres civils)

### Validation
- Le taux de liaison des factures doit être ≥ 90% (mesuré via l'endpoint data-quality)
- Aucune régression sur les factures déjà liées
- Les tests passent à 100%

---

## ÉTAPE 2 : Détection et liaison mutuelle par client [ ]

**Objectif** : Pour chaque client, identifier SA mutuelle et stocker cette relation.

### Contexte fichiers à lire
- `backend/app/models/cosium_reference.py` (CosiumMutuelle)
- `backend/app/models/cosium_data.py` (CosiumInvoice, CosiumThirdPartyPayment)
- `backend/app/models/client.py` (Customer)
- `backend/app/integrations/cosium/cosium_connector.py` (voir s'il y a un endpoint customer→mutuelle)

### Sous-tâches

- [ ] **2.1** Créer la table `client_mutuelles` (relation N-N car un client peut avoir plusieurs mutuelles, et changer de mutuelle dans le temps) :
  ```python
  class ClientMutuelle(Base):
      __tablename__ = "client_mutuelles"
      id: int  # PK
      tenant_id: int  # FK tenants
      customer_id: int  # FK customers
      mutuelle_id: int | None  # FK cosium_mutuelles (nullable si pas trouvée en ref)
      mutuelle_name: str  # Nom de la mutuelle (dénormalisé, toujours renseigné)
      numero_adherent: str | None  # Numéro d'adhérent
      type_beneficiaire: str  # "assure" | "conjoint" | "enfant"
      date_debut: date | None  # Début de couverture
      date_fin: date | None  # Fin de couverture
      source: str  # "cosium_tpp" | "document_ocr" | "manual" | "cosium_invoice"
      confidence: float  # 0.0 à 1.0
      active: bool  # True = mutuelle en cours
      created_at: datetime
      updated_at: datetime
  ```

- [ ] **2.2** Migration Alembic pour cette table

- [ ] **2.3** Créer `repositories/client_mutuelle_repo.py` (CRUD)

- [ ] **2.4** Créer `services/client_mutuelle_service.py` avec une logique de **détection automatique** :
  1. Parcourir les `CosiumThirdPartyPayment` du client → si `additional_health_care_amount > 0`, il y a une mutuelle
  2. Parcourir les `CosiumInvoice` du client → si `share_private_insurance > 0`, confirmer
  3. Croiser avec la table `CosiumMutuelle` par nom (si le nom apparaît dans un champ quelconque)
  4. Si le client a des documents de type "attestation mutuelle", l'OCR (étape 3) pourra extraire le nom et le numéro d'adhérent

- [ ] **2.5** Endpoint `GET /api/v1/clients/{id}/mutuelles` et `POST /api/v1/clients/{id}/mutuelles` (ajout/correction manuelle)

- [ ] **2.6** Ajouter dans la vue 360 (`client_360_service.py`) la section `mutuelles` avec les données détectées

- [ ] **2.7** Schema Pydantic `ClientMutuelleResponse`, `ClientMutuelleCreate`

- [ ] **2.8** Tests : 8+ tests (détection depuis TPP, depuis invoice, manuelle, multi-mutuelles)

### Validation
- Chaque client avec un historique de paiement mutuelle doit avoir au moins une entrée dans `client_mutuelles`
- L'endpoint `/clients/{id}/mutuelles` retourne les données correctes
- La confiance est correctement calculée (1.0 si confirmée par TPP, 0.7 si déduite des montants, 0.5 si manuelle)

---

## ÉTAPE 3 : Infrastructure OCR et extraction documentaire [ ]

**Objectif** : Mettre en place un pipeline d'extraction de texte depuis les documents PDF/images stockés dans MinIO.

### Choix techniques

**Option retenue : Tesseract OCR + pdfplumber (pas de dépendance cloud)**
- `pdfplumber` : extraction de texte depuis les PDF natifs (texte sélectionnable)
- `pytesseract` + `Pillow` : OCR pour les PDF scannés et images
- `pdf2image` (poppler) : conversion PDF → images pour OCR
- Pas de dépendance à un service cloud (pas de Google Vision, pas d'AWS Textract)

**Alternative future** : Intégrer un LLM (Claude) pour l'extraction structurée — mais en V12, on reste sur du local pour la fiabilité et le coût.

### Sous-tâches

- [ ] **3.1** Ajouter les dépendances dans `requirements.txt` :
  ```
  pdfplumber>=0.10.0
  pytesseract>=0.3.10
  Pillow>=10.0.0
  pdf2image>=1.16.3
  ```

- [ ] **3.2** Installer Tesseract et poppler dans le Dockerfile :
  ```dockerfile
  RUN apt-get update && apt-get install -y \
      tesseract-ocr \
      tesseract-ocr-fra \
      poppler-utils \
      && rm -rf /var/lib/apt/lists/*
  ```

- [ ] **3.3** Créer le service `services/ocr_service.py` :
  ```python
  class OCRService:
      def extract_text_from_pdf(self, file_bytes: bytes) -> ExtractedDocument:
          """Extrait le texte d'un PDF (natif ou scanné)."""
          # 1. Essayer pdfplumber (PDF natif avec texte)
          # 2. Si pas de texte → pdf2image + pytesseract (OCR)
          # 3. Retourner ExtractedDocument avec texte brut + métadonnées

      def extract_text_from_image(self, file_bytes: bytes) -> ExtractedDocument:
          """OCR sur une image (jpg, png, tiff)."""

      def classify_document(self, text: str) -> DocumentClassification:
          """Classifie le document par type métier."""
          # Patterns regex pour détecter :
          # - ordonnance (mots-clés : "ordonnance", "prescription", "OD", "OG", "sphère")
          # - devis (mots-clés : "devis", "monture", "verre", "montant TTC")
          # - attestation mutuelle (mots-clés : "attestation", "mutuelle", "adhérent", "bénéficiaire")
          # - facture (mots-clés : "facture", "total TTC", "TVA")
          # - carte mutuelle (mots-clés : "carte", "tiers payant", "AMC")
          # - autre
  ```

- [ ] **3.4** Créer les schemas dans `domain/schemas/ocr.py` :
  ```python
  class ExtractedDocument(BaseModel):
      raw_text: str
      page_count: int
      extraction_method: str  # "pdfplumber" | "tesseract_ocr"
      confidence: float  # 0.0-1.0 (OCR quality)
      language: str  # "fra"
      extracted_at: datetime

  class DocumentClassification(BaseModel):
      document_type: str  # ordonnance | devis | attestation_mutuelle | facture | carte_mutuelle | autre
      confidence: float
      keywords_found: list[str]
  ```

- [ ] **3.5** Créer la table `document_extractions` pour stocker les résultats d'extraction :
  ```python
  class DocumentExtraction(Base):
      __tablename__ = "document_extractions"
      id: int
      tenant_id: int
      document_id: int | None  # FK documents (OptiFlow)
      cosium_document_id: int | None  # FK cosium_documents
      raw_text: Text  # Texte brut extrait
      document_type: str  # Classification
      classification_confidence: float
      extraction_method: str
      ocr_confidence: float | None
      structured_data: JSON | None  # Données structurées extraites (étape 4)
      extracted_at: datetime
      created_at: datetime
  ```

- [ ] **3.6** Migration Alembic

- [ ] **3.7** Créer `repositories/document_extraction_repo.py`

- [ ] **3.8** Créer un endpoint `POST /api/v1/documents/{id}/extract` qui lance l'extraction sur un document et retourne le résultat

- [ ] **3.9** Créer une tâche Celery `tasks/extraction_tasks.py` pour l'extraction en batch de tous les documents d'un client

- [ ] **3.10** Tests : 10+ tests (PDF natif, PDF scanné, image, classification ordonnance, classification devis, document vide, confiance basse)

### Validation
- L'extraction fonctionne sur des PDF natifs (pdfplumber) ET scannés (OCR)
- La classification détecte correctement les ordonnances, devis, attestations
- Les résultats sont stockés dans `document_extractions`
- Docker build passe (Tesseract installé)

---

## ÉTAPE 4 : Parsers spécialisés [ ]

**Objectif** : Extraire des données STRUCTURÉES depuis le texte brut des documents classifiés.

### Sous-tâches

- [ ] **4.1** Créer `services/parsers/ordonnance_parser.py` :
  ```python
  class OrdonnanceData(BaseModel):
      prescriber_name: str | None
      prescription_date: date | None
      sphere_od: float | None  # OD = Oeil Droit
      cylinder_od: float | None
      axis_od: int | None
      addition_od: float | None
      sphere_og: float | None  # OG = Oeil Gauche
      cylinder_og: float | None
      axis_og: int | None
      addition_og: float | None
      pupillary_distance: float | None  # Écart pupillaire
      notes: str | None
      confidence_per_field: dict[str, float]  # Confiance par champ

  def parse_ordonnance(text: str) -> OrdonnanceData:
      """Parse le texte d'une ordonnance optique."""
      # Regex pour : OD +2.50 (-0.75 à 90°) Add +2.00
      # Regex pour : OG +3.00 (-1.00 à 180°) Add +2.25
      # Regex pour : Dr Dupont, Date: 15/03/2026
      # Etc.
  ```

- [ ] **4.2** Créer `services/parsers/devis_parser.py` :
  ```python
  class DevisData(BaseModel):
      numero_devis: str | None
      date_devis: date | None
      lignes: list[DevisLigneData]
      montant_ht: float | None
      montant_ttc: float | None
      part_secu: float | None
      part_mutuelle: float | None
      reste_a_charge: float | None
      monture: MontureLigneData | None  # Ligne monture identifiée
      verres: list[VerreLigneData]  # Lignes verres identifiées
      confidence_per_field: dict[str, float]

  class DevisLigneData(BaseModel):
      designation: str
      code_lpp: str | None  # Code Liste des Produits et Prestations
      quantite: int
      prix_unitaire: float | None
      montant: float | None
  ```

- [ ] **4.3** Créer `services/parsers/attestation_mutuelle_parser.py` :
  ```python
  class AttestationMutuelleData(BaseModel):
      nom_mutuelle: str | None
      code_organisme: str | None  # Code AMC
      numero_adherent: str | None
      nom_assure: str | None
      prenom_assure: str | None
      date_naissance_assure: date | None
      beneficiaires: list[BeneficiaireData]
      date_debut_droits: date | None
      date_fin_droits: date | None
      regime: str | None  # "Obligatoire" | "Complémentaire"
      confidence_per_field: dict[str, float]

  class BeneficiaireData(BaseModel):
      nom: str
      prenom: str
      date_naissance: date | None
      lien: str | None  # "assuré" | "conjoint" | "enfant"
      numero_securite_sociale: str | None
  ```

- [ ] **4.4** Créer `services/parsers/facture_parser.py` (extraction depuis factures PDF) :
  ```python
  class FactureData(BaseModel):
      numero_facture: str | None
      date_facture: date | None
      montant_ht: float | None
      tva: float | None
      montant_ttc: float | None
      lignes: list[FactureLigneData]
      confidence_per_field: dict[str, float]
  ```

- [ ] **4.5** Créer un `services/parsers/__init__.py` avec un dispatcher :
  ```python
  def parse_document(text: str, document_type: str) -> BaseModel:
      parsers = {
          "ordonnance": parse_ordonnance,
          "devis": parse_devis,
          "attestation_mutuelle": parse_attestation_mutuelle,
          "facture": parse_facture,
      }
      parser = parsers.get(document_type)
      if parser:
          return parser(text)
      return None
  ```

- [ ] **4.6** Enrichir `document_extractions.structured_data` avec le résultat du parser (JSON sérialisé)

- [ ] **4.7** Tests : 15+ tests avec des exemples réels de texte d'ordonnance, de devis, d'attestation (créer des fixtures de test)

### Validation
- Le parser d'ordonnance extrait correctement les valeurs OD/OG depuis du texte type
- Le parser de devis extrait les montants et les lignes
- Le parser d'attestation extrait le nom mutuelle et le numéro adhérent
- Chaque champ a un score de confiance

---

## ÉTAPE 5 : Moteur de consolidation multi-sources [ ]

**Objectif** : Créer le cœur du système — un moteur qui agrège les données de TOUTES les sources pour un client donné et produit un profil consolidé avec provenance.

### Sous-tâches

- [ ] **5.1** Créer `services/consolidation_service.py` :

  **Modèle de sortie** :
  ```python
  class ConsolidatedField(BaseModel):
      """Un champ consolidé avec sa source et sa confiance."""
      value: Any
      source: str  # "devis_123" | "cosium_prescription_456" | "document_ocr_789" | "cosium_client" | "manual"
      source_label: str  # Label humain : "Devis n°D-2026-042" | "Ordonnance du 15/03/2026"
      confidence: float  # 0.0-1.0
      last_updated: datetime

  class ConsolidatedClientProfile(BaseModel):
      """Profil client consolidé depuis toutes les sources."""
      # Identité
      nom: ConsolidatedField
      prenom: ConsolidatedField
      date_naissance: ConsolidatedField | None
      numero_secu: ConsolidatedField | None

      # Mutuelle
      mutuelle_nom: ConsolidatedField | None
      mutuelle_numero_adherent: ConsolidatedField | None
      mutuelle_code_organisme: ConsolidatedField | None
      type_beneficiaire: ConsolidatedField | None
      date_fin_droits: ConsolidatedField | None

      # Correction optique (dernière)
      sphere_od: ConsolidatedField | None
      cylinder_od: ConsolidatedField | None
      axis_od: ConsolidatedField | None
      addition_od: ConsolidatedField | None
      sphere_og: ConsolidatedField | None
      cylinder_og: ConsolidatedField | None
      axis_og: ConsolidatedField | None
      addition_og: ConsolidatedField | None
      ecart_pupillaire: ConsolidatedField | None
      prescripteur: ConsolidatedField | None
      date_ordonnance: ConsolidatedField | None

      # Équipement (depuis le devis)
      monture: ConsolidatedField | None
      verres: list[ConsolidatedField]

      # Financier
      montant_ttc: ConsolidatedField | None
      part_secu: ConsolidatedField | None
      part_mutuelle: ConsolidatedField | None
      reste_a_charge: ConsolidatedField | None

      # Métadonnées
      alertes: list[ConsolidationAlert]
      champs_manquants: list[str]
      score_completude: float  # 0-100%
      sources_utilisees: list[str]

  class ConsolidationAlert(BaseModel):
      severity: str  # "error" | "warning" | "info"
      field: str  # Champ concerné
      message: str  # "Incohérence : sphère OD = +2.50 dans l'ordonnance mais +2.00 dans le devis"
      sources: list[str]  # Sources en conflit
  ```

- [ ] **5.2** Implémenter les **règles de priorité** entre sources :
  ```
  RÈGLES DE PRIORITÉ (de la plus haute à la plus basse) :

  Identité patient :
    1. Cosium (source pivot) → nom, prénom, date naissance, numéro sécu
    2. Document OCR (attestation mutuelle) → numéro sécu si absent de Cosium
    3. Saisie manuelle → fallback

  Données mutuelle :
    1. Document OCR (attestation mutuelle) → nom mutuelle, n° adhérent, code organisme
    2. Cosium third-party payments → confirmation mutuelle (montants)
    3. Cosium invoices → share_private_insurance (montants)
    4. Saisie manuelle → fallback

  Correction optique :
    1. Cosium prescriptions → sphère, cylindre, axe, addition (données structurées)
    2. Document OCR (ordonnance) → si pas de prescription Cosium
    3. Remarque : si les deux existent, COMPARER et alerter si écart

  Données tarifaires :
    1. Devis OptiFlow → montant TTC, part sécu, part mutuelle, reste à charge, lignes
    2. Document OCR (devis PDF) → si pas de devis dans OptiFlow
    3. Cosium invoices → montants facturés (source de vérité post-facturation)

  Équipement :
    1. Devis OptiFlow → monture, verres (lignes du devis)
    2. Cosium prescriptions → spectacles_json (données brutes des montures sélectionnées)
    3. Document OCR (devis) → extraction des lignes
  ```

- [ ] **5.3** Implémenter la **fonction de consolidation principale** :
  ```python
  def consolidate_client_for_pec(
      db: Session,
      tenant_id: int,
      customer_id: int,
      devis_id: int | None = None,  # Si un devis spécifique est ciblé
  ) -> ConsolidatedClientProfile:
      """Consolide toutes les sources de données pour un client."""
      # 1. Charger les données Cosium (client, prescriptions, invoices, tpp, documents)
      # 2. Charger les devis OptiFlow du client
      # 3. Charger les extractions documentaires (document_extractions)
      # 4. Charger les mutuelles détectées (client_mutuelles)
      # 5. Appliquer les règles de priorité
      # 6. Détecter les incohérences (étape 6)
      # 7. Calculer le score de complétude
      # 8. Retourner le profil consolidé
  ```

- [ ] **5.4** Tests : 12+ tests (consolidation complète, source manquante, conflit entre sources, calcul de confiance)

### Validation
- La consolidation produit un profil complet quand toutes les sources sont présentes
- Les alertes sont générées quand deux sources se contredisent
- Le score de complétude reflète les champs renseignés vs nécessaires
- Chaque champ a sa source traçable

---

## ÉTAPE 6 : Détection d'incohérences et alertes [ ]

**Objectif** : Identifier et signaler les contradictions et anomalies dans les données consolidées.

### Sous-tâches

- [ ] **6.1** Créer `services/incoherence_detector.py` avec les règles suivantes :

  **Incohérences optiques** :
  - Sphère OD/OG : écart > 0.25 dioptrie entre ordonnance et prescription Cosium → ALERTE
  - Cylindre OD/OG : écart > 0.25 → ALERTE
  - Addition OD vs OG : si écart > 0.50 → ALERTE (rare en pratique)
  - Date ordonnance > 1 an → WARNING "Ordonnance expirée"
  - Date ordonnance > 3 ans → ERROR "Ordonnance périmée — non utilisable pour PEC"

  **Incohérences financières** :
  - `part_secu + part_mutuelle > montant_ttc` → ERROR
  - `reste_a_charge < 0` → ERROR
  - Montant devis ≠ montant facture (écart > 1€) → WARNING
  - `part_mutuelle > 0` mais pas de mutuelle identifiée → WARNING

  **Incohérences identitaires** :
  - Nom sur attestation mutuelle ≠ nom Cosium → WARNING
  - Date de naissance sur attestation ≠ Cosium → ERROR
  - Numéro sécu sur attestation ≠ Cosium (si les deux existent) → ERROR
  - Droits mutuelle expirés (`date_fin_droits < aujourd'hui`) → ERROR

  **Données manquantes critiques pour PEC** :
  - Pas de numéro sécu → ERROR "N° sécurité sociale requis"
  - Pas de mutuelle identifiée → WARNING "Mutuelle non identifiée"
  - Pas de numéro adhérent → WARNING "N° adhérent mutuelle manquant"
  - Pas d'ordonnance → ERROR "Ordonnance requise pour PEC optique"
  - Pas de devis → ERROR "Devis requis pour PEC"
  - Ordonnance sans date → WARNING

- [ ] **6.2** Les alertes ont 3 niveaux : `error` (bloquant, la PEC ne peut pas être soumise), `warning` (à vérifier mais non bloquant), `info` (information contextuelle)

- [ ] **6.3** Tests : 15+ tests (chaque type d'incohérence)

### Validation
- Chaque type d'incohérence est détecté et correctement classifié (error/warning/info)
- Un profil sans erreur bloquante est marqué "prêt pour PEC"
- Un profil avec erreurs est marqué "incomplet — X problèmes à résoudre"

---

## ÉTAPE 7 : Modèle de données PEC enrichi [ ]

**Objectif** : Enrichir le modèle PEC existant pour supporter la fiche d'assistance.

### Sous-tâches

- [ ] **7.1** Créer la table `pec_preparations` (la fiche d'assistance PEC, distincte de `pec_requests` qui est le workflow) :
  ```python
  class PecPreparation(Base):
      __tablename__ = "pec_preparations"
      id: int
      tenant_id: int
      customer_id: int  # FK customers
      devis_id: int | None  # FK devis (devis ciblé)
      pec_request_id: int | None  # FK pec_requests (si une PEC est créée depuis cette préparation)

      # Snapshot des données consolidées (JSON complet)
      consolidated_data: JSON  # ConsolidatedClientProfile sérialisé

      # Statut de la préparation
      status: str  # "en_preparation" | "prete" | "soumise" | "archivee"
      completude_score: float  # 0-100%
      errors_count: int
      warnings_count: int

      # Validations manuelles de l'utilisateur
      user_validations: JSON  # {field: {"validated": true, "validated_by": user_id, "at": datetime}}
      user_corrections: JSON  # {field: {"original": ..., "corrected": ..., "by": user_id, "at": datetime}}

      # Documents justificatifs liés
      # (via table de liaison pec_preparation_documents)

      created_at: datetime
      updated_at: datetime
      created_by: int  # FK users
  ```

- [ ] **7.2** Table de liaison `pec_preparation_documents` :
  ```python
  class PecPreparationDocument(Base):
      __tablename__ = "pec_preparation_documents"
      id: int
      preparation_id: int  # FK pec_preparations
      document_id: int | None  # FK documents (OptiFlow)
      cosium_document_id: int | None  # FK cosium_documents
      document_role: str  # "ordonnance" | "devis" | "attestation_mutuelle" | "facture" | "autre"
      extraction_id: int | None  # FK document_extractions (si le doc a été parsé)
  ```

- [ ] **7.3** Migrations Alembic pour `pec_preparations` et `pec_preparation_documents`

- [ ] **7.4** Schemas Pydantic dans `domain/schemas/pec_preparation.py`

- [ ] **7.5** Repository `repositories/pec_preparation_repo.py`

- [ ] **7.6** Tests : 8+ tests

### Validation
- Le modèle peut stocker un profil consolidé complet
- Les corrections utilisateur sont traçables
- Les documents sont liés à la préparation

---

## ÉTAPE 8 : Service d'assistance PEC [ ]

**Objectif** : Le service central qui orchestre tout — consolidation, détection d'incohérences, génération de la fiche.

### Sous-tâches

- [ ] **8.1** Créer `services/pec_preparation_service.py` :
  ```python
  class PecPreparationService:
      def prepare_pec(
          self, db, tenant_id, customer_id, devis_id=None, user_id=0
      ) -> PecPreparationResponse:
          """Prépare une fiche PEC pour un client."""
          # 1. Lancer l'extraction OCR sur les documents non encore parsés
          # 2. Appeler le moteur de consolidation
          # 3. Détecter les incohérences
          # 4. Calculer le score de complétude
          # 5. Identifier les documents justificatifs
          # 6. Créer/mettre à jour la PecPreparation
          # 7. Retourner la fiche structurée

      def validate_field(
          self, db, preparation_id, field_name, validated_by
      ) -> PecPreparationResponse:
          """L'utilisateur valide un champ manuellement."""

      def correct_field(
          self, db, preparation_id, field_name, new_value, corrected_by
      ) -> PecPreparationResponse:
          """L'utilisateur corrige un champ manuellement."""

      def refresh_preparation(
          self, db, preparation_id
      ) -> PecPreparationResponse:
          """Relance la consolidation (après ajout de document, etc.)."""

      def create_pec_from_preparation(
          self, db, preparation_id, user_id
      ) -> PecRequestResponse:
          """Crée une PecRequest depuis la préparation validée."""
  ```

- [ ] **8.2** Endpoints API dans `api/routers/pec_preparation.py` :
  ```
  POST   /api/v1/clients/{id}/pec-preparation          → Préparer une fiche PEC
  GET    /api/v1/clients/{id}/pec-preparation/{prep_id} → Voir la fiche
  POST   /api/v1/pec-preparations/{id}/validate-field   → Valider un champ
  POST   /api/v1/pec-preparations/{id}/correct-field    → Corriger un champ
  POST   /api/v1/pec-preparations/{id}/refresh          → Rafraîchir
  POST   /api/v1/pec-preparations/{id}/submit           → Créer la PEC depuis la préparation
  GET    /api/v1/pec-preparations/{id}/documents         → Documents liés
  POST   /api/v1/pec-preparations/{id}/documents         → Attacher un document
  ```

- [ ] **8.3** Enregistrer le router dans `main.py`

- [ ] **8.4** Tests : 15+ tests (préparation complète, champs manquants, correction, validation, soumission)

### Validation
- `POST /clients/{id}/pec-preparation` retourne une fiche complète avec toutes les données, alertes, et score
- La correction d'un champ met à jour la fiche et recalcule les alertes
- La soumission crée une PecRequest pré-remplie

---

## ÉTAPE 9 : Frontend — Onglet PEC dans la fiche client [ ]

**Objectif** : Ajouter un onglet "Assistance PEC" dans la fiche client (page `/clients/[id]`).

### Contexte fichiers
- `frontend/src/app/clients/[id]/page.tsx` (tabs existants)
- `frontend/src/app/clients/[id]/tabs/` (composants par onglet)
- Respecter la charte frontend CLAUDE.md (shadcn/ui, Tailwind, français, 4 états)

### Sous-tâches

- [ ] **9.1** Créer `frontend/src/app/clients/[id]/tabs/TabPEC.tsx` :
  - Affiche la liste des préparations PEC du client
  - Bouton "Nouvelle assistance PEC" (avec sélecteur de devis optionnel)
  - État vide : "Aucune préparation PEC. Créez votre première assistance PEC pour ce client."
  - État loading : skeleton
  - État erreur : message + retry

- [ ] **9.2** Ajouter l'onglet dans `page.tsx` :
  ```tsx
  <TabsTrigger value="pec">Assistance PEC</TabsTrigger>
  <TabsContent value="pec"><TabPEC clientId={id} /></TabsContent>
  ```

- [ ] **9.3** Créer les types TypeScript dans `frontend/src/lib/types/pec-preparation.ts`

- [ ] **9.4** Créer les appels API dans `frontend/src/lib/api.ts` ou un hook SWR dédié

- [ ] **9.5** Tests frontend : 5+ tests (rendu, état vide, chargement, erreur)

### Validation
- L'onglet PEC apparaît dans la fiche client
- Le bouton "Nouvelle assistance PEC" appelle l'API
- Les 4 états (loading, erreur, vide, données) sont gérés

---

## ÉTAPE 10 : Frontend — Fiche d'assistance PEC interactive [ ]

**Objectif** : L'écran principal — la fiche PEC complète, interactive, avec toutes les sections.

### Structure de l'interface

```
┌─────────────────────────────────────────────────────────────────┐
│  Assistance PEC — Client DUPONT Jean         [Rafraîchir] [PDF] │
│  Score complétude : ██████████░░ 78%    ⚠ 2 alertes  ❌ 1 erreur│
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────── SECTION 1 : IDENTITÉ PATIENT ───────────────┐    │
│  │ Nom : DUPONT          Source: Cosium ✓     [Valider]    │    │
│  │ Prénom : Jean          Source: Cosium ✓     [Valider]    │    │
│  │ N° Sécu : 1 85 03 ... Source: Cosium ✓     [Valider]    │    │
│  │ Date naiss. : 15/03/85 Source: Cosium ✓     [Valider]    │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────── SECTION 2 : MUTUELLE / OCAM ────────────────┐    │
│  │ Mutuelle : HARMONIE    Source: Attestation  [Valider]    │    │
│  │ N° Adhérent : 123456   Source: Attestation  [Valider]    │    │
│  │ Code AMC : 01234       Source: Attestation  [Valider]    │    │
│  │ ⚠ Droits expirés le 31/12/2025 — vérifier renouvellement │   │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────── SECTION 3 : CORRECTION OPTIQUE ─────────────┐    │
│  │        OD                    OG                          │    │
│  │ Sph : +2.50 (ordo ✓)  Sph : +3.00 (ordo ✓)            │    │
│  │ Cyl : -0.75 (ordo ✓)  Cyl : -1.00 (ordo ✓)            │    │
│  │ Axe : 90° (ordo ✓)    Axe : 180° (ordo ✓)             │    │
│  │ Add : +2.00 (ordo ✓)  Add : +2.25 (ordo ✓)            │    │
│  │ Prescripteur : Dr Martin     Date : 15/03/2026          │    │
│  │ ❌ ALERTE : Sphère OD = +2.50 ordo vs +2.00 Cosium     │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────── SECTION 4 : ÉQUIPEMENT (DEVIS) ────────────┐    │
│  │ Devis n° D-2026-042 du 20/03/2026                       │    │
│  │ ┌──────────────────────────────────────────────────┐     │    │
│  │ │ Monture Ray-Ban RB5154       1 × 150,00 €       │     │    │
│  │ │ Verre progressif OD          1 × 280,00 €       │     │    │
│  │ │ Verre progressif OG          1 × 280,00 €       │     │    │
│  │ └──────────────────────────────────────────────────┘     │    │
│  │ Total TTC : 852,00 €                                     │    │
│  │ Part Sécu : 12,00 €                                      │    │
│  │ Part Mutuelle : 450,00 €                                 │    │
│  │ Reste à charge : 390,00 €                                │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────── SECTION 5 : PIÈCES JUSTIFICATIVES ─────────┐    │
│  │ ✅ Ordonnance         — ordo_dupont_150326.pdf          │    │
│  │ ✅ Devis signé         — devis_D-2026-042.pdf           │    │
│  │ ✅ Attestation mutuelle — attestation_harmonie.pdf       │    │
│  │ ❌ Carte vitale        — MANQUANTE                      │    │
│  │                                     [+ Ajouter document] │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────── SECTION 6 : ALERTES & INCOHÉRENCES ────────┐    │
│  │ ❌ Sphère OD incohérente entre ordo (+2.50) et          │    │
│  │    Cosium (+2.00) — vérifier avec le client              │    │
│  │ ⚠ Droits mutuelle expirés — confirmer renouvellement    │    │
│  │ ℹ Ordonnance datée de moins de 6 mois — OK              │    │
│  └──────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │  [Soumettre la PEC]  [Exporter PDF]  [Annuler]          │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

### Sous-tâches

- [ ] **10.1** Créer `frontend/src/app/clients/[id]/pec-preparation/[prepId]/page.tsx` — la page complète

- [ ] **10.2** Composants réutilisables à créer :
  - `components/pec/PecSection.tsx` — Section avec titre, icône, statut
  - `components/pec/ConsolidatedField.tsx` — Champ avec source, confiance, boutons valider/corriger
  - `components/pec/AlertPanel.tsx` — Liste des alertes triées par sévérité
  - `components/pec/DocumentChecklist.tsx` — Pièces justificatives avec statut
  - `components/pec/CorrectionTable.tsx` — Tableau OD/OG avec code couleur
  - `components/pec/CompletionGauge.tsx` — Jauge de complétude (score %)

- [ ] **10.3** Chaque champ `ConsolidatedField` affiche :
  - La valeur
  - Un badge source (couleur par type : Cosium=bleu, Devis=vert, OCR=orange, Manuel=gris)
  - Un indicateur de confiance (icône check vert si ≥0.9, orange si 0.6-0.9, rouge si <0.6)
  - Bouton "Valider ✓" (l'utilisateur confirme)
  - Bouton "Corriger ✏" (ouvre un champ d'édition inline)

- [ ] **10.4** Section Alertes : triées par sévérité (erreurs en haut, rouge), avec bouton "J'ai vérifié" pour chaque

- [ ] **10.5** Bouton "Soumettre la PEC" : désactivé tant qu'il y a des erreurs non résolues. Au clic : appelle `POST /pec-preparations/{id}/submit`

- [ ] **10.6** Bouton "Exporter PDF" : génère un PDF de la fiche PEC complète (réutiliser `services/pdf_service.py`)

- [ ] **10.7** Tests frontend : 8+ tests

### Validation
- L'interface affiche toutes les sections avec les bonnes données
- Les champs avec incohérence sont visuellement marqués
- La validation/correction par l'utilisateur fonctionne
- Le bouton Soumettre crée bien une PecRequest
- Tous les textes sont en français

---

## ÉTAPE 11 : Tests E2E et validation métier [ ]

**Objectif** : S'assurer que le parcours complet fonctionne de bout en bout.

### Sous-tâches

- [ ] **11.1** Test E2E backend : créer un client → sync factures → extraire documents → consolider → préparer PEC → corriger → soumettre

- [ ] **11.2** Test avec données réelles Cosium (si disponible) : vérifier la qualité d'extraction sur de vrais documents

- [ ] **11.3** Test de performance : la consolidation doit prendre < 3 secondes même avec 50 documents à parser

- [ ] **11.4** Vérifier que TOUTES les règles d'incohérence se déclenchent correctement

- [ ] **11.5** Vérifier l'endpoint `data-quality` → le taux de liaison doit être > 90%

- [ ] **11.6** Revue de sécurité : aucune donnée patient ne doit leaker dans les logs (masquer NIR, etc.)

### Validation
- Parcours complet fonctionnel
- 0 erreur Python au démarrage
- Tous les tests passent
- Docker compose build OK

---

## ÉTAPE 12 : Évolutions futures (post-MVP) [ ]

**Objectif** : Planifier les améliorations pour les versions suivantes.

### Sous-tâches (non bloquantes pour la V12)

- [ ] **12.1** **Extraction IA** : Remplacer les regex par un appel Claude pour le parsing des documents → meilleure précision sur les formats variés d'ordonnances et attestations

- [ ] **12.2** **Multi-OCAM** : Base de données des OCAM avec leurs portails, formats, et règles spécifiques. Adapter la fiche PEC en fonction de l'opérateur ciblé

- [ ] **12.3** **Pré-remplissage PDF** : Générer des formulaires CERFA ou formulaires OCAM pré-remplis (PDF avec champs de formulaire)

- [ ] **12.4** **Historique PEC** : Apprendre des PEC précédentes du même client / même mutuelle pour améliorer la confiance et détecter les patterns

- [ ] **12.5** **Détection de renouvellement PEC** : Alerter quand une PEC arrive à expiration et proposer un renouvellement automatique

- [ ] **12.6** **Connexion directe portails OCAM** : API directe vers les portails de tiers payant (Almerys, Visilab, etc.) pour pré-remplir automatiquement — phase 2

- [ ] **12.7** **Dashboard PEC** : Vue synthétique de toutes les PEC en cours, taux d'acceptation, délais moyens, montants récupérés

---

## RÉSUMÉ DES DÉPENDANCES À INSTALLER

```
# Backend (requirements.txt)
rapidfuzz>=3.0.0          # Fuzzy matching pour liaison noms
pdfplumber>=0.10.0        # Extraction texte PDF natif
pytesseract>=0.3.10       # OCR via Tesseract
Pillow>=10.0.0            # Manipulation images
pdf2image>=1.16.3         # Conversion PDF → images

# Dockerfile
tesseract-ocr             # Engine OCR
tesseract-ocr-fra         # Données langue française
poppler-utils             # PDF utilities (pdftotext, pdftoppm)
```

## TABLES À CRÉER (migrations Alembic)

```
client_mutuelles           — Liaison client ↔ mutuelle
document_extractions       — Résultats OCR/extraction
pec_preparations           — Fiches d'assistance PEC
pec_preparation_documents  — Liaison préparation ↔ documents
```

## FICHIERS À CRÉER

```
# Backend
services/ocr_service.py
services/consolidation_service.py
services/incoherence_detector.py
services/pec_preparation_service.py
services/parsers/__init__.py
services/parsers/ordonnance_parser.py
services/parsers/devis_parser.py
services/parsers/attestation_mutuelle_parser.py
services/parsers/facture_parser.py
models/document_extraction.py
models/client_mutuelle.py
models/pec_preparation.py
repositories/document_extraction_repo.py
repositories/client_mutuelle_repo.py
repositories/pec_preparation_repo.py
domain/schemas/ocr.py
domain/schemas/pec_preparation.py
domain/schemas/consolidation.py
domain/schemas/client_mutuelle.py
api/routers/pec_preparation.py
tasks/extraction_tasks.py
scripts/relink_orphan_invoices.py

# Frontend
app/clients/[id]/tabs/TabPEC.tsx
app/clients/[id]/pec-preparation/[prepId]/page.tsx
components/pec/PecSection.tsx
components/pec/ConsolidatedField.tsx
components/pec/AlertPanel.tsx
components/pec/DocumentChecklist.tsx
components/pec/CorrectionTable.tsx
components/pec/CompletionGauge.tsx
lib/types/pec-preparation.ts
```

## FICHIERS À MODIFIER

```
# Backend
integrations/cosium/adapter.py          — Extraire _links.customer des factures
integrations/erp_models.py              — Enrichir ERPInvoice si besoin
services/erp_sync_invoices.py           — Ajouter fuzzy matching
services/erp_sync_service.py            — Exporter les fonctions de matching
services/client_360_service.py          — Ajouter section mutuelles
requirements.txt                         — Nouvelles dépendances
main.py                                  — Enregistrer nouveaux routers

# Docker
backend/Dockerfile                       — Installer Tesseract + poppler
backend/Dockerfile.prod                  — Idem

# Frontend
app/clients/[id]/page.tsx               — Ajouter onglet PEC
lib/api.ts                              — Nouveaux appels API
lib/types/index.ts                      — Exporter nouveaux types
```

---

## ORDRE D'EXÉCUTION RECOMMANDÉ

```
1. ÉTAPE 1 (liaison client)      — CRITIQUE, fondation pour tout le reste
2. ÉTAPE 2 (mutuelle)            — Nécessaire pour PEC
3. ÉTAPE 3 (OCR infra)           — Prérequis pour les parsers
4. ÉTAPE 4 (parsers)             — Prérequis pour la consolidation
5. ÉTAPE 5 (consolidation)       — Le cœur du système
6. ÉTAPE 6 (incohérences)        — Enrichit la consolidation
7. ÉTAPE 7 (modèle PEC enrichi)  — Prérequis pour le service
8. ÉTAPE 8 (service PEC)         — Backend complet
9. ÉTAPE 9 (frontend onglet)     — UI shell
10. ÉTAPE 10 (frontend fiche)    — UI complète
11. ÉTAPE 11 (tests E2E)         — Validation finale
12. ÉTAPE 12 (évolutions)        — Post-MVP
```

**Estimation** : ~80-100 heures de développement pour les étapes 1-11.
**Complexité principale** : Les parsers (étape 4) dépendent de la qualité et variété des documents réels.
