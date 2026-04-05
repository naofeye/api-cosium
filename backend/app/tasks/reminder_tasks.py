"""
Celery tasks for automated reminder generation.

Usage:
    This task should be scheduled to run daily via Celery Beat:

    CELERY_BEAT_SCHEDULE = {
        'auto-generate-reminders': {
            'task': 'app.tasks.reminder_tasks.auto_generate_reminders',
            'schedule': crontab(hour=8, minute=0),  # Every day at 8am
        },
    }

    For now, it can also be triggered manually via the API:
    POST /api/v1/reminders/auto-generate
"""

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.repositories import reminder_repo
from app.services import reminder_service
from app.tasks import celery_app

logger = get_logger("reminder_tasks")


@celery_app.task(
    name="app.tasks.reminder_tasks.auto_generate_reminders",
    bind=True,
    max_retries=2,
    default_retry_delay=300,
)
def auto_generate_reminders(self) -> dict[str, int]:
    """Execute all active reminder plans against overdue items.

    Returns a summary of created reminders per plan.
    """
    db = SessionLocal()
    try:
        plans = reminder_repo.list_plans(db)
        active_plans = [p for p in plans if p.is_active]
        total_created = 0
        plan_results: dict[str, int] = {}

        for plan in active_plans:
            created = reminder_service.execute_plan(db, plan.id)
            count = len(created)
            plan_results[plan.name] = count
            total_created += count

            # Auto-send email reminders
            for r in created:
                if r.channel == "email":
                    reminder_service.send_reminder(db, r.id)

        logger.info(
            "auto_generate_complete",
            plans_executed=len(active_plans),
            reminders_created=total_created,
        )
        return plan_results
    finally:
        db.close()
