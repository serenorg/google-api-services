import unittest

from fastapi.testclient import TestClient

import main as calendar_main


class FakeCalendarClient:
    def __init__(self):
        self.calls = []

    async def list_events(self, **kwargs):
        self.calls.append(kwargs)
        return {"items": []}


class ListEventsQueryParamTests(unittest.TestCase):
    def setUp(self):
        self.fake_client = FakeCalendarClient()
        calendar_main.app.dependency_overrides[calendar_main.get_calendar_client] = lambda: self.fake_client
        self.client = TestClient(calendar_main.app)

    def tearDown(self):
        calendar_main.app.dependency_overrides.clear()

    def test_list_events_accepts_google_style_query_parameter_names(self):
        response = self.client.get(
            "/events",
            params={
                "calendarId": "team@example.com",
                "timeMin": "2026-03-22T00:00:00Z",
                "timeMax": "2026-03-28T23:59:59Z",
                "singleEvents": "false",
                "orderBy": "updated",
                "maxResults": "50",
                "pageToken": "next-page",
                "showDeleted": "true",
                "q": "launch",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.fake_client.calls[-1],
            {
                "calendar_id": "team@example.com",
                "max_results": 50,
                "page_token": "next-page",
                "time_min": "2026-03-22T00:00:00Z",
                "time_max": "2026-03-28T23:59:59Z",
                "q": "launch",
                "single_events": False,
                "order_by": "updated",
                "show_deleted": True,
            },
        )

    def test_list_events_keeps_existing_snake_case_query_parameter_names(self):
        response = self.client.get(
            "/events",
            params={
                "calendar_id": "primary",
                "time_min": "2026-03-22T00:00:00Z",
                "time_max": "2026-03-29T00:00:00Z",
                "single_events": "true",
                "order_by": "startTime",
                "max_results": "5",
                "show_deleted": "false",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            self.fake_client.calls[-1],
            {
                "calendar_id": "primary",
                "max_results": 5,
                "page_token": None,
                "time_min": "2026-03-22T00:00:00Z",
                "time_max": "2026-03-29T00:00:00Z",
                "q": None,
                "single_events": True,
                "order_by": "startTime",
                "show_deleted": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
