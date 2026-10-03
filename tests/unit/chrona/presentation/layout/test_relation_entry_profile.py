"""The `relationRouting.entry` declaration: parsed, defaulted, validated at its exact pointer (#1030).

Profiles are built from plain dictionaries; nothing reads `examples/`.
"""
from __future__ import annotations

import pytest

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.profile import resolve_layout_profile

from tests.unit.chrona.presentation.layout.test_region_frame_profile import (
    SOURCES, THEME, profile, slot, solved,
)


def with_routing(routing: dict | None) -> dict:
    value = profile(slot("a", "title"))
    if routing is not None:
        value["relationRouting"] = routing
    return value


@pytest.mark.parametrize(("routing", "expected"), [
    (None, "side-when-free"),
    ({"maxBends": 4, "maxDetourRatio": 2}, "side-when-free"),
    ({"maxBends": 4, "maxDetourRatio": 2, "entry": "any"}, "any"),
    ({"maxBends": 4, "maxDetourRatio": 2, "entry": "side-when-free"}, "side-when-free"),
])
def test_the_entry_policy_reaches_the_manifest_and_absent_means_any(routing, expected):
    assert solved(with_routing(routing)).relation_entry == expected


def test_the_default_adds_nothing_to_the_manifest_bytes_and_any_is_recorded():
    # (the profile hash differs between declarations; the routing payload is what is compared)
    for routing in (None, {"maxBends": 4, "maxDetourRatio": 2}, {"maxBends": 4, "maxDetourRatio": 2, "entry": "side-when-free"}):
        assert b'"entry"' not in solved(with_routing(routing)).canonical_bytes()
    explicit = solved(with_routing({"maxBends": 4, "maxDetourRatio": 2, "entry": "any"})).canonical_bytes()
    assert b'"entry":"any"' in explicit


@pytest.mark.parametrize("entry", ["nearest", "SIDE-WHEN-FREE", 1, None])
def test_an_unknown_entry_policy_fails_at_its_exact_pointer(entry):
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(with_routing({"maxBends": 4, "maxDetourRatio": 2, "entry": entry}),
                               available_sources=SOURCES, theme=THEME)
    assert (error.value.diagnostic_id, error.value.path) == ("E_LAYOUT_SCHEMA", "/relationRouting/entry")
