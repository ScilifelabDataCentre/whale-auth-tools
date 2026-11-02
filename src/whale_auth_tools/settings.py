"""Application configuration loaded from environment variables."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings. Secrets intentionally have no development defaults."""

    model_config = SettingsConfigDict(case_sensitive=False, extra="ignore")

    api_token: str = Field(default="", validation_alias="WHALE_AUTH_API_TOKEN")
    altcha_hmac_secret: str = Field(default="", validation_alias="ALTCHA_HMAC_SECRET")
    altcha_hmac_key_secret: str = Field(
        default="", validation_alias="ALTCHA_HMAC_KEY_SECRET"
    )
    database_path: Path = Field(
        default=Path("./data/questionnaires.sqlite3"), validation_alias="DATABASE_PATH"
    )
    altcha_required: bool = Field(default=False, validation_alias="ALTCHA_REQUIRED")
    altcha_algorithm: str = Field(
        default="PBKDF2/SHA-256", validation_alias="ALTCHA_ALGORITHM"
    )
    altcha_cost: int = Field(default=5000, ge=1, validation_alias="ALTCHA_COST")
    altcha_ttl_seconds: int = Field(
        default=600, ge=30, le=3600, validation_alias="ALTCHA_TTL_SECONDS"
    )
    cors_origins: str = Field(default="", validation_alias="CORS_ORIGINS")
    docs_enabled: bool = Field(default=True, validation_alias="DOCS_ENABLED")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    def validate_secrets(self) -> None:
        missing = [
            name
            for name, value in {
                "WHALE_AUTH_API_TOKEN": self.api_token,
                "ALTCHA_HMAC_SECRET": self.altcha_hmac_secret,
                "ALTCHA_HMAC_KEY_SECRET": self.altcha_hmac_key_secret,
            }.items()
            if not value
        ]
        if missing:
            raise RuntimeError(f"Missing required configuration: {', '.join(missing)}")
