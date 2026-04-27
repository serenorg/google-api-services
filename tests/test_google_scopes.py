# Critical regression test for serenorg/google-api-services#18.
#
# The OAuth scope list minted by the auth service must include every scope
# required by a deployed publisher in this repo. Drive/Docs publishers were
# returning ACCESS_TOKEN_SCOPE_INSUFFICIENT on DriveFiles.List because the
# auth service was minting Gmail/Calendar-only tokens. This test fails if a
# future scope removal breaks Drive discovery, Drive export, or Docs reads.

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


REQUIRED_SCOPES = {
    # Gmail publisher
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.modify",
    # Calendar publisher
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
    # Drive publisher — files.list discovery (issue #18)
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    # Drive publisher — files.export content download (issue #18)
    "https://www.googleapis.com/auth/drive.readonly",
    # Docs publisher — documents.get by document ID (issue #18)
    "https://www.googleapis.com/auth/documents.readonly",
}


class GoogleScopesCoverageTests(unittest.TestCase):
    def test_settings_google_scopes_covers_all_deployed_publishers(self):
        # Provide the env vars Settings() requires so import succeeds.
        import os

        os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client")
        os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-secret")
        os.environ.setdefault("DATABASE_URL", "postgresql://test")
        os.environ.setdefault("TOKEN_ENCRYPTION_KEY", "x" * 44)

        from config import Settings  # type: ignore[import-not-found]

        scopes = set(Settings().google_scopes.split())
        missing = REQUIRED_SCOPES - scopes
        self.assertEqual(
            missing,
            set(),
            "Settings.google_scopes is missing scopes required by deployed "
            f"publishers (would re-introduce ACCESS_TOKEN_SCOPE_INSUFFICIENT): {sorted(missing)}",
        )


if __name__ == "__main__":
    unittest.main()
