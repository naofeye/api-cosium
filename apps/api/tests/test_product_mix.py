"""Tests de l'endpoint product-mix et du service compute_product_mix."""

from datetime import UTC, datetime

from app.models.cosium_data import CosiumInvoicedItem
from app.services.analytics_cosium_extras import compute_product_mix


def _add_item(db, tenant_id: int, *, cosium_id: int, family: str, total: float, qty: int = 1) -> None:
    db.add(
        CosiumInvoicedItem(
            tenant_id=tenant_id,
            cosium_id=cosium_id,
            invoice_cosium_id=1000 + cosium_id,
            product_label=f"Produit {cosium_id}",
            product_family=family,
            quantity=qty,
            unit_price_ti=total / max(1, qty),
            total_ti=total,
            synced_at=datetime.now(UTC).replace(tzinfo=None),
        )
    )


def test_product_mix_retourne_vide_si_aucune_sync(db, default_tenant) -> None:
    res = compute_product_mix(db, default_tenant.id)
    assert res["synced"] is False
    assert res["total_ca"] == 0
    assert res["families"] == []


def test_product_mix_agrege_par_famille(db, default_tenant) -> None:
    _add_item(db, default_tenant.id, cosium_id=1, family="monture", total=200)
    _add_item(db, default_tenant.id, cosium_id=2, family="monture", total=300)
    _add_item(db, default_tenant.id, cosium_id=3, family="verres", total=500)
    db.commit()

    res = compute_product_mix(db, default_tenant.id)
    assert res["synced"] is True
    assert res["total_ca"] == 1000.0
    families = {f["family"]: f for f in res["families"]}
    assert families["verres"]["ca"] == 500.0
    assert families["monture"]["ca"] == 500.0
    assert families["verres"]["share_pct"] == 50.0
    # Tri desc par CA (ex-aequo : ordre SQL arbitraire)
    assert len(res["families"]) == 2


def test_product_mix_periode_filtre_ancien(db, default_tenant) -> None:
    from datetime import timedelta
    old = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=200)
    recent = datetime.now(UTC).replace(tzinfo=None)
    db.add(
        CosiumInvoicedItem(
            tenant_id=default_tenant.id,
            cosium_id=10,
            invoice_cosium_id=1010,
            product_family="monture",
            total_ti=999,
            synced_at=old,
        )
    )
    db.add(
        CosiumInvoicedItem(
            tenant_id=default_tenant.id,
            cosium_id=11,
            invoice_cosium_id=1011,
            product_family="verres",
            total_ti=100,
            synced_at=recent,
        )
    )
    db.commit()

    res = compute_product_mix(db, default_tenant.id, days=30)
    # Ancien exclu, on ne voit que la recent
    assert res["total_ca"] == 100.0
    assert len(res["families"]) == 1
    assert res["families"][0]["family"] == "verres"
