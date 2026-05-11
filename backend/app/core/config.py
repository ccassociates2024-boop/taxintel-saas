from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Core ──────────────────────────────────────────────────────────────────
    app_env: str = Field(default="local", alias="APP_ENV")
    base_url: str = Field(default="http://localhost:8000", alias="BASE_URL")
    database_url: str = Field(alias="DATABASE_URL")
    jwt_secret: str = Field(alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=720, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")
    max_upload_mb: int = Field(default=25, alias="MAX_UPLOAD_MB")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4.1", alias="OPENAI_MODEL")
    enable_openai: bool = Field(default=True, alias="ENABLE_OPENAI")

    # ── Observability ─────────────────────────────────────────────────────────
    sentry_dsn: str | None = Field(default=None, alias="SENTRY_DSN")

    # ── Redis / Worker ────────────────────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")

    # ── Object Storage (S3 / MinIO / R2) ─────────────────────────────────────
    s3_endpoint_url: str | None = Field(default=None, alias="S3_ENDPOINT_URL")
    s3_region: str = Field(default="ap-south-1", alias="S3_REGION")
    s3_bucket: str = Field(default="taxintel-local", alias="S3_BUCKET")
    s3_access_key: str = Field(default="minioadmin", alias="S3_ACCESS_KEY")
    s3_secret_key: str = Field(default="minioadmin", alias="S3_SECRET_KEY")

    # ── PII Encryption ────────────────────────────────────────────────────────
    pii_encryption_key: str | None = Field(default=None, alias="PII_ENCRYPTION_KEY")

    # ── Razorpay (Phase 1B) ───────────────────────────────────────────────────
    razorpay_key_id: str | None = Field(default=None, alias="RAZORPAY_KEY_ID")
    razorpay_key_secret: str | None = Field(default=None, alias="RAZORPAY_KEY_SECRET")
    razorpay_webhook_secret: str | None = Field(default=None, alias="RAZORPAY_WEBHOOK_SECRET")
    # Razorpay plan IDs (create once in Razorpay dashboard, paste here)
    razorpay_plan_pro: str | None = Field(default=None, alias="RAZORPAY_PLAN_PRO")
    razorpay_plan_enterprise: str | None = Field(default=None, alias="RAZORPAY_PLAN_ENTERPRISE")

    # ── Digio e-sign (Phase 1C) ───────────────────────────────────────────────
    digio_client_id: str | None = Field(default=None, alias="DIGIO_CLIENT_ID")
    digio_client_secret: str | None = Field(default=None, alias="DIGIO_CLIENT_SECRET")
    digio_webhook_secret: str | None = Field(default=None, alias="DIGIO_WEBHOOK_SECRET")
    digio_base_url: str = Field(default="https://api.digio.in", alias="DIGIO_BASE_URL")

    # ── DigiLocker OAuth (Phase 1D) ───────────────────────────────────────────
    digilocker_client_id: str | None = Field(default=None, alias="DIGILOCKER_CLIENT_ID")
    digilocker_client_secret: str | None = Field(default=None, alias="DIGILOCKER_CLIENT_SECRET")
    digilocker_redirect_uri: str = Field(
        default="http://localhost:8000/api/v1/digilocker/callback",
        alias="DIGILOCKER_REDIRECT_URI",
    )

    # ── WhatsApp / Meta Cloud API (Phase 1E) ──────────────────────────────────
    meta_app_secret: str | None = Field(default=None, alias="META_APP_SECRET")
    meta_whatsapp_token: str | None = Field(default=None, alias="META_WHATSAPP_TOKEN")
    meta_phone_number_id: str | None = Field(default=None, alias="META_PHONE_NUMBER_ID")
    meta_verify_token: str | None = Field(default=None, alias="META_VERIFY_TOKEN")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def json_logs(self) -> bool:
        return self.app_env != "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
