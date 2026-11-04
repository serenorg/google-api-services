# ABOUTME: Configuration settings for the auth service.
# ABOUTME: Manages Google OAuth credentials and database connection.

from functools import lru_cache
from pydantic_settings import BaseSettings


# Scopes the Seren Gateway's Google OAuth provider record
# (c95d05fb-3a93-4499-aa12-d108cde0424b) requests on top of
# Settings.google_scopes. This difference is intended and permanent: the two
# sign-in paths are not expected to match. The Gateway keeps these scopes
# because live consumers need them, and /auth/google does not request them.
# Any scope added to Settings.google_scopes must be declared on the consent
# screen first, because Google silently substitutes another scope for an
# undeclared one. auth/scope_check.py fails when the live record differs from
# Settings.google_scopes plus exactly these scopes.
GATEWAY_ONLY_SCOPES: dict[str, str] = {
    "https://www.googleapis.com/auth/drive.readonly": (
        "seren-core Employee hires require it (scopes_sufficient in "
        "managed_agent_hires.rs)"
    ),
    "https://www.googleapis.com/auth/contacts.other.readonly": (
        "google-contacts GET /otherContacts returns 403 without it"
    ),
    "https://www.googleapis.com/auth/presentations": (
        "google-slides publisher, which uses the same Gateway provider"
    ),
}


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

    # OAuth scopes for Gmail, Calendar, Contacts, Sheets, Docs, and Drive.
    # Every scope below is declared and approved on the production OAuth
    # consent screen. Requesting an undeclared scope causes Google to
    # silently substitute a different (declared) scope at consent time
    # (issue #25). Drive access is per-file via the Drive Picker UI
    # (drive.file), which needs no consent-screen declaration.
    # This string is the single source of truth for what /auth/google
    # requests: the Seren Gateway's Google OAuth provider record must hold it
    # plus GATEWAY_ONLY_SCOPES, and the README "OAuth Scopes" section is
    # checked against it.
    google_scopes: str = (
        "openid email profile "
        "https://www.googleapis.com/auth/gmail.readonly "
        "https://www.googleapis.com/auth/gmail.send "
        "https://www.googleapis.com/auth/gmail.modify "
        "https://www.googleapis.com/auth/calendar "
        "https://www.googleapis.com/auth/calendar.events "
        "https://www.googleapis.com/auth/contacts.readonly "
        "https://www.googleapis.com/auth/spreadsheets "
        "https://www.googleapis.com/auth/documents "
        "https://www.googleapis.com/auth/drive.file"
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
