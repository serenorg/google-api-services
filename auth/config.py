# ABOUTME: Configuration settings for the auth service.
# ABOUTME: Manages Google OAuth credentials and database connection.

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Auth service settings loaded from environment variables."""

    # Logging
    log_level: str = "INFO"

    # Google OAuth credentials
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8003/auth/google/callback"

    # Google OAuth endpoints
    google_auth_url: str = "https://accounts.google.com/o/oauth2/v2/auth"
    google_token_url: str = "https://oauth2.googleapis.com/token"
    google_userinfo_url: str = "https://www.googleapis.com/oauth2/v2/userinfo"

    # OAuth scopes for Gmail and Calendar
    google_scopes: str = (
        "openid email profile "
        "https://www.googleapis.com/auth/gmail.readonly "
        "https://www.googleapis.com/auth/gmail.send "
        "https://www.googleapis.com/auth/gmail.modify "
        "https://www.googleapis.com/auth/calendar "
        "https://www.googleapis.com/auth/calendar.events"
    )

    # Database for token storage
    database_url: str

    # Encryption key for refresh tokens (32 bytes, base64 encoded)
    token_encryption_key: str

    # Seren API for validating API keys
    seren_api_url: str = "https://api.serendb.com"

    # Request timeout (seconds)
    request_timeout: int = 30

    # Access token lifetime (seconds) - slightly less than Google's 1 hour
    access_token_lifetime: int = 3500

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
