# ABOUTME: Restricts Seren-funded services to the Seren gateway.
# ABOUTME: Refuses requests when the shared gateway credential is absent or wrong.

import hmac

from fastapi import Header, HTTPException

from .config import get_settings


def require_gateway_secret(x_seren_gateway_secret: str | None = Header(None)) -> None:
    """Authenticate the gateway before allowing a paid service operation."""
    expected = get_settings().gateway_secret
    if not expected:
        raise HTTPException(status_code=503, detail="Gateway access is not configured")
    if x_seren_gateway_secret is None or not hmac.compare_digest(
        x_seren_gateway_secret.encode("utf-8"), expected.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid gateway credential")
