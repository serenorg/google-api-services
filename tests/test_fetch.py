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


def test_compression_is_refused_before_buffered_response_decoding(monkeypatch):
    # Reproduces the review finding: a tiny gzip body can expand past max_bytes.
    import gzip
    import importlib

    module = importlib.import_module("shared.fetch")
    compressed = gzip.compress(b"x" * 6_000_000)
    assert len(compressed) < 5_000_000

    async def check():
        for status in (200, 302, 403, 429, 500):
            seen = []

            def respond(request):
                seen.append(str(request.url))
                return httpx.Response(
                    status, headers={"Content-Encoding": "gzip", "Location": "/next"},
                    stream=httpx.ByteStream(compressed),
                )

            monkeypatch.setattr(module, "_PinnedTransport", lambda address, proxy: httpx.MockTransport(respond))
            received = []
            error = httpx.HTTPStatusError if status in (403, 429) else ValueError
            with pytest.raises(error):
                await fetch("https://www.tiktok.com/@tiktok", on_bytes=received.append)
            assert len(seen) == 1  # Encoded redirects must never be followed.
            assert sum(received) == len(compressed)

    asyncio.run(check())
