from functools import lru_cache
from typing import Literal

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Lively API"
    app_env: str = "development"
    debug: bool = True
    api_v1_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/lively"

    jwt_secret_key: str = "change-me-to-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24 * 7

    verification_code_expire_minutes: int = 15
    verification_code_length: int = 4
    # Keep true for local/dev testing; set false in production once email is live
    include_verification_code_in_response: bool = True

    # Family invite codes: alphanumeric (readable alphabet) or numeric (digits only)
    invite_code_format: Literal["alphanumeric", "numeric"] = "alphanumeric"
    invite_code_length: int = 6

    # Campaign Monitor transactional email
    campaign_monitor_api_key: str = ""
    campaign_monitor_sender_email: str = ""
    campaign_monitor_sender_name: str = "Lively"
    campaign_monitor_client_id: str = ""

    @field_validator("invite_code_format", mode="before")
    @classmethod
    def normalize_invite_code_format(cls, value: object) -> str:
        if value is None or value == "":
            return "alphanumeric"
        normalized = str(value).strip().lower()
        if normalized not in ("alphanumeric", "numeric"):
            raise ValueError("INVITE_CODE_FORMAT must be 'alphanumeric' or 'numeric'")
        return normalized

    @field_validator("invite_code_length")
    @classmethod
    def invite_code_length_positive(cls, value: int) -> int:
        if value < 1:
            raise ValueError("INVITE_CODE_LENGTH must be at least 1")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
