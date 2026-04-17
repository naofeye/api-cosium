"""Tache hebdomadaire : envoie un resume des KPIs + alertes par email a l'admin de chaque tenant.

Utilise `analytics_kpi_service` pour calculer CA/recouvrement/balance agee
et `action_item_service` pour compter les alertes ouvertes.
"""
from datetime import UTC, datetime, timedelta

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.tasks import celery_app

logger = get_logger("weekly_report")


@celery_app.task(name="app.tasks.weekly_report_tasks.send_weekly_reports")
def send_weekly_reports() -> dict:
    """Parcourt les tenants et envoie un rapport hebdo a chaque admin actif."""
    from sqlalchemy import select

    from app.models import Tenant, TenantUser, User
    from app.services import action_item_service, analytics_kpi_service
    from app.tasks.email_tasks import send_email_async

    db = SessionLocal()
    sent = 0
    skipped = 0
    try:
        tenants = db.scalars(select(Tenant).where(Tenant.is_active.is_(True))).all()
        for tenant in tenants:
            admins = db.execute(
                select(User.email, User.id)
                .join(TenantUser, TenantUser.user_id == User.id)
                .where(
                    TenantUser.tenant_id == tenant.id,
                    TenantUser.role == "admin",
                    TenantUser.is_active.is_(True),
                    User.is_active.is_(True),
                )
            ).all()
            if not admins:
                skipped += 1
                continue

            try:
                week_ago = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=7)
                financial = analytics_kpi_service.get_financial_kpis(db, tenant.id, date_from=week_ago)
                aging = analytics_kpi_service.get_aging_balance(db, tenant.id)
                # Compte alertes pour le 1er admin (user-scoped)
                actions = action_item_service.list_action_items(
                    db, tenant.id, admins[0].id, status="pending", limit=1
                )
                action_total = actions.total
            except Exception as e:
                logger.error("weekly_report_compute_failed", tenant_id=tenant.id, error=str(e))
                continue

            subject = f"[OptiFlow] Resume hebdo - {tenant.name}"
            body_html = _render_report(
                tenant_name=tenant.name,
                ca=financial.ca_total,
                encaisse=financial.montant_encaisse,
                reste=financial.reste_a_encaisser,
                taux=financial.taux_recouvrement,
                aging_0_30=float(aging.zero_to_thirty or 0),
                aging_30_60=float(aging.thirty_to_sixty or 0),
                aging_60_plus=float((aging.sixty_to_ninety or 0) + (aging.ninety_plus or 0)),
                alerts_count=action_total,
            )

            for admin in admins:
                send_email_async.delay(admin.email, subject, body_html)
                sent += 1
        logger.info("weekly_reports_dispatched", sent=sent, skipped=skipped)
        return {"sent": sent, "skipped": skipped, "tenants": len(tenants)}
    finally:
        db.close()


def _fmt_eur(value: float) -> str:
    """Format montant en EUR style francais: 1 234,56 EUR."""
    return f"{value:,.2f}".replace(",", " ").replace(".", ",") + " EUR"


def _render_report(
    *,
    tenant_name: str,
    ca: float,
    encaisse: float,
    reste: float,
    taux: float,
    aging_0_30: float,
    aging_30_60: float,
    aging_60_plus: float,
    alerts_count: int,
) -> str:
    return f"""\
<!doctype html>
<html><body style="font-family:system-ui,sans-serif;color:#111;max-width:560px;margin:0 auto;padding:24px">
  <h2 style="color:#2563eb">Resume hebdomadaire &mdash; {tenant_name}</h2>
  <p>Voici un apercu de votre activite sur les 7 derniers jours.</p>
  <table style="width:100%;border-collapse:collapse;margin:16px 0">
    <tr><td style="padding:6px 0;color:#6b7280">CA total</td><td style="text-align:right;font-weight:600">{_fmt_eur(ca)}</td></tr>
    <tr><td style="padding:6px 0;color:#6b7280">Encaisse</td><td style="text-align:right;font-weight:600;color:#059669">{_fmt_eur(encaisse)}</td></tr>
    <tr><td style="padding:6px 0;color:#6b7280">Reste a encaisser</td><td style="text-align:right;font-weight:600;color:#dc2626">{_fmt_eur(reste)}</td></tr>
    <tr><td style="padding:6px 0;color:#6b7280">Taux de recouvrement</td><td style="text-align:right;font-weight:600">{taux:.1f}%</td></tr>
  </table>
  <h3>Balance agee</h3>
  <ul style="color:#6b7280">
    <li>0-30 jours : <b style="color:#111">{_fmt_eur(aging_0_30)}</b></li>
    <li>30-60 jours : <b style="color:#111">{_fmt_eur(aging_30_60)}</b></li>
    <li>60 jours et plus : <b style="color:#dc2626">{_fmt_eur(aging_60_plus)}</b></li>
  </ul>
  <p style="background:#fef3c7;padding:12px;border-radius:8px;color:#92400e">
    <b>{alerts_count} actions en attente</b> dans votre file. Connectez-vous a OptiFlow pour les traiter.
  </p>
  <p style="color:#9ca3af;font-size:12px;margin-top:32px">
    Email automatique - OptiFlow AI. Pour vous desinscrire, contactez votre administrateur.
  </p>
</body></html>
"""
