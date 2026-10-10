"""A trailing inset extends only the completed text-sized group-header band (#1368)."""
from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.layout.model import Rect
from chrona.usecases.render_review import RenderFailed
from tests.integration.test_group_header_text_extent import (
    _assert_svg_bounds, _by_id, _parts, _render, _source,
)


def _with_end_inset(parts, ratio: float):
    body = parts["theme"]["body"]
    body["values"]["header-end-inset"] = {"type": "number", "value": ratio}
    body["roles"]["groupHeader"]["labelInsetEnd"] = "header-end-inset"
    return parts


def _header_text(rendered, group_id: str):
    prefix = f"group-header:{group_id}"
    return tuple(item for item in rendered.surface.primitives
                 if item.scene_id == prefix or item.scene_id.startswith(prefix + "#run"))


def _font_size(parts):
    body = parts["theme"]["body"]
    token = body["roles"]["groupHeader"]["fontSize"]
    return body["values"][token]["value"]


def _band(rendered, group_id):
    return _by_id(rendered)[f"group-header-band:{group_id}"]


@pytest.mark.parametrize("marked", [False, True], ids=["plain", "mixed-role-runs"])
def test_trailing_inset_extends_actual_drawn_run_end_without_moving_text(tmp_path, monkeypatch, marked):
    import chrona.presentation.layout.surface_composer as composer

    original = composer.compose_group_presentation
    captured = []

    def capture(**kwargs):
        value = original(**kwargs)
        captured.append(value)
        return value

    monkeypatch.setattr(composer, "compose_group_presentation", capture)
    base_parts = _parts(marked=marked, inset=0.4, extent="text")
    inset_parts = _with_end_inset(_parts(marked=marked, inset=0.4, extent="text"), 0.5)
    base = _render(tmp_path, base_parts, name="base")
    extended = _render(tmp_path, inset_parts, name="extended")
    assert len(captured) == 2
    assert dict(captured[0].header_content_bounds) == dict(captured[1].header_content_bounds)

    base_items, new_items = _by_id(base), _by_id(extended)
    assert {key: value for key, value in base_items.items() if key.startswith("group-header:")} == {
        key: value for key, value in new_items.items() if key.startswith("group-header:")
    }
    font_size = _font_size(inset_parts)
    table = next(slot.bounds for slot in extended.surface.slots if slot.slot_id == "table")
    svg = ET.fromstring(extended.artifact.content)
    svg_by_id = {item.attrib.get("data-scene-id"): item for item in svg.iter()
                 if item.attrib.get("data-scene-id")}
    for group_id in ("team-0", "team-1"):
        previous, actual = _band(base, group_id), _band(extended, group_id)
        text = _header_text(extended, group_id)
        # Scene contains only emitted (nonsuppressed) text placements.
        drawn = [item for item in text if item.bounds[2] > 0]
        assert drawn
        drawn_end = max(Decimal(str(item.bounds[0] + item.bounds[2])) for item in drawn)
        expected_right = min(
            Decimal(str(table[0] + table[2])),
            drawn_end + Decimal("0.5") * Decimal(str(font_size)),
        )
        assert actual.bounds[0] == previous.bounds[0]
        assert actual.bounds[0] + actual.bounds[2] == pytest.approx(float(expected_right))
        assert actual.bounds[1] == previous.bounds[1]
        assert actual.bounds[3] == previous.bounds[3]
        _assert_svg_bounds(extended, actual.scene_id)
        old_text = _header_text(base, group_id)
        for before, after in zip(old_text, text, strict=True):
            svg_text = svg_by_id[after.scene_id]
            assert after.bounds == before.bounds
            assert after.baseline == before.baseline
            assert float(svg_text.attrib["x"]) == pytest.approx(before.baseline[0])


def test_ellipsized_text_end_is_padded_then_clamped_without_changing_caption(tmp_path, monkeypatch):
    import chrona.presentation.layout.surface_composer as composer

    original = composer.compose_group_presentation
    captured = []

    def capture(**kwargs):
        value = original(**kwargs)
        captured.append(value)
        return value

    monkeypatch.setattr(composer, "compose_group_presentation", capture)
    source = _source()
    source["entities"]["team-0"]["title"] = "Long header " * 24
    base_parts = _parts(extent="text", tab=(100, "end"))
    ratio = 2.0
    inset_parts = _with_end_inset(_parts(extent="text", tab=(100, "end")), ratio)
    base = _render(tmp_path, base_parts, source=source, name="ellipsis-base")
    extended = _render(tmp_path, inset_parts, source=source, name="ellipsis-trailing")
    previous_text = _header_text(base, "team-0")
    actual_text = _header_text(extended, "team-0")
    assert len(previous_text) == len(actual_text) == 1
    previous_layout = next(item for item in captured[0].text if item.placement_id == "group-header:team-0")
    actual_layout = next(item for item in captured[1].text if item.placement_id == "group-header:team-0")
    assert actual_layout.overflow == previous_layout.overflow == "ellipsized"
    assert actual_text[0].text == previous_text[0].text
    assert actual_text[0].bounds == previous_text[0].bounds
    assert actual_text[0].baseline == previous_text[0].baseline
    table = next(slot.bounds for slot in extended.surface.slots if slot.slot_id == "table")
    band = _band(extended, "team-0")
    text_end = actual_layout.bounds.inline + actual_layout.bounds.inline_size
    font_size = Decimal(str(_font_size(inset_parts)))
    expected_end = min(Decimal(str(table[0] + table[2])), text_end + Decimal(str(ratio)) * font_size)
    assert band.bounds[0] + band.bounds[2] == pytest.approx(float(expected_end))
    _assert_svg_bounds(extended, band.scene_id)


