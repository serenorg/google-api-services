import unittest

from fastapi.testclient import TestClient

import main as gmail_main


class FakeGmailClient:
    def __init__(self):
        self.modify_calls = []
        self.batch_modify_calls = []
        self.create_label_calls = []

    async def modify_message(self, **kwargs):
        self.modify_calls.append(kwargs)
        return {"id": kwargs["message_id"], "labelIds": kwargs.get("add_label_ids") or []}

    async def batch_modify_messages(self, **kwargs):
        self.batch_modify_calls.append(kwargs)
        return None

    async def create_label(self, **kwargs):
        self.create_label_calls.append(kwargs)
        return {"id": "Label_999", **kwargs}


class ModifyMessageBodyTests(unittest.TestCase):
    """Issue #20: POST /messages/{id}/modify must accept addLabelIds /
    removeLabelIds in the JSON body (the canonical Gmail API shape), not just
    repeated query params."""

    def setUp(self):
        self.fake_client = FakeGmailClient()
        gmail_main.app.dependency_overrides[gmail_main.get_gmail_client] = lambda: self.fake_client
        self.client = TestClient(gmail_main.app)

    def tearDown(self):
        gmail_main.app.dependency_overrides.clear()

    def test_modify_accepts_label_ids_from_json_body(self):
        response = self.client.post(
            "/messages/MSG123/modify",
            json={"addLabelIds": ["Label_116"], "removeLabelIds": ["INBOX"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.fake_client.modify_calls[-1],
            {
                "message_id": "MSG123",
                "add_label_ids": ["Label_116"],
                "remove_label_ids": ["INBOX"],
            },
        )

    def test_modify_still_accepts_repeated_query_params(self):
        response = self.client.post(
            "/messages/MSG123/modify?addLabelIds=Label_A&addLabelIds=Label_B&removeLabelIds=INBOX",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.fake_client.modify_calls[-1],
            {
                "message_id": "MSG123",
                "add_label_ids": ["Label_A", "Label_B"],
                "remove_label_ids": ["INBOX"],
            },
        )

    def test_modify_body_takes_precedence_over_query_params(self):
        response = self.client.post(
            "/messages/MSG123/modify?addLabelIds=QUERY_ONLY",
            json={"addLabelIds": ["BODY_WINS"]},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.fake_client.modify_calls[-1]["add_label_ids"],
            ["BODY_WINS"],
        )


class CreateLabelBodyTests(unittest.TestCase):
    """Issue #20 follow-up: POST /labels has the same bug — accepts only query
    params. Must also accept the canonical Gmail API JSON body shape."""

    def setUp(self):
        self.fake_client = FakeGmailClient()
        gmail_main.app.dependency_overrides[gmail_main.get_gmail_client] = lambda: self.fake_client
        self.client = TestClient(gmail_main.app)

    def tearDown(self):
        gmail_main.app.dependency_overrides.clear()

    def test_create_label_accepts_json_body(self):
        response = self.client.post(
            "/labels",
            json={
                "name": "Newsletters/Inbox",
                "messageListVisibility": "show",
                "labelListVisibility": "labelShow",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.fake_client.create_label_calls[-1],
            {
                "name": "Newsletters/Inbox",
                "message_list_visibility": "show",
                "label_list_visibility": "labelShow",
            },
        )


class BatchModifyMessagesTests(unittest.TestCase):
    """Issue #20 follow-up: expose POST /messages/batchModify so callers can
    label up to 1000 IDs in one call instead of N individual POSTs."""

    def setUp(self):
        self.fake_client = FakeGmailClient()
        gmail_main.app.dependency_overrides[gmail_main.get_gmail_client] = lambda: self.fake_client
        self.client = TestClient(gmail_main.app)

    def tearDown(self):
        gmail_main.app.dependency_overrides.clear()

    def test_batch_modify_accepts_ids_and_label_lists_from_body(self):
        response = self.client.post(
            "/messages/batchModify",
            json={
                "ids": ["MSG1", "MSG2", "MSG3"],
                "addLabelIds": ["Label_X"],
                "removeLabelIds": ["INBOX"],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok", "count": 3})
        self.assertEqual(
            self.fake_client.batch_modify_calls[-1],
            {
                "ids": ["MSG1", "MSG2", "MSG3"],
                "add_label_ids": ["Label_X"],
                "remove_label_ids": ["INBOX"],
            },
        )

    def test_batch_modify_rejects_empty_ids(self):
        response = self.client.post(
            "/messages/batchModify",
            json={"ids": [], "addLabelIds": ["Label_X"]},
        )
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
