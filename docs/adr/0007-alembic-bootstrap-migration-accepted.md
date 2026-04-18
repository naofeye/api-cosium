# ADR 0007 — Migration bootstrap `h3b4c5d6e7f8` avec `IF NOT EXISTS` acceptée

**Date** : 2026-04-18
**Statut** : Accepted
**Contexte audit** : TODO.md P1 "Migration `CREATE TABLE IF NOT EXISTS`"

## Contexte

La migration Alembic `h3b4c5d6e7f8_add_cosium_reference_and_sync_tables.py` (créée le 2026-04-05) utilise des commandes SQL brutes avec `CREATE TABLE IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS` pour créer 21 tables Cosium et 3 modifications de `cosium_invoices`. L'audit interne a flagué ce pattern comme dette technique :

1. **Divergence silencieuse possible** : si une BDD a une table pré-existante avec un schéma différent, `IF NOT EXISTS` n'émet aucune erreur — le schéma réel peut diverger du schéma Alembic sans qu'on le sache.
2. **Style atypique** : les autres migrations du projet utilisent l'API Alembic standard (`op.create_table`, `op.add_column`, `op.create_index`) qui est introspectable par les outils (autogenerate, diff).
3. **Test rollback partiel** : le `downgrade()` fait un `DROP TABLE IF EXISTS` sans vérification de cohérence.

Historique : cette migration a été créée pour rattraper un état de BDD divergent. Plusieurs environnements de développement avaient déjà les tables Cosium créées via `Base.metadata.create_all()` lors de phases expérimentales antérieures à l'introduction systématique d'Alembic. La migration devait être applicable aussi bien sur une BDD vierge que sur une BDD déjà partiellement peuplée, sans erreur `relation already exists`.

## Options considérées

### Option A — Refactoriser en migrations atomiques

Remplacer `IF NOT EXISTS` par `op.create_table`, éventuellement via plusieurs sous-migrations atomiques.

- ➕ Alignement stylistique avec le reste des migrations
- ➕ Autogenerate Alembic fonctionnera proprement sur les changements futurs de ces tables
- ➖ **Bloquant** : casserait les BDDs déjà migrées (prod + envs de dev), qui ont déjà appliqué cette migration. Il faudrait en plus un script de `alembic stamp` conditionnel ou une migration de "catch-up" complexe.
- ➖ Risque élevé pour un gain purement cosmétique

### Option B — Bootstrap one-shot accepté + interdiction pour le futur

Conserver la migration telle quelle, la marquer explicitement comme bootstrap historique, et interdire ce pattern pour toutes les futures migrations.

- ➕ Zéro risque pour les envs existants
- ➕ Effort limité (docstring + ADR + règle de review)
- ➕ Respecte la formulation du TODO ("migrations atomiques **ou** bootstrap one-shot")
- ➖ Le pattern reste dans le codebase (mais documenté et clos)

### Option C — Refacto + script de migration manuelle

Refactoriser + fournir un runbook `docs/RUNBOOK.md` pour re-stamper les BDDs existantes.

- ➕ Théoriquement propre à long terme
- ➖ Surface d'erreur pendant l'opération, fenêtre de risque en prod
- ➖ Gain marginal vs option B pour un effort significatif

## Décision

**Option B** — `h3b4c5d6e7f8` est acceptée comme **migration bootstrap one-shot**, historique et immuable. Les 21 tables créées correspondent toutes à un modèle SQLAlchemy dans `apps/api/app/models/` (vérifié par script, cf. section Implémentation). Le schéma réel des BDDs est donc aligné avec les modèles ORM pour les cas standards.

Pour empêcher la réapparition du pattern dans de futures migrations :

- **Règle** : toute nouvelle migration **doit** utiliser l'API Alembic (`op.create_table`, `op.add_column`, `op.create_index`, etc.). Aucun `CREATE … IF NOT EXISTS` dans les migrations postérieures à `h3b4c5d6e7f8`.
- **Enforcement** : revue de PR + éventuellement une règle `ruff`/`grep` CI ultérieure si le pattern réapparaît.
- **Documentation inline** : ajout d'une docstring en tête de la migration pointant vers cet ADR.

## Implémentation

1. **Vérification de cohérence** — les 21 tables créées par la migration ont toutes un modèle SQLAlchemy correspondant dans `apps/api/app/models/cosium_data.py` et `apps/api/app/models/cosium_reference.py` :
   - `cosium_payments`, `cosium_third_party_payments`, `cosium_prescriptions`, `cosium_documents`, `cosium_calendar_events`, `cosium_mutuelles`, `cosium_doctors`, `cosium_brands`, `cosium_suppliers`, `cosium_tags`, `cosium_sites`, `cosium_banks`, `cosium_companies`, `cosium_users`, `cosium_equipment_types`, `cosium_frame_materials`, `cosium_calendar_categories`, `cosium_lens_focus_types`, `cosium_lens_focus_categories`, `cosium_lens_materials`, `cosium_customer_tags`
2. **Docstring migration** : la docstring en tête de `h3b4c5d6e7f8_add_cosium_reference_and_sync_tables.py` est enrichie pour pointer vers cet ADR et marquer la migration comme **bootstrap historique — ne pas reproduire ce pattern**.
3. **TODO.md** : l'entrée P1 "Migration `CREATE TABLE IF NOT EXISTS`" est fermée avec référence à cet ADR.

## Conséquences

✅ **Risque nul pour les environnements existants** — aucun changement fonctionnel, aucune migration applicative.
✅ **Dette documentée** — un développeur qui ouvre la migration comprend immédiatement son statut et la règle pour la suite.
✅ **P1 fermé** — la liste des bloquants production grand public passe à 1 item (splash screens iOS, non-critique).
⚠️ **Divergence schéma non détectée** — si une BDD avait reçu un `CREATE TABLE` manuel avec un schéma différent avant cette migration, la divergence persisterait. Mitigation : les tests d'intégration en CI tournent sur une BDD fraîche où Alembic crée tout de zéro, donc le schéma Alembic est validé contre les modèles à chaque CI. Si une divergence apparaissait en prod, elle se manifesterait par un `UndefinedColumn` / `UndefinedFunction` PostgreSQL lors de l'exécution d'une query ORM — détectable via Sentry.
⚠️ **Future refonte possible** — si un chantier d'envergure (ex: migration PostgreSQL 17, RLS policies) requiert de redescendre complètement les migrations Cosium, cet ADR pourra être superseded par une ADR de refonte guidée.

## Références

- Migration concernée : `apps/api/alembic/versions/h3b4c5d6e7f8_add_cosium_reference_and_sync_tables.py`
- Modèles SQLAlchemy : `apps/api/app/models/cosium_data.py`, `apps/api/app/models/cosium_reference.py`
- TODO correspondant : `TODO.md` section P1 "Qualité / régression"