def test_all_suppressed_runs_keep_only_the_leading_interval(tmp_path, monkeypatch):
    def _render_suppressed(name, ratio):
        parts = _parts(marked=True, inset=0.4, extent="text")
        if ratio is not None:
            _with_end_inset(parts, ratio)
        with monkeypatch.context() as scoped:
            return _render(tmp_path, parts, name=name, suppress_header_runs=True, monkeypatch=scoped)

    without = _render_suppressed("suppressed-base", None)
    with_end = _render_suppressed("suppressed-inset", 2.0)
    for group_id in ("team-0", "team-1"):
        before, after = _band(without, group_id), _band(with_end, group_id)
        assert before.bounds == after.bounds
        assert not _header_text(with_end, group_id)


def test_zero_width_nonsuppressed_run_does_not_activate_trailing_inset(tmp_path, monkeypatch):
    import chrona.presentation.layout.surface_groups as groups
    import chrona.presentation.layout.surface_composer as composer

    original = groups.place_group_header_runs
    original_compose = composer.compose_group_presentation
    captured = []

    def capture(**kwargs):
        value = original_compose(**kwargs)
        captured.append(value)
        return value

    monkeypatch.setattr(composer, "compose_group_presentation", capture)

    def zero_width(**kwargs):
        placements, warnings = original(**kwargs)
        return tuple(replace(item, bounds=Rect(item.bounds.inline, item.bounds.block,
                                                Decimal(0), item.bounds.block_size))
                     for item in placements), warnings

    monkeypatch.setattr(groups, "place_group_header_runs", zero_width)
    base_parts = _parts(marked=True, inset=0.4, extent="text")
    end_parts = _with_end_inset(_parts(marked=True, inset=0.4, extent="text"), 2.0)
    base = _render(tmp_path, base_parts, name="zero-width-base")
    rendered = _render(tmp_path, end_parts, name="zero-width")
    assert len(captured) == 2
    for group_id in ("team-0", "team-1"):
        band = _band(rendered, group_id)
        before = _band(base, group_id)
        assert _header_text(rendered, group_id)
        assert all(item.bounds[2] == 0 for item in _header_text(rendered, group_id))
        assert band.bounds == before.bounds


@pytest.mark.parametrize("extent", ["both", "table", "timeline"])
def test_valid_trailing_inset_is_inactive_for_other_extents(tmp_path, extent):
    base = _render(tmp_path, _parts(extent=extent), name=f"{extent}-base")
    changed = _render(tmp_path, _with_end_inset(_parts(extent=extent), 1.0), name=f"{extent}-inset")
    assert base.artifact.content == changed.artifact.content
    assert base.surface.primitives == changed.surface.primitives
    assert base.scene.provenance != changed.scene.provenance


def test_absent_and_zero_trailing_inset_keep_geometry_and_svg_but_provenance_is_authored(tmp_path):
    absent = _render(tmp_path, _parts(extent="text"), name="absent")
    zero = _render(tmp_path, _with_end_inset(_parts(extent="text"), 0), name="zero")
    assert absent.artifact.content == zero.artifact.content
    assert absent.surface.primitives == zero.surface.primitives
    assert absent.scene.provenance != zero.scene.provenance


@pytest.mark.parametrize("token", [
    {"type": "number", "value": -0.1},
    {"type": "textTransform", "value": "uppercase"},
])
def test_invalid_trailing_inset_fails_at_its_theme_property(tmp_path, token):
    parts = _parts(extent="text")
    parts["theme"]["body"]["values"]["header-end-inset"] = token
    parts["theme"]["body"]["roles"]["groupHeader"]["labelInsetEnd"] = "header-end-inset"
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, parts)
    assert (raised.value.code, raised.value.source_ref) == (
        "E_THEME_TOKEN_TYPE", "/body/roles/groupHeader/labelInsetEnd")


def test_vertical_group_header_rejects_authored_zero_trailing_inset(tmp_path):
    parts = _parts(vertical=True, extent="text")
    _with_end_inset(parts, 0)
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, parts)
    assert (raised.value.code, raised.value.source_ref) == (
        "E_THEME_ROLE_PROPERTY_UNSUPPORTED", "/body/roles/groupHeader/labelInsetEnd")
