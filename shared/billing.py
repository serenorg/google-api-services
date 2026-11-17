# ABOUTME: Wraps publisher results with their exact per-item dollar charge.
# ABOUTME: Exposes billing.cost in the format consumed by Seren Core.

from decimal import Decimal
from typing import Any


def billed(data: Any, items: int, unit_price: Decimal) -> dict:
    """Return data and a Decimal-priced billing summary without float rounding."""
    return {
        "data": data,
        "billing": {
            "items": items,
            "unit_price": str(unit_price),
            "cost": str(items * unit_price),
        },
    }
