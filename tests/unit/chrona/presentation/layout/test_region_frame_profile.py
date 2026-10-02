"""The region frame declaration: parsed, validated at exact pointers, recorded with its node, moves nothing (#889).

Profiles are built here from plain dictionaries; nothing reads `examples/`.
"""
from __future__ import annotations

from copy import deepcopy
from decimal import Decimal

import pytest

from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.model import LayoutError, Measurement, RegionFrame
from chrona.presentation.layout.profile import LayoutBase, resolve_layout_profile

SOURCES = {"title", "table", "timeline", "timeline-axis", "legend", "notes"}
THEME = {"body": {"values": {name: {"type": "number", "value": value} for name, value in
                             {"spacing.none": 0, "spacing.s": 8, "spacing.m": 16, "spacing.l": 24}.items()}}}
TOKENS = ["spacing.l", "spacing.m", "spacing.s"]


def m(i, b):
    return Measurement(Decimal(i) / 2, Decimal(i), Decimal(i) * 2, Decimal(b) / 2, Decimal(b), Decimal(b) * 2)


MEASUREMENTS = {"a": m(300, 40), "b": m(200, 60), "title": m(300, 40), "notes": m(120, 30)}


def slot(node_id: str, source: str, **extra) -> dict:
    return {"id": node_id, "kind": "slot", "source": source, "inlineSize": "content", "blockSize": "content",
            "place": {"inline": "start", "block": "start", "safety": "safe"}, "priority": extra.pop("priority", "required"),
            "overflow": "visible-overflow", **extra}


def container(kind: str, node_id: str, children: list, **extra) -> dict:
    node = {"id": node_id, "kind": kind, "inlineSize": "fill", "blockSize": "content", "padding": {"token": "spacing.m"},
            "children": children, **extra}
    if kind in {"row", "column", "grid", "flow"}:
        node.update(gap={"token": "spacing.s"}, alignItems="start", justifyContent="start")
    if kind == "grid":
        node.update(columnTracks=["content", "content"], rowTracks=["content"])
        for index, child in enumerate(children):
            child["cell"] = {"column": index + 1, "row": 1}
    if kind == "flow":
        node["itemMinInlineSize"] = {"token": "spacing.l"}
    return node


def used_tokens(value) -> list:
    """The exact, sorted Theme tokens a profile fragment references."""
    if isinstance(value, dict):
        if set(value) == {"token"}:
            return [value["token"]]
        return [token for item in value.values() for token in used_tokens(item)]
    if isinstance(value, list):
        return [token for item in value for token in used_tokens(item)]
    return []


def profile(panel: dict, *, extra: list | None = None) -> dict:
    root_tokens = ["spacing.l", "spacing.m"]
    return {"version": "chrona/layout-profile/v0.10", "id": "frames", "flowDirection": "horizontal",
            "dependencyNetworkFlowDirection": "horizontal",
            "requiredThemeTokens": sorted({*root_tokens, *used_tokens([panel, *(extra or [])])}),
            "reviewSurface": {"rowDistribution": "pack", "backgroundExtents": {
                "rowBand": "table", "groupBand": "timeline", "groupHeaderBand": "both", "calendarClosed": "timeline"},
                "annotationRouting": {"maxBends": 4, "maxDetourRatio": 2}},
            "root": {"id": "page", "kind": "column", "inlineSize": "fill", "blockSize": "fill",
                     "gap": {"token": "spacing.m"}, "padding": {"token": "spacing.l"}, "alignItems": "stretch",
                     "justifyContent": "start", "children": [panel, *(extra or [])]}}


def solved(value: dict, measurements=MEASUREMENTS):
    resolved = resolve_layout_profile(value, available_sources=SOURCES, theme=THEME)
    return solve_layout(resolved, viewport_inline=1600, viewport_block=900, measurements=measurements)


def bounds(manifest) -> dict:
    return {item.node_id: item.bounds for item in manifest.decisions}


def panel(kind: str, *, frame: dict | None) -> dict:
    node = container(kind, "panel", [slot("a", "title"), slot("b", "legend")])
    if frame is not None:
        node["frame"] = frame
    return node


@pytest.mark.parametrize("kind", ["row", "column", "grid", "flow", "overlay"])
def test_a_frame_moves_nothing_on_any_container_kind(kind) -> None:
    plain = solved(profile(panel(kind, frame=None)))
    framed = solved(profile(panel(kind, frame={"inset": {"token": "spacing.s"}})))

    assert bounds(framed) == bounds(plain)
    assert [item.node_id for item in framed.decisions] == [item.node_id for item in plain.decisions]
    assert {item.node_id: item.frame for item in framed.decisions if item.frame} == {
        "panel": RegionFrame(Decimal(8), True)}
    assert all(item.frame is None for item in plain.decisions)


