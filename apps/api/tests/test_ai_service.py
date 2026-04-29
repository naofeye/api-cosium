"""Tests unitaires pour ai_service.

Couvre :
- copilot_query : chaque mode (dossier, financier, documentaire, marketing)
- Gestion des erreurs du provider IA
- Token counting / billing (_estimate_cost)
- Construction du contexte client (get_client_cosium_context, _build_case_context)
- Enregistrement de l'usage (ai_usage_repo.create)
"""
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.models import Case, Customer, Tenant
from app.services import ai_service
from app.services.ai_service import (
    _build_case_context,
    _estimate_cost,
    copilot_query,
    get_client_cosium_context,
)


# ---------------------------------------------------------------------------
# _estimate_cost — token billing
# ---------------------------------------------------------------------------

class TestEstimateCost:
    def test_zero_tokens_gives_zero_cost(self) -> None:
        assert _estimate_cost(0, 0) == 0.0

    def test_cost_uses_haiku_rates(self) -> None:
        """Haiku : 0.25 USD / M token entree, 1.25 USD / M token sortie."""
        cost = _estimate_cost(1_000_000, 0)
        assert abs(cost - 0.25) < 1e-6

        cost = _estimate_cost(0, 1_000_000)
        assert abs(cost - 1.25) < 1e-6

    def test_mixed_token_count(self) -> None:
        cost = _estimate_cost(200, 100)
        expected = round((200 * 0.00000025) + (100 * 0.00000125), 6)
        assert cost == expected

    def test_result_is_rounded_to_6_decimal_places(self) -> None:
        cost = _estimate_cost(123, 456)
        # Should not have more than 6 decimal places
        decimal_part = str(cost).split(".")
        if len(decimal_part) == 2:
            assert len(decimal_part[1]) <= 6


# ---------------------------------------------------------------------------
# Fixtures helpers
# ---------------------------------------------------------------------------

def _make_provider_result(text: str = "Reponse IA.", tokens_in: int = 10, tokens_out: int = 20) -> dict:
    return {"text": text, "tokens_in": tokens_in, "tokens_out": tokens_out, "model": "claude-haiku-3-5"}


def _seed_customer_and_case(db: Session, tenant_id: int) -> tuple[Customer, Case]:
    """Insere un Customer + Case lies dans la BDD de test."""
    customer = Customer(
        tenant_id=tenant_id,
        first_name="Marie",
        last_name="Curie",
        email="marie@example.com",
        phone="0601020304",
    )
    db.add(customer)
    db.flush()

    case = Case(
        tenant_id=tenant_id,
        customer_id=customer.id,
        status="en_cours",
        source="manual",
    )
    db.add(case)
    db.commit()
    db.refresh(customer)
    db.refresh(case)
    return customer, case


# ---------------------------------------------------------------------------
# copilot_query — mode dossier
# ---------------------------------------------------------------------------

