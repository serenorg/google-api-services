# ABOUTME: Checks contact extraction on two captured real business pages.
# ABOUTME: Source addresses and 2026-11-18 capture dates are recorded in each fixture.

import asyncio
import os
from pathlib import Path
import re

import httpx

from shared.billing import billed
from shared.config import get_settings
from web_contacts.extract import empty_contacts, extract_contacts
from web_contacts.main import ContactsRequest, app
from web_contacts.pages import domain, site_links
from bs4 import BeautifulSoup
from decimal import Decimal


def test_extract_real_business_pages():
    fixtures = Path(__file__).parent / "fixtures"
    examples = (
        ("heritage850", "https://www.heritage850.com/about-us", "hello@heritage850.com", "8509077500", "instagram", {"Lance Rezmer", "Hannah Rowland"}),
        ("larsonplumbing", "https://www.larsonplumbing.net/about-us", "info@larsonplumbing.net", "8132420911", "facebook", {"Chris Larson", "Vonda Larson"}),
    )
    results = []
    for filename, url, email, phone, platform, owners in examples:
        html = (fixtures / (filename + ".html")).read_text()
        found = extract_contacts(html, url)
        assert email in found["emails"]
        assert phone in [re.sub(r"\D", "", value) for value in found["phones"]]
        assert found["social_links"][platform]
        assert {person["name"] for person in found["owners"]} == owners
        assert all(address.endswith("@" + domain(url)) for address in found["emails"])
        soup = BeautifulSoup(html, "html.parser")
        links = site_links([a["href"] for a in soup.select("a[href]")], url)
        assert len(links) <= 5
        assert all(domain(link) == domain(url) for link in links)
        # One malformed anchor must not discard a real page's valid contacts or links.
        malformed = '<a href="http://[bad">Broken</a><a href="https://example.com:bad/contact">Broken port</a>'
        assert extract_contacts(html + malformed, url) == found
        assert site_links(["http://[bad", "https://example.com:bad/contact", *links], url) == links
        results.append(found)
    assert billed(results, len(results), Decimal("0.002"))["billing"]["cost"] == "0.004"

    # Page addresses for the same site cannot become separate billable sites.
    root = "https://www.heritage850.com/"
    assert ContactsRequest(urls=[root, root + "#team", root + "about-us?from=search", "http://heritage850.com:80/"]).urls == [root]
    assert ContactsRequest(urls=["https://www.heritage850.com:443/#team", root]).urls == ["https://www.heritage850.com:443/"]
    # Copyright ranges, dates, ZIP codes and business identifiers are not contacts.
    for text in (
        "Copyright 2015-2026 Acme", "Copyright 2015 – 2026 Acme", "Updated 2026-11-18",
        "Order number: 1234567890", "License: 123-456-7890", "ZIP: 12345-6789",
        "Account 1234567", "IP: 123.123.123.123",
    ):
        assert extract_contacts("<p>" + text + "</p>", root) == empty_contacts()
    assert extract_contacts("<p>Call: 555-0123</p>", root)["phones"] == ["555-0123"]
    assert extract_contacts("<p>Phone: 8509077500</p>", root)["phones"] == ["8509077500"]

    previous = os.environ.get("GATEWAY_SECRET")
    os.environ["GATEWAY_SECRET"] = "test-only-web-contacts-secret"
    get_settings.cache_clear()
    try:
        async def check_routes():
            # Exercise the actual ASGI app directly, without a TestClient startup thread.
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://service") as client:
                assert (await client.get("/health")).json()["service"] == "web-contacts"
                assert (await client.post("/contacts", json={"urls": [examples[0][1]]})).status_code == 401
                assert (await client.post("/contacts", json={}, headers={"X-Seren-Gateway-Secret": "wrong"})).status_code == 401
                headers = {"X-Seren-Gateway-Secret": "test-only-web-contacts-secret"}
                for urls in ([], [examples[0][1]] * 26, ["file:///etc/passwd"], ["https://user:password@example.com/"], ["http://example.com:bad/"]):
                    assert (await client.post("/contacts", json={"urls": urls}, headers=headers)).status_code == 422
                # The real shared fetcher refuses these addresses before making a connection.
                response = await client.post("/contacts", json={"urls": ["http://127.0.0.1/", "http://127.0.0.1/#team"]}, headers=headers)
                assert response.status_code == 200
                assert response.json()["billing"]["cost"] == "0.000"
                assert len(response.json()["data"]["sites"]) == 1
                assert response.json()["data"]["sites"][0]["sources"] == []
                os.environ["GATEWAY_SECRET"] = ""
                get_settings.cache_clear()
                assert (await client.post("/contacts", json={"urls": [examples[0][1]]}, headers=headers)).status_code == 503
        asyncio.run(check_routes())
    finally:
        if previous is None:
            os.environ.pop("GATEWAY_SECRET", None)
        else:
            os.environ["GATEWAY_SECRET"] = previous
        get_settings.cache_clear()
