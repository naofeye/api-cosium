from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.domain.schemas.reminders import OverdueItem
from app.repositories import reminder_repo

logger = get_logger("collection_prioritizer")

# Probabilite de recouvrement estimee par age
RECOVERY_PROBABILITY = {
    30: 0.90,
    60: 0.70,
    90: 0.50,
    180: 0.25,
    365: 0.10,
}


def _estimate_recovery_probability(days_overdue: int) -> float:
    for threshold, prob in sorted(RECOVERY_PROBABILITY.items()):
        if days_overdue <= threshold:
            return prob
    return 0.05


def _recommend_action(days_overdue: int, payer_type: str) -> str:
    if payer_type in ("mutuelle", "secu"):
        if days_overdue < 14:
            return "email"
        if days_overdue < 45:
            return "courrier"
        return "telephone"
    # Client
    if days_overdue < 15:
        return "email"
    if days_overdue < 30:
        return "sms"
    if days_overdue < 60:
        return "courrier"
    return "telephone"


def prioritize_overdue(db: Session, tenant_id: int, min_days: int = 0) -> list[OverdueItem]:
    items = reminder_repo.get_all_overdue(db, tenant_id, min_days)
    results = []

    for item in items:
        days = item["days_overdue"]
        amount = item["amount"]
        age_factor = 1 + (days / 30)
        recovery_prob = _estimate_recovery_probability(days)
        score = round(amount * age_factor * recovery_prob, 2)
        action = _recommend_action(days, item["payer_type"])

        results.append(
            OverdueItem(
                entity_type=item["entity_type"],
                entity_id=item["entity_id"],
                customer_name=item["customer_name"],
                payer_type=item["payer_type"],
                amount=amount,
                days_overdue=days,
                score=score,
                action=action,
            )
        )

    results.sort(key=lambda x: x.score, reverse=True)
    logger.info("overdue_prioritized", tenant_id=tenant_id, count=len(results))
    return results
