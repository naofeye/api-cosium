"""Add all Cosium reference and sync tables.

⚠️  MIGRATION BOOTSTRAP HISTORIQUE — NE PAS REPRODUIRE CE PATTERN.

Cette migration utilise `CREATE TABLE IF NOT EXISTS` pour rattraper un état
de BDD divergent (tables Cosium créées via `Base.metadata.create_all()` dans
des envs de dev pré-Alembic). Elle est acceptée comme bootstrap one-shot
et documentée dans l'ADR 0007 (`docs/adr/0007-alembic-bootstrap-migration-accepted.md`).

**Règle pour les migrations futures** : utiliser l'API Alembic standard
(`op.create_table`, `op.add_column`, `op.create_index`). Aucun
`CREATE ... IF NOT EXISTS` dans les migrations postérieures à celle-ci.

Covers: cosium_payments, cosium_third_party_payments, cosium_prescriptions,
cosium_documents, cosium_calendar_events, cosium_mutuelles, cosium_doctors,
cosium_brands, cosium_suppliers, cosium_tags, cosium_sites, cosium_banks,
cosium_companies, cosium_users, cosium_equipment_types, cosium_frame_materials,
cosium_calendar_categories, cosium_lens_focus_types, cosium_lens_focus_categories,
cosium_lens_materials, cosium_customer_tags.

Also adds missing columns/indexes on cosium_invoices (customer_cosium_id, tenant_type index).

Les 21 tables créées ici correspondent toutes à un modèle SQLAlchemy dans
`apps/api/app/models/cosium_data.py` et `cosium_reference.py` (vérifié par
script, cf. ADR 0007 § Implémentation).

Revision ID: h3b4c5d6e7f8
Revises: 5ae5ee2cc95d
Create Date: 2026-04-05 12:00:00.000000
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "h3b4c5d6e7f8"
down_revision: Union[str, Sequence[str], None] = "5ae5ee2cc95d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all Cosium reference/sync tables if they don't exist."""

    # --- cosium_invoices: add missing column + index ---
    op.execute("""
        ALTER TABLE cosium_invoices
            ADD COLUMN IF NOT EXISTS customer_cosium_id VARCHAR(50);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_cosium_invoices_customer_cosium_id
            ON cosium_invoices (customer_cosium_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_cosium_invoices_tenant_type
            ON cosium_invoices (tenant_id, type);
    """)

    # --- cosium_payments ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_payments (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            cosium_id INTEGER NOT NULL,
            payment_type_id INTEGER,
            amount DOUBLE PRECISION NOT NULL DEFAULT 0,
            original_amount DOUBLE PRECISION,
            type VARCHAR(50) NOT NULL DEFAULT '',
            due_date TIMESTAMP,
            issuer_name VARCHAR(255) NOT NULL DEFAULT '',
            bank VARCHAR(100) NOT NULL DEFAULT '',
            site_name VARCHAR(100) NOT NULL DEFAULT '',
            comment VARCHAR(500),
            payment_number VARCHAR(100) NOT NULL DEFAULT '',
            invoice_cosium_id INTEGER,
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_payments_tenant_id ON cosium_payments (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_payments_cosium_id ON cosium_payments (cosium_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_payments_tenant_cosium ON cosium_payments (tenant_id, cosium_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_payments_invoice_cosium_id ON cosium_payments (invoice_cosium_id);")

    # --- cosium_third_party_payments ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_third_party_payments (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            cosium_id INTEGER NOT NULL,
            social_security_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
            social_security_tpp BOOLEAN NOT NULL DEFAULT FALSE,
            additional_health_care_amount DOUBLE PRECISION NOT NULL DEFAULT 0,
            additional_health_care_tpp BOOLEAN NOT NULL DEFAULT FALSE,
            invoice_cosium_id INTEGER,
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_tpp_tenant_id ON cosium_third_party_payments (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_tpp_cosium_id ON cosium_third_party_payments (cosium_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_tpp_tenant_cosium ON cosium_third_party_payments (tenant_id, cosium_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_tpp_invoice_cosium_id ON cosium_third_party_payments (invoice_cosium_id);")

    # --- cosium_prescriptions ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_prescriptions (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            cosium_id INTEGER NOT NULL,
            prescription_date VARCHAR(20),
            file_date TIMESTAMP,
            customer_cosium_id INTEGER,
            customer_id INTEGER REFERENCES customers(id),
            sphere_right DOUBLE PRECISION,
            cylinder_right DOUBLE PRECISION,
            axis_right DOUBLE PRECISION,
            addition_right DOUBLE PRECISION,
            sphere_left DOUBLE PRECISION,
            cylinder_left DOUBLE PRECISION,
            axis_left DOUBLE PRECISION,
            addition_left DOUBLE PRECISION,
            spectacles_json TEXT,
            prescriber_name VARCHAR(255),
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_prescriptions_tenant_id ON cosium_prescriptions (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_prescriptions_cosium_id ON cosium_prescriptions (cosium_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_prescriptions_tenant_cosium ON cosium_prescriptions (tenant_id, cosium_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_prescriptions_customer_cosium_id ON cosium_prescriptions (customer_cosium_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_prescriptions_customer_id ON cosium_prescriptions (customer_id);")

    # --- cosium_documents ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_documents (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            customer_cosium_id INTEGER NOT NULL,
            customer_id INTEGER REFERENCES customers(id),
            cosium_document_id INTEGER NOT NULL,
            name VARCHAR(500),
            content_type VARCHAR(100) NOT NULL DEFAULT 'application/pdf',
            size_bytes INTEGER NOT NULL DEFAULT 0,
            minio_key VARCHAR(500),
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_docs_tenant_id ON cosium_documents (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_docs_tenant_cust ON cosium_documents (tenant_id, customer_cosium_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_docs_unique ON cosium_documents (tenant_id, customer_cosium_id, cosium_document_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_docs_customer_cosium_id ON cosium_documents (customer_cosium_id);")

    # --- cosium_calendar_events ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_calendar_events (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            cosium_id INTEGER NOT NULL,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            subject VARCHAR(255) NOT NULL DEFAULT '',
            customer_fullname VARCHAR(255) NOT NULL DEFAULT '',
            customer_number VARCHAR(50) NOT NULL DEFAULT '',
            category_name VARCHAR(100) NOT NULL DEFAULT '',
            category_color VARCHAR(20) NOT NULL DEFAULT '',
            category_family VARCHAR(50) NOT NULL DEFAULT '',
            status VARCHAR(50) NOT NULL DEFAULT '',
            canceled BOOLEAN NOT NULL DEFAULT FALSE,
            missed BOOLEAN NOT NULL DEFAULT FALSE,
            customer_arrived BOOLEAN NOT NULL DEFAULT FALSE,
            observation TEXT,
            site_name VARCHAR(100),
            modification_date TIMESTAMP,
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_calendar_tenant_id ON cosium_calendar_events (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_calendar_cosium_id ON cosium_calendar_events (cosium_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_calendar_tenant_cosium ON cosium_calendar_events (tenant_id, cosium_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_calendar_tenant_start ON cosium_calendar_events (tenant_id, start_date);")

    # --- cosium_mutuelles ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_mutuelles (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            cosium_id INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL DEFAULT '',
            code VARCHAR(100) NOT NULL DEFAULT '',
            label VARCHAR(255) NOT NULL DEFAULT '',
            phone VARCHAR(50) NOT NULL DEFAULT '',
            email VARCHAR(255) NOT NULL DEFAULT '',
            city VARCHAR(100) NOT NULL DEFAULT '',
            hidden BOOLEAN NOT NULL DEFAULT FALSE,
            opto_amc BOOLEAN NOT NULL DEFAULT FALSE,
            coverage_request_phone VARCHAR(50) NOT NULL DEFAULT '',
            coverage_request_email VARCHAR(255) NOT NULL DEFAULT '',
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_mutuelles_tenant_id ON cosium_mutuelles (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_mutuelles_cosium_id ON cosium_mutuelles (cosium_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_mutuelles_tenant_cosium ON cosium_mutuelles (tenant_id, cosium_id);")

    # --- cosium_doctors ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_doctors (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            cosium_id VARCHAR(100) NOT NULL,
            firstname VARCHAR(255) NOT NULL DEFAULT '',
            lastname VARCHAR(255) NOT NULL DEFAULT '',
            civility VARCHAR(50) NOT NULL DEFAULT '',
            email VARCHAR(255),
            phone VARCHAR(50),
            rpps_number VARCHAR(20),
            specialty VARCHAR(100) NOT NULL DEFAULT '',
            optic_prescriber BOOLEAN NOT NULL DEFAULT FALSE,
            audio_prescriber BOOLEAN NOT NULL DEFAULT FALSE,
            hidden BOOLEAN NOT NULL DEFAULT FALSE,
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_doctors_tenant_id ON cosium_doctors (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_doctors_cosium_id ON cosium_doctors (cosium_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_doctors_tenant_cosium ON cosium_doctors (tenant_id, cosium_id);")

    # --- cosium_brands ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_brands (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            name VARCHAR(255) NOT NULL,
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_brands_tenant_id ON cosium_brands (tenant_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_brands_tenant_name ON cosium_brands (tenant_id, name);")

    # --- cosium_suppliers ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_suppliers (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            name VARCHAR(255) NOT NULL,
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_suppliers_tenant_id ON cosium_suppliers (tenant_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_suppliers_tenant_name ON cosium_suppliers (tenant_id, name);")

    # --- cosium_tags ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_tags (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            cosium_id INTEGER NOT NULL,
            code VARCHAR(100) NOT NULL DEFAULT '',
            description VARCHAR(255) NOT NULL DEFAULT '',
            hidden BOOLEAN NOT NULL DEFAULT FALSE,
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_tags_tenant_id ON cosium_tags (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_tags_cosium_id ON cosium_tags (cosium_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_tags_tenant_cosium ON cosium_tags (tenant_id, cosium_id);")

    # --- cosium_sites ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_sites (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            cosium_id INTEGER NOT NULL,
            name VARCHAR(255) NOT NULL DEFAULT '',
            code VARCHAR(50) NOT NULL DEFAULT '',
            long_label VARCHAR(255) NOT NULL DEFAULT '',
            address VARCHAR(255) NOT NULL DEFAULT '',
            postcode VARCHAR(20) NOT NULL DEFAULT '',
            city VARCHAR(100) NOT NULL DEFAULT '',
            country VARCHAR(100) NOT NULL DEFAULT '',
            phone VARCHAR(50) NOT NULL DEFAULT '',
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_sites_tenant_id ON cosium_sites (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_sites_cosium_id ON cosium_sites (cosium_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_sites_tenant_cosium ON cosium_sites (tenant_id, cosium_id);")

    # --- cosium_banks ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_banks (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            cosium_id INTEGER,
            name VARCHAR(255) NOT NULL DEFAULT '',
            address VARCHAR(255) NOT NULL DEFAULT '',
            city VARCHAR(100) NOT NULL DEFAULT '',
            post_code VARCHAR(20) NOT NULL DEFAULT '',
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_banks_tenant_id ON cosium_banks (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_banks_cosium_id ON cosium_banks (cosium_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_banks_tenant_name ON cosium_banks (tenant_id, name);")

    # --- cosium_companies ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_companies (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            cosium_id INTEGER,
            name VARCHAR(255) NOT NULL DEFAULT '',
            siret VARCHAR(50) NOT NULL DEFAULT '',
            ape_code VARCHAR(20) NOT NULL DEFAULT '',
            address VARCHAR(255) NOT NULL DEFAULT '',
            city VARCHAR(100) NOT NULL DEFAULT '',
            post_code VARCHAR(20) NOT NULL DEFAULT '',
            phone VARCHAR(50) NOT NULL DEFAULT '',
            email VARCHAR(255) NOT NULL DEFAULT '',
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_companies_tenant_id ON cosium_companies (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_companies_cosium_id ON cosium_companies (cosium_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_companies_tenant_name ON cosium_companies (tenant_id, name);")

    # --- cosium_users ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_users (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            cosium_id INTEGER NOT NULL,
            alias VARCHAR(100) NOT NULL DEFAULT '',
            firstname VARCHAR(255) NOT NULL DEFAULT '',
            lastname VARCHAR(255) NOT NULL DEFAULT '',
            title VARCHAR(100) NOT NULL DEFAULT '',
            bot BOOLEAN NOT NULL DEFAULT FALSE,
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_users_tenant_id ON cosium_users (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_users_cosium_id ON cosium_users (cosium_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_users_tenant_cosium ON cosium_users (tenant_id, cosium_id);")

    # --- cosium_equipment_types ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_equipment_types (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            label VARCHAR(255) NOT NULL DEFAULT '',
            label_code VARCHAR(100) NOT NULL DEFAULT '',
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_equip_types_tenant_id ON cosium_equipment_types (tenant_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_equip_types_tenant_code ON cosium_equipment_types (tenant_id, label_code);")

    # --- cosium_frame_materials ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_frame_materials (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            code VARCHAR(100) NOT NULL DEFAULT '',
            description VARCHAR(255) NOT NULL DEFAULT '',
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_frame_mat_tenant_id ON cosium_frame_materials (tenant_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_frame_mat_tenant_code ON cosium_frame_materials (tenant_id, code);")

    # --- cosium_calendar_categories ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_calendar_categories (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            cosium_id INTEGER,
            name VARCHAR(255) NOT NULL DEFAULT '',
            color VARCHAR(20) NOT NULL DEFAULT '',
            family_name VARCHAR(100) NOT NULL DEFAULT '',
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_cal_cat_tenant_id ON cosium_calendar_categories (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_cal_cat_cosium_id ON cosium_calendar_categories (cosium_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_cal_cat_tenant_name ON cosium_calendar_categories (tenant_id, name);")

    # --- cosium_lens_focus_types ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_lens_focus_types (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            code VARCHAR(100) NOT NULL DEFAULT '',
            label VARCHAR(255) NOT NULL DEFAULT '',
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_lft_tenant_id ON cosium_lens_focus_types (tenant_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_lft_tenant_code ON cosium_lens_focus_types (tenant_id, code);")

    # --- cosium_lens_focus_categories ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_lens_focus_categories (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            code VARCHAR(100) NOT NULL DEFAULT '',
            label VARCHAR(255) NOT NULL DEFAULT '',
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_lfc_tenant_id ON cosium_lens_focus_categories (tenant_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_lfc_tenant_code ON cosium_lens_focus_categories (tenant_id, code);")

    # --- cosium_lens_materials ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_lens_materials (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            code VARCHAR(100) NOT NULL DEFAULT '',
            label VARCHAR(255) NOT NULL DEFAULT '',
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_lm_tenant_id ON cosium_lens_materials (tenant_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_lm_tenant_code ON cosium_lens_materials (tenant_id, code);")

    # --- cosium_customer_tags ---
    op.execute("""
        CREATE TABLE IF NOT EXISTS cosium_customer_tags (
            id SERIAL PRIMARY KEY,
            tenant_id INTEGER NOT NULL REFERENCES tenants(id),
            customer_id INTEGER REFERENCES customers(id),
            customer_cosium_id VARCHAR(50) NOT NULL,
            tag_code VARCHAR(100) NOT NULL,
            synced_at TIMESTAMP NOT NULL DEFAULT NOW()
        );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_cust_tags_tenant_id ON cosium_customer_tags (tenant_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_cust_tags_customer_cosium_id ON cosium_customer_tags (customer_cosium_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_cust_tags_customer_id ON cosium_customer_tags (customer_id);")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_cosium_cust_tags_tenant_cust_tag ON cosium_customer_tags (tenant_id, customer_cosium_id, tag_code);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_cosium_cust_tags_tenant_cust ON cosium_customer_tags (tenant_id, customer_cosium_id);")


def downgrade() -> None:
    """Drop all Cosium reference/sync tables."""
    tables = [
        "cosium_customer_tags",
        "cosium_lens_materials",
        "cosium_lens_focus_categories",
        "cosium_lens_focus_types",
        "cosium_calendar_categories",
        "cosium_frame_materials",
        "cosium_equipment_types",
        "cosium_users",
        "cosium_companies",
        "cosium_banks",
        "cosium_sites",
        "cosium_tags",
        "cosium_suppliers",
        "cosium_brands",
        "cosium_doctors",
        "cosium_mutuelles",
        "cosium_calendar_events",
        "cosium_documents",
        "cosium_prescriptions",
        "cosium_third_party_payments",
        "cosium_payments",
    ]
    for table in tables:
        op.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")

    # Remove added columns/indexes from cosium_invoices
    op.execute("DROP INDEX IF EXISTS ix_cosium_invoices_tenant_type;")
    op.execute("DROP INDEX IF EXISTS ix_cosium_invoices_customer_cosium_id;")
    op.execute("ALTER TABLE cosium_invoices DROP COLUMN IF EXISTS customer_cosium_id;")
