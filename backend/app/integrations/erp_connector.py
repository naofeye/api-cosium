"""Interface abstraite ERPConnector — contrat que tout connecteur ERP doit respecter.

REGLES DE SECURITE :
- Tous les connecteurs sont LECTURE SEULE (sauf authenticate)
- Aucune methode d'ecriture (put, post, delete, patch) ne doit exister
- La synchronisation est UNIDIRECTIONNELLE : ERP -> OptiFlow
"""

from abc import ABC, abstractmethod

from app.integrations.erp_models import (
    ERPCustomer,
    ERPInvoice,
    ERPPaymentType,
    ERPProduct,
    ERPStock,
)


class ERPConnector(ABC):
    """Interface abstraite pour les connecteurs ERP optiques.

    Tout connecteur (Cosium, Icanopee, Hexaoptic, etc.) DOIT implementer
    cette interface. Les methodes retournent des modeles generiques ERPxxx.
    """

    @abstractmethod
    def authenticate(self, base_url: str, tenant: str, login: str, password: str) -> str:
        """Authentification aupres de l'ERP. Retourne un token."""
        ...

    @abstractmethod
    def get_customers(self, page: int = 0, page_size: int = 100) -> list[ERPCustomer]:
        """Liste les clients de l'ERP (pagine)."""
        ...

    @abstractmethod
    def get_invoices(self, page: int = 0, page_size: int = 100) -> list[ERPInvoice]:
        """Liste les factures/devis de l'ERP (pagine)."""
        ...

    @abstractmethod
    def get_invoiced_items(self, invoice_erp_id: str) -> list[dict]:
        """Retourne les lignes detaillees d'une facture."""
        ...

    @abstractmethod
    def get_products(self, page: int = 0, page_size: int = 100) -> list[ERPProduct]:
        """Liste les produits du catalogue ERP."""
        ...

    @abstractmethod
    def get_product_stock(self, product_erp_id: str) -> list[ERPStock]:
        """Retourne les stocks d'un produit par site."""
        ...

    @abstractmethod
    def get_payment_types(self) -> list[ERPPaymentType]:
        """Liste les moyens de paiement acceptes."""
        ...

    @property
    @abstractmethod
    def erp_type(self) -> str:
        """Identifiant du type d'ERP (ex: 'cosium', 'icanopee')."""
        ...

    @property
    @abstractmethod
    def is_authenticated(self) -> bool:
        """Indique si le connecteur est authentifie."""
        ...
