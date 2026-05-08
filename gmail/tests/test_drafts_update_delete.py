import unittest

import httpx
from fastapi.testclient import TestClient

import main as gmail_main


class FakeGmailClient:
    def __init__(self):
        self.update_calls = []
        self.delete_calls = []
        self.next_update_response = {"id": "DRAFT123", "message": {"id": "MSG1"}}
        self.delete_should_404 = False

    async def update_draft(self, **kwargs):
        self.update_calls.append(kwargs)
        return self.next_update_response

    async def delete_draft(self, **kwargs):
        self.delete_calls.append(kwargs)
        if self.delete_should_404:
            request = httpx.Request("DELETE", "https://gmail.googleapis.com/gmail/v1/users/me/drafts/missing")
            response = httpx.Response(status_code=404, request=request, text='{"error":"not found"}')
            raise httpx.HTTPStatusError("not found", request=request, response=response)
        return None


class UpdateDraftTests(unittest.TestCase):
    """Issue #22: PUT /drafts/{draft_id} must accept the canonical Gmail draft
    update body (raw + optional threadId) and return the updated draft."""

    def setUp(self):
        self.fake_client = FakeGmailClient()
        gmail_main.app.dependency_overrides[gmail_main.get_gmail_client] = lambda: self.fake_client
        self.client = TestClient(gmail_main.app)

    def tearDown(self):
        gmail_main.app.dependency_overrides.clear()

    def test_put_draft_replaces_contents(self):
        response = self.client.put(
            "/drafts/DRAFT123",
            json={"raw": "VGVzdDI=", "threadId": "thread-1"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"id": "DRAFT123", "message": {"id": "MSG1"}})
        self.assertEqual(
            self.fake_client.update_calls[-1],
            {"draft_id": "DRAFT123", "raw": "VGVzdDI=", "thread_id": "thread-1"},
        )

    def test_put_draft_without_thread_id(self):
        response = self.client.put(
            "/drafts/DRAFT123",
            json={"raw": "VGVzdA=="},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.fake_client.update_calls[-1],
            {"draft_id": "DRAFT123", "raw": "VGVzdA==", "thread_id": None},
        )


class DeleteDraftTests(unittest.TestCase):
    """Issue #22: DELETE /drafts/{draft_id} must return 204 on success and
    surface upstream 404 when the draft does not exist."""

    def setUp(self):
        self.fake_client = FakeGmailClient()
        gmail_main.app.dependency_overrides[gmail_main.get_gmail_client] = lambda: self.fake_client
        self.client = TestClient(gmail_main.app)

    def tearDown(self):
        gmail_main.app.dependency_overrides.clear()

    def test_delete_draft_returns_204(self):
        response = self.client.delete("/drafts/DRAFT123")

        self.assertEqual(response.status_code, 204)
        self.assertEqual(self.fake_client.delete_calls[-1], {"draft_id": "DRAFT123"})

    def test_delete_missing_draft_returns_404(self):
        self.fake_client.delete_should_404 = True

        response = self.client.delete("/drafts/missing")

        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