def test_a_frame_on_a_slot_records_the_slot_as_populated() -> None:
    value = profile(slot("title", "title", frame={}))

    manifest = solved(value)

    assert {item.node_id: item.frame for item in manifest.decisions if item.frame} == {"title": RegionFrame(Decimal(0), True)}
    assert bounds(manifest) == bounds(solved(profile(slot("title", "title"))))


def test_frames_nest_and_each_node_records_its_own_inset() -> None:
    inner = container("row", "inner", [slot("a", "title")], frame={"inset": 2})
    outer = container("column", "outer", [inner, slot("b", "legend")], frame={"inset": 6})

    manifest = solved(profile(outer))

    assert {item.node_id: item.frame for item in manifest.decisions if item.frame} == {
        "outer": RegionFrame(Decimal(6), True), "inner": RegionFrame(Decimal(2), True)}
    assert [item.node_id for item in manifest.decisions if item.frame] == ["outer", "inner"]


def test_two_sibling_panels_are_separated_by_exactly_the_parent_gap() -> None:
    row = container("row", "masthead", [container("row", "left", [slot("a", "title")], frame={}),
                                        container("row", "right", [slot("b", "legend")], frame={})])
    row["gap"] = {"token": "spacing.l"}

    placed = bounds(solved(profile(row)))

    assert placed["right"].inline - (placed["left"].inline + placed["left"].inline_size) == 24


def test_an_absent_optional_slot_leaves_an_unpopulated_container_and_moves_nothing() -> None:
    node = container("row", "notes-panel", [slot("notes", "notes", priority="optional")], frame={})
    sibling = slot("title", "title")
    without = {name: value for name, value in MEASUREMENTS.items() if name != "notes"}
    framed = solved(profile(node, extra=[sibling]), without)
    unframed_node = deepcopy(node)
    del unframed_node["frame"]
    unframed = solved(profile(unframed_node, extra=[deepcopy(sibling)]), without)

    assert [item.node_id for item in framed.decisions] == ["page", "notes-panel", "title"]
    assert {item.node_id: item.frame for item in framed.decisions if item.frame} == {"notes-panel": RegionFrame(Decimal(0), False)}
    assert bounds(framed) == bounds(unframed)
    present = solved(profile(node, extra=[sibling]))
    assert {item.node_id: item.frame for item in present.decisions if item.frame} == {"notes-panel": RegionFrame(Decimal(0), True)}


def test_a_slot_that_collapsed_to_no_area_does_not_populate_its_panel() -> None:
    node = container("row", "empty", [slot("a", "title")], frame={})
    collapsed = {**MEASUREMENTS, "a": m(0, 0)}

    manifest = solved(profile(node), collapsed)

    assert {item.node_id: item.frame for item in manifest.decisions if item.frame} == {"empty": RegionFrame(Decimal(0), False)}
    assert bounds(manifest)["a"].inline_size == 0
    present = solved(profile(deepcopy(node)))
    assert {item.node_id: item.frame for item in present.decisions if item.frame} == {"empty": RegionFrame(Decimal(0), True)}


def test_the_manifest_names_a_frame_only_when_one_is_declared() -> None:
    plain = solved(profile(panel("row", frame=None))).canonical_bytes()
    framed = solved(profile(panel("row", frame={"inset": 4}))).canonical_bytes()

    assert b'"frame":' not in plain
    assert b'"frame":{"inset":"4.000","populated":true}' in framed


def test_the_inset_is_a_collected_distance_and_a_token_resolves_through_the_theme() -> None:
    literal = resolve_layout_profile(profile(panel("row", frame={"inset": 4})), available_sources=SOURCES, theme=THEME)
    token = resolve_layout_profile(profile(panel("row", frame={"inset": {"token": "spacing.s"}})), available_sources=SOURCES, theme=THEME)
    empty = resolve_layout_profile(profile(panel("row", frame={})), available_sources=SOURCES, theme=THEME)

    assert literal.distances["/root/children/0/frame/inset"] == 4
    assert "/root/children/0/frame/inset" in literal.literal_distance_paths
    assert token.distances["/root/children/0/frame/inset"] == 8
    assert "/root/children/0/frame/inset" not in empty.distances


@pytest.mark.parametrize(("frame", "pointer"), [
    (True, "/root/children/0/frame"),
    ([], "/root/children/0/frame"),
    ("panel", "/root/children/0/frame"),
    ({"colour": "red"}, "/root/children/0/frame/colour"),
    ({"inset": -1}, "/root/children/0/frame/inset"),
    ({"inset": "4"}, "/root/children/0/frame/inset"),
    ({"inset": True}, "/root/children/0/frame/inset"),
    ({"inset": 1000001}, "/root/children/0/frame/inset"),
    ({"inset": {"token": "9bad"}}, "/root/children/0/frame/inset"),
    ({"inset": {"token": "spacing.s", "extra": 1}}, "/root/children/0/frame/inset"),
])
def test_a_malformed_frame_fails_at_its_exact_pointer(frame, pointer) -> None:
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(profile(panel("row", frame=frame)), available_sources=SOURCES, theme=THEME)

    assert (error.value.diagnostic_id, error.value.path) == ("E_LAYOUT_SCHEMA", pointer)


