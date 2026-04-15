from sqlalchemy.orm import Session

from app.models import (
    Case,
    Customer,
    Document,
    DocumentType,
    Organization,
    Payment,
    ReminderTemplate,
    Tenant,
    TenantUser,
    User,
)
from app.security import hash_password

DOCUMENT_TYPES = [
    {"code": "ordonnance", "label": "Ordonnance", "category": "medical", "is_required": True},
    {"code": "devis_signe", "label": "Devis signe", "category": "commercial", "is_required": True},
    {"code": "attestation_mutuelle", "label": "Attestation mutuelle", "category": "assurance", "is_required": True},
    {"code": "consentement_rgpd", "label": "Consentement RGPD", "category": "legal", "is_required": True},
    {"code": "facture", "label": "Facture", "category": "comptable", "is_required": False},
    {"code": "bon_livraison", "label": "Bon de livraison", "category": "logistique", "is_required": False},
    {"code": "certificat_conformite", "label": "Certificat de conformite", "category": "qualite", "is_required": False},
]


def _ensure_default_tenant(db: Session) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.slug == "default").first()
    if tenant:
        return tenant
    org = db.query(Organization).filter(Organization.slug == "default").first()
    if not org:
        org = Organization(
            name="Organisation par défaut", slug="default", contact_email="admin@optiflow.com", plan="solo"
        )
        db.add(org)
        db.flush()
    tenant = Tenant(organization_id=org.id, name="Magasin principal", slug="default")
    db.add(tenant)
    db.flush()
    return tenant


def seed_data(db: Session) -> None:
    tenant = _ensure_default_tenant(db)

    if db.query(User).count() == 0:
        user = User(email="admin@optiflow.com", password_hash=hash_password("Admin123"), role="admin")
        db.add(user)
        db.flush()
        db.add(TenantUser(user_id=user.id, tenant_id=tenant.id, role="admin"))
    else:
        user = db.query(User).filter(User.email == "admin@optiflow.com").first()
        if (
            user
            and db.query(TenantUser).filter(TenantUser.user_id == user.id, TenantUser.tenant_id == tenant.id).count()
            == 0
        ):
            db.add(TenantUser(user_id=user.id, tenant_id=tenant.id, role="admin"))

    if db.query(Customer).count() == 0:
        c = Customer(
            tenant_id=tenant.id, first_name="Marie", last_name="Dupont", phone="0600000000", email="marie@example.com"
        )
        db.add(c)
        db.flush()
        d = Case(tenant_id=tenant.id, customer_id=c.id, status="documents_missing", source="Cosium")
        db.add(d)
        db.flush()
        db.add(
            Document(
                tenant_id=tenant.id,
                case_id=d.id,
                type="ordonnance",
                filename="ordonnance.pdf",
                storage_key="demo/ordonnance.pdf",
            )
        )
        db.add(
            Payment(
                tenant_id=tenant.id,
                case_id=d.id,
                payer_type="mutuelle",
                amount_due=120.00,
                amount_paid=60.00,
                status="partial",
            )
        )

    if db.query(DocumentType).count() == 0:
        for dt in DOCUMENT_TYPES:
            db.add(DocumentType(**dt))

    if db.query(ReminderTemplate).count() == 0:
        templates = [
            ReminderTemplate(
                tenant_id=tenant.id,
                name="Relance client - 1ere",
                channel="email",
                payer_type="client",
                subject="Rappel de paiement - Facture {{facture_numero}}",
                body="Bonjour {{client_name}},\n\nNous vous rappelons que la facture {{facture_numero}} d'un montant de {{montant}} EUR est en attente de paiement depuis {{jours_retard}} jours.\n\nMerci de proceder au reglement.\n\nCordialement,\nOptiFlow",
                is_default=True,
            ),
            ReminderTemplate(
                tenant_id=tenant.id,
                name="Relance client - 2eme",
                channel="email",
                payer_type="client",
                subject="Seconde relance - Facture {{facture_numero}}",
                body="Bonjour {{client_name}},\n\nMalgre notre precedent rappel, la facture {{facture_numero}} de {{montant}} EUR reste impayee.\n\nNous vous prions de bien vouloir regulariser cette situation dans les plus brefs delais.\n\nCordialement,\nOptiFlow",
                is_default=False,
            ),
            ReminderTemplate(
                tenant_id=tenant.id,
                name="Relance mutuelle",
                channel="email",
                payer_type="mutuelle",
                subject="Relance PEC - Dossier {{client_name}}",
                body="Madame, Monsieur,\n\nNous vous relanceons concernant la prise en charge du dossier de {{client_name}} pour un montant de {{montant}} EUR.\n\nMerci de nous faire parvenir votre accord.\n\nCordialement,\nOptiFlow",
                is_default=True,
            ),
            ReminderTemplate(
                tenant_id=tenant.id,
                name="Relance secu",
                channel="email",
                payer_type="secu",
                subject="Relance remboursement - {{client_name}}",
                body="Madame, Monsieur,\n\nNous attendons le remboursement du dossier de {{client_name}} pour un montant de {{montant}} EUR.\n\nCordialement,\nOptiFlow",
                is_default=True,
            ),
            ReminderTemplate(
                tenant_id=tenant.id,
                name="SMS rappel client",
                channel="sms",
                payer_type="client",
                subject=None,
                body="OptiFlow: Rappel - facture {{facture_numero}} de {{montant}} EUR en attente. Merci de regulariser.",
                is_default=True,
            ),
        ]
        for t in templates:
            db.add(t)
    db.commit()
