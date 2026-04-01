import unittest

from fastapi.testclient import TestClient

import main as gmail_main


class FakeGmailClient:
    def __init__(self):
        self.calls = []

    async def list_messages(self, **kwargs):
        self.calls.append(kwargs)
        return {"messages": []}


class ListMessagesQueryParamTests(unittest.TestCase):
    def setUp(self):
        self.fake_client = FakeGmailClient()
        gmail_main.app.dependency_overrides[gmail_main.get_gmail_client] = lambda: self.fake_client
        self.client = TestClient(gmail_main.app)

    def tearDown(self):
        gmail_main.app.dependency_overrides.clear()

    def test_openapi_exposes_google_style_query_parameters_for_messages(self):
        operation = gmail_main.app.openapi()["paths"]["/messages"]["get"]
        parameter_names = {parameter["name"] for parameter in operation["parameters"]}

        self.assertTrue({"q", "maxResults", "pageToken", "labelIds"}.issubset(parameter_names))

    def test_list_messages_accepts_google_style_query_parameter_names(self):
        response = self.client.get(
            "/messages",
            params={
                "q": "from:harris rendero",
                "maxResults": "25",
                "pageToken": "next-page",
                "labelIds": ["INBOX", "UNREAD"],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.fake_client.calls[-1],
            {
                "max_results": 25,
                "page_token": "next-page",
                "q": "from:harris rendero",
                "label_ids": ["INBOX", "UNREAD"],
            },
        )


if __name__ == "__main__":
    unittest.main()
