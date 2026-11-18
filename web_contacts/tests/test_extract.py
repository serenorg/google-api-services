# ABOUTME: Checks contact extraction on two captured real business pages.
# ABOUTME: Source addresses and 2026-11-18 capture dates are recorded in each fixture.

import os
from pathlib import Path
import re

from fastapi.testclient import TestClient

from shared.billing import billed
from shared.config import get_settings
from web_contacts.extract import extract_contacts
from web_contacts.main import app
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
        results.append(found)
    assert billed(results, len(results), Decimal("0.002"))["billing"]["cost"] == "0.004"

    previous = os.environ.get("GATEWAY_SECRET")
    os.environ["GATEWAY_SECRET"] = "test-only-web-contacts-secret"
    get_settings.cache_clear()
    try:
        with TestClient(app) as client:
            assert client.get("/health").json()["service"] == "web-contacts"
            assert client.post("/contacts", json={"urls": [examples[0][1]]}).status_code == 401
            assert client.post("/contacts", json={}, headers={"X-Seren-Gateway-Secret": "wrong"}).status_code == 401
            headers = {"X-Seren-Gateway-Secret": "test-only-web-contacts-secret"}
            for urls in ([], [examples[0][1]] * 26, ["file:///etc/passwd"], ["https://user:password@example.com/"]):
                assert client.post("/contacts", json={"urls": urls}, headers=headers).status_code == 422
            # The real shared fetcher refuses these addresses before making a connection.
            response = client.post("/contacts", json={"urls": ["http://127.0.0.1/"]}, headers=headers)
            assert response.status_code == 200
            assert response.json()["billing"]["cost"] == "0.000"
            assert response.json()["data"]["sites"][0]["sources"] == []
            os.environ["GATEWAY_SECRET"] = ""
            get_settings.cache_clear()
            assert client.post("/contacts", json={"urls": [examples[0][1]]}, headers=headers).status_code == 503
    finally:
        if previous is None:
            os.environ.pop("GATEWAY_SECRET", None)
        else:
            os.environ["GATEWAY_SECRET"] = previous
        get_settings.cache_clear()
