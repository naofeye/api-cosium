# Re-export all models for backward compatibility
# Usage: from app.models import User, Case, etc.

from app.models.ai import AiConversation, AiMessage, AiUsageLog  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.batch_operation import BatchOperation, BatchOperationItem  # noqa: F401
from app.models.case import Case  # noqa: F401
from app.models.client import Customer  # noqa: F401
from app.models.client_mutuelle import ClientMutuelle  # noqa: F401
from app.models.cosium_data import (  # noqa: F401
    CosiumDocument,
    CosiumInvoice,
    CosiumInvoicedItem,
    CosiumPayment,
    CosiumPrescription,
    CosiumProduct,
    CosiumThirdPartyPayment,
)
from app.models.cosium_reference import (  # noqa: F401
    CosiumBank,
    CosiumBrand,
    CosiumCalendarCategory,
    CosiumCalendarEvent,
    CosiumCompany,
    CosiumCustomerTag,
    CosiumDoctor,
    CosiumEquipmentType,
    CosiumFrameMaterial,
    CosiumLensFocusCategory,
    CosiumLensFocusType,
    CosiumLensMaterial,
    CosiumMutuelle,
    CosiumSite,
    CosiumSupplier,
    CosiumTag,
    CosiumUser,
)
from app.models.devis import Devis, DevisLigne  # noqa: F401
from app.models.document import Document, DocumentType  # noqa: F401
from app.models.document_extraction import DocumentExtraction  # noqa: F401
from app.models.facture import Facture, FactureLigne  # noqa: F401
from app.models.interaction import Interaction  # noqa: F401
from app.models.marketing import Campaign, MarketingConsent, MessageLog, Segment, SegmentMembership  # noqa: F401
from app.models.notification import ActionItem, Notification  # noqa: F401
from app.models.ocam_operator import OcamOperator  # noqa: F401
from app.models.payment import BankTransaction, Payment  # noqa: F401
from app.models.pec import PayerContract, PayerOrganization, PecRequest, PecStatusHistory, Relance  # noqa: F401
from app.models.pec_audit import PecAuditEntry  # noqa: F401
from app.models.pec_preparation import PecPreparation, PecPreparationDocument  # noqa: F401
from app.models.push_subscription import PushSubscription  # noqa: F401
from app.models.reconciliation import DossierReconciliation  # noqa: F401
from app.models.reminder import Reminder, ReminderPlan, ReminderTemplate  # noqa: F401
from app.models.tenant import Organization, Tenant, TenantErpCredentials, TenantUser  # noqa: F401
from app.models.user import PasswordResetToken, RefreshToken, User  # noqa: F401
