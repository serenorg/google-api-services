# ABOUTME: Exercises public-page fetch limits and refusal of private destinations.
# ABOUTME: Uses real HTTPS responses from httpbin.dev, verified on 2026-11-17.

import asyncio

import httpx
import pytest

from shared.fetch import UnsafeURL, fetch


def test_public_fetch_refuses_private_destinations():
    async def check():
        for url in (
            "http://169.254.169.254/", "http://metadata.google.internal/",
            "http://127.0.0.1/", "http://[::1]/", "http://[::ffff:127.0.0.1]/",
            "http://10.0.0.1/", "file:///etc/passwd",
        ):
            with pytest.raises(UnsafeURL):
                await fetch(url)
        # Live HTTP 302 Location: http://127.0.0.1/, observed 2026-11-17.
        with pytest.raises(UnsafeURL):
            await fetch("https://httpbin.dev/redirect-to?url=http://127.0.0.1/")

        # A real public page succeeds, including through a relative redirect.
        response = await fetch("https://httpbin.dev/relative-redirect/1")
        assert response.status_code == 200
        assert response.url.path == "/get"
        assert response.json()["url"].endswith("/get")
        with pytest.raises(ValueError, match="max_bytes"):
            await fetch("https://httpbin.dev/bytes/100", max_bytes=10)
        with pytest.raises(httpx.TooManyRedirects):
            await fetch("https://httpbin.dev/relative-redirect/6")
    asyncio.run(check())
