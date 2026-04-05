"""Tests unitaires pour reminder_service — plans, execution, templates, stats."""

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.domain.schemas.reminders import (
    ReminderCreate,
    ReminderPlanCreate,
    ReminderTemplateCreate,
)
from app.models import Tenant
from app.services import reminder_service


class TestReminderPlans:
    """Tests de creation et gestion des plans de relance."""

    def test_create_plan_happy_path(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        payload = ReminderPlanCreate(
            name="Plan client standard",
            payer_type="client",
            rules_json={"min_days_overdue": 7, "min_amount": 10, "max_reminders": 3},
            channel_sequence=["email", "courrier", "telephone"],
            interval_days=7,
        )
        result = reminder_service.create_plan(db, tenant.id, payload, seed_user.id)

        assert result.id is not None
        assert result.name == "Plan client standard"
        assert result.payer_type == "client"
        assert result.is_active is True
        assert result.interval_days == 7

    def test_create_plan_minimal(self, db, seed_user):
        """Creation avec les valeurs par defaut."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        payload = ReminderPlanCreate(name="Plan minimal", payer_type="mutuelle")
        result = reminder_service.create_plan(db, tenant.id, payload, seed_user.id)

        assert result.name == "Plan minimal"
        assert result.payer_type == "mutuelle"

    def test_list_plans(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        reminder_service.create_plan(
            db, tenant.id, ReminderPlanCreate(name="Plan 1", payer_type="client"), seed_user.id
        )
        results = reminder_service.list_plans(db, tenant.id)
        assert len(results) >= 1

    def test_toggle_plan(self, db, seed_user):
        """Activer/desactiver un plan de relance."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        plan = reminder_service.create_plan(
            db, tenant.id, ReminderPlanCreate(name="Toggle plan", payer_type="client"), seed_user.id
        )
        assert plan.is_active is True

        toggled = reminder_service.toggle_plan(db, tenant.id, plan.id, False)
        assert toggled.is_active is False

        toggled_back = reminder_service.toggle_plan(db, tenant.id, plan.id, True)
        assert toggled_back.is_active is True

    def test_toggle_plan_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        with pytest.raises(NotFoundError):
            reminder_service.toggle_plan(db, tenant.id, 99999, False)


class TestExecutePlan:
    """Tests d'execution de plan de relance."""

    def test_execute_plan_no_overdue(self, db, seed_user):
        """Execution d'un plan sans factures en retard retourne une liste vide."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        plan = reminder_service.create_plan(
            db, tenant.id,
            ReminderPlanCreate(
                name="Exec plan", payer_type="client",
                rules_json={"min_days_overdue": 0, "min_amount": 0, "max_reminders": 5},
            ),
            seed_user.id,
        )
        result = reminder_service.execute_plan(db, tenant.id, plan.id, seed_user.id)
        assert isinstance(result, list)

    def test_execute_plan_not_found(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        with pytest.raises(NotFoundError):
            reminder_service.execute_plan(db, tenant.id, 99999, seed_user.id)


class TestManualReminder:
    """Tests de creation de relance manuelle."""

    def test_create_manual_reminder(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        payload = ReminderCreate(
            target_type="client", target_id=1, channel="telephone",
            content="Appel de relance"
        )
        result = reminder_service.create_reminder(db, tenant.id, payload, seed_user.id)

        assert result.id is not None
        assert result.channel == "telephone"
        assert result.status == "scheduled"
        assert result.target_type == "client"

    def test_create_reminder_email(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        payload = ReminderCreate(
            target_type="payer_organization", target_id=1, channel="email",
            content="Relance email mutuelle"
        )
        result = reminder_service.create_reminder(db, tenant.id, payload, seed_user.id)

        assert result.channel == "email"
        assert result.target_type == "payer_organization"


class TestReminderStats:
    """Tests des statistiques de relance."""

    def test_get_stats(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        stats = reminder_service.get_stats(db, tenant.id)

        assert stats.total_overdue_amount >= 0
        assert stats.total_reminders_sent >= 0
        assert stats.recovery_rate >= 0
        assert isinstance(stats.overdue_by_age, dict)


class TestReminderTemplates:
    """Tests des modeles de relance."""

    def test_list_templates_includes_default(self, db, seed_user):
        """Le conftest seed un template par defaut."""
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        templates = reminder_service.list_templates(db, tenant.id)
        assert len(templates) >= 1
        assert any(t.is_default for t in templates)

    def test_create_template(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        payload = ReminderTemplateCreate(
            name="Relance urgente",
            channel="email",
            payer_type="client",
            subject="URGENT - Relance paiement",
            body="Bonjour {{client_name}}, votre paiement de {{montant}} EUR est en retard.",
        )
        result = reminder_service.create_template(db, tenant.id, payload, seed_user.id)

        assert result.id is not None
        assert result.name == "Relance urgente"
        assert result.channel == "email"
        assert result.is_default is False


class TestListReminders:
    """Tests du listing des relances."""

    def test_list_reminders_empty(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        items, total = reminder_service.list_reminders(db, tenant.id)
        assert total >= 0
        assert isinstance(items, list)

    def test_list_reminders_after_creation(self, db, seed_user):
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        reminder_service.create_reminder(
            db, tenant.id,
            ReminderCreate(target_type="client", target_id=1, channel="email", content="Test"),
            seed_user.id,
        )
        items, total = reminder_service.list_reminders(db, tenant.id)
        assert total >= 1
        assert len(items) >= 1
