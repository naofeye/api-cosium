"""Reconciliation des factures Cosium orphelines (customer_id NULL).

Apres une sync ERP, certaines factures peuvent rester non liees a un client
parce que le client n'avait pas encore ete importe ou parce que le matching
par nom a echoue. Ce service permet de rejouer le matching apres coup, en
beneficiant des nouveaux clients importes entre-temps.

Strategie :
1. Build customer maps (nom + cosium_id) comme dans erp_sync_invoices
2. Pour chaque facture orpheline :
   a. Tenter le matching par cosium_id (champ customer_cosium_id stocke)
   b. Sinon par nom (fuzzy)
3. Update customer_id si trouve

Best-effort : ne crash pas en bloc si une ligne pose probleme.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.client import Customer
from app.models.cosium_data import CosiumInvoice
from app.services.erp_matching_service import (
    _match_customer_by_name,
    _normalize_name,
)

logger = get_logger("orphan_invoice_service")


def _build_customer_maps(
    db: Session, tenant_id: int
) -> tuple[dict[str, int], dict[str, int]]:
    """Construit les maps utilisees pour le matching (nom + cosium_id)."""
    customers = db.scalars(
        select(Customer).where(Customer.tenant_id == tenant_id)
    ).all()
    name_map: dict[str, int] = {}
    cosium_id_map: dict[str, int] = {}
    for c in customers:
        normalized_full = _normalize_name(f"{c.last_name} {c.first_name}")
        name_map[normalized_full] = c.id
        normalized_reverse = _normalize_name(f"{c.first_name} {c.last_name}")
        name_map[normalized_reverse] = c.id
        for prefix in ("M. ", "MME. ", "MLLE. ", "MME ", "MLLE ", "MR. ", "MRS. "):
            name_map[f"{prefix}{normalized_full}"] = c.id
            name_map[f"{prefix}{normalized_reverse}"] = c.id
        if c.cosium_id:
            cosium_id_map[str(c.cosium_id)] = c.id
    return name_map, cosium_id_map


def count_orphan_invoices(db: Session, tenant_id: int) -> dict[str, int | float]:
    """Statistiques orphelines : total + par strategie de match potentielle."""
    total_orphans = db.scalar(
        select(func.count(CosiumInvoice.id)).where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.customer_id.is_(None),
        )
    ) or 0

    total_invoices = db.scalar(
        select(func.count(CosiumInvoice.id)).where(
            CosiumInvoice.tenant_id == tenant_id
        )
    ) or 0

    return {
        "total_invoices": int(total_invoices),
        "orphans": int(total_orphans),
        "linked_pct": (
            round(100.0 * (total_invoices - total_orphans) / total_invoices, 1)
            if total_invoices > 0
            else 100.0
        ),
    }


def reconcile_orphan_invoices(
    db: Session,
    tenant_id: int,
    *,
    limit: int | None = None,
) -> dict[str, int]:
    """Rejoue le matching pour les factures orphelines.

    Args:
        db: session SQLAlchemy
        tenant_id: tenant scope
        limit: max factures a traiter (None = toutes). Utile pour batchs.

    Returns:
        {"processed": N, "matched": M, "still_orphan": K}
    """
    query = (
        select(CosiumInvoice)
        .where(
            CosiumInvoice.tenant_id == tenant_id,
            CosiumInvoice.customer_id.is_(None),
        )
        .order_by(CosiumInvoice.id)
    )
    if limit is not None:
        query = query.limit(limit)

    orphans = list(db.scalars(query).all())
    if not orphans:
        return {"processed": 0, "matched": 0, "still_orphan": 0}

    name_map, cosium_id_map = _build_customer_maps(db, tenant_id)

    matched = 0
    still_orphan = 0
    for inv in orphans:
        new_customer_id: int | None = None

        # 1) cosium_id direct
        if inv.customer_cosium_id:
            new_customer_id = cosium_id_map.get(str(inv.customer_cosium_id))

        # 2) name fallback
        if not new_customer_id and inv.customer_name:
            new_customer_id = _match_customer_by_name(inv.customer_name, name_map)

        if new_customer_id:
            inv.customer_id = new_customer_id
            matched += 1
        else:
            still_orphan += 1

    if matched > 0:
        db.commit()

    logger.info(
        "orphan_invoices_reconciled",
        tenant_id=tenant_id,
        processed=len(orphans),
        matched=matched,
        still_orphan=still_orphan,
    )
    return {
        "processed": len(orphans),
        "matched": matched,
        "still_orphan": still_orphan,
    }
