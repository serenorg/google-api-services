# ABOUTME: Runs the real YouTube routes against recorded Google HTTP responses.
# ABOUTME: Checks exact item billing, query forwarding and unbilled quota refusals.

from decimal import Decimal

import httpx
from fastapi.testclient import TestClient

from shared.config import get_settings
from youtube.main import app
from youtube.tests.captured_responses import (
    FORBIDDEN_RESPONSE,
    QUOTA_RESPONSE,
    SEARCH_RESPONSE,
)


def test_youtube_routes(monkeypatch):
    monkeypatch.setenv("GATEWAY_SECRET", "test-only-gateway-secret")
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-only-youtube-key")
    get_settings.cache_clear()
    headers = {"X-Seren-Gateway-Secret": "test-only-gateway-secret"}
    routes = ("search", "videos", "channels", "playlists", "playlistItems", "commentThreads")
    requests = []
    response_status, response_body = 200, SEARCH_RESPONSE

    def replay(request):
        # Replace only the Google HTTP boundary, never the service or its client.
        assert request.method == "GET"
        assert request.url.scheme == "https"
        assert request.url.host == "www.googleapis.com"
        assert request.url.path.removeprefix("/youtube/v3/") in routes
        assert request.url.params["key"] == "test-only-youtube-key"
        assert "X-Seren-Gateway-Secret" not in request.headers
        requests.append(request)
        return httpx.Response(response_status, json=response_body)

    async_client = httpx.AsyncClient
    monkeypatch.setattr(
        "youtube.client.httpx.AsyncClient",
        lambda **kwargs: async_client(transport=httpx.MockTransport(replay), **kwargs),
    )

    try:
        with TestClient(app) as client:
            assert client.get("/health").json() == {"status": "healthy", "service": "youtube"}
            for route in routes:
                for credential in ({}, {"X-Seren-Gateway-Secret": "wrong"}):
                    denied = client.get(f"/{route}", headers=credential)
                    assert denied.status_code == 401
                    assert "billing" not in denied.json()
            assert not requests

            operation = client.get("/openapi.json").json()["paths"]["/search"]["get"]
            query_names = {p["name"] for p in operation["parameters"] if p["in"] == "query"}
            assert query_names == {
                "q", "type", "order", "publishedAfter", "publishedBefore", "regionCode",
                "relevanceLanguage", "videoDuration", "eventType", "channelId", "playlistId",
                "videoId", "pageToken", "maxResults", "part", "id",
            }

            params = {
                "q": "news", "part": "snippet", "type": "video", "order": "date",
                "channelId": "UC_x5XG1OV2P6uZZ5FSM9Ttw", "maxResults": "5",
                "publishedAfter": "2020-01-01T00:00:00Z",
                "publishedBefore": "2020-04-01T00:00:00Z", "regionCode": "US",
                "relevanceLanguage": "en", "videoDuration": "short", "eventType": "completed",
                "pageToken": "CAUQAA",
            }
            response = client.get("/search", params={**params, "key": "caller-key"}, headers=headers)
            assert response.status_code == 200
            result = response.json()
            assert result["data"] == SEARCH_RESPONSE
            assert result["billing"]["items"] == len(SEARCH_RESPONSE["items"])
            assert result["billing"]["unit_price"] == "0.004"
            assert Decimal(result["billing"]["cost"]) == len(SEARCH_RESPONSE["items"]) * Decimal("0.004")
            assert dict(requests[-1].url.params) == {**params, "key": "test-only-youtube-key"}
            assert result["data"]["nextPageToken"] == SEARCH_RESPONSE["nextPageToken"]

            before = len(requests)
            for size in ("0", "51", "not-an-integer"):
                assert client.get("/search", params={"maxResults": size}, headers=headers).status_code == 422
            assert len(requests) == before

            response_status, response_body = 403, QUOTA_RESPONSE
            for route in routes:
                exhausted = client.get(f"/{route}", headers=headers)
                assert exhausted.status_code == 429
                assert exhausted.json()["detail"] == QUOTA_RESPONSE
                assert "billing" not in exhausted.json()

            response_body = FORBIDDEN_RESPONSE
            denied = client.get("/search", headers=headers)
            assert denied.status_code == 403
            assert "billing" not in denied.json()

            before = len(requests)
            monkeypatch.setenv("YOUTUBE_API_KEY", "")
            get_settings.cache_clear()
            for route in routes:
                assert client.get(f"/{route}", headers=headers).status_code == 503
            monkeypatch.setenv("GATEWAY_SECRET", "")
            get_settings.cache_clear()
            for route in routes:
                assert client.get(f"/{route}", headers=headers).status_code == 503
                assert client.get(f"/{route}").status_code == 503
            assert len(requests) == before
            assert client.get("/health").status_code == 200
    finally:
        get_settings.cache_clear()
