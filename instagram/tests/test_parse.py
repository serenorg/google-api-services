# ABOUTME: Replays saved real Instagram profile, reel and post data through the paid service.
# ABOUTME: Checks parsing, gateway refusal, partial-batch charges and proxy safeguards in one critical test.

import importlib
from pathlib import Path

from fastapi.testclient import TestClient
import httpx

from instagram import parse
from instagram.main import app
from shared.config import get_settings


FIXTURES = Path(__file__).parent / "fixtures"


def test_saved_profile_and_reel_pages(monkeypatch):
    profile_page = (FIXTURES / "profile.html").read_text()
    reel_page = (FIXTURES / "reel.html").read_text()
    post_page = (FIXTURES / "post.html").read_text()
    login_page = (FIXTURES / "login.html").read_text()
    assert parse.profile(profile_page) == {
        "id": "25025320", "username": "instagram", "followers": 331753136,
        "posts": 6215, "bio": "Bringing you closer to the people and things you love. ❤️",
        "category": None, "verified": True, "business": False,
    }
    reel = parse.post(reel_page)
    assert reel["id"] == "2913440072144448240"
    assert (reel["likes"], reel["comments"], reel["views"]) == (972927, 15716, 11140692)
    assert reel["caption"].startswith("“Gingerton”")
    assert reel["hashtags"] == ["WeeklyFluff"]
    assert reel["posted_time"] is None
    assert reel["co_authors"] is None
    assert reel["music"] == {
        "artist_name": "", "song_name": "", "uses_original_audio": False, "should_mute_audio": True,
    }
    assert parse.post(post_page) == {
        "id": "1554881076849508313", "shortcode": "BWUDBntl3_Z", "likes": 159071,
        "comments": 1747, "views": None, "caption": "The first Model 3 production car",
        "hashtags": [], "posted_time": 1499576290, "co_authors": [], "music": None,
    }
    calls, sessions = [], []
    blocked_links = {"/capture1", "/capture4", "/capture7", "/capture10"}

    def respond(request):
        calls.append(request)
        if request.url.path in blocked_links:
            return httpx.Response(302, headers={"Location": "/accounts/login/"}, stream=httpx.ByteStream(b""))
        if request.url.path == "/accounts/login/":
            page = login_page
        elif request.url.path.startswith("/reel/"):
            page = reel_page
        elif request.url.path.startswith("/p/"):
            page = post_page
        else:
            page = profile_page
        return httpx.Response(200, stream=httpx.ByteStream(page.encode()))

    def transport(address, proxy):
        sessions.append(proxy)
        return httpx.MockTransport(respond)

    monkeypatch.setattr(importlib.import_module("shared.fetch"), "_PinnedTransport", transport)
    monkeypatch.setenv("GATEWAY_SECRET", "capture-gateway")
    for name, value in {"USERNAME": "capture", "PASSWORD": "capture", "HOST": "geo.iproyal.com", "PORT": "12321"}.items():
        monkeypatch.setenv(f"PROXY_{name}", value)
    get_settings.cache_clear()
    header = {"X-Seren-Gateway-Secret": "capture-gateway"}
    try:
        with TestClient(app) as client:
            assert client.get("/health").json() == {"status": "healthy", "service": "instagram"}
            for route, link, expected in (
                ("profiles", "https://www.instagram.com/instagram/", parse.profile(profile_page)),
                ("posts", "https://www.instagram.com/reel/Chunk8-jurw/", reel),
                ("posts", "https://www.instagram.com/p/BWUDBntl3_Z/", parse.post(post_page)),
            ):
                payload = {"links": [link]}
                assert client.post(f"/{route}", json=payload).status_code == 401
                assert client.post(f"/{route}", json=payload, headers={"X-Seren-Gateway-Secret": "wrong"}).status_code == 401
                response = client.post(f"/{route}", json=payload, headers=header)
                assert response.status_code == 200
                body = response.json()
                assert body["billing"] == {"items": 1, "unit_price": "0.0027", "cost": "0.0027"}
                assert body["data"]["items"] == [{"link": link, "status": "read", **expected}]
                assert body["data"]["paused"] is False
                assert body["data"]["proxy_bytes"] > 0
            assert len(calls) == 3
            for payload in (
                {"links": []}, {"links": ["https://www.instagram.com/instagram/"] * 51},
                {"links": ["http://169.254.169.254/"]},
                {"links": ["https://www.instagram.com.evil.test/instagram/"]},
                {"links": ["https://user:pass@www.instagram.com/instagram/"]},
                {"links": ["https://www.instagram.com:123/instagram/"]},
                {"links": ["https://www.instagram.com/accounts/login/"]},
                {"links": ["https://www.instagram.com/reel/Chunk8-jurw/"]},
            ):
                assert client.post("/profiles", json=payload, headers=header).status_code == 422
            assert client.post("/posts", json={"links": ["https://www.instagram.com/instagram/"]}, headers=header).status_code == 422
            assert len(calls) == 3

            links = [f"https://www.instagram.com/capture{i}" for i in range(20)]
            response = client.post("/profiles", json={"links": links}, headers=header)
            assert response.status_code == 200
            body = response.json()
            assert body["data"]["paused"] is True
            assert body["billing"] == {"items": 7, "unit_price": "0.0027", "cost": "0.0189"}
            assert [item["status"] for item in body["data"]["items"][:11]] == [
                "read", "blocked", "read", "read", "blocked", "read", "read", "blocked", "read", "read", "blocked",
            ]
            assert body["data"]["items"][11:] == [{"link": link, "status": "skipped"} for link in links[11:]]
            assert [sum(request.url.path == path for request in calls) for path in sorted(blocked_links)] == [3, 1, 3, 3]
            assert body["data"]["proxy_bytes"] == 7 * len(profile_page.encode()) + 10 * len(login_page.encode())
            # Each retry gets a fresh session; redirects keep the same one.
            assert len(set(sessions)) == 20
            assert all(session is not None for session in sessions)

            monkeypatch.delenv("PROXY_PASSWORD")
            assert client.post("/profiles", json={"links": [links[0]]}, headers=header).status_code == 503
            monkeypatch.delenv("GATEWAY_SECRET")
            get_settings.cache_clear()
            assert client.post("/profiles", json={"links": [links[0]]}).status_code == 503
    finally:
        get_settings.cache_clear()
