"""Tests unitaires pour audit_service — creation, filtrage, pagination."""

import json

from sqlalchemy.orm import Session

from app.models import AuditLog, Tenant
from app.services import audit_service


class TestLogAction:
    """Tests de creation d'entrees d'audit."""

    def test_log_action_creates_entry(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        audit_service.log_action(
            db,
            tenant_id=tenant.id,
            user_id=seed_user.id,
            action="create",
            entity_type="case",
            entity_id=1,
        )

        logs = db.query(AuditLog).filter(AuditLog.entity_type == "case").all()
        assert len(logs) >= 1
        assert logs[0].action == "create"
        assert logs[0].user_id == seed_user.id

    def test_log_action_with_old_new_values(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        old_val = {"status": "draft"}
        new_val = {"status": "en_cours"}
        audit_service.log_action(
            db,
            tenant_id=tenant.id,
            user_id=seed_user.id,
            action="update",
            entity_type="case",
            entity_id=42,
            old_value=old_val,
            new_value=new_val,
        )

        log = db.query(AuditLog).filter(
            AuditLog.entity_type == "case", AuditLog.entity_id == 42
        ).first()
        assert log is not None
        assert json.loads(log.old_value) == old_val
        assert json.loads(log.new_value) == new_val

    def test_log_action_without_values(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        audit_service.log_action(
            db,
            tenant_id=tenant.id,
            user_id=seed_user.id,
            action="delete",
            entity_type="document",
            entity_id=99,
        )

        log = db.query(AuditLog).filter(
            AuditLog.entity_type == "document", AuditLog.entity_id == 99
        ).first()
        assert log is not None
        assert log.old_value is None
        assert log.new_value is None


class TestSearchLogs:
    """Tests du filtrage et de la pagination des logs d'audit."""

    def _seed_logs(self, db: Session, seed_user, tenant_id: int) -> None:
        """Helper pour creer plusieurs logs d'audit."""
        for i in range(8):
            audit_service.log_action(
                db,
                tenant_id=tenant_id,
                user_id=seed_user.id,
                action="create" if i % 2 == 0 else "update",
                entity_type="case" if i < 4 else "client",
                entity_id=i + 1,
            )

    def test_filter_by_entity_type(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        self._seed_logs(db, seed_user, tenant.id)

        result = audit_service.search_logs(
            db, tenant_id=tenant.id, entity_type="case",
            entity_id=None, user_id=None, date_from=None, date_to=None,
            page=1, page_size=50,
        )
        assert result.total >= 4
        for item in result.items:
            assert item.entity_type == "case"

    def test_filter_by_action(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        self._seed_logs(db, seed_user, tenant.id)

        result = audit_service.search_logs(
            db, tenant_id=tenant.id, entity_type=None,
            entity_id=None, user_id=None, date_from=None, date_to=None,
            page=1, page_size=50, action="create",
        )
        assert result.total >= 4
        for item in result.items:
            assert item.action == "create"

    def test_pagination_page_size(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        self._seed_logs(db, seed_user, tenant.id)

        result = audit_service.search_logs(
            db, tenant_id=tenant.id, entity_type=None,
            entity_id=None, user_id=None, date_from=None, date_to=None,
            page=1, page_size=3,
        )
        assert len(result.items) <= 3
        assert result.total >= 8
        assert result.page == 1
        assert result.page_size == 3

    def test_pagination_second_page(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        self._seed_logs(db, seed_user, tenant.id)

        page1 = audit_service.search_logs(
            db, tenant_id=tenant.id, entity_type=None,
            entity_id=None, user_id=None, date_from=None, date_to=None,
            page=1, page_size=3,
        )
        page2 = audit_service.search_logs(
            db, tenant_id=tenant.id, entity_type=None,
            entity_id=None, user_id=None, date_from=None, date_to=None,
            page=2, page_size=3,
        )
        # Different pages should return different items
        page1_ids = {i.id for i in page1.items}
        page2_ids = {i.id for i in page2.items}
        assert page1_ids.isdisjoint(page2_ids)

    def test_search_enriches_user_email(self, db: Session, seed_user) -> None:
        tenant = db.query(Tenant).filter(Tenant.slug == "test-magasin").first()
        audit_service.log_action(
            db, tenant_id=tenant.id, user_id=seed_user.id,
            action="create", entity_type="test_enrich", entity_id=1,
        )

        result = audit_service.search_logs(
            db, tenant_id=tenant.id, entity_type="test_enrich",
            entity_id=None, user_id=None, date_from=None, date_to=None,
            page=1, page_size=10,
        )
        assert len(result.items) >= 1
        assert result.items[0].user_email == "test@optiflow.local"
