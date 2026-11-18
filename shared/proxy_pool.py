# ABOUTME: Reads bounded public pages through fresh residential proxy sessions.
# ABOUTME: Caps retries, meters received bytes and pauses batches above fifteen percent blocked links.

from dataclasses import dataclass, field
from html.parser import HTMLParser
import os
import re
from urllib.parse import quote
from uuid import uuid4

import httpx

from .fetch import UnsafeURL, fetch


class ProxyNotConfigured(ValueError):
    """The residential proxy settings are absent or invalid."""


class _VisiblePage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []
        self.challenge = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1
        attributes = dict(attrs)
        self.challenge |= attributes.get("id", "").lower() in (
            "captcha_container", "captcha-verify-container", "secsdk-captcha-drag-wrapper",
        )

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def is_blocked(response: httpx.Response) -> bool:
    if response.status_code in (403, 429):
        return True
    if response.headers.get("cf-mitigated", "").lower() == "challenge":
        return True
    if re.search(r"/(login|challenge|captcha)(/|$)", response.url.path, re.I):
        return True
    page = _VisiblePage()
    page.feed(response.text)
    text = " ".join(" ".join(page.parts).lower().split())
    return page.challenge or any(marker in text for marker in (
        "verify you are human", "verify to continue", "complete the captcha",
        "security verification", "log in to tiktok", "sign in to continue",
        "login to continue", "log in to continue", "log in to instagram",
        "just a moment...", "attention required! | cloudflare",
    ))


@dataclass
class BatchCounter:
    total: int
    blocked: int = 0
    attempts: int = 0
    proxy_bytes: int = 0
    _blocked_indices: set = field(default_factory=set, repr=False)

    @property
    def paused(self):
        return self.blocked * 100 > self.total * 15

    def add_bytes(self, count):
        self.proxy_bytes += count

    def record(self, index, response):
        """Count each blocked link once, including blocks recovered by retries."""
        self.attempts += 1
        blocked = is_blocked(response)
        if blocked and index not in self._blocked_indices:
            self._blocked_indices.add(index)
            self.blocked += 1
        return blocked

    def skipped(self, links):
        return [{"link": link, "status": "skipped"} for link in links]


class ProxyPool:
    def __init__(self):
        values = [os.environ.get(f"PROXY_{name}", "") for name in ("USERNAME", "PASSWORD", "HOST", "PORT")]
        if not all(values):
            raise ProxyNotConfigured("Residential proxy is not configured")
        self._username, self._password, self._host, port = values
        if not re.fullmatch(r"[a-zA-Z0-9.-]+", self._host) or not port.isdecimal() or not 1 <= int(port) <= 65535:
            raise ProxyNotConfigured("Residential proxy settings are invalid")
        self._port = int(port)

    def session_url(self):
        session = uuid4().hex[:8]
        username, password = self._username, self._password
        if self._host.endswith(".superproxy.io"):
            username += f"-session-{session}"
        else:
            password += f"_session-{session}"
        return f"http://{quote(username, safe='')}:{quote(password, safe='')}@{self._host}:{self._port}"

    async def read_batch(self, links, parse):
        counter = BatchCounter(len(links))
        items = []
        for index, link in enumerate(links):
            if counter.paused:
                items.extend(counter.skipped(links[index:]))
                break
            result = {"link": link, "status": "error"}
            for attempt in range(3):
                try:
                    response = await fetch(link, proxy=self.session_url(), on_bytes=counter.add_bytes)
                    blocked = counter.record(index, response)
                    if blocked:
                        result = {"link": link, "status": "blocked"}
                    else:
                        data = parse(response.text)
                        result = {"link": link, "status": "read", **data}
                        break
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    blocked = counter.record(index, exc.response)
                    result = {"link": link, "status": "blocked" if blocked else "error", "http_status": status}
                    if not blocked and status < 500:
                        break
                except UnsafeURL:
                    result = {"link": link, "status": "error", "reason": "unsafe_link"}
                    break
                except (httpx.RequestError, ValueError, TimeoutError):
                    result = {"link": link, "status": "error"}
                if counter.paused:
                    break
            items.append(result)
        return {"items": items, "paused": counter.paused, "proxy_bytes": counter.proxy_bytes}
