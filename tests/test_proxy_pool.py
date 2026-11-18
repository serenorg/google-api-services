# ABOUTME: Replays captured public TikTok pages through real proxy batching and bounded fetching.
# ABOUTME: Checks retry sessions, bytes and the fourth blocked link in a twenty-link batch.

import asyncio
import importlib
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from shared.config import get_settings
from tiktok.main import app

from shared.proxy_pool import ProxyPool
from tiktok.parse import profile


FIXTURES = Path(__file__).resolve().parents[1] / "tiktok/tests/fixtures"


def test_twenty_link_batch_pauses_after_four_blocked_links(monkeypatch):
    # Network replay only: bodies are actual page excerpts, fetched 2026-11-18.
    # The repository has no saved S5 captures; login.html records that provenance.
    good = (FIXTURES / "profile.html").read_bytes()
    login = (FIXTURES / "login.html").read_bytes()
    links = [f"https://www.tiktok.com/@captured{i}" for i in range(20)]
    sessions, requests = [], []
    blocks = {1: 403, 4: 429, 7: 200, 10: 200}

    def respond(request):
        index = links.index(str(request.url))
        requests.append(index)
        return httpx.Response(blocks.get(index, 200), stream=httpx.ByteStream(login if index in blocks else good))

    def transport(address, proxy):
        sessions.append(proxy)
        return httpx.MockTransport(respond)

    monkeypatch.setattr(importlib.import_module("shared.fetch"), "_PinnedTransport", transport)
    for name, value in {"USERNAME": "capture-user", "PASSWORD": "p@ss:word", "HOST": "geo.iproyal.com", "PORT": "12321"}.items():
        monkeypatch.setenv(f"PROXY_{name}", value)
    result = asyncio.run(ProxyPool().read_batch(links, profile))
    assert result["paused"] is True
    assert len(result["items"]) == 20
    assert [item["status"] for item in result["items"][:11]] == [
        "read", "blocked", "read", "read", "blocked", "read", "read", "blocked", "read", "read", "blocked",
    ]
    assert result["items"][11:] == [{"link": link, "status": "skipped"} for link in links[11:]]
    # First three blocked links get exactly two retries; the fourth pauses immediately.
    assert [requests.count(index) for index in blocks] == [3, 3, 3, 1]
    assert len(requests) == 17
    assert result["proxy_bytes"] == 7 * len(good) + 10 * len(login)
    assert len(set(sessions)) == len(sessions)
    assert all(httpx.Proxy(url).raw_auth[1].startswith(b"p@ss:word_session-") for url in sessions)

    # The paid route must preserve partial results as HTTP 200 and charge only reads.
    monkeypatch.setenv("GATEWAY_SECRET", "capture-batch-gateway")
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            response = client.post(
                "/profiles", json={"links": links},
                headers={"X-Seren-Gateway-Secret": "capture-batch-gateway"},
            )
        assert response.status_code == 200
        assert response.json()["data"] == result
        assert response.json()["billing"] == {
            "items": 7, "unit_price": "0.0037", "cost": "0.0259",
        }
    finally:
        get_settings.cache_clear()
