# ABOUTME: Compares the Seren Gateway's live Google OAuth provider record with
# ABOUTME: auth/config.py so scope drift between the two sign-in paths is caught.
"""Check the Gateway's Google OAuth provider scopes against auth/config.py.

The record must hold exactly ``Settings.google_scopes`` plus
``GATEWAY_ONLY_SCOPES``. Anything else is drift: a scope the Gateway lacks
means Gateway sign-ins get less than ``/auth/google``; an unlisted extra
scope means ``/auth/google`` sign-ins silently get less than the Gateway.

Usage (from the repository root)::

    SEREN_API_KEY=... python3 auth/scope_check.py

Exit codes: 0 in sync, 1 drift, 2 the record could not be read.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Callable, Iterable

DEFAULT_PROVIDER_ID = "c95d05fb-3a93-4499-aa12-d108cde0424b"
DEFAULT_SEREN_API_URL = "https://api.serendb.com"

# Google reports the identity scopes under their long names in some places.
_SCOPE_ALIASES = {
    "https://www.googleapis.com/auth/userinfo.email": "email",
    "https://www.googleapis.com/auth/userinfo.profile": "profile",
}


def normalize_scope(scope: str) -> str:
    scope = scope.strip()
    return _SCOPE_ALIASES.get(scope, scope)


def normalize_scopes(scopes: Iterable[str]) -> set[str]:
    return {normalize_scope(s) for s in scopes if s.strip()}


@dataclass
class ScopeDrift:
    """Differences between the Gateway record and what it should hold."""

    missing_from_gateway: set[str] = field(default_factory=set)
    unexpected_in_gateway: set[str] = field(default_factory=set)

    @property
    def in_sync(self) -> bool:
        return not self.missing_from_gateway and not self.unexpected_in_gateway

    def report(self) -> str:
        if self.in_sync:
            return "Gateway Google OAuth scopes match auth/config.py."
        lines = ["Gateway Google OAuth scopes differ from auth/config.py:"]
        for scope in sorted(self.missing_from_gateway):
            lines.append(f"  missing from the Gateway record: {scope}")
        for scope in sorted(self.unexpected_in_gateway):
            lines.append(
                f"  in the Gateway record but not in google_scopes or "
                f"GATEWAY_ONLY_SCOPES: {scope}"
            )
        return "\n".join(lines)


def compare_scopes(
    gateway_scopes: Iterable[str],
    configured_scopes: Iterable[str],
    gateway_only_scopes: Iterable[str],
) -> ScopeDrift:
    gateway = normalize_scopes(gateway_scopes)
    expected = normalize_scopes(configured_scopes) | normalize_scopes(gateway_only_scopes)
    return ScopeDrift(
        missing_from_gateway=expected - gateway,
        unexpected_in_gateway=gateway - expected,
    )


def extract_provider_scopes(payload: object, provider_id: str) -> list[str]:
    """Pull one provider's scopes out of a ``GET /oauth/providers`` body.

    Accepts ``{"providers": [...]}``, a ``{"data": ...}`` wrapper around
    that, or a bare list. Scopes may be a list or a space-separated string.
    """
    if isinstance(payload, dict) and "data" in payload:
        payload = payload["data"]
    if isinstance(payload, dict) and "providers" in payload:
        payload = payload["providers"]
    if not isinstance(payload, list):
        raise ValueError("unexpected /oauth/providers response shape")
    for provider in payload:
        if isinstance(provider, dict) and str(provider.get("id")) == provider_id:
            scopes = provider.get("scopes")
            if isinstance(scopes, str):
                return scopes.split()
            if isinstance(scopes, list) and all(isinstance(s, str) for s in scopes):
                return scopes
            raise ValueError(f"provider {provider_id} has no readable scopes")
    raise LookupError(f"provider {provider_id} not found in /oauth/providers")


def fetch_providers(api_url: str, api_key: str, timeout: int = 30) -> object:
    request = urllib.request.Request(
        f"{api_url.rstrip('/')}/oauth/providers",
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def configured_scopes() -> tuple[list[str], list[str]]:
    """Return (Settings.google_scopes, GATEWAY_ONLY_SCOPES) from config.py."""
    # Settings requires runtime secrets this offline check never uses.
    for name, value in (
        ("GOOGLE_CLIENT_ID", "scope-check"),
        ("GOOGLE_CLIENT_SECRET", "scope-check"),
        ("DATABASE_URL", "postgresql://scope-check"),
        ("TOKEN_ENCRYPTION_KEY", "x" * 44),
    ):
        os.environ.setdefault(name, value)
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from config import GATEWAY_ONLY_SCOPES, Settings  # type: ignore[import-not-found]

    return Settings().google_scopes.split(), list(GATEWAY_ONLY_SCOPES)


def main(
    env: dict[str, str] | None = None,
    fetch: Callable[[str, str], object] = fetch_providers,
    out=sys.stdout,
) -> int:
    env = dict(os.environ) if env is None else env
    api_key = env.get("SEREN_API_KEY", "")
    if not api_key:
        print("SEREN_API_KEY is not set; cannot read the Gateway record.", file=out)
        return 2
    api_url = env.get("SEREN_API_URL", DEFAULT_SEREN_API_URL)
    provider_id = env.get("GOOGLE_OAUTH_PROVIDER_ID", DEFAULT_PROVIDER_ID)
    try:
        gateway = extract_provider_scopes(fetch(api_url, api_key), provider_id)
    except (urllib.error.URLError, OSError, ValueError, LookupError) as exc:
        print(f"Could not read the Gateway record: {exc}", file=out)
        return 2
    configured, gateway_only = configured_scopes()
    drift = compare_scopes(gateway, configured, gateway_only)
    print(drift.report(), file=out)
    return 0 if drift.in_sync else 1


if __name__ == "__main__":
    sys.exit(main())
