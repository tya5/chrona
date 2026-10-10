"""Completed group-header text extents for the opt-in text band (#1283)."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.scene.serialization import scene_document, serialize_scene
from chrona.presentation.layout.model import LayoutError, Rect
from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt


def _source(*, long_group: str | None = None):
    source = sr.bunched_project(groups=2, per_group=2)
    for index in range(2):
        title = f"Group {index}"
        if long_group == f"team-{index}":
            title = "A deliberately long group header that reaches the table edge"
        source["entities"][f"team-{index}"]["title"] = title
    return source


def _parts(*, marked: bool = False, inset: float | None = None, extent: str = "text",
           vertical: bool = False, tab: tuple[float, str] | None = None,
           group_decoration: str = "none"):
    parts = sr.bundle("control-room-dark")
    parts["layout"]["reviewSurface"]["backgroundExtents"]["groupHeaderBand"] = extent
    body = parts["theme"]["body"]
    if inset is not None:
        body["values"]["header-inset"] = {"type": "number", "value": inset}
        body["roles"]["groupHeader"]["labelInset"] = "header-inset"
    if marked:
        body["values"]["ordinal-size"] = {"type": "number", "value": 22}
        base = body["roles"]["groupHeader"]
        body["roles"]["group-ordinal"] = {
            key: base[key] for key in
            ("fontFamily", "fontWeight", "lineHeight", "letterSpacing", "textTransform", "numericSpacing")
        }
        body["roles"]["group-ordinal"]["fontSize"] = "ordinal-size"
        body["colorBindings"]["group-ordinal.fill"] = "warning"
        parts["view"]["body"]["grouping"]["header"] = {"text": "{ordinal|group-ordinal} {title}"}
    if vertical:
        tt.with_vertical_groups(parts)
    if tab is not None:
        width, position = tab
        body["values"]["tab-inline"] = {"type": "number", "value": width}
        body["values"]["tab-opacity"] = {"type": "number", "value": 1}
        body["roles"]["group-tab"] = {
            "backgroundTreatment": "fill", "backgroundPaintOrder": 13,
            "tabInlineSize": "tab-inline", "opacity": "tab-opacity",
        }
        body["colorBindings"]["group-tab.fill"] = "warning"
        if position == "end":
            body["roles"]["group-tab"]["tabPosition"] = "end"
    parts["view"]["body"]["backgroundDecoration"] = {"rows": "none", "groups": group_decoration}
    return parts


def _render(tmp_path, parts, *, source=None, name="render", suppress_header_runs=False, monkeypatch=None):
    if suppress_header_runs:
        from decimal import Decimal
        import chrona.presentation.layout.surface_groups as groups

        original = groups.place_group_header_runs

        def suppress(**kwargs):
            return original(**{**kwargs, "size": Decimal(0), "bounded": True})

        monkeypatch.setattr(groups, "place_group_header_runs", suppress)
    output = tmp_path / name
    output.mkdir(parents=True, exist_ok=True)
    return sr.render(output, source or _source(), presentation=parts)


def _by_id(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def _assert_svg_bounds(rendered, scene_id):
    root = ET.fromstring(rendered.artifact.content)
    element = next(node for node in root.iter() if node.attrib.get("data-scene-id") == scene_id)
    scene = _by_id(rendered)[scene_id]
    for attribute, index in (("x", 0), ("y", 1), ("width", 2), ("height", 3)):
        assert float(element.attrib[attribute]) == pytest.approx(scene.bounds[index], abs=0.001)


def _install_legacy_geometry_replay(monkeypatch):
    """Replay the pre-#1283 three extent branches and full-Rect folded replacement in tests only."""
    import chrona.presentation.layout.surface_backgrounds as backgrounds
    import chrona.presentation.layout.surface_composer as composer

    def old_bounds(*, semantic_id, extent, source_bounds, table_bounds, timeline_bounds, text_bounds=None):
        # Frozen pre-#1283 implementation from the 5a7fff0 baseline: calendar validation and the three
        # existing whole-Rect extent choices. Keep this independent of the current implementation.
        if semantic_id in {"calendarClosed", "calendarException"}:
            if extent != "timeline":
                raise LayoutError("E_LAYOUT_BACKGROUND_EXTENT", "/layoutManifest/reviewSurface/backgroundExtents")
            return source_bounds, "timeline"
        table_inline, _, table_inline_size, _ = table_bounds
        timeline_inline, _, timeline_inline_size, _ = timeline_bounds
        if extent == "table":
            return Rect(Decimal(str(table_inline)), source_bounds.block,
                        Decimal(str(table_inline_size)), source_bounds.block_size), "table"
        if extent == "timeline":
            return Rect(Decimal(str(timeline_inline)), source_bounds.block,
                        Decimal(str(timeline_inline_size)), source_bounds.block_size), "timeline"
        if extent == "both":
            return (Rect(Decimal(str(table_inline)), source_bounds.block,
                         Decimal(str(timeline_inline + timeline_inline_size - table_inline)),
                         source_bounds.block_size), "review-surface")
        raise LayoutError("E_LAYOUT_BACKGROUND_EXTENT", "/layoutManifest/reviewSurface/backgroundExtents")

    def old_replace(shapes, update, *, extent="both"):
        placement_id = f"group-header-band:{update.source.group_id}"
        return tuple(replace(shape, bounds=update.header_bounds) if shape.placement_id == placement_id else shape
                     for shape in shapes)

    monkeypatch.setattr(backgrounds, "_background_bounds", old_bounds)
    monkeypatch.setattr(composer, "replace_group_header_band", old_replace)


