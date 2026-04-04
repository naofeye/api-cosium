# Re-export all models for backward compatibility
# Usage: from app.models import User, Case, etc.

from app.models.ai import AiUsageLog  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.case import Case  # noqa: F401
from app.models.client import Customer  # noqa: F401
from app.models.devis import Devis, DevisLigne  # noqa: F401
from app.models.document import Document, DocumentType  # noqa: F401
from app.models.facture import Facture, FactureLigne  # noqa: F401
from app.models.interaction import Interaction  # noqa: F401
from app.models.marketing import Campaign, MarketingConsent, MessageLog, Segment, SegmentMembership  # noqa: F401
from app.models.notification import ActionItem, Notification  # noqa: F401
from app.models.payment import BankTransaction, Payment  # noqa: F401
from app.models.pec import PayerContract, PayerOrganization, PecRequest, PecStatusHistory, Relance  # noqa: F401
from app.models.reminder import Reminder, ReminderPlan, ReminderTemplate  # noqa: F401
from app.models.tenant import Organization, Tenant, TenantErpCredentials, TenantUser  # noqa: F401
from app.models.user import PasswordResetToken, RefreshToken, User  # noqa: F401
