# Regression test for serenorg/google-api-services#29.
#
# The Seren Gateway's Google OAuth provider record requested 3 scopes that
# auth/config.py neither requests nor documents, and nothing detected it.
# auth/scope_check.py compares the live record with Settings.google_scopes
# plus the explicit GATEWAY_ONLY_SCOPES allowlist; these tests pin that
# comparison against the record as read in production on 2026-11-04.

from __future__ import annotations

import io
import os
import pathlib
import sys
import unittest

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
AUTH_DIR = REPO_ROOT / "auth"
if str(AUTH_DIR) not in sys.path:
    sys.path.insert(0, str(AUTH_DIR))

os.environ.setdefault("GOOGLE_CLIENT_ID", "test-client")
os.environ.setdefault("GOOGLE_CLIENT_SECRET", "test-secret")
os.environ.setdefault("DATABASE_URL", "postgresql://test")
os.environ.setdefault("TOKEN_ENCRYPTION_KEY", "x" * 44)

import scope_check  # type: ignore[import-not-found]  # noqa: E402
from config import GATEWAY_ONLY_SCOPES, Settings  # type: ignore[import-not-found]  # noqa: E402

PROVIDER_ID = scope_check.DEFAULT_PROVIDER_ID
G = "https://www.googleapis.com/auth/"

# GET /oauth/providers record c95d05fb-... as read on 2026-11-04 (issue #29).
LIVE_GATEWAY_SCOPES_2026_11_04 = [
    "openid",
    "email",
    "profile",
    G + "gmail.readonly",
    G + "gmail.send",
    G + "gmail.modify",
    G + "calendar",
    G + "calendar.events",
    G + "contacts.readonly",
    G + "contacts.other.readonly",
    G + "spreadsheets",
    G + "documents",
    G + "presentations",
    G + "drive.file",
    G + "drive.readonly",
]


def _configured():
    return Settings().google_scopes.split(), list(GATEWAY_ONLY_SCOPES)


class GatewayOnlyScopesTests(unittest.TestCase):
    def test_issue_29_scopes_are_listed_as_gateway_only(self):
        self.assertEqual(
            set(GATEWAY_ONLY_SCOPES),
            {G + "contacts.other.readonly", G + "presentations", G + "drive.readonly"},
        )
        for scope, reason in GATEWAY_ONLY_SCOPES.items():
            self.assertTrue(reason.strip(), f"{scope} needs a reason")

    def test_gateway_only_scopes_are_not_requested_by_auth_google(self):
        overlap = set(GATEWAY_ONLY_SCOPES) & set(Settings().google_scopes.split())
        self.assertEqual(overlap, set())


class CompareScopesTests(unittest.TestCase):
    def test_live_record_from_issue_29_is_in_sync(self):
        drift = scope_check.compare_scopes(LIVE_GATEWAY_SCOPES_2026_11_04, *_configured())
        self.assertTrue(drift.in_sync, drift.report())

    def test_unlisted_gateway_scope_is_drift(self):
        # Before this fix nothing listed these 3 scopes, so the record drifted.
        drift = scope_check.compare_scopes(
            LIVE_GATEWAY_SCOPES_2026_11_04, Settings().google_scopes.split(), []
        )
        self.assertFalse(drift.in_sync)
        self.assertEqual(drift.unexpected_in_gateway, set(GATEWAY_ONLY_SCOPES))
        self.assertIn("presentations", drift.report())

    def test_configured_scope_missing_from_gateway_is_drift(self):
        record = [s for s in LIVE_GATEWAY_SCOPES_2026_11_04 if s != G + "drive.file"]
        drift = scope_check.compare_scopes(record, *_configured())
        self.assertEqual(drift.missing_from_gateway, {G + "drive.file"})
        self.assertEqual(drift.unexpected_in_gateway, set())

    def test_gateway_only_scope_missing_from_gateway_is_drift(self):
        record = [s for s in LIVE_GATEWAY_SCOPES_2026_11_04 if s != G + "drive.readonly"]
        drift = scope_check.compare_scopes(record, *_configured())
        self.assertEqual(drift.missing_from_gateway, {G + "drive.readonly"})

    def test_userinfo_names_match_identity_scopes(self):
        record = [
            G + "userinfo.email" if s == "email" else G + "userinfo.profile" if s == "profile" else s
            for s in LIVE_GATEWAY_SCOPES_2026_11_04
        ]
        drift = scope_check.compare_scopes(record, *_configured())
        self.assertTrue(drift.in_sync, drift.report())


class ExtractProviderScopesTests(unittest.TestCase):
    def _provider(self, scopes):
        return {"id": PROVIDER_ID, "slug": "google", "scopes": scopes}

    def test_providers_envelope(self):
        payload = {"providers": [{"id": "other", "scopes": []}, self._provider(["a", "b"])]}
        self.assertEqual(scope_check.extract_provider_scopes(payload, PROVIDER_ID), ["a", "b"])

    def test_data_envelope_and_string_scopes(self):
        payload = {"data": {"providers": [self._provider("a b")]}}
        self.assertEqual(scope_check.extract_provider_scopes(payload, PROVIDER_ID), ["a", "b"])

    def test_bare_list(self):
        self.assertEqual(
            scope_check.extract_provider_scopes([self._provider(["a"])], PROVIDER_ID), ["a"]
        )

    def test_missing_provider(self):
        with self.assertRaises(LookupError):
            scope_check.extract_provider_scopes({"providers": []}, PROVIDER_ID)

    def test_bad_shape(self):
        with self.assertRaises(ValueError):
            scope_check.extract_provider_scopes({"error": "nope"}, PROVIDER_ID)


class MainTests(unittest.TestCase):
    def _run(self, payload=None, env=None, error=None):
        def fetch(api_url, api_key):
            self.assertEqual(api_key, "key")
            self.seen_url = api_url
            if error:
                raise error
            return payload

        out = io.StringIO()
        code = scope_check.main(
            env={"SEREN_API_KEY": "key"} if env is None else env, fetch=fetch, out=out
        )
        return code, out.getvalue()

    def test_in_sync_exits_0(self):
        code, out = self._run({"providers": [{"id": PROVIDER_ID, "scopes": LIVE_GATEWAY_SCOPES_2026_11_04}]})
        self.assertEqual(code, 0, out)
        self.assertEqual(self.seen_url, scope_check.DEFAULT_SEREN_API_URL)

    def test_drift_exits_1(self):
        record = LIVE_GATEWAY_SCOPES_2026_11_04 + [G + "drive"]
        code, out = self._run({"providers": [{"id": PROVIDER_ID, "scopes": record}]})
        self.assertEqual(code, 1)
        self.assertIn(G + "drive", out)

    def test_missing_key_exits_2(self):
        code, out = self._run(env={})
        self.assertEqual(code, 2)
        self.assertIn("SEREN_API_KEY", out)

    def test_unreadable_record_exits_2(self):
        code, _ = self._run(error=OSError("connection refused"))
        self.assertEqual(code, 2)
        code, _ = self._run({"providers": []})
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
