# ABOUTME: Reads a business home page and up to five relevant same-site pages.
# ABOUTME: Uses the shared public-only fetcher and bounds retries and blocked batches.

from dataclasses import dataclass
from urllib.parse import unquote, urldefrag, urljoin, urlsplit

from bs4 import BeautifulSoup
import httpx

from shared.fetch import fetch


SITE_LINK_WORDS = ("contact", "about", "team", "our-story", "staff")
MAX_PAGES = 6


def domain(url: str) -> str:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    return host[4:] if host.startswith("www.") else host


def site_links(links: list[str], home: str) -> list[str]:
    """Sheila's same-site selection, extended to the contact service's keywords."""
    found = []
    for link in links:
        link = urldefrag(urljoin(home, link))[0]
        parsed = urlsplit(link)
        if (
            parsed.scheme in ("http", "https")
            and not parsed.username and not parsed.password
            and domain(link) == domain(home)
            and any(word in unquote(parsed.path).casefold() for word in SITE_LINK_WORDS)
            and link != home and link not in found
        ):
            found.append(link)
    return found[:MAX_PAGES - 1]


@dataclass
class Batch:
    requests: int = 0
    blocked: int = 0

    @property
    def paused(self) -> bool:
        return self.requests > 0 and self.blocked / self.requests > 0.15


def is_challenge(html: str) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True).casefold() if soup.title else ""
    return title in ("just a moment...", "access denied", "sign in", "attention required! | cloudflare") or bool(
        soup.select_one("#challenge-form, #cf-challenge-running")
    )


async def _read(url: str, batch: Batch) -> httpx.Response:
    for attempt in range(3):
        batch.requests += 1
        try:
            response = await fetch(url)
            content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
            if content_type not in ("text/html", "application/xhtml+xml"):
                raise ValueError("The page did not return HTML")
            if is_challenge(response.text):
                batch.blocked += 1
                raise ValueError("The website requires sign-in or blocked this request")
            return response
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (403, 429):
                batch.blocked += 1
                raise ValueError("The website blocked this request") from None
            if exc.response.status_code < 500 or attempt == 2:
                raise
        except (httpx.TransportError, TimeoutError):
            if attempt == 2:
                raise
    raise AssertionError("Unreachable retry state")


async def read_pages(url: str, batch: Batch) -> tuple[list[tuple[str, str]], list[dict]]:
    """Return (final URL, HTML) pages and safe errors, without loading resources."""
    pages, errors = [], []
    pending = [url]
    visited = set()
    while pending and len(visited) < MAX_PAGES and not batch.paused:
        current = pending.pop(0)
        if current in visited:
            continue
        visited.add(current)
        try:
            response = await _read(current, batch)
            final = str(response.url)
            if domain(final) != domain(url):
                raise ValueError("The page redirected to a different website")
            if final in {page[0] for page in pages}:
                continue
            html = response.text
            pages.append((final, html))
            if len(pages) == 1:
                soup = BeautifulSoup(html, "html.parser")
                pending = site_links([a["href"] for a in soup.select("a[href]")], final)
        except (ValueError, httpx.HTTPError, TimeoutError):
            # Never return request headers, credentials or arbitrary upstream bodies.
            errors.append({"url": current, "error": "Page could not be read"})
    return pages, errors
