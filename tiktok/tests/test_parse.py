# ABOUTME: Reads saved real TikTok profile/video pages and checks the paid route contract.
# ABOUTME: Replays only captured page data while retaining real parsing, gateway checks and billing.

import importlib
from pathlib import Path

from fastapi.testclient import TestClient
import httpx

from shared.config import get_settings
from tiktok import parse
from tiktok.main import app


FIXTURES = Path(__file__).parent / "fixtures"


def test_saved_profile_and_video_pages(monkeypatch):
    profile_page = (FIXTURES / "profile.html").read_text()
    video_page = (FIXTURES / "video.html").read_text()
    assert parse.profile(profile_page) == {
        "id": "107955", "username": "tiktok", "followers": 96900000,
        "likes": 469000000, "video_count": 1519,
        "bio": "Your next discovery is waiting on TikTok.", "bio_link": None,
    }
    item = parse.video(video_page)
    assert item == {
        "id": "6718335390845095173", "views": 160300, "likes": 35200,
        "comments": 5838, "shares": 1529, "saves": 652, "posted_time": 1564234358,
        "caption": "Scramble up ur name & I’ll try to guess it😍❤️ #foryoupage #petsoftiktok #aesthetic",
        "sound": {"id": "6689804660171082501", "title": "original sound", "author": "tiff", "original": True},
    }
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(200, text=video_page if "/video/" in request.url.path else profile_page)

    monkeypatch.setattr(importlib.import_module("shared.fetch"), "_PinnedTransport", lambda address, proxy: httpx.MockTransport(respond))
    monkeypatch.setenv("GATEWAY_SECRET", "capture-gateway")
    for name, value in {"USERNAME": "capture", "PASSWORD": "capture", "HOST": "geo.iproyal.com", "PORT": "12321"}.items():
        monkeypatch.setenv(f"PROXY_{name}", value)
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            assert client.get("/health").status_code == 200
            for route, link in (("profiles", "https://www.tiktok.com/@tiktok"), ("videos", "https://www.tiktok.com/@scout2015/video/6718335390845095173")):
                payload = {"links": [link]}
                assert client.post(f"/{route}", json=payload).status_code == 401
                assert client.post(f"/{route}", json=payload, headers={"X-Seren-Gateway-Secret": "wrong"}).status_code == 401
                response = client.post(f"/{route}", json=payload, headers={"X-Seren-Gateway-Secret": "capture-gateway"})
                assert response.status_code == 200
                body = response.json()
                assert body["billing"] == {"items": 1, "unit_price": "0.0037", "cost": "0.0037"}
                assert body["data"]["items"][0]["status"] == "read"
                assert body["data"]["paused"] is False
                assert body["data"]["proxy_bytes"] > 0
            assert len(calls) == 2
            header = {"X-Seren-Gateway-Secret": "capture-gateway"}
            for payload in ({"links": []}, {"links": ["https://www.tiktok.com/@tiktok"] * 51}, {"links": ["http://169.254.169.254/"]}, {"links": ["https://www.tiktok.com.evil.test/@tiktok"]}):
                assert client.post("/profiles", json=payload, headers=header).status_code == 422
            monkeypatch.delenv("PROXY_PASSWORD")
            assert client.post("/profiles", json={"links": ["https://www.tiktok.com/@tiktok"]}, headers=header).status_code == 503
            monkeypatch.delenv("GATEWAY_SECRET")
            get_settings.cache_clear()
            assert client.post("/profiles", json={"links": ["https://www.tiktok.com/@tiktok"]}).status_code == 503
    finally:
        get_settings.cache_clear()
