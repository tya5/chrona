"""Explicit pre-#1294 axis policy for tests of independent render rules.

These fixtures keep historical multi-tier output stable without making the
packaged preset itself an oracle for the old declaration.
"""
from __future__ import annotations

from typing import Any


def use_legacy_six_tier_axis(parts: dict[str, Any]) -> dict[str, Any]:
    """Restore the former quarter/month axis on a synthetic bundle in place."""
    parts["view"]["body"]["axis"] = {
        "tiers": [
            {"unit": "quarter", "every": 1, "role": "band", "typographyRole": "axisQuarter"},
            {"unit": "quarter", "every": 1, "role": "grid-major"},
            {
                "unit": "quarter", "every": 1, "role": "labels", "typographyRole": "axisQuarter",
                "label": {"form": "year-quarter", "align": "center", "overflow": "visible-overflow",
                          "orientation": "horizontal"},
            },
            {"unit": "month", "every": 1, "role": "band", "typographyRole": "axisMonth"},
            {
                "unit": "month", "every": 1, "role": "labels", "typographyRole": "axisMonth",
                "label": {"form": "short-month", "align": "start", "overflow": "thin-with-record",
                          "orientation": "horizontal"},
            },
            {"unit": "month", "every": 1, "role": "grid-minor"},
        ]
    }
    return parts
