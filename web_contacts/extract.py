# ABOUTME: Finds business emails, phones, social links and owners without a model.
# ABOUTME: Uses visible page content, contact links and schema.org JSON-LD.

import json
import re
from urllib.parse import unquote, urljoin, urlsplit

from bs4 import BeautifulSoup

from .pages import domain


_EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<![\w\d])\+?\d[\d ()\u00a0.\-]{5,}\d(?![\w\d])")
_NAME = r"[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+(?:['’\-][A-ZÀ-ÖØ-Þ]?[a-zà-öø-ÿ]+)*\s+[A-ZÀ-ÖØ-Þ][a-zà-öø-ÿ]+(?:['’\-][A-ZÀ-ÖØ-Þ]?[a-zà-öø-ÿ]+)*"
_ROLE = r"(?i:Owner|Founder|CEO|President)"
_GAP = r"\s*(?:[,|:/–—\-]\s*)?"
_OWNER_PATTERNS = (
    re.compile(rf"\b(?P<name>{_NAME}){_GAP}(?P<role>{_ROLE})\b"),
    # Pipes and conjunctions after a role introduce other titles or descriptions.
    re.compile(rf"\b(?P<role>{_ROLE})\s*(?:[:,–—\-]\s*)?(?P<name>{_NAME})\b"),
)
_SOCIAL_HOSTS = {
    "facebook.com": "facebook", "instagram.com": "instagram",
    "x.com": "twitter", "twitter.com": "twitter", "linkedin.com": "linkedin",
    "youtube.com": "youtube", "youtu.be": "youtube", "tiktok.com": "tiktok",
}


def empty_contacts() -> dict:
    return {"emails": [], "phones": [], "social_links": {}, "owners": []}


def _json_people(value, owners: list[dict], *, founder=False):
    if isinstance(value, list):
        for item in value:
            _json_people(item, owners, founder=founder)
    elif isinstance(value, dict):
        types = value.get("@type", [])
        types = types if isinstance(types, list) else [types]
        person = any(str(t).rstrip("/").rsplit("/", 1)[-1] == "Person" for t in types)
        name = value.get("name")
        if isinstance(name, str) and name.strip() and (person or founder):
            role = "Founder" if founder else value.get("jobTitle", "Person")
            owners.append({"name": " ".join(name.split()), "role": role if isinstance(role, str) else "Person"})
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                _json_people(item, owners, founder=key == "founder")
            elif key == "founder" and isinstance(item, str) and re.fullmatch(_NAME, item.strip()):
                owners.append({"name": item.strip(), "role": "Founder"})


def extract_contacts(html: str, url: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    result = empty_contacts()
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            _json_people(json.loads(script.get_text()), result["owners"])
        except (ValueError, RecursionError):
            pass
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    text = " ".join(soup.stripped_strings)
    links = [a["href"] for a in soup.select("a[href]")]
    email_text = text + "\n" + "\n".join(unquote(href) for href in links if href.lower().startswith("mailto:"))
    host = domain(url)
    for email in _EMAIL.findall(email_text):
        email = email.lower()
        mailbox_host = email.rsplit("@", 1)[1]
        if mailbox_host == host or mailbox_host.endswith("." + host):
            result["emails"].append(email)
    # A tel link is direct site evidence; text candidates need seven displayed digits.
    phones = [unquote(href[4:]).split(";", 1)[0].split("?", 1)[0].strip() for href in links if href.lower().startswith("tel:")]
    phones.extend(match.group().strip() for match in _PHONE.finditer(text))
    seen_digits = set()
    for phone in phones:
        digits = re.sub(r"\D", "", phone)
        if 7 <= len(digits) <= 15 and digits not in seen_digits:
            seen_digits.add(digits)
            result["phones"].append(phone)
    for href in links:
        link = urljoin(url, href)
        try:
            parsed = urlsplit(link)
        except ValueError:
            continue
        social_host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme not in ("http", "https") or parsed.username or parsed.password:
            continue
        for allowed, platform in _SOCIAL_HOSTS.items():
            if social_host == allowed or social_host.endswith("." + allowed):
                if platform == "linkedin" and not parsed.path.startswith(("/company/", "/in/")):
                    continue
                result["social_links"].setdefault(platform, []).append(link)
                break
    for pattern in _OWNER_PATTERNS:
        for match in pattern.finditer(text):
            result["owners"].append({"name": " ".join(match["name"].split()), "role": match["role"]})
    result["emails"] = sorted(set(result["emails"]))
    for platform, values in result["social_links"].items():
        result["social_links"][platform] = sorted(set(values))
    result["owners"] = [dict(item) for item in dict.fromkeys(tuple(owner.items()) for owner in result["owners"])]
    return result
