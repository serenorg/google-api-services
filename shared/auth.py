# ABOUTME: OAuth authentication utilities for Google API services.
# ABOUTME: Handles token extraction from headers and token refresh.

import httpx
from fastapi import HTTPException, Header
from typing import Optional

from .config import get_settings


def get_token_from_header(authorization: Optional[str] = Header(None)) -> str:
    """
    Extract Bearer token from Authorization header.

    Args:
        authorization: The Authorization header value

    Returns:
        The access token string

    Raises:
        HTTPException: If header is missing or malformed
    """
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Missing Authorization header"
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Invalid Authorization header format. Expected: Bearer <token>"
        )

    return parts[1]


async def refresh_access_token(
    refresh_token: str,
    client_id: str,
    client_secret: str
) -> dict:
    """
    Refresh an expired Google OAuth access token.

    Args:
        refresh_token: The refresh token
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret

    Returns:
        Dict containing new access_token and expires_in

    Raises:
        HTTPException: If token refresh fails
    """
    settings = get_settings()

    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.google_token_url,
            data={
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=settings.request_timeout,
        )

        if response.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail=f"Token refresh failed: {response.text}"
            )

        return response.json()
