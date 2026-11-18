# ABOUTME: Serves bounded website contact extraction behind Seren gateway access.
# ABOUTME: Bills only sites with contacts at two tenths of one cent each.

from decimal import Decimal
from urllib.parse import urlsplit, urlunsplit

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field, field_validator

from shared.billing import billed
from shared.gateway_auth import require_gateway_secret

from .extract import empty_contacts, extract_contacts
from .pages import Batch, domain, read_pages


app = FastAPI(title="Website Contacts Service", version="1.0.0")


class ContactsRequest(BaseModel):
    urls: list[str] = Field(min_length=1, max_length=25)

    @field_validator("urls")
    @classmethod
    def public_web_urls(cls, urls):
        sites = {}
        for url in urls:
            parsed = urlsplit(url)
            if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("Use HTTP(S) website addresses without credentials")
            # Paths, queries and fragments identify pages, not additional sites.
            # Treat www and the default HTTP(S) ports as equivalent too.
            port = parsed.port
            key = (domain(url), None if port in (None, 80 if parsed.scheme == "http" else 443) else port)
            sites.setdefault(key, urlunsplit((parsed.scheme, parsed.netloc.lower(), "/", "", "")))
        return list(sites.values())


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "web-contacts"}


@app.post("/contacts", dependencies=[Depends(require_gateway_secret)])
async def contacts(request: ContactsRequest):
    batch = Batch()
    sites = []
    skipped = []
    for url in request.urls:
        if batch.paused:
            skipped.append(url)
            continue
        pages, errors = await read_pages(url, batch)
        site = {"url": url, **empty_contacts(), "sources": [], "errors": errors}
        for source, html in pages:
            found = extract_contacts(html, source)
            site["sources"].append(source)
            for key in ("emails", "phones", "owners"):
                for item in found[key]:
                    if item not in site[key]:
                        site[key].append(item)
            for platform, links in found["social_links"].items():
                target = site["social_links"].setdefault(platform, [])
                target.extend(link for link in links if link not in target)
        sites.append(site)
    items = sum(any(site[key] for key in ("emails", "phones", "social_links", "owners")) for site in sites)
    return billed({"sites": sites, "paused": batch.paused, "skipped": skipped}, items, Decimal("0.002"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_contacts.main:app", host="0.0.0.0", port=8008)
