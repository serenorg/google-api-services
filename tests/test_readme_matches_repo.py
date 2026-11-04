# Regression test for serenorg/google-api-services#14.
#
# auth/config.py:Settings.google_scopes is the single source of truth for
# the Google OAuth scopes this repo requests. The README must document
# exactly that set, and its services table must list every service that
# docker-compose.yml runs, so the docs cannot silently drift from what is
# deployed.

from __future__ import annotations

import os
import pathlib
import re
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
AUTH_DIR = REPO_ROOT / "auth"
README = REPO_ROOT / "README.md"
COMPOSE = REPO_ROOT / "docker-compose.yml"

if str(AUTH_DIR) not in sys.path:
    sys.path.insert(0, str(AUTH_DIR))

# OpenID Connect identity scopes, not Google API scopes; the README's
# OAuth Scopes section documents API scopes only.
IDENTITY_SCOPES = {"openid", "email", "profile"}

# docker-compose services that are infrastructure, not this repo's code.
NON_SERVICE_COMPOSE_ENTRIES = {"postgres"}


def _readme_section(title: str) -> str:
    text = README.read_text()
    match = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    if match is None:
        raise AssertionError(f"README.md has no '## {title}' section")
    return match.group(1)


def _compose_services() -> dict[str, str]:
    """Map each docker-compose service name to its published host port."""
    services: dict[str, str] = {}
    current = None
    in_services = False
    for line in COMPOSE.read_text().splitlines():
        if re.match(r"^services:\s*$", line):
            in_services = True
            continue
        if in_services and re.match(r"^\S", line):
            in_services = False
        if not in_services:
            continue
        name = re.match(r"^  ([a-z][\w-]*):\s*$", line)
        if name:
            current = name.group(1)
            continue
        port = re.match(r'^\s+- "(\d+):\d+"', line)
        if port and current and current not in services:
            services[current] = port.group(1)
    return services


class ReadmeMatchesRepoTests(unittest.TestCase):
    def test_readme_scopes_match_config(self):
        os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client")
        os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-secret")
        os.environ.setdefault("DATABASE_URL", "postgresql://test")
        os.environ.setdefault("TOKEN_ENCRYPTION_KEY", "x" * 44)
        from config import Settings  # type: ignore[import-not-found]

        config_scopes = set(Settings().google_scopes.split()) - IDENTITY_SCOPES
        section = _readme_section("OAuth Scopes")
        readme_scopes = set(
            re.findall(r"^- `(https://www\.googleapis\.com/auth/[^`]+)`", section, re.M)
        )
        self.assertEqual(
            readme_scopes,
            config_scopes,
            "README 'OAuth Scopes' must list exactly auth/config.py google_scopes "
            f"(missing from README: {sorted(config_scopes - readme_scopes)}; "
            f"not in config: {sorted(readme_scopes - config_scopes)})",
        )

    def test_readme_services_table_lists_every_compose_service(self):
        services = {
            name: port
            for name, port in _compose_services().items()
            if name not in NON_SERVICE_COMPOSE_ENTRIES
        }
        self.assertGreaterEqual(len(services), 6, f"parsed too few services: {services}")

        table = _readme_section("Services")
        rows = {}
        for row in re.findall(r"^\|(.+)\|\s*$", table, re.M):
            cells = [c.strip() for c in row.split("|")]
            if len(cells) >= 2 and cells[1].isdigit():
                rows[cells[1]] = cells[0]

        missing = {
            name: port for name, port in services.items() if port not in rows
        }
        self.assertEqual(
            missing,
            {},
            "README 'Services' table is missing docker-compose services "
            "(name: host port)",
        )
        for name, port in services.items():
            self.assertIn(
                name.lower(),
                rows[port].lower(),
                f"README 'Services' row for port {port} should name the '{name}' service",
            )


if __name__ == "__main__":
    unittest.main()
