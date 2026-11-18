# ABOUTME: Configuration settings for Google API services.
# ABOUTME: Uses pydantic-settings for environment variable management.

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Logging
    log_level: str = "INFO"

    # Seren-funded services fail closed without a gateway credential.
    gateway_secret: str = ""
    google_ai_studio_api_key: str = ""
    gemini_image_model: str = "gemini-3-pro-image-preview"
    youtube_api_key: str = ""

    # Google API base URLs
    gmail_api_base: str = "https://gmail.googleapis.com/gmail/v1"
    calendar_api_base: str = "https://www.googleapis.com/calendar/v3"
    docs_api_base: str = "https://docs.googleapis.com/v1"
    sheets_api_base: str = "https://sheets.googleapis.com/v4"
    contacts_api_base: str = "https://people.googleapis.com/v1"

    # OAuth token refresh endpoint
    google_token_url: str = "https://oauth2.googleapis.com/token"

    # Request timeout (seconds)
    request_timeout: int = 30

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
