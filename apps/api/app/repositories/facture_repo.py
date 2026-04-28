from datetime import UTC, datetime

from sqlalchemy import extract, func, select
from sqlalchemy.orm import Session

from app.models import Case, Customer, Devis, Facture, FactureLigne


def generate_numero(db: Session, tenant_id: int) -> str:
    year = datetime.now(UTC).replace(tzinfo=None).year
    count = (
        db.scalar(
            select(func.count())
            .select_from(Facture)
            .where(extract("year", Facture.created_at) == year, Facture.tenant_id == tenant_id)
        )
        or 0
    )
    return f"F-{year}-{count + 1:04d}"


def create(
    db: Session,
    tenant_id: int,
    case_id: int,
    devis_id: int,
    numero: str,
    montant_ht: float,
    tva: float,
    montant_ttc: float,
) -> Facture:
    facture = Facture(
        tenant_id=tenant_id,
        case_id=case_id,
        devis_id=devis_id,
        numero=numero,
        montant_ht=montant_ht,
        tva=tva,
        montant_ttc=montant_ttc,
    )
    db.add(facture)
    db.flush()
    return facture


def add_ligne(
    db: Session,
    tenant_id: int,
    facture_id: int,
    designation: str,
    quantite: int,
    prix_unitaire_ht: float,
    taux_tva: float,
    montant_ht: float,
    montant_ttc: float,
) -> FactureLigne:
    ligne = FactureLigne(
        tenant_id=tenant_id,
        facture_id=facture_id,
        designation=designation,
        quantite=quantite,
        prix_unitaire_ht=prix_unitaire_ht,
        taux_tva=taux_tva,
        montant_ht=montant_ht,
        montant_ttc=montant_ttc,
    )
    db.add(ligne)
    return ligne


def get_by_id(db: Session, facture_id: int, tenant_id: int) -> Facture | None:
    return db.scalars(select(Facture).where(Facture.id == facture_id, Facture.tenant_id == tenant_id)).first()


def get_by_devis_id(db: Session, devis_id: int, tenant_id: int) -> Facture | None:
    return db.scalars(select(Facture).where(Facture.devis_id == devis_id, Facture.tenant_id == tenant_id)).first()


def get_lignes(db: Session, facture_id: int, tenant_id: int) -> list[FactureLigne]:
    return list(
        db.scalars(
            select(FactureLigne)
            .where(FactureLigne.facture_id == facture_id, FactureLigne.tenant_id == tenant_id)
            .order_by(FactureLigne.id)
        ).all()
    )


def list_all(db: Session, tenant_id: int, limit: int = 25, offset: int = 0) -> list[dict]:
    rows = db.execute(
        select(
            Facture.id,
            Facture.case_id,
            Facture.devis_id,
            Facture.numero,
            Facture.date_emission,
            Facture.montant_ht,
            Facture.tva,
            Facture.montant_ttc,
            Facture.status,
            Facture.created_at,
            Customer.first_name,
            Customer.last_name,
        )
        .join(Case, Case.id == Facture.case_id)
        .join(Customer, Customer.id == Case.customer_id)
        .where(Facture.tenant_id == tenant_id)
        .order_by(Facture.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [
        {
            "id": r.id,
            "case_id": r.case_id,
            "devis_id": r.devis_id,
            "numero": r.numero,
            "date_emission": r.date_emission,
            "montant_ht": float(r.montant_ht),
            "tva": float(r.tva),
            "montant_ttc": float(r.montant_ttc),
            "status": r.status,
            "created_at": r.created_at,
            "customer_name": f"{r.first_name} {r.last_name}",
        }
        for r in rows
    ]


def get_detail(db: Session, facture_id: int, tenant_id: int) -> dict | None:
    row = db.execute(
        select(
            Facture.id,
            Facture.case_id,
            Facture.devis_id,
            Facture.numero,
            Facture.date_emission,
            Facture.montant_ht,
            Facture.tva,
            Facture.montant_ttc,
            Facture.status,
            Facture.created_at,
            Customer.first_name,
            Customer.last_name,
            Customer.email,
            Devis.numero.label("devis_numero"),
        )
        .join(Case, Case.id == Facture.case_id)
        .join(Customer, Customer.id == Case.customer_id)
        .join(Devis, Devis.id == Facture.devis_id)
        .where(Facture.id == facture_id, Facture.tenant_id == tenant_id)
    ).first()
    if not row:
        return None
    return {
        "id": row.id,
        "case_id": row.case_id,
        "devis_id": row.devis_id,
        "numero": row.numero,
        "date_emission": row.date_emission,
        "montant_ht": float(row.montant_ht),
        "tva": float(row.tva),
        "montant_ttc": float(row.montant_ttc),
        "status": row.status,
        "created_at": row.created_at,
        "customer_name": f"{row.first_name} {row.last_name}",
        "customer_email": row.email,
        "devis_numero": row.devis_numero,
    }


def get_customer_contact(
    db: Session, facture_id: int, tenant_id: int
) -> dict | None:
    """Retourne {customer_name, customer_email, facture_numero, facture_date}."""
    row = db.execute(
        select(
            Customer.first_name,
            Customer.last_name,
            Customer.email,
            Facture.numero,
            Facture.date_emission,
            Facture.montant_ht,
            Facture.tva,
            Facture.montant_ttc,
        )
        .join(Case, Case.id == Facture.case_id)
        .join(Customer, Customer.id == Case.customer_id)
        .where(Facture.id == facture_id, Facture.tenant_id == tenant_id)
    ).first()
    if not row:
        return None
    return {
        "customer_name": f"{row.first_name} {row.last_name}".strip(),
        "customer_email": row.email,
        "facture_numero": row.numero,
        "facture_date": row.date_emission,
        "montant_ht": float(row.montant_ht),
        "tva": float(row.tva),
        "montant_ttc": float(row.montant_ttc),
    }


def update_status(db: Session, facture: Facture, status: str) -> None:
    facture.status = status
    db.flush()
    db.refresh(facture)