def test_a_malformed_frame_deep_in_the_tree_and_on_a_slot_is_named_by_its_own_path() -> None:
    inner = container("row", "inner", [slot("a", "title", frame={"inset": -3})])
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(profile(container("column", "outer", [inner])), available_sources=SOURCES, theme=THEME)

    assert (error.value.diagnostic_id, error.value.path) == (
        "E_LAYOUT_SCHEMA", "/root/children/0/children/0/children/0/frame/inset")


def test_an_inset_token_the_profile_does_not_require_or_the_theme_lacks_is_a_token_error() -> None:
    not_required = profile(panel("row", frame={"inset": {"token": "spacing.none"}}))
    not_required["requiredThemeTokens"].remove("spacing.none")
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(not_required, available_sources=SOURCES, theme=THEME)
    assert (error.value.diagnostic_id, error.value.path) == ("E_LAYOUT_TOKEN_REQUIREMENT_MISSING", "/requiredThemeTokens")

    unavailable = profile(panel("row", frame={"inset": {"token": "frame.inset"}}))
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(unavailable, available_sources=SOURCES, theme=THEME)
    assert (error.value.diagnostic_id, error.value.path) == (
        "E_LAYOUT_TOKEN_REQUIREMENT_UNAVAILABLE", "/root/children/0/frame/inset")

    extraneous = profile(panel("row", frame={}))
    extraneous["requiredThemeTokens"] = sorted([*extraneous["requiredThemeTokens"], "spacing.none"])
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(extraneous, available_sources=SOURCES, theme=THEME)
    assert error.value.diagnostic_id == "E_LAYOUT_TOKEN_REQUIREMENT_EXTRANEOUS"


def derived(base: dict, overrides: dict) -> tuple[dict, dict]:
    identity = "sha256:" + "0" * 64
    value = {"version": "chrona/layout-profile/v0.10", "id": "derived", "flowDirection": "horizontal",
             "dependencyNetworkFlowDirection": "horizontal", "requiredThemeTokens": base["requiredThemeTokens"],
             "reviewSurface": base["reviewSurface"],
             "extends": {"id": "frames", "kind": "layout-profile", "store": {"provider": "local", "identity": "local"},
                         "address": "layouts/frames.yaml", "revision": {"token": "main"}, "contentIdentity": identity},
             "overrides": overrides}
    return value, {"frames": LayoutBase(base, "main", identity)}


def test_an_override_adds_or_replaces_a_frame_and_cannot_name_an_unknown_node() -> None:
    base = profile(panel("row", frame=None))
    value, bases = derived(base, {"panel": {"frame": {"inset": 3}}})
    resolved = resolve_layout_profile(value, available_sources=SOURCES, theme=THEME, bases=bases)
    manifest = solve_layout(resolved, viewport_inline=1600, viewport_block=900, measurements=MEASUREMENTS)
    assert {item.node_id: item.frame for item in manifest.decisions if item.frame} == {"panel": RegionFrame(Decimal(3), True)}

    replaced_base = profile(panel("row", frame={"inset": 9}))
    value, bases = derived(replaced_base, {"panel": {"frame": {}}})
    resolved = resolve_layout_profile(value, available_sources=SOURCES, theme=THEME, bases=bases)
    assert resolved.profile["root"]["children"][0]["frame"] == {}

    value, bases = derived(base, {"missing": {"frame": {}}})
    with pytest.raises(LayoutError) as error:
        resolve_layout_profile(value, available_sources=SOURCES, theme=THEME, bases=bases)
    assert error.value.diagnostic_id == "E_LAYOUT_OVERRIDE_UNKNOWN"

    # An override is not under a container union, so the schema itself names the exact path.
    for frame, pointer in ((True, "/overrides/panel/frame"), ({"colour": "red"}, "/overrides/panel/frame"),
                           ({"inset": -1}, "/overrides/panel/frame/inset"), ({"inset": "4"}, "/overrides/panel/frame/inset")):
        value, bases = derived(base, {"panel": {"frame": frame}})
        with pytest.raises(LayoutError) as error:
            resolve_layout_profile(value, available_sources=SOURCES, theme=THEME, bases=bases)
        assert (error.value.diagnostic_id, error.value.path) == ("E_LAYOUT_SCHEMA", pointer)


def test_the_frame_is_part_of_the_profile_identity() -> None:
    plain = resolve_layout_profile(profile(panel("row", frame=None)), available_sources=SOURCES, theme=THEME)
    framed = resolve_layout_profile(profile(panel("row", frame={})), available_sources=SOURCES, theme=THEME)

    assert plain.content_hash != framed.content_hash
