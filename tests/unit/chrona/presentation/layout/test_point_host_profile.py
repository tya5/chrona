from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.model import Measurement, PointHostMode
from chrona.presentation.layout.profile import resolve_layout_profile
from chrona.resources import schema_validator


ROOT = Path(__file__).parents[5]
SOURCES = {"title", "table", "timeline", "timeline-axis", "legend", "notes"}
THEME = {"body": {"values": {name: {"type": "number", "value": number} for name, number in {
    "spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24, "panel.minimum": 180,
}.items()}}}


def profile():
    return yaml.safe_load((ROOT / "conformance/layout-profile-intent-v0.2.yaml").read_text(encoding="utf-8"))


def resolve(value):
    return resolve_layout_profile(value, available_sources=SOURCES, theme=THEME)


def manifest(value):
    measurements = {source: Measurement(*(Decimal(n) for n in (10, 20, 40, 10, 20, 40)),
                                        Decimal(12), Decimal(12))
                    for source in SOURCES}
    return solve_layout(resolve(value), viewport_inline=1200, viewport_block=800, measurements=measurements)


def test_point_host_profile_is_closed_and_accepts_only_the_opt_in():
    value = profile()
    validator = schema_validator("layout-profile-v0.10.schema.yaml")
    opted_in = deepcopy(value)
    opted_in["reviewSurface"]["marks"] = {"points": {"host": "span-when-inside"}}
    assert not list(validator.iter_errors(opted_in))
    for marks in ({"points": {"host": "nearest"}}, {"points": {"host": "span-when-inside", "extra": True}},
                  {"unknown": {}}, {"points": {"unknown": True}}):
        invalid = deepcopy(value)
        invalid["reviewSurface"]["marks"] = marks
        assert list(validator.iter_errors(invalid))


def test_point_host_policy_is_default_off_and_serializes_only_when_enabled():
    omitted = manifest(profile())
    assert omitted.point_host_mode is None
    assert b'"marks"' not in omitted.canonical_bytes()

    opted_in = profile()
    opted_in["reviewSurface"]["marks"] = {"points": {"host": "span-when-inside"}}
    enabled = manifest(opted_in)
    assert enabled.point_host_mode is PointHostMode.SPAN_WHEN_INSIDE
    assert b'"marks":{"points":{"host":"span-when-inside"}}' in enabled.canonical_bytes()
