# ABOUTME: Extracts public Instagram profile, post and reel facts from embedded page data.
# ABOUTME: Reads legacy state and Relay or embed payloads without executing scripts or loading media.

from html.parser import HTMLParser
import json
import re


class PageUnavailable(ValueError):
    """The page does not contain one readable public item."""


class _StateParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.active = False
        self.parts = []
        self.states = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            self.active = True
            self.parts = []

    def handle_data(self, data):
        if self.active:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag != "script" or not self.active:
            return
        self.active = False
        script = "".join(self.parts).strip()
        # Decode JSON literals only; never evaluate the surrounding JavaScript.
        starts = [0] if script.startswith(("{", "[")) else []
        starts.extend(match.end() for match in re.finditer(
            r"(?:window\._sharedData\s*=|\b\w+\.handle\(|"
            r"(?:window\.)?__additionalDataLoaded\([^,]+,)\s*", script,
        ))
        for start in starts:
            try:
                self.states.append(json.JSONDecoder().raw_decode(script[start:])[0])
            except (ValueError, RecursionError):
                pass


def _objects(page):
    parser = _StateParser()
    parser.feed(page)
    pending = [(state, 0) for state in reversed(parser.states)]
    while pending:
        value, depth = pending.pop()
        if depth > 50:
            continue
        if isinstance(value, dict):
            yield value
            pending.extend((child, depth + 1) for child in reversed(list(value.values())))
        elif isinstance(value, list):
            pending.extend((child, depth + 1) for child in reversed(value))
        elif isinstance(value, str) and value.startswith(("{", "[")):
            try:
                pending.append((json.loads(value), depth + 1))
            except (ValueError, RecursionError):
                pass


def _count(item, *keys):
    for key in keys:
        value = item.get(key)
        if isinstance(value, dict):
            value = value.get("count")
        if value is not None:
            count = int(value)
            return count if count >= 0 else None
    return None


def profile(page: str) -> dict:
    users = [item for item in _objects(page) if item.get("username") and (
        "edge_owner_to_timeline_media" in item or "media_count" in item
    ) and ("edge_followed_by" in item or "follower_count" in item)]
    if len(users) != 1 or users[0].get("is_private"):
        raise PageUnavailable("Profile is unavailable or private")
    user = users[0]
    return {
        "id": str(user.get("id", user.get("pk"))) if user.get("id", user.get("pk")) is not None else None,
        "username": user["username"],
        "followers": _count(user, "edge_followed_by", "follower_count"),
        "posts": _count(user, "edge_owner_to_timeline_media", "media_count"),
        "bio": user.get("biography", ""),
        "category": user.get("category_name") or user.get("business_category_name") or user.get("category"),
        "verified": user.get("is_verified"),
        "business": user.get("is_business_account"),
    }


def post(page: str) -> dict:
    media = []
    for obj in _objects(page):
        for key in ("shortcode_media", "xdt_shortcode_media"):
            if isinstance(obj.get(key), dict):
                media.append(obj[key])
        for key, value in obj.items():
            if key.startswith("xdt_api__v1__media__shortcode__web_info") and isinstance(value, dict):
                media.extend(value.get("items") or [])
    if len(media) != 1:
        raise PageUnavailable("Post is unavailable")
    item = media[0]
    if not (item.get("shortcode") or item.get("code")) or item.get("is_private") or (item.get("owner") or item.get("user") or {}).get("is_private"):
        raise PageUnavailable("Post is unavailable or private")
    likes = _count(item, "edge_media_preview_like", "edge_liked_by", "like_count")
    comments = _count(item, "edge_media_to_parent_comment", "edge_media_to_comment", "comment_count")
    views = _count(item, "video_view_count", "video_play_count", "play_count", "view_count")
    if all(value is None for value in (likes, comments, views)):
        raise PageUnavailable("Post statistics are unavailable")
    caption = item.get("caption")
    if isinstance(caption, dict):
        caption = caption.get("text")
    if caption is None:
        edges = (item.get("edge_media_to_caption") or {}).get("edges") or []
        caption = "\n".join(edge["node"]["text"] for edge in edges if edge.get("node", {}).get("text"))
    collaborators = item.get("coauthor_producers")
    music = item.get("clips_music_attribution_info")
    if music is None:
        metadata = item.get("music_metadata") or item.get("clips_metadata") or {}
        music = metadata.get("music_info") or metadata.get("original_sound_info")
    return {
        "id": str(item.get("id", item.get("pk"))) if item.get("id", item.get("pk")) is not None else None,
        "shortcode": item.get("shortcode") or item.get("code"),
        "likes": likes, "comments": comments, "views": views,
        "caption": caption,
        "hashtags": list(dict.fromkeys(re.findall(r"#(\w+)", caption))),
        "posted_time": _count(item, "taken_at_timestamp", "taken_at"),
        "co_authors": None if collaborators is None else [
            {"id": str(author.get("id", author.get("pk"))) if author.get("id", author.get("pk")) is not None else None,
             "username": author.get("username")} for author in collaborators
        ],
        "music": music,
    }