class TestCopilotQueryDossierMode:
    @patch("app.services.ai_service.ai_usage_repo")
    @patch("app.services._ai.context.ai_context_repo")
    @patch("app.services.ai_service.claude_provider")
    def test_dossier_mode_returns_ai_text(
        self,
        mock_provider: MagicMock,
        mock_ctx_repo: MagicMock,
        mock_usage_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        mock_provider.query_with_usage.return_value = _make_provider_result("Resume du dossier OK.")
        # Minimal context: case not found -> fallback message
        mock_ctx_repo.get_case_with_customer.return_value = None
        mock_ctx_repo.get_case_customer_id.return_value = None
        mock_ctx_repo.get_case_documents.return_value = []
        mock_ctx_repo.get_case_devis.return_value = []
        mock_ctx_repo.get_case_factures.return_value = []
        mock_ctx_repo.get_case_payments.return_value = []
        mock_ctx_repo.get_case_pecs.return_value = []
        mock_usage_repo.create.return_value = None

        result = copilot_query(
            db,
            tenant_id=default_tenant.id,
            question="Resumé ce dossier",
            user_id=1,
            case_id=999,
            mode="dossier",
        )

        assert result == "Resume du dossier OK."
        mock_provider.query_with_usage.assert_called_once()
        call_kwargs = mock_provider.query_with_usage.call_args
        assert "dossier" in call_kwargs.kwargs.get("system", "") or "Copilote Dossier" in call_kwargs.kwargs.get("system", "")

    @patch("app.services.ai_service.ai_usage_repo")
    @patch("app.services._ai.context.ai_context_repo")
    @patch("app.services.ai_service.claude_provider")
    def test_usage_is_logged_after_query(
        self,
        mock_provider: MagicMock,
        mock_ctx_repo: MagicMock,
        mock_usage_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        mock_provider.query_with_usage.return_value = _make_provider_result(tokens_in=50, tokens_out=30)
        mock_ctx_repo.get_case_with_customer.return_value = None
        mock_ctx_repo.get_case_customer_id.return_value = None
        mock_ctx_repo.get_case_documents.return_value = []
        mock_ctx_repo.get_case_devis.return_value = []
        mock_ctx_repo.get_case_factures.return_value = []
        mock_ctx_repo.get_case_payments.return_value = []
        mock_ctx_repo.get_case_pecs.return_value = []
        mock_usage_repo.create.return_value = None

        copilot_query(
            db,
            tenant_id=default_tenant.id,
            question="Analyse",
            user_id=7,
            case_id=1,
            mode="dossier",
        )

        mock_usage_repo.create.assert_called_once()
        call_kwargs = mock_usage_repo.create.call_args.kwargs
        assert call_kwargs["user_id"] == 7
        assert call_kwargs["tokens_in"] == 50
        assert call_kwargs["tokens_out"] == 30
        assert call_kwargs["copilot_type"] == "dossier"
        assert call_kwargs["cost_usd"] == _estimate_cost(50, 30)


# ---------------------------------------------------------------------------
# copilot_query — mode financier
# ---------------------------------------------------------------------------

class TestCopilotQueryFinancierMode:
    @patch("app.services.ai_service.ai_usage_repo")
    @patch("app.services._ai.context.ai_context_repo")
    @patch("app.services.ai_service.claude_provider")
    def test_financier_mode_uses_financier_system_prompt(
        self,
        mock_provider: MagicMock,
        mock_ctx_repo: MagicMock,
        mock_usage_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        mock_provider.query_with_usage.return_value = _make_provider_result("Pas de retard detecte.")
        mock_usage_repo.create.return_value = None

        copilot_query(
            db,
            tenant_id=default_tenant.id,
            question="Analyse financiere",
            user_id=1,
            mode="financier",
        )

        call_kwargs = mock_provider.query_with_usage.call_args.kwargs
        assert "Financier" in call_kwargs.get("system", "")


# ---------------------------------------------------------------------------
# copilot_query — mode documentaire (RAG)
# ---------------------------------------------------------------------------

class TestCopilotQueryDocumentaireMode:
    @patch("app.services.ai_service.ai_usage_repo")
    @patch("app.services.ai_service.claude_provider")
    @patch("app.services._ai.context.search_docs")
    def test_documentaire_mode_calls_rag(
        self,
        mock_search: MagicMock,
        mock_provider: MagicMock,
        mock_usage_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        mock_search.return_value = "Extrait de doc Cosium pertinent."
        mock_provider.query_with_usage.return_value = _make_provider_result("Voici la procedure.")
        mock_usage_repo.create.return_value = None

        result = copilot_query(
            db,
            tenant_id=default_tenant.id,
            question="Comment faire une remise ?",
            user_id=1,
            mode="documentaire",
        )

        mock_search.assert_called_once_with("Comment faire une remise ?")
        call_kwargs = mock_provider.query_with_usage.call_args.kwargs
        assert "Extrait de doc Cosium pertinent." in call_kwargs.get("context", "")
        assert result == "Voici la procedure."

    @patch("app.services.ai_service.ai_usage_repo")
    @patch("app.services.ai_service.claude_provider")
    @patch("app.services._ai.context.search_docs")
    def test_documentaire_mode_fallback_when_rag_empty(
        self,
        mock_search: MagicMock,
        mock_provider: MagicMock,
        mock_usage_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        mock_search.return_value = ""  # Aucun resultat RAG
        mock_provider.query_with_usage.return_value = _make_provider_result("Je ne sais pas.")
        mock_usage_repo.create.return_value = None

        copilot_query(
            db,
            tenant_id=default_tenant.id,
            question="Question obscure",
            user_id=1,
            mode="documentaire",
        )

        call_kwargs = mock_provider.query_with_usage.call_args.kwargs
        assert "Aucun extrait" in call_kwargs.get("context", "")


# ---------------------------------------------------------------------------
# copilot_query — mode marketing
# ---------------------------------------------------------------------------

class TestCopilotQueryMarketingMode:
    @patch("app.services.ai_service.ai_usage_repo")
    @patch("app.services._ai.context.ai_context_repo")
    @patch("app.services.ai_service.claude_provider")
    def test_marketing_mode_provides_stats_context(
        self,
        mock_provider: MagicMock,
        mock_ctx_repo: MagicMock,
        mock_usage_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        mock_ctx_repo.count_customers.return_value = 150
        mock_ctx_repo.count_cases.return_value = 320
        mock_provider.query_with_usage.return_value = _make_provider_result("Campagne recommandee : email.")
        mock_usage_repo.create.return_value = None

        copilot_query(
            db,
            tenant_id=default_tenant.id,
            question="Quelle campagne suggeres-tu ?",
            user_id=1,
            mode="marketing",
        )

        mock_ctx_repo.count_customers.assert_called_once_with(db, default_tenant.id)
        mock_ctx_repo.count_cases.assert_called_once_with(db, default_tenant.id)
        call_kwargs = mock_provider.query_with_usage.call_args.kwargs
        context = call_kwargs.get("context", "")
        assert "150" in context
        assert "320" in context


# ---------------------------------------------------------------------------
# copilot_query — provider error handling
# ---------------------------------------------------------------------------

class TestCopilotQueryProviderErrors:
    @patch("app.services.ai_service.ai_usage_repo")
    @patch("app.services._ai.context.ai_context_repo")
    @patch("app.services.ai_service.claude_provider")
    def test_provider_error_text_is_returned(
        self,
        mock_provider: MagicMock,
        mock_ctx_repo: MagicMock,
        mock_usage_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        """Quand le provider retourne un message d'erreur grace a sa gestion interne, le service le propage."""
        error_response = {
            "text": "[Erreur IA] Une erreur est survenue lors de la requete IA. Veuillez reessayer.",
            "tokens_in": 0,
            "tokens_out": 0,
            "model": "claude-haiku-3-5",
        }
        mock_provider.query_with_usage.return_value = error_response
        mock_ctx_repo.get_case_with_customer.return_value = None
        mock_ctx_repo.get_case_customer_id.return_value = None
        mock_ctx_repo.get_case_documents.return_value = []
        mock_ctx_repo.get_case_devis.return_value = []
        mock_ctx_repo.get_case_factures.return_value = []
        mock_ctx_repo.get_case_payments.return_value = []
        mock_ctx_repo.get_case_pecs.return_value = []
        mock_usage_repo.create.return_value = None

        result = copilot_query(
            db,
            tenant_id=default_tenant.id,
            question="Teste",
            user_id=1,
            mode="dossier",
        )

        assert "Erreur IA" in result

    @patch("app.services.ai_service.ai_usage_repo")
    @patch("app.services._ai.context.ai_context_repo")
    @patch("app.services.ai_service.claude_provider")
    def test_usage_logged_with_zero_tokens_on_error(
        self,
        mock_provider: MagicMock,
        mock_ctx_repo: MagicMock,
        mock_usage_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        """Meme en cas d'erreur IA, l'usage est logue avec 0 tokens."""
        mock_provider.query_with_usage.return_value = {
            "text": "[Erreur IA]",
            "tokens_in": 0,
            "tokens_out": 0,
            "model": "claude-haiku-3-5",
        }
        mock_ctx_repo.get_case_with_customer.return_value = None
        mock_ctx_repo.get_case_customer_id.return_value = None
        mock_ctx_repo.get_case_documents.return_value = []
        mock_ctx_repo.get_case_devis.return_value = []
        mock_ctx_repo.get_case_factures.return_value = []
        mock_ctx_repo.get_case_payments.return_value = []
        mock_ctx_repo.get_case_pecs.return_value = []
        mock_usage_repo.create.return_value = None

        copilot_query(db, tenant_id=default_tenant.id, question="Q", user_id=5, mode="dossier")

        call_kwargs = mock_usage_repo.create.call_args.kwargs
        assert call_kwargs["tokens_in"] == 0
        assert call_kwargs["tokens_out"] == 0
        assert call_kwargs["cost_usd"] == 0.0


# ---------------------------------------------------------------------------
# copilot_query — unknown mode falls back to "dossier" system prompt
# ---------------------------------------------------------------------------

class TestCopilotQueryUnknownMode:
    @patch("app.services.ai_service.ai_usage_repo")
    @patch("app.services.ai_service.claude_provider")
    def test_unknown_mode_falls_back_to_dossier_prompt(
        self,
        mock_provider: MagicMock,
        mock_usage_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        mock_provider.query_with_usage.return_value = _make_provider_result("OK")
        mock_usage_repo.create.return_value = None

        copilot_query(
            db,
            tenant_id=default_tenant.id,
            question="Q",
            user_id=1,
            mode="inexistant",
        )

        call_kwargs = mock_provider.query_with_usage.call_args.kwargs
        # Doit utiliser le system prompt du mode "dossier"
        assert "Copilote Dossier" in call_kwargs.get("system", "")


# ---------------------------------------------------------------------------
# get_client_cosium_context — construction du contexte client depuis BDD
# ---------------------------------------------------------------------------

class TestGetClientCosiumContext:
    @patch("app.services._ai.context.ai_context_repo")
    def test_returns_empty_string_when_no_data(
        self,
        mock_ctx_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        mock_ctx_repo.get_cosium_invoices.return_value = []
        mock_ctx_repo.get_cosium_prescriptions.return_value = []
        mock_ctx_repo.get_cosium_invoice_ids.return_value = []
        mock_ctx_repo.get_cosium_payments_by_invoice_ids.return_value = []

        result = get_client_cosium_context(db, customer_id=1, tenant_id=default_tenant.id)

        assert result == ""

    @patch("app.services._ai.context.ai_context_repo")
    def test_includes_invoice_summary(
        self,
        mock_ctx_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        from datetime import date

        # Construire un objet factice qui se comporte comme une Row SQLAlchemy
        inv = MagicMock()
        inv.invoice_number = "FAC-2025-001"
        inv.invoice_date = date(2025, 3, 1)
        inv.total_ti = 450.0
        inv.outstanding_balance = 150.0
        inv.type = "FA"
        inv.settled = False

        mock_ctx_repo.get_cosium_invoices.return_value = [inv]
        mock_ctx_repo.get_cosium_prescriptions.return_value = []
        mock_ctx_repo.get_cosium_invoice_ids.return_value = [101]
        mock_ctx_repo.get_cosium_payments_by_invoice_ids.return_value = []

        result = get_client_cosium_context(db, customer_id=1, tenant_id=default_tenant.id)

        assert "FACTURES COSIUM" in result
        assert "FAC-2025-001" in result
        assert "450.00 EUR" in result
        assert "reste 150.00 EUR" in result

    @patch("app.services._ai.context.ai_context_repo")
    def test_includes_prescription_summary(
        self,
        mock_ctx_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        rx = MagicMock()
        rx.prescription_date = "2025-01-10"
        rx.sphere_right = -1.5
        rx.cylinder_right = -0.5
        rx.axis_right = 90
        rx.addition_right = None
        rx.sphere_left = -1.25
        rx.cylinder_left = None
        rx.axis_left = None
        rx.addition_left = None
        rx.prescriber_name = "Martin"

        mock_ctx_repo.get_cosium_invoices.return_value = []
        mock_ctx_repo.get_cosium_prescriptions.return_value = [rx]
        mock_ctx_repo.get_cosium_invoice_ids.return_value = []
        mock_ctx_repo.get_cosium_payments_by_invoice_ids.return_value = []

        result = get_client_cosium_context(db, customer_id=1, tenant_id=default_tenant.id)

        assert "ORDONNANCES COSIUM" in result
        assert "Martin" in result
        assert "sph -1.50" in result

    @patch("app.services._ai.context.ai_context_repo")
    def test_includes_payment_summary(
        self,
        mock_ctx_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        from datetime import date

        inv = MagicMock()
        inv.invoice_number = "FAC-001"
        inv.invoice_date = date(2025, 1, 1)
        inv.total_ti = 300.0
        inv.outstanding_balance = 0.0
        inv.type = "FA"
        inv.settled = True

        pmt = MagicMock()
        pmt.payment_number = "PAY-001"
        pmt.type = "CB"
        pmt.due_date = date(2025, 1, 15)
        pmt.amount = 300.0

        mock_ctx_repo.get_cosium_invoices.return_value = [inv]
        mock_ctx_repo.get_cosium_prescriptions.return_value = []
        mock_ctx_repo.get_cosium_invoice_ids.return_value = [55]
        mock_ctx_repo.get_cosium_payments_by_invoice_ids.return_value = [pmt]

        result = get_client_cosium_context(db, customer_id=1, tenant_id=default_tenant.id)

        assert "PAIEMENTS COSIUM" in result
        assert "PAY-001" in result
        assert "300.00 EUR" in result


# ---------------------------------------------------------------------------
# _build_case_context — construction du contexte dossier complet
# ---------------------------------------------------------------------------

class TestBuildCaseContext:
    @patch("app.services._ai.context.ai_context_repo")
    def test_returns_not_found_message_for_unknown_case(
        self,
        mock_ctx_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        mock_ctx_repo.get_case_with_customer.return_value = None

        result = _build_case_context(db, tenant_id=default_tenant.id, case_id=99999)

        assert "introuvable" in result.lower()

    @patch("app.services._ai.context.ai_context_repo")
    def test_builds_context_with_case_info(
        self,
        mock_ctx_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        from datetime import datetime

        case_row = MagicMock()
        case_row.id = 42
        case_row.first_name = "Jean"
        case_row.last_name = "Dupont"
        case_row.status = "en_cours"
        case_row.source = "manual"
        case_row.phone = "0601020304"
        case_row.email = "jean@example.com"
        case_row.created_at = datetime(2025, 4, 1, 10, 0)

        mock_ctx_repo.get_case_with_customer.return_value = case_row
        mock_ctx_repo.get_case_documents.return_value = []
        mock_ctx_repo.get_case_devis.return_value = []
        mock_ctx_repo.get_case_factures.return_value = []
        mock_ctx_repo.get_case_payments.return_value = []
        mock_ctx_repo.get_case_pecs.return_value = []
        mock_ctx_repo.get_case_customer_id.return_value = None
        mock_ctx_repo.get_cosium_invoices.return_value = []
        mock_ctx_repo.get_cosium_prescriptions.return_value = []

        result = _build_case_context(db, tenant_id=default_tenant.id, case_id=42)

        assert "DOSSIER #42" in result
        assert "Jean" in result
        assert "Dupont" in result
        assert "en_cours" in result

    @patch("app.services._ai.context.ai_context_repo")
    def test_includes_documents_when_present(
        self,
        mock_ctx_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        from datetime import datetime

        case_row = MagicMock()
        case_row.id = 1
        case_row.first_name = "Alice"
        case_row.last_name = "Smith"
        case_row.status = "complet"
        case_row.source = "manual"
        case_row.phone = None
        case_row.email = None
        case_row.created_at = datetime(2025, 1, 1)

        doc = MagicMock()
        doc.type = "ordonnance"
        doc.filename = "ordo_2025.pdf"
        doc.uploaded_at = datetime(2025, 2, 1)

        mock_ctx_repo.get_case_with_customer.return_value = case_row
        mock_ctx_repo.get_case_documents.return_value = [doc]
        mock_ctx_repo.get_case_devis.return_value = []
        mock_ctx_repo.get_case_factures.return_value = []
        mock_ctx_repo.get_case_payments.return_value = []
        mock_ctx_repo.get_case_pecs.return_value = []
        mock_ctx_repo.get_case_customer_id.return_value = None

        result = _build_case_context(db, tenant_id=default_tenant.id, case_id=1)

        assert "DOCUMENTS" in result
        assert "ordonnance" in result
        assert "ordo_2025.pdf" in result

    @patch("app.services._ai.context.ai_context_repo")
    def test_includes_cosium_data_when_customer_linked(
        self,
        mock_ctx_repo: MagicMock,
        db: Session,
        default_tenant: Tenant,
    ) -> None:
        """Quand un customer_id est lie au dossier, le contexte Cosium est inclus."""
        from datetime import datetime

        case_row = MagicMock()
        case_row.id = 5
        case_row.first_name = "Bob"
        case_row.last_name = "Lens"
        case_row.status = "en_cours"
        case_row.source = "cosium"
        case_row.phone = None
        case_row.email = None
        case_row.created_at = datetime(2025, 3, 10)

        inv = MagicMock()
        inv.invoice_number = "FAC-COSIUM-001"
        inv.invoice_date = datetime(2025, 3, 1).date()
        inv.total_ti = 200.0
        inv.outstanding_balance = 0.0
        inv.type = "FA"
        inv.settled = True

        mock_ctx_repo.get_case_with_customer.return_value = case_row
        mock_ctx_repo.get_case_documents.return_value = []
        mock_ctx_repo.get_case_devis.return_value = []
        mock_ctx_repo.get_case_factures.return_value = []
        mock_ctx_repo.get_case_payments.return_value = []
        mock_ctx_repo.get_case_pecs.return_value = []
        mock_ctx_repo.get_case_customer_id.return_value = 77
        mock_ctx_repo.get_cosium_invoices.return_value = [inv]
        mock_ctx_repo.get_cosium_prescriptions.return_value = []
        mock_ctx_repo.get_cosium_invoice_ids.return_value = []
        mock_ctx_repo.get_cosium_payments_by_invoice_ids.return_value = []

        result = _build_case_context(db, tenant_id=default_tenant.id, case_id=5)

        assert "DONNEES COSIUM" in result
        assert "FAC-COSIUM-001" in result
