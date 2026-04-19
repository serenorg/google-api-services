import unittest

from fastapi.testclient import TestClient

import main as gmail_main


class FakeGmailClient:
    def __init__(self):
        self.calls = []

    async def get_attachment(self, **kwargs):
        self.calls.append(kwargs)
        return {"size": 12345, "data": "aGVsbG8td29ybGQ"}


class GetAttachmentRouteTests(unittest.TestCase):
    def setUp(self):
        self.fake_client = FakeGmailClient()
        gmail_main.app.dependency_overrides[gmail_main.get_gmail_client] = lambda: self.fake_client
        self.client = TestClient(gmail_main.app)

    def tearDown(self):
        gmail_main.app.dependency_overrides.clear()

    def test_get_attachment_proxies_ids_and_returns_gmail_payload(self):
        response = self.client.get("/messages/MSG123/attachments/ATT456")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"size": 12345, "data": "aGVsbG8td29ybGQ"})
        self.assertEqual(
            self.fake_client.calls[-1],
            {"message_id": "MSG123", "attachment_id": "ATT456"},
        )


if __name__ == "__main__":
    unittest.main()
