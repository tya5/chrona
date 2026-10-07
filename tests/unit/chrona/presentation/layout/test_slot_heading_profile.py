"""The slot heading declaration: parsed, validated at exact pointers, recorded with its node, moves nothing (#1064).

Profiles are built here from plain dictionaries; nothing reads `examples/`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.model import LayoutError, Measurement, SlotHeading
from chrona.presentation.layout.profile import LayoutBase, resolve_layout_profile

SOURCES = {"title", "table", "timeline", "timeline-axis", "legend", "notes", "annotations", "summary"}
THEME = {"body": {"values": {name: {"type": "number", "value": value} for name, value in
                             {"spacing.m": 16, "spacing.l": 24}.items()}}}


def m(i, b):
    return Measurement(Decimal(i) / 2, Decimal(i), Decimal(i) * 2, Decimal(b) / 2, Decimal(b), Decimal(b) * 2)


MEASUREMENTS = {"title": m(300, 40), "notes": m(120, 30), "annotations": m(200, 60), "legend": m(200, 20)}


def slot(node_id: str, source: str, **extra) -> dict:
    return {"id": node_id, "kind": "slot", "source": source, "inlineSize": "content", "blockSize": "content",
            "place": {"inline": "start", "block": "start", "safety": "safe"}, "priority": extra.pop("priority", "required"),
            "overflow": "visible-overflow", **extra}


def profile(*children: dict) -> dict:
    return {"version": "chrona/layout-profile/v0.10", "id": "headings", "flowDirection": "horizontal",
            "dependencyNetworkFlowDirection": "horizontal", "requiredThemeTokens": ["spacing.l", "spacing.m"],
            "reviewSurface": {"rowDistribution": "pack", "backgroundExtents": {
                "rowBand": "table", "groupBand": "timeline", "groupHeaderBand": "both", "calendarClosed": "timeline"},
                "annotationRouting": {"maxBends": 4, "maxDetourRatio": 2}},
            "root": {"id": "page", "kind": "column", "inlineSize": "fill", "blockSize": "fill",
                     "gap": {"token": "spacing.m"}, "padding": {"token": "spacing.l"}, "alignItems": "stretch",
                     "justifyContent": "start", "children": list(children)}}


def solved(value: dict):
    resolved = resolve_layout_profile(value, available_sources=SOURCES, theme=THEME)
    return solve_layout(resolved, viewport_inline=1600, viewport_block=900, measurements=MEASUREMENTS)


def bounds(manifest) -> dict:
    return {item.node_id: item.bounds for item in manifest.decisions}


def test_a_heading_is_recorded_with_its_slot_and_moves_nothing() -> None:
    plain = solved(profile(slot("title", "title"), slot("notes", "notes")))
    headed = solved(profile(slot("title", "title"),
                            slot("notes", "notes", heading={"text": "Notes", "align": "center", "block": "header-row"})))

    assert bounds(headed) == bounds(plain)
    assert {item.node_id: item.heading for item in headed.decisions if item.heading} == {
        "notes": SlotHeading("Notes", "center", "header-row")}
    assert all(item.heading is None for item in plain.decisions)


def test_the_defaults_are_start_and_top() -> None:
    manifest = solved(profile(slot("notes", "notes", heading={"text": "Notes"})))

    assert next(item.heading for item in manifest.decisions if item.node_id == "notes") == SlotHeading("Notes", "start", "top")


def test_axis_tier_is_an_optional_in_place_block_mode() -> None:
    manifest = solved(profile(slot("notes", "notes", heading={"text": "Notes", "block": "axis-tier"})))
    assert next(item.heading for item in manifest.decisions if item.node_id == "notes") == SlotHeading("Notes", "start", "axis-tier")


def test_the_manifest_names_a_heading_only_when_one_is_declared() -> None:
    plain = solved(profile(slot("notes", "notes"))).canonical_bytes()
    headed = solved(profile(slot("notes", "notes", heading={"text": "Notes"}))).canonical_bytes()

    assert b'"heading"' not in plain
    assert b'"heading":{"align":"start","block":"top","text":"Notes"}' in headed


@pytest.mark.parametrize(("heading", "pointer"), [
    (True, "/root/children/0/heading"),
    ([], "/root/children/0/heading"),
    ("Notes", "/root/children/0/heading"),
    ({}, "/root/children/0/heading"),
    ({"text": ""}, "/root/children/0/heading/text"),
    ({"text": "x" * 81}, "/root/children/0/heading/text"),
    ({"text": "line\nbreak"}, "/root/children/0/heading/text"),
    ({"text": 7}, "/root/children/0/heading/text"),
    ({"text": "Notes", "role": "slot-heading"}, "/root/children/0/heading/role"),
    ({"text": "Notes", "align": "left"}, "/root/children/0/heading/align"),
    ({"text": "Notes", "block": "bottom"}, "/root/children/0/heading/block"),
])
def test_a_malformed_heading_fails_at_its_exact_pointer(heading, pointer) -> None:
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(profile(slot("notes", "notes", heading=heading)), available_sources=SOURCES, theme=THEME)

    assert (error.value.diagnostic_id, error.value.path) == ("E_LAYOUT_SCHEMA", pointer)


@pytest.mark.parametrize("source", ["notes", "annotations", "legend", "summary"])
def test_the_supported_sources_take_a_heading(source) -> None:
    resolve_layout_profile(profile(slot("one", source, heading={"text": "Caption"})), available_sources=SOURCES, theme=THEME)


@pytest.mark.parametrize("source", ["title", "table", "timeline", "timeline-axis"])
def test_a_source_whose_block_other_rules_own_rejects_a_heading(source) -> None:
    value = profile(slot("one", source, heading={"text": "Caption"}))
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(value, available_sources=SOURCES, theme=THEME)

    assert (error.value.diagnostic_id, error.value.path) == ("E_LAYOUT_SLOT_HEADING_SOURCE", "/root/children/0/heading")


def derived(base: dict, overrides: dict) -> tuple[dict, dict]:
    identity = "sha256:" + "0" * 64
    value = {"version": "chrona/layout-profile/v0.10", "id": "derived", "flowDirection": "horizontal",
             "dependencyNetworkFlowDirection": "horizontal", "requiredThemeTokens": base["requiredThemeTokens"],
             "reviewSurface": base["reviewSurface"],
             "extends": {"id": "headings", "kind": "layout-profile", "store": {"provider": "local", "identity": "local"},
                         "address": "layouts/headings.yaml", "revision": {"token": "main"}, "contentIdentity": identity},
             "overrides": overrides}
    return value, {"headings": LayoutBase(base, "main", identity)}


def test_a_derived_profile_replaces_the_copy_alone_or_adds_a_heading() -> None:
    base = profile(slot("notes", "notes", heading={"text": "Notes", "align": "end"}), slot("legend", "legend"))
    value, bases = derived(base, {"notes": {"heading": {"text": "Remarks"}}, "legend": {"heading": {"text": "Key"}}})

    resolved = resolve_layout_profile(value, available_sources=SOURCES, theme=THEME, bases=bases)
    manifest = solve_layout(resolved, viewport_inline=1600, viewport_block=900, measurements=MEASUREMENTS)

    assert {item.node_id: item.heading for item in manifest.decisions if item.heading} == {
        "notes": SlotHeading("Remarks", "start", "top"),  # the whole declaration is replaced, not merged
        "legend": SlotHeading("Key", "start", "top")}


def test_a_derived_profile_cannot_give_an_unsupported_source_a_heading_or_a_malformed_one() -> None:
    base = profile(slot("title", "title"), slot("notes", "notes"))
    value, bases = derived(base, {"title": {"heading": {"text": "Nope"}}})
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(value, available_sources=SOURCES, theme=THEME, bases=bases)
    assert error.value.diagnostic_id == "E_LAYOUT_SLOT_HEADING_SOURCE"

    value, bases = derived(base, {"notes": {"heading": {"text": "", "block": "top"}}})
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(value, available_sources=SOURCES, theme=THEME, bases=bases)
    assert (error.value.diagnostic_id, error.value.path) == ("E_LAYOUT_SCHEMA", "/overrides/notes/heading/text")
