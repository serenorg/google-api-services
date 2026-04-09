import base64
import unittest
from email import message_from_bytes

from fastapi.testclient import TestClient

import main as gmail_main


class FakeGmailClient:
    def __init__(self):
        self.calls = []

    async def send_message(self, **kwargs):
        self.calls.append(kwargs)
        return {"id": "msg_abc123", "threadId": "thread_abc123", "labelIds": ["SENT"]}


class FriendlySendTests(unittest.TestCase):
    def setUp(self):
        self.fake_client = FakeGmailClient()
        gmail_main.app.dependency_overrides[gmail_main.get_gmail_client] = lambda: self.fake_client
        self.client = TestClient(gmail_main.app)

    def tearDown(self):
        gmail_main.app.dependency_overrides.clear()

    def test_send_friendly_constructs_valid_rfc2822_message(self):
        """POST /send should build an RFC 2822 MIME message and base64url-encode it."""
        response = self.client.post(
            "/send",
            json={
                "to": "alice@example.com",
                "subject": "Hello from agent",
                "body": "This is a test email.",
                "cc": "bob@example.com",
                "bcc": "charlie@example.com",
                "inReplyTo": "<original-msg-id@example.com>",
                "references": "<original-msg-id@example.com>",
                "threadId": "thread_xyz",
            },
        )

        self.assertEqual(response.status_code, 200)

        # Verify the client was called with the right thread_id
        call = self.fake_client.calls[-1]
        self.assertEqual(call["thread_id"], "thread_xyz")

        # Decode the raw payload and verify RFC 2822 headers
        raw_bytes = base64.urlsafe_b64decode(call["raw"])
        msg = message_from_bytes(raw_bytes)

        self.assertEqual(msg["To"], "alice@example.com")
        self.assertEqual(msg["Subject"], "Hello from agent")
        self.assertEqual(msg["Cc"], "bob@example.com")
        self.assertEqual(msg["Bcc"], "charlie@example.com")
        self.assertEqual(msg["In-Reply-To"], "<original-msg-id@example.com>")
        self.assertEqual(msg["References"], "<original-msg-id@example.com>")
        self.assertIn("This is a test email.", msg.get_payload(decode=True).decode())


if __name__ == "__main__":
    unittest.main()
