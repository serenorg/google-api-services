# ABOUTME: Extracts public profile and video facts from TikTok page hydration data.
# ABOUTME: Supports universal and SIGI state without executing scripts or loading media.

from html.parser import HTMLParser
import json


class PageUnavailable(ValueError):
    """The page does not contain a readable public item."""


class _StateParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.active = None
        self.parts = []
        self.states = {}

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            name = dict(attrs).get("id")
            if name in ("__UNIVERSAL_DATA_FOR_REHYDRATION__", "SIGI_STATE", "sigi-persisted-data"):
                self.active = name
                self.parts = []

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.active:
            try:
                value = json.loads("".join(self.parts))
                if isinstance(value, dict):
                    self.states[self.active] = value
            except (ValueError, TypeError):
                pass
            self.active = None


def _states(page):
    parser = _StateParser()
    parser.feed(page)
    universal = parser.states.get("__UNIVERSAL_DATA_FOR_REHYDRATION__", {}).get("__DEFAULT_SCOPE__", {})
    legacy = parser.states.get("SIGI_STATE", parser.states.get("sigi-persisted-data", {}))
    return universal, legacy


def _count(value):
    # Never turn a missing figure into a fabricated zero.
    return int(value) if value is not None else None


def profile(page: str) -> dict:
    universal, legacy = _states(page)
    detail = universal.get("webapp.user-detail", {})
    if detail.get("statusCode", 0) != 0:
        raise PageUnavailable("Profile is unavailable")
    info = detail.get("userInfo", {})
    user, stats = info.get("user", {}), info.get("stats", {})
    if not user:
        module = legacy.get("UserModule", {})
        users = module.get("users", {})
        if len(users) == 1:
            key, user = next(iter(users.items()))
            stats = module.get("stats", {}).get(key, {})
    if not user.get("uniqueId") or not stats or user.get("privateAccount") or user.get("secret"):
        raise PageUnavailable("Profile is unavailable or private")
    bio_link = user.get("bioLink") or {}
    return {
        "id": user.get("id"), "username": user["uniqueId"],
        "followers": _count(stats.get("followerCount")),
        "likes": _count(stats.get("heartCount", stats.get("heart"))),
        "video_count": _count(stats.get("videoCount")),
        "bio": user.get("signature", ""),
        "bio_link": bio_link.get("link") if isinstance(bio_link, dict) else bio_link,
    }


def video(page: str) -> dict:
    universal, legacy = _states(page)
    detail = universal.get("webapp.video-detail", {})
    if detail.get("statusCode", 0) != 0:
        raise PageUnavailable("Video is unavailable")
    item = detail.get("itemInfo", {}).get("itemStruct", {})
    if not item:
        items = legacy.get("ItemModule", {})
        if len(items) == 1:
            item = next(iter(items.values()))
    if not item.get("id") or item.get("privateItem") or item.get("secret"):
        raise PageUnavailable("Video is unavailable or private")
    stats = item.get("statsV2") or item.get("stats", {})
    if not stats:
        raise PageUnavailable("Video statistics are unavailable")
    music = item.get("music") or {}
    return {
        "id": str(item["id"]),
        "views": _count(stats.get("playCount")), "likes": _count(stats.get("diggCount")),
        "comments": _count(stats.get("commentCount")), "shares": _count(stats.get("shareCount")),
        "saves": _count(stats.get("collectCount")),
        "posted_time": _count(item.get("createTime")), "caption": item.get("desc", ""),
        "sound": {"id": music.get("id"), "title": music.get("title"),
                  "author": music.get("authorName"), "original": music.get("original")},
    }
