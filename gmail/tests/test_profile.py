import unittest

from fastapi.testclient import TestClient

import main as gmail_main


class FakeGmailClient:
    def __init__(self):
        self.calls = []

    async def get_profile(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "emailAddress": "taariq@alphagrowth.io",
            "messagesTotal": 4821,
            "threadsTotal": 3310,
            "historyId": "992144",
        }


class ProfileRouteTests(unittest.TestCase):
    def setUp(self):
        self.fake_client = FakeGmailClient()
        gmail_main.app.dependency_overrides[gmail_main.get_gmail_client] = lambda: self.fake_client
        self.client = TestClient(gmail_main.app)

    def tearDown(self):
        gmail_main.app.dependency_overrides.clear()

    def test_profile_returns_the_authenticated_mailbox(self):
        """Agents acting under a user OAuth grant need to know whose mailbox
        they hold before they send anything as that person."""
        response = self.client.get("/profile")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["emailAddress"], "taariq@alphagrowth.io")
        self.assertEqual(self.fake_client.calls[-1], {})


if __name__ == "__main__":
    unittest.main()
