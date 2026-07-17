from functools import lru_cache

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
    # Keep true for local/dev testing; set false in production once Brevo is live
    include_verification_code_in_response: bool = True

    # Brevo transactional email
    brevo_api_key: str = ""
    brevo_sender_email: str = ""
    brevo_sender_name: str = "Lively"


@lru_cache
def get_settings() -> Settings:
    return Settings()
