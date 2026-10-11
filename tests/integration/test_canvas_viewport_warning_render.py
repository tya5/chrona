"""#1279: declared viewport evidence survives real Layout/Scene/SVG rendering."""
from datetime import date
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.layout import dependency_network, surface_completion
from tests.integration.test_title_ink import _network_parts
from tests.support import synthetic_review as sr


CODE = "W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT"


def _source(count=1):
    return sr.project({f"t{index}": sr.span(f"t{index}", date(2026, 1, 5), 28)
                       for index in range(count)})


def _warning(rendered):
    rows = [item for item in rendered.warning_records if item.payload["code"] == CODE]
    assert len(rows) == 1
    warning = rows[0]
    assert warning.identity in rendered.scene.diagnostics
    assert warning.payload["sourceRef"] == "/body/environment/viewport"
    x, y, width, height = rendered.surface.canvas_bounds
    assert warning.payload["actual"] == {
        "inlineStart": x, "blockStart": y, "inlineSize": width, "blockSize": height}
    assert [float(value) for value in ET.fromstring(rendered.artifact.content).attrib["viewBox"].split()] == pytest.approx(
        (x, y, width, height), abs=.001)
    assert warning.payload["contributors"]
    assert warning.payload["contributorCount"] >= len(warning.payload["contributors"])
    return warning.payload


def test_original_fixed_viewport_is_not_replaced_by_grown_allocation(tmp_path):
    rendered = sr.render(tmp_path, _source(8), viewport=(1600, 200))
    assert rendered.surface.canvas_bounds[3] > 200
    payload = _warning(rendered)
    assert payload["declared"] == {"inlineSize": 1600, "blockSize": 200}
    assert any(item["overrun"]["blockEnd"] > 0 for item in payload["contributors"])


def test_fitting_surface_has_no_canvas_warning(tmp_path):
    rendered = sr.render(tmp_path, _source())
    assert rendered.surface.canvas_bounds == pytest.approx((0, 0, 1600, 900))
    assert rendered.surface.canvas_warning is None
    assert not any(item.payload["code"] == CODE for item in rendered.warning_records)


@pytest.mark.parametrize("block", [900, None])
def test_negative_origin_warns_with_full_extent_and_keeps_auto_block_unconstrained(tmp_path, block):
    parts = sr.bundle()
    # A deliberate overlay anchor, not the out-of-window mark defect (#1292),
    # proves the independent general canvas-growth warning (#1279).
    title = parts["layout"]["root"]["children"][0]
    title["anchor"] = {"self": {"inline": "end", "block": "start"},
                       "target": {"inline": {"ref": "parent", "point": "start"},
                                  "block": {"ref": "parent", "point": "start"}}}
    title["place"]["safety"] = "strict"
    parts["layout"]["root"]["children"][0] = {
        "id": "title-overlay", "kind": "overlay", "inlineSize": "fill", "blockSize": "content",
        "padding": {"token": "spacing.none"}, "children": [title]}
    rendered = sr.render(tmp_path, _source(), presentation=parts, viewport=(1600, block))
    assert rendered.surface.canvas_bounds[0] < 0
    assert not any(item.payload["code"] == "W_LAYOUT_OUTSIDE_WINDOW" for item in rendered.warning_records)
    payload = _warning(rendered)
    assert payload["declared"] == {"inlineSize": 1600, "blockSize": block}
    assert any(item["overrun"]["inlineStart"] > 0 for item in payload["contributors"])
    if block is None:
        assert all(item["overrun"]["blockStart"] == item["overrun"]["blockEnd"] == 0
                   for item in payload["contributors"])


def test_auto_height_has_no_invented_block_limit(tmp_path):
    rendered = sr.render(tmp_path, _source(20), viewport=(1600, None))
    assert rendered.surface.canvas_bounds[3] > 900
    assert rendered.surface.canvas_warning is None
    assert not any(item.payload["code"] == CODE for item in rendered.warning_records)


def test_network_uses_the_same_declaration_warning_without_removing_allocation_warning(tmp_path):
    rendered = sr.render(tmp_path, _source(8), presentation=_network_parts(), viewport=(1600, 200))
    assert rendered.surface.canvas_bounds[3] > 200
    payload = _warning(rendered)
    assert payload["surfaceId"] == "dependency-network"
    assert payload["declared"] == {"inlineSize": 1600, "blockSize": 200}
    assert any(item.code == "W_LAYOUT_NETWORK_OVERFLOW" for item in rendered.surface.fit_warnings)


@pytest.mark.parametrize("network", [False, True], ids=["table-timeline", "dependency-network"])
def test_warning_addition_changes_no_geometry_or_svg_bytes(tmp_path, monkeypatch, network):
    (tmp_path / "warning").mkdir()
    (tmp_path / "without-warning").mkdir()
    source = _source(8)
    presentation = _network_parts() if network else sr.bundle()
    warned = sr.render(tmp_path / "warning", source, presentation=presentation, viewport=(1600, 200))
    _warning(warned)
    owner = dependency_network if network else surface_completion
    monkeypatch.setattr(owner, "canvas_viewport_warning", lambda **_: None)
    plain = sr.render(tmp_path / "without-warning", source, presentation=presentation, viewport=(1600, 200))
    assert plain.surface.canvas_warning is None
    assert warned.surface.primitives == plain.surface.primitives
    assert warned.surface.slots == plain.surface.slots
    assert warned.surface.rows == plain.surface.rows
    assert warned.surface.groups == plain.surface.groups
    assert warned.surface.canvas_bounds == plain.surface.canvas_bounds
    assert warned.artifact.content == plain.artifact.content
