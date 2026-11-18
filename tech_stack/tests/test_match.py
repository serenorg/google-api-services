# ABOUTME: Detects Shopify end to end from a saved real public store page.
# ABOUTME: Exercises handmade rules, versions, confidence and technology relationships.

import json
from pathlib import Path

import httpx

from tech_stack.match import detect
from tech_stack.rules import RuleSet


def test_saved_shopify_store(tmp_path):
    # Independently written test rules, not copied from the GPL fingerprint set.
    technologies = {
        "Shopify": {
            "cats": [6], "website": "https://shopify.com",
            "meta": {"shopify-digital-wallet": r".*\;confidence:50"},
            "scriptSrc": r"cdn\.shopify\.com/\;confidence:50",
            "implies": r"Cart Functionality\;confidence:75", "excludes": "Legacy Cart",
        },
        "Cart Functionality": {"cats": [6]},
        "Shopify Checkout": {
            "requires": ["Unknown platform", "Shopify"],
            "meta": {"shopify-digital-wallet": ""},
        },
        "Commerce Extension": {
            "requiresCategory": [6], "scriptSrc": r"cdn\.shopify\.com/",
        },
        "Missing Prerequisite": {
            "requires": "Unknown platform", "meta": {"shopify-digital-wallet": ""},
        },
        "Legacy Cart": {"html": "shopify-digital-wallet", "implies": "Legacy Extension"},
        "Legacy Extension": {},
        "Shopify Script Loader": {
            "scriptSrc": r"modules/v(\d+)/loader\..*\;version:\1\;confidence:35",
        },
        "Shopify Store URL": {"url": r"^https://www\.tattly\.com/"},
    }
    rule_dir = tmp_path / "rules"
    (rule_dir / "technologies").mkdir(parents=True)
    (rule_dir / "technologies" / "test.json").write_text(json.dumps(technologies))
    (rule_dir / "categories.json").write_text(json.dumps({"6": {"name": "Ecommerce", "groups": [3]}}))
    (rule_dir / "groups.json").write_text(json.dumps({"3": {"name": "Web development"}}))
    response = httpx.Response(
        200, content=(Path(__file__).parent / "fixtures" / "tattly.html").read_bytes(),
        request=httpx.Request("GET", "https://www.tattly.com/"),
    )
    matches = {item["name"]: item for item in detect(response, RuleSet.load(rule_dir))}
    assert set(matches) == {
        "Shopify", "Cart Functionality", "Shopify Checkout", "Commerce Extension",
        "Shopify Script Loader", "Shopify Store URL",
    }
    assert matches["Shopify"]["confidence"] == 100
    assert matches["Cart Functionality"]["confidence"] == 75
    assert matches["Shopify Script Loader"]["version"] == "2"
    assert matches["Shopify Script Loader"]["confidence"] == 35
    assert matches["Shopify"]["categories"] == [
        {"id": 6, "name": "Ecommerce", "groups": [{"id": 3, "name": "Web development"}]},
    ]
