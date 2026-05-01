from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Valeurs par defaut UNIQUEMENT pour dev local — jamais en production
_DEV_DB_URL = "postgresql+psycopg://optiflow:optiflow@postgres:5432/optiflow"
_DEV_JWT_SECRET = "dev-only-change-me-super-secret"
_DEV_S3_KEY = "minioadmin"

_VALID_APP_ENVS = ("local", "development", "test", "staging", "production")


class Settings(BaseSettings):
    # App
    app_env: str = "local"

    # Database
    database_url: str = _DEV_DB_URL
    # Pool sizing pour 50 tenants concurrents :
    # - API: pool_size=20 + max_overflow=30 → 50 connexions max par worker uvicorn
    # - Worker Celery: meme pool (concurrency=2 → 100 connexions au pire cas)
    # - Postgres max_connections=150 (docker-compose) supporte ce trafic
    # Tuner a la hausse si SLO p95 > 500ms ET pool wait > 5s observe (Sentry).
    database_pool_size: int = 20
    database_max_overflow: int = 30
    database_pool_recycle_seconds: int = 1800
    database_pool_timeout_seconds: int = 30

    # Auth
    jwt_secret: str = _DEV_JWT_SECRET
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: str = "http://localhost:3000"

    # URL publique du frontend (pour les liens dans les emails : reset password,
    # validation email, devis envoyes au client). Si vide, on prend le premier
    # cors_origins par fallback (peu fiable car peut etre ordonne arbitrairement).
    frontend_base_url: str = ""

    # Trusted proxies (CSV) — IPs autorisees a faire confiance au header X-Forwarded-For
    # Vide par defaut : on n'accepte JAMAIS X-Forwarded-For sans config explicite
    # En prod derriere nginx : "127.0.0.1" suffit ; en docker compose, ajouter l'IP du proxy
    trusted_proxies: str = ""

    # Storage (MinIO/S3)
    s3_endpoint: str = "http://minio:9000"
    # Endpoint utilise UNIQUEMENT pour les URLs presignees servies au navigateur.
    # `s3_endpoint` (interne Docker) n'est pas resolvable depuis l'exterieur ;
    # en prod, mettre ici l'URL HTTPS publique exposee par le reverse-proxy.
    # Si vide, on retombe sur s3_endpoint (utile en dev local).
    s3_public_endpoint: str = ""
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

    # Runtime flags
    seed_on_startup: bool = True  # Seeding auto en dev (desactiver avec SEED_ON_STARTUP=false)
    celery_worker: bool = False  # True si execute dans un worker Celery (CELERY_WORKER=true)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def _validate_app_env(self) -> "Settings":
        """Refuse tout boot avec un APP_ENV inconnu.

        Garde-fou : empeche un typo (`APP_ENV=prod` au lieu de `production`) de retomber
        silencieusement sur les defauts dev. La valeur doit explicitement faire partie de
        `_VALID_APP_ENVS`, sinon le boot echoue immediatement.
        """
        if self.app_env not in _VALID_APP_ENVS:
            raise ValueError(
                f"APP_ENV invalide : '{self.app_env}'. "
                f"Valeurs autorisees : {', '.join(_VALID_APP_ENVS)}"
            )
        return self

    @model_validator(mode="after")
    def _validate_production_secrets(self) -> "Settings":
        """Refuse les valeurs par defaut dangereuses en production/staging."""
        if self.app_env in ("production", "staging"):
            errors: list[str] = []
            if self.jwt_secret == _DEV_JWT_SECRET or "change-me" in self.jwt_secret:
                errors.append("JWT_SECRET doit etre defini avec une valeur securisee")
            if len(self.jwt_secret) < 32:
                errors.append("JWT_SECRET doit faire au moins 32 caracteres (HS256 requires 256 bits)")
            if self.s3_access_key == _DEV_S3_KEY or self.s3_secret_key == _DEV_S3_KEY:
                errors.append("S3_ACCESS_KEY/S3_SECRET_KEY ne doivent pas etre 'minioadmin'")
            if not self.encryption_key:
                errors.append("ENCRYPTION_KEY est obligatoire (generer avec: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\")")
            if self.database_url == _DEV_DB_URL:
                errors.append("DATABASE_URL doit utiliser des credentials securises")
            if self.database_pool_size > 50:
                errors.append("DATABASE_POOL_SIZE ne doit pas depasser 50 sans justification explicite")
            if "*" in self.cors_origins:
                errors.append("CORS_ORIGINS ne doit pas contenir '*' en production")
            if errors:
                raise ValueError(
                    f"Configuration invalide pour {self.app_env} :\n- " + "\n- ".join(errors)
                )
        return self


settings = Settings()
