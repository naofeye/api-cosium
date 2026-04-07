from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valeurs par defaut UNIQUEMENT pour dev local — jamais en production
_DEV_DB_URL = "postgresql+psycopg://optiflow:optiflow@postgres:5432/optiflow"
_DEV_JWT_SECRET = "dev-only-change-me-super-secret"
_DEV_S3_KEY = "minioadmin"


class Settings(BaseSettings):
    # App
    app_env: str = "local"

    # Database
    database_url: str = _DEV_DB_URL

    # Auth
    jwt_secret: str = _DEV_JWT_SECRET
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Storage (MinIO/S3)
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = _DEV_S3_KEY
    s3_secret_key: str = _DEV_S3_KEY
    s3_bucket: str = "optiflow-docs"

    # Redis / Celery
    redis_url: str = "redis://redis:6379/0"

    # Email (Mailhog)
    mailhog_smtp_host: str = "mailhog"
    mailhog_smtp_port: int = 1025

    # Monitoring
    sentry_dsn: str = ""

    # IA (Anthropic)
    anthropic_api_key: str = ""
    ai_model: str = "claude-haiku-4-5-20251001"

    # Stripe (Facturation SaaS)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_solo: str = ""
    stripe_price_reseau: str = ""
    stripe_price_ia_pro: str = ""

    # Upload
    max_upload_size_mb: int = 20

    # Encryption
    encryption_key: str = ""

    # Cosium API (LECTURE SEULE)
    cosium_base_url: str = "https://c1.cosium.biz"
    cosium_tenant: str = ""
    cosium_login: str = ""
    cosium_password: str = ""
    cosium_oidc_token_url: str = ""
    cosium_oidc_client_id: str = ""
    cosium_access_token: str = ""  # Cookie access_token from browser
    cosium_device_credential: str = ""  # Cookie device-credential from browser

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """Refuse les valeurs par defaut dangereuses en production/staging."""
        if self.app_env in ("production", "staging"):
            errors: list[str] = []
            if self.jwt_secret == _DEV_JWT_SECRET or "change-me" in self.jwt_secret:
                errors.append("JWT_SECRET doit etre defini avec une valeur securisee")
            if self.s3_access_key == _DEV_S3_KEY:
                errors.append("S3_ACCESS_KEY/S3_SECRET_KEY ne doivent pas etre 'minioadmin'")
            if not self.encryption_key:
                errors.append("ENCRYPTION_KEY est obligatoire (generer avec: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\")")
            if self.database_url == _DEV_DB_URL:
                errors.append("DATABASE_URL doit utiliser des credentials securises")
            if "*" in self.cors_origins:
                errors.append("CORS_ORIGINS ne doit pas contenir '*' en production")
            if errors:
                raise ValueError(
                    f"Configuration invalide pour {self.app_env} :\n- " + "\n- ".join(errors)
                )
        return self


settings = Settings()
