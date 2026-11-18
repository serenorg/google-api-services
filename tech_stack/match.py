# ABOUTME: Detects technologies from one buffered public-page response.
# ABOUTME: Reads headers, cookies, metadata, script links, HTML and the final URL.

from collections import defaultdict
from html.parser import HTMLParser
from urllib.parse import urljoin

import httpx

from .rules import RuleSet


class PageSignals(HTMLParser):
    def __init__(self, url: str):
        super().__init__(convert_charrefs=True)
        self.url = url
        self.meta = defaultdict(list)
        self.scripts = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "meta":
            name = attrs.get("name") or attrs.get("property") or attrs.get("http-equiv")
            if name and attrs.get("content") is not None:
                self.meta[name.lower()].append(attrs["content"])
        if tag == "script" and attrs.get("src"):
            self.scripts.append(urljoin(self.url, attrs["src"]))


def detect(response: httpx.Response, rules: RuleSet) -> list[dict]:
    page = PageSignals(str(response.url))
    page.feed(response.text)
    headers = defaultdict(list)
    for key, value in response.headers.multi_items():
        headers[key.lower()].append(value)
    cookies = defaultdict(list)
    for cookie in response.cookies.jar:
        cookies[cookie.name.lower()].append(cookie.value)
    signals = {
        "headers": headers, "cookies": cookies, "meta": page.meta,
        "scriptSrc": {"": page.scripts}, "html": {"": [response.text]},
        "url": {"": [str(response.url)]},
    }
    evidence = {}
    for name, patterns in rules.patterns.items():
        confidence, version = 0, ""
        for field, key, pattern in patterns:
            for value in signals[field].get(key, []):
                match = pattern.search(value)
                if match is not None:
                    confidence += pattern.confidence
                    version = version or pattern.get_version(match)
                    break
        if confidence:
            evidence[name] = (min(100, confidence), version)
    return rules.resolve(evidence)
