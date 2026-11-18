# ABOUTME: Reads YouTube Data API collections with Seren's service API key.
# ABOUTME: Restricts requests to the six supported Google HTTPS endpoints.

from typing import Any

import httpx

from shared.config import get_settings


class YouTubeClient:
    """Read public YouTube data without requiring a hirer's OAuth token."""

    BASE_URL = "https://www.googleapis.com/youtube/v3"
    RESOURCES = frozenset({
        "search", "videos", "channels", "playlists", "playlistItems", "commentThreads",
    })

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.timeout = get_settings().request_timeout

    async def list(self, resource: str, params: dict[str, Any]) -> dict[str, Any]:
        """Fetch one page, keeping upstream errors available to the route."""
        if resource not in self.RESOURCES:
            raise ValueError("Unsupported YouTube resource")
        async with httpx.AsyncClient(follow_redirects=False) as client:
            response = await client.get(
                f"{self.BASE_URL}/{resource}",
                params={**params, "key": self.api_key},
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()
