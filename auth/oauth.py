# ABOUTME: Google OAuth flow implementation.
# ABOUTME: Handles authorization URL generation, token exchange, and refresh.

import secrets
from typing import Optional
from urllib.parse import urlencode

import httpx

from config import get_settings


class GoogleOAuth:
    """Google OAuth 2.0 implementation."""

    def __init__(self):
        self.settings = get_settings()

    def get_authorization_url(self, state: str) -> str:
        """Generate the Google OAuth authorization URL."""
        params = {
            "client_id": self.settings.google_client_id,
            "redirect_uri": self.settings.google_redirect_uri,
            "response_type": "code",
            "scope": self.settings.google_scopes,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Force consent to ensure refresh token
            "state": state,
        }
        return f"{self.settings.google_auth_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(self, code: str) -> dict:
        """Exchange authorization code for access and refresh tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.settings.google_token_url,
                data={
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.settings.google_redirect_uri,
                },
                timeout=self.settings.request_timeout,
            )
            response.raise_for_status()
            return response.json()

    async def refresh_access_token(self, refresh_token: str) -> dict:
        """Use refresh token to get a new access token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.settings.google_token_url,
                data={
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=self.settings.request_timeout,
            )
            response.raise_for_status()
            return response.json()

    async def get_user_info(self, access_token: str) -> dict:
        """Get user info from Google."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                self.settings.google_userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=self.settings.request_timeout,
            )
            response.raise_for_status()
            return response.json()

    @staticmethod
    def generate_state() -> str:
        """Generate a random state parameter for CSRF protection."""
        return secrets.token_urlsafe(32)
