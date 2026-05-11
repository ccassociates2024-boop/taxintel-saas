from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "Indian AIS Parser Service"
    service_version: str = "1.0.0"
    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/tax_platform",
        alias="DATABASE_URL",
    )
    enable_ocr: bool = Field(default=True, alias="ENABLE_OCR")
    ocr_lang: str = Field(default="eng", alias="OCR_LANG")
    max_upload_mb: int = Field(default=25, alias="MAX_UPLOAD_MB")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", populate_by_name=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

