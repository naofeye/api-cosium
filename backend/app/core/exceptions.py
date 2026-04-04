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
