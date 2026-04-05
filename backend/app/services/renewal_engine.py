"""Moteur de detection et scoring des opportunites de renouvellement."""

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.renewals import (
    RenewalConfig,
    RenewalDashboardResponse,
    RenewalOpportunity,
)
from app.repositories import renewal_repo

logger = get_logger("renewal_engine")


def _score_opportunity(
    months_since: int,
    last_amount: float,
    has_mutuelle: bool,
    config: RenewalConfig,
) -> float:
    """Calcule un score 0-100 pour une opportunite de renouvellement.

    Facteurs :
    - Anciennete de l'achat (plus c'est vieux, plus le score monte, plafond a 48 mois)
    - Montant de la derniere facture (indicateur de valeur client)
    - Couverture mutuelle active (bonus car le client paie moins)
    """
    # Facteur anciennete : 0-40 points (lineaire de 24 a 48 mois)
    age_score = max(min((months_since - config.age_minimum_months) / 24, 1.0), 0.0) * 40

    # Facteur valeur client : 0-30 points (base sur le montant, plafond a 1000 EUR)
    value_score = min(max(last_amount, 0) / 1000, 1.0) * 30

    # Facteur reactivite estimee : 15 points de base
    reactivity_score = 15.0

    # Bonus mutuelle : 0-15 points
    mutuelle_score = config.mutuelle_bonus if has_mutuelle else 0.0

    total = age_score + value_score + reactivity_score + mutuelle_score
    return round(min(total, 100.0), 1)


def _suggest_action(score: float, has_email: bool, has_phone: bool) -> str:
    """Suggere le meilleur canal de contact selon le score et les coordonnees."""
    if score >= 70 and has_phone:
        return "telephone"
    if has_email:
        return "email"
    if has_phone:
        return "sms"
    return "courrier"


def _build_reason(months_since: int, equipment_type: str | None, has_mutuelle: bool) -> str:
    """Genere une explication humaine de l'opportunite."""
    parts = [f"Dernier achat il y a {months_since} mois"]
    if equipment_type:
        labels = {
            "monture": "monture de lunettes",
            "verre": "verres correcteurs",
            "lentille": "lentilles de contact",
            "solaire": "lunettes solaires",
        }
        parts.append(f"equipement : {labels.get(equipment_type, equipment_type)}")
    if has_mutuelle:
        parts.append("mutuelle active (reste a charge reduit)")
    return ". ".join(parts) + "."


def detect_renewals(
    db: Session,
    tenant_id: int,
    config: RenewalConfig | None = None,
) -> list[RenewalOpportunity]:
    """Detecte toutes les opportunites de renouvellement pour un tenant."""

    if config is None:
        config = RenewalConfig()

    candidates = renewal_repo.get_customers_with_last_purchase(
        db,
        tenant_id,
        age_minimum_months=config.age_minimum_months,
        min_invoice_amount=config.min_invoice_amount,
    )

    # Cap candidates to prevent runaway N+1 queries on large datasets
    max_candidates = 500
    if len(candidates) > max_candidates:
        logger.warning(
            "renewal_candidates_capped",
            tenant_id=tenant_id,
            total=len(candidates),
            cap=max_candidates,
        )
        candidates = candidates[:max_candidates]

    opportunities: list[RenewalOpportunity] = []

    for item in candidates:
        customer = item["customer"]

        has_mutuelle = renewal_repo.customer_has_active_pec(
            db,
            tenant_id,
            customer.id,
        )

        equipment_type = renewal_repo.get_equipment_type_from_last_invoice(
            db,
            tenant_id,
            customer.id,
        )

        # Filtrer par type d'equipement si configure
        if config.equipment_types and equipment_type and equipment_type not in config.equipment_types:
            continue

        score = _score_opportunity(
            item["months_since_purchase"],
            item["last_invoice_amount"],
            has_mutuelle,
            config,
        )

        opportunity = RenewalOpportunity(
            customer_id=customer.id,
            customer_name=f"{customer.first_name} {customer.last_name}",
            phone=customer.phone,
            email=customer.email,
            last_purchase_date=item["last_purchase_date"],
            months_since_purchase=item["months_since_purchase"],
            equipment_type=equipment_type,
            last_invoice_amount=item["last_invoice_amount"],
            has_active_mutuelle=has_mutuelle,
            score=score,
            suggested_action=_suggest_action(score, bool(customer.email), bool(customer.phone)),
            reason=_build_reason(item["months_since_purchase"], equipment_type, has_mutuelle),
        )
        opportunities.append(opportunity)

    # Trier par score decroissant
    opportunities.sort(key=lambda o: o.score, reverse=True)

    logger.info(
        "renewals_detected",
        tenant_id=tenant_id,
        total=len(opportunities),
        high_score=sum(1 for o in opportunities if o.score >= 70),
    )

    return opportunities


def get_renewal_dashboard(
    db: Session,
    tenant_id: int,
    config: RenewalConfig | None = None,
) -> RenewalDashboardResponse:
    """Construit le tableau de bord renouvellement."""

    opportunities = detect_renewals(db, tenant_id, config)

    high_score = [o for o in opportunities if o.score >= 70]
    avg_months = sum(o.months_since_purchase for o in opportunities) / len(opportunities) if opportunities else 0
    estimated_revenue = sum(o.last_invoice_amount for o in high_score)

    campaigns_total = renewal_repo.count_renewal_campaigns(db, tenant_id)
    campaigns_month = renewal_repo.count_renewal_campaigns(db, tenant_id, this_month_only=True)

    return RenewalDashboardResponse(
        total_opportunities=len(opportunities),
        high_score_count=len(high_score),
        avg_months_since_purchase=round(avg_months, 1),
        estimated_revenue=round(estimated_revenue, 2),
        campaigns_sent=campaigns_total,
        campaigns_this_month=campaigns_month,
        top_opportunities=opportunities[:10],
    )
