# Critical regression test for serenorg/google-api-services#25.
#
# The OAuth scope list minted by the auth service must only request scopes
# that are DECLARED on the Google consent screen for the production OAuth
# client. Requesting an undeclared scope causes Google to silently
# substitute a different (declared) scope at consent time — masking the
# fact that the user never granted what the code asked for.
#
# History:
#   - Issue #18 added drive.readonly + drive.metadata.readonly + documents.readonly
#     to fix ACCESS_TOKEN_SCOPE_INSUFFICIENT, but those scopes were never declared
#     on the consent screen, so Google silently downgraded to drive.file + documents.
#   - Issue #25 reconciles auth/config.py with the consent screen declaration.
#
# Future scope additions must EITHER be declared on the consent screen first
# OR ship as a separate change paired with the GCP declaration.

from __future__ import annotations

import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
AUTH_DIR = REPO_ROOT / "auth"

# The auth service's config.py is imported directly so the test runs without
# needing the rest of the FastAPI stack installed.
if str(AUTH_DIR) not in sys.path:
    sys.path.insert(0, str(AUTH_DIR))


# Scopes that MUST be present — declared on the consent screen and used
# by a deployed publisher in this repo.
REQUIRED_SCOPES = {
    # Gmail publisher
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    # Calendar publisher
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    # Contacts publisher
    "https://www.googleapis.com/auth/contacts.readonly",
    # Sheets publisher (full — declared on consent screen)
    "https://www.googleapis.com/auth/spreadsheets",
    # Docs publisher (full — declared on consent screen; client.py does
    # documents.create and documents.batchUpdate, so the readonly variant
    # would be insufficient).
    "https://www.googleapis.com/auth/documents",
    # Drive publisher — per-file access via Drive Picker UI.
    # drive.file requires no consent-screen declaration.
    "https://www.googleapis.com/auth/drive.file",
}

# Scopes that MUST NOT be present — these were requested by a prior
# revision but are not declared on the consent screen, so Google silently
# substituted them. Re-introducing them re-introduces the bug.
FORBIDDEN_SCOPES = {
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "https://www.googleapis.com/auth/documents.readonly",
}


class GoogleScopesConsentScreenAlignmentTests(unittest.TestCase):
    def setUp(self):
        # Provide the env vars Settings() requires so import succeeds.
        import os

        os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client")
        os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-secret")
        os.environ.setdefault("DATABASE_URL", "postgresql://test")
        os.environ.setdefault("TOKEN_ENCRYPTION_KEY", "x" * 44)

        from config import Settings  # type: ignore[import-not-found]

        self.scopes = set(Settings().google_scopes.split())

    def test_required_scopes_present(self):
        missing = REQUIRED_SCOPES - self.scopes
        self.assertEqual(
            missing,
            set(),
            "Settings.google_scopes is missing scopes required by deployed "
            f"publishers: {sorted(missing)}",
        )

    def test_undeclared_scopes_absent(self):
        # Re-requesting any of these without a consent-screen declaration
        # re-introduces issue #25 (silent scope downgrade).
        present_forbidden = FORBIDDEN_SCOPES & self.scopes
        self.assertEqual(
            present_forbidden,
            set(),
            "Settings.google_scopes requests scopes not declared on the "
            "Google consent screen — Google will silently downgrade these "
            f"and the granted token will not match: {sorted(present_forbidden)}",
        )


if __name__ == "__main__":
    unittest.main()
