from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    app_env: str = "local"

    # Database
    database_url: str = "postgresql+psycopg://optiflow:optiflow@postgres:5432/optiflow"

    # Auth
    jwt_secret: str = "change-me-super-secret"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: str = "http://localhost:3000"

    # Storage (MinIO/S3)
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
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

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