def _assert_text_band(rendered, *, expected_group_ids=("team-0", "team-1")):
    items = _by_id(rendered)
    groups = {group.group_id: group for group in rendered.surface.groups}
    for group_id in expected_group_ids:
        band = items[f"group-header-band:{group_id}"]
        header = groups[group_id].header_bounds
        texts = [item for item in rendered.surface.primitives
                 if item.scene_id == f"group-header:{group_id}"
                 or item.scene_id.startswith(f"group-header:{group_id}#run")]
        right = max((item.bounds[0] + item.bounds[2] for item in texts), default=header[0])
        expected_right = min(header[0] + header[2], right)
        assert band.bounds[0] == pytest.approx(header[0])
        assert band.bounds[0] + band.bounds[2] == pytest.approx(expected_right)
        assert band.bounds[1] == pytest.approx(header[1])
        assert band.bounds[3] == pytest.approx(header[3])


@pytest.mark.parametrize("marked", [False, True], ids=["plain", "marked-runs"])
def test_text_band_uses_each_groups_completed_header_interval_in_scene_and_svg(tmp_path, marked):
    rendered = _render(tmp_path, _parts(marked=marked, inset=0.4))
    _assert_text_band(rendered)
    for group_id in ("team-0", "team-1"):
        _assert_svg_bounds(rendered, f"group-header-band:{group_id}")


@pytest.mark.parametrize("tab", [(30, "start"), (30, "end")], ids=["start-tab", "end-tab"])
@pytest.mark.parametrize("inset", [None, 2.0], ids=["absent-inset", "explicit-inset"])
def test_text_band_includes_tab_reservation_and_leading_inset(tmp_path, tab, inset):
    rendered = _render(tmp_path, _parts(inset=inset, tab=tab))
    _assert_text_band(rendered)
    items = _by_id(rendered)
    for group_id in ("team-0", "team-1"):
        band = items[f"group-header-band:{group_id}"]
        tab_shape = items[f"group-tab:{group_id}"]
        header = next(group for group in rendered.surface.groups if group.group_id == group_id).header_bounds
        assert band.bounds[0] == pytest.approx(header[0])
        assert band.bounds[0] + band.bounds[2] >= tab_shape.bounds[0] or tab[1] == "end"
        _assert_svg_bounds(rendered, f"group-header-band:{group_id}")


def test_text_band_clamps_long_header_at_table_edge(tmp_path):
    rendered = _render(tmp_path, _parts(), source=_source(long_group="team-0"))
    items = _by_id(rendered)
    band = items["group-header-band:team-0"]
    text = items["group-header:team-0"]
    table = next(slot.bounds for slot in rendered.surface.slots if slot.slot_id == "table")
    assert band.bounds[0] >= table[0]
    assert band.bounds[0] + band.bounds[2] == pytest.approx(table[0] + table[2])
    assert text.bounds[0] + text.bounds[2] > band.bounds[0] + band.bounds[2]
    assert text.text == "A deliberately long group header that reaches the table edge"
    _assert_svg_bounds(rendered, "group-header-band:team-0")


def test_group_band_selection_is_unchanged_by_text_extent(tmp_path):
    text_mode = _render(tmp_path, _parts(group_decoration="alternate"), name="alternate-text")
    legacy_mode = _render(tmp_path, _parts(extent="both", group_decoration="alternate"), name="alternate-both")
    text_ids = {item.scene_id for item in text_mode.surface.primitives}
    legacy_ids = {item.scene_id for item in legacy_mode.surface.primitives}
    group_backgrounds = lambda values: {value for value in values
                                        if value.startswith(("group:", "group-header-band:"))}
    assert group_backgrounds(text_ids) == group_backgrounds(legacy_ids) == {"group:team-0"}


