# Critical regression tests for serenorg/google-api-services#6.
#
# Gmail's list endpoints return only {id, threadId}, which causes agents
# to misreport searches as broken because they cannot distinguish results.
# These tests pin down the enrichment behavior so it does not silently
# regress to the opaque-ID shape.

import asyncio
import unittest
from unittest.mock import patch

import client as gmail_client


def _make_message_meta(message_id: str, sender: str, subject: str, snippet: str):
    return {
        "id": message_id,
        "threadId": f"thread-{message_id}",
        "snippet": snippet,
        "labelIds": ["INBOX"],
        "internalDate": "1700000000000",
        "payload": {
            "headers": [
                {"name": "From", "value": sender},
                {"name": "Subject", "value": subject},
                {"name": "Date", "value": "Fri, 03 Apr 2026 12:00:00 -0700"},
            ],
        },
    }


class ListMessagesEnrichmentTests(unittest.TestCase):
    def test_list_messages_enriches_stubs_with_snippet_from_subject(self):
        """Default list_messages must surface snippet/from/subject for each result.

        This is the bug from issue #6 — without these fields agents cannot
        tell whether a search query returned different results from an
        unfiltered query, and falsely report Gmail search as broken.
        """
        client_instance = gmail_client.GmailClient(access_token="fake-token")

        async def fake_request(method, path, params=None, json=None):
            if path == "/users/me/messages":
                return {
                    "messages": [
                        {"id": "msg-a", "threadId": "thread-msg-a"},
                        {"id": "msg-b", "threadId": "thread-msg-b"},
                    ],
                }
            if path == "/users/me/messages/msg-a":
                return _make_message_meta("msg-a", "alice@example.com", "Lunch?", "Hey, lunch tomorrow?")
            if path == "/users/me/messages/msg-b":
                return _make_message_meta("msg-b", "bob@example.com", "Q3 review", "The Q3 numbers are in")
            raise AssertionError(f"unexpected path {path}")

        with patch.object(client_instance, "_request", side_effect=fake_request):
            result = asyncio.run(client_instance.list_messages(q="from:someone"))

        messages = result["messages"]
        self.assertEqual(len(messages), 2)

        a, b = messages
        self.assertEqual(a["id"], "msg-a")
        self.assertEqual(a["snippet"], "Hey, lunch tomorrow?")
        self.assertEqual(a["from"], "alice@example.com")
        self.assertEqual(a["subject"], "Lunch?")
        self.assertEqual(a["labelIds"], ["INBOX"])

        self.assertEqual(b["from"], "bob@example.com")
        self.assertEqual(b["subject"], "Q3 review")
        self.assertEqual(b["snippet"], "The Q3 numbers are in")

    def test_list_messages_enriched_false_makes_no_followup_calls(self):
        """Opt-out path must skip per-message metadata fetches entirely.

        This guards against accidentally making enrichment unconditional —
        a 500-message list with mandatory enrichment would burst 500 calls
        into the user's Gmail quota.
        """
        client_instance = gmail_client.GmailClient(access_token="fake-token")
        observed_paths = []

        async def fake_request(method, path, params=None, json=None):
            observed_paths.append(path)
            return {"messages": [{"id": "msg-a", "threadId": "thread-msg-a"}]}

        with patch.object(client_instance, "_request", side_effect=fake_request):
            result = asyncio.run(client_instance.list_messages(enriched=False))

        self.assertEqual(observed_paths, ["/users/me/messages"])
        self.assertEqual(result["messages"], [{"id": "msg-a", "threadId": "thread-msg-a"}])


if __name__ == "__main__":
    unittest.main()
