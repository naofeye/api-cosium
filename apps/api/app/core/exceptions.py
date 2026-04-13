class BusinessError(Exception):
    def __init__(self, message: str, code: str = "BUSINESS_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)

    def to_dict(self) -> dict:
        return {"error": {"code": self.code, "message": self.message}}


class NotFoundError(BusinessError):
    def __init__(self, entity: str, entity_id: int | str) -> None:
        self.entity = entity
        self.entity_id = entity_id
        super().__init__(
            message=f"{entity} avec l'id {entity_id} introuvable",
            code="NOT_FOUND",
        )


class AuthenticationError(BusinessError):
    def __init__(self, message: str = "Identifiants invalides") -> None:
        super().__init__(message=message, code="AUTHENTICATION_ERROR")


class ForbiddenError(BusinessError):
    def __init__(self, message: str = "Acces refuse") -> None:
        super().__init__(message=message, code="FORBIDDEN")


class ValidationError(BusinessError):
    def __init__(self, field: str, message: str) -> None:
        self.field = field
        super().__init__(
            message=f"Erreur de validation sur '{field}' : {message}",
            code="VALIDATION_ERROR",
        )

    def to_dict(self) -> dict:
        return {"error": {"code": self.code, "message": self.message, "field": self.field}}


class SyncError(BusinessError):
    """Erreur lors de la synchronisation ERP."""

    def __init__(self, message: str, source: str = "") -> None:
        self.source = source
        super().__init__(message=message, code="SYNC_ERROR")


class ExtractionError(BusinessError):
    """Erreur lors de l'extraction de donnees d'un document."""

    def __init__(self, message: str, document_id: int | str = "") -> None:
        self.document_id = document_id
        super().__init__(message=message, code="EXTRACTION_ERROR")


class ImportDataError(BusinessError):
    """Erreur lors de l'import de donnees."""

    def __init__(self, message: str, source: str = "") -> None:
        self.source = source
        super().__init__(message=message, code="IMPORT_ERROR")


class ExportError(BusinessError):
    """Erreur lors de l'export de donnees."""

    def __init__(self, message: str, format: str = "") -> None:
        self.format = format
        super().__init__(message=message, code="EXPORT_ERROR")


class MergeConflictError(BusinessError):
    """Conflit lors de la fusion de deux entites."""

    def __init__(self, message: str, entity_type: str = "") -> None:
        self.entity_type = entity_type
        super().__init__(message=message, code="MERGE_CONFLICT")


class ExternalServiceError(BusinessError):
    """Erreur lors d'un appel a un service externe."""

    def __init__(self, message: str, service: str = "") -> None:
        self.service = service
        super().__init__(message=message, code="EXTERNAL_SERVICE_ERROR")