@pytest.mark.parametrize(("inset", "expected"), [(None, 0), (0, 0), (0.4, None)])
def test_all_suppressed_runs_keep_only_declared_leading_interval(tmp_path, monkeypatch, inset, expected):
    rendered = _render(tmp_path, _parts(marked=True, inset=inset),
                       suppress_header_runs=True, monkeypatch=monkeypatch)
    band = _by_id(rendered)["group-header-band:team-0"]
    header = next(group for group in rendered.surface.groups if group.group_id == "team-0").header_bounds
    assert not any(item.scene_id.startswith("group-header:team-0#run")
                   for item in rendered.surface.primitives)
    assert band.bounds[0] == pytest.approx(header[0])
    if expected is not None:
        assert band.bounds[2] == pytest.approx(expected)
    else:
        body = _parts(inset=inset)["theme"]["body"]
        font_size = body["values"][body["roles"]["groupHeader"]["fontSize"]]["value"]
        assert band.bounds[2] == pytest.approx(inset * font_size)


def test_text_extent_changes_only_header_inline_extent_when_folded_rows_grow(tmp_path):
    source = _source()
    source["objects"].update({
        f"point-{index}": sr.point(f"point-{index}", date(2026, 2, 2 + index), owner="team-0")
        for index in range(4)
    })
    def folded_parts(extent):
        parts = _parts(inset=0.4, extent=extent)
        parts["theme"]["body"]["values"].update({
            "header-size": {"type": "number", "value": 20},
            "header-leading": {"type": "number", "value": 1.6},
        })
        parts["theme"]["body"]["roles"]["groupHeader"].update(
            {"fontSize": "header-size", "lineHeight": "header-leading"})
        parts["view"]["body"]["rows"] = {"mode": "automatic", "points": "group-header"}
        return parts

    rendered = _render(tmp_path, folded_parts("text"), source=source, name="folded-text")
    legacy = _render(tmp_path, folded_parts("both"), source=source, name="folded-both")
    items, old_items = _by_id(rendered), _by_id(legacy)
    band, text = items["group-header-band:team-0"], items["group-header:team-0"]
    old_band, old_text = old_items["group-header-band:team-0"], old_items["group-header:team-0"]
    assert band.bounds[2] == pytest.approx(text.bounds[0] + text.bounds[2] - band.bounds[0])
    assert band.bounds[3] > 20 * 1.6
    assert band.bounds[0] == pytest.approx(old_band.bounds[0])
    assert band.bounds[1] == pytest.approx(old_band.bounds[1])
    assert band.bounds[3] == pytest.approx(old_band.bounds[3])
    assert text.bounds == old_text.bounds
    assert text.baseline == old_text.baseline
    _assert_svg_bounds(rendered, "group-header-band:team-0")


@pytest.mark.parametrize("extent", ["both", "table", "timeline"])
@pytest.mark.parametrize("folded", [False, True], ids=["unfolded", "folded"])
@pytest.mark.parametrize("marked", [False, True], ids=["plain", "marked-runs"])
def test_legacy_extents_replay_prechange_scene_and_svg_bytes(tmp_path, monkeypatch, extent, folded, marked):
    source = _source()
    if folded:
        source["objects"].update({
            f"point-{index}": sr.point(f"point-{index}", date(2026, 2, 2 + index), owner="team-0")
            for index in range(4)
        })

    def parts():
        value = _parts(extent=extent, marked=marked)
        if folded:
            value["theme"]["body"]["values"].update({
                "header-size": {"type": "number", "value": 20},
                "header-leading": {"type": "number", "value": 1.6},
            })
            value["theme"]["body"]["roles"]["groupHeader"].update(
                {"fontSize": "header-size", "lineHeight": "header-leading"})
            value["view"]["body"]["rows"] = {"mode": "automatic", "points": "group-header"}
        return value

    current = _render(tmp_path, parts(), source=source, name="current")
    _install_legacy_geometry_replay(monkeypatch)
    legacy = _render(tmp_path, parts(), source=source, name="legacy")
    assert scene_document(current.scene) == scene_document(legacy.scene)
    assert serialize_scene(current.scene) == serialize_scene(legacy.scene)
    assert current.artifact.content == legacy.artifact.content


def test_vertical_tag_cell_and_non_text_extent_keep_their_existing_bytes(tmp_path):
    vertical = _render(tmp_path, _parts(vertical=True), name="vertical")
    vertical_default = _render(tmp_path, _parts(vertical=True, extent="both"), name="vertical-default")
    assert vertical.artifact.content == vertical_default.artifact.content
    assert vertical.surface.primitives == vertical_default.surface.primitives

    no_band_text = _parts(extent="text")
    no_band_legacy = _parts(extent="both")
    no_band_text["theme"]["body"]["roles"]["group-header-band"]["backgroundTreatment"] = "none"
    no_band_legacy["theme"]["body"]["roles"]["group-header-band"]["backgroundTreatment"] = "none"
    text_mode = _render(tmp_path, no_band_text, name="no-band-text")
    legacy_mode = _render(tmp_path, no_band_legacy, name="no-band-legacy")
    assert text_mode.artifact.content == legacy_mode.artifact.content
    assert text_mode.surface.primitives == legacy_mode.surface.primitives
