from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import Case, Customer, Devis, DevisLigne


def generate_numero(db: Session, tenant_id: int) -> str:
    count = db.scalar(select(func.count()).select_from(Devis).where(Devis.tenant_id == tenant_id)) or 0
    return f"DEV-{count + 1:05d}"


def create(db: Session, tenant_id: int, case_id: int, numero: str) -> Devis:
    devis = Devis(tenant_id=tenant_id, case_id=case_id, numero=numero)
    db.add(devis)
    db.flush()
    return devis


def add_ligne(
    db: Session,
    tenant_id: int,
    devis_id: int,
    designation: str,
    quantite: int,
    prix_unitaire_ht: float,
    taux_tva: float,
    montant_ht: float,
    montant_ttc: float,
) -> DevisLigne:
    ligne = DevisLigne(
        tenant_id=tenant_id,
        devis_id=devis_id,
        designation=designation,
        quantite=quantite,
        prix_unitaire_ht=prix_unitaire_ht,
        taux_tva=taux_tva,
        montant_ht=montant_ht,
        montant_ttc=montant_ttc,
    )
    db.add(ligne)
    return ligne


def clear_lignes(db: Session, devis_id: int, tenant_id: int) -> None:
    db.execute(delete(DevisLigne).where(DevisLigne.devis_id == devis_id, DevisLigne.tenant_id == tenant_id))


def get_by_id(db: Session, devis_id: int, tenant_id: int) -> Devis | None:
    return db.scalars(select(Devis).where(Devis.id == devis_id, Devis.tenant_id == tenant_id)).first()


def get_lignes(db: Session, devis_id: int, tenant_id: int) -> list[DevisLigne]:
    return list(
        db.scalars(
            select(DevisLigne)
            .where(DevisLigne.devis_id == devis_id, DevisLigne.tenant_id == tenant_id)
            .order_by(DevisLigne.id)
        ).all()
    )


def list_all(db: Session, tenant_id: int, limit: int = 25, offset: int = 0) -> list[dict]:
    rows = db.execute(
        select(
            Devis.id,
            Devis.case_id,
            Devis.numero,
            Devis.status,
            Devis.montant_ht,
            Devis.tva,
            Devis.montant_ttc,
            Devis.part_secu,
            Devis.part_mutuelle,
            Devis.reste_a_charge,
            Devis.created_at,
            Devis.updated_at,
            Customer.first_name,
            Customer.last_name,
        )
        .join(Case, Case.id == Devis.case_id)
        .join(Customer, Customer.id == Case.customer_id)
        .where(Devis.tenant_id == tenant_id)
        .order_by(Devis.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return [
        {
            "id": r.id,
            "case_id": r.case_id,
            "numero": r.numero,
            "status": r.status,
            "montant_ht": float(r.montant_ht),
            "tva": float(r.tva),
            "montant_ttc": float(r.montant_ttc),
            "part_secu": float(r.part_secu),
            "part_mutuelle": float(r.part_mutuelle),
            "reste_a_charge": float(r.reste_a_charge),
            "created_at": r.created_at,
            "updated_at": r.updated_at,
            "customer_name": f"{r.first_name} {r.last_name}",
        }
        for r in rows
    ]


def get_detail(db: Session, devis_id: int, tenant_id: int) -> dict | None:
    row = db.execute(
        select(
            Devis.id,
            Devis.case_id,
            Devis.numero,
            Devis.status,
            Devis.montant_ht,
            Devis.tva,
            Devis.montant_ttc,
            Devis.part_secu,
            Devis.part_mutuelle,
            Devis.reste_a_charge,
            Devis.created_at,
            Devis.updated_at,
            Customer.first_name,
            Customer.last_name,
        )
        .join(Case, Case.id == Devis.case_id)
        .join(Customer, Customer.id == Case.customer_id)
        .where(Devis.id == devis_id, Devis.tenant_id == tenant_id)
    ).first()
    if not row:
        return None
    return {
        "id": row.id,
        "case_id": row.case_id,
        "numero": row.numero,
        "status": row.status,
        "montant_ht": float(row.montant_ht),
        "tva": float(row.tva),
        "montant_ttc": float(row.montant_ttc),
        "part_secu": float(row.part_secu),
        "part_mutuelle": float(row.part_mutuelle),
        "reste_a_charge": float(row.reste_a_charge),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "customer_name": f"{row.first_name} {row.last_name}",
    }


def update_totals(
    db: Session,
    devis: Devis,
    montant_ht: float,
    tva: float,
    montant_ttc: float,
    part_secu: float,
    part_mutuelle: float,
    reste_a_charge: float,
) -> None:
    devis.montant_ht = montant_ht
    devis.tva = tva
    devis.montant_ttc = montant_ttc
    devis.part_secu = part_secu
    devis.part_mutuelle = part_mutuelle
    devis.reste_a_charge = reste_a_charge
    db.flush()


def update_status(db: Session, devis: Devis, status: str) -> None:
    devis.status = status
    db.commit()
    db.refresh(devis)
