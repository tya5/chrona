"""Timeline-owned horizontal group headers reuse measured group-header geometry (#1936)."""
from __future__ import annotations

from datetime import date
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.scene.serialization import scene_document
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt
from tests.acceptance.output.test_generated_output_properties import _collapsed_table_is_intentionally_empty


def _parts(*, placement="timeline", band_extent="both"):
    parts = sr.bundle("executive-light")
    body = parts["view"]["body"]
    body["rows"] = {"mode": "automatic"}
    body.pop("tableColumns", None)
    body["grouping"] = {
        "by": "field", "field": "owner", "missing": "Unassigned",
        "presentation": "header", "headerPlacement": placement,
    }
    parts["layout"]["reviewSurface"]["backgroundExtents"]["groupHeaderBand"] = band_extent
    return parts


def _project(label="Systems"):
    project = sr.project({
        "one": sr.span("one", date(2026, 2, 2), 8, owner=label, title="First task"),
        "two": sr.span("two", date(2026, 2, 12), 8, owner="Operations", title="Second task"),
    })
    project["entities"][label]["title"] = label
    project["entities"]["Operations"]["title"] = "Operations"
    return project


def _slot(rendered, source):
    return next(item for item in rendered.surface.slots if item.source == source)


def _header(rendered, group_id="Systems"):
    return next(item for item in rendered.surface.primitives
                if item.purpose == "group-header" and item.scene_id == f"group-header:{group_id}")


def _svg_text(rendered, scene_id):
    root = ET.fromstring(rendered.artifact.content)
    node = next(item for item in root.iter()
                if item.tag.rsplit("}", 1)[-1] == "text" and item.attrib.get("data-scene-id") == scene_id)
    return "".join(node.itertext())


def test_timeline_header_uses_completed_plot_bounds_and_collapses_empty_table(tmp_path):
    rendered = sr.render(tmp_path, _project(), presentation=_parts(), viewport=(1200, 700))
    table, timeline = _slot(rendered, "table"), _slot(rendered, "timeline")
    header = _header(rendered)

    assert table.bounds[2] == 0
    assert header.slot_id == timeline.slot_id
    assert header.bounds[0] >= timeline.bounds[0]
    assert header.bounds[0] + header.bounds[2] <= timeline.bounds[0] + timeline.bounds[2]
    assert header.text == "Systems"
    assert "Systems" in _svg_text(rendered, header.scene_id)
    assert _collapsed_table_is_intentionally_empty(scene_document(rendered.scene))


def test_group_header_text_extent_follows_timeline_text_without_moving_other_extents(tmp_path):
    parts = _parts(band_extent="text")
    parts["view"]["body"]["backgroundDecoration"]["groups"] = "none"
    rendered = sr.render(tmp_path, _project(), presentation=parts, viewport=(1200, 700))
    timeline = _slot(rendered, "timeline")
    header = _header(rendered)
    band = next(item for item in rendered.surface.primitives
                if item.purpose == "group-header-band" and item.scene_id == "group-header-band:Systems")

    assert band.slot_id == timeline.slot_id
    assert band.bounds[0] >= timeline.bounds[0]
    assert band.bounds[0] + band.bounds[2] <= timeline.bounds[0] + timeline.bounds[2]
    assert band.bounds[0] <= header.bounds[0]
    assert band.bounds[0] + band.bounds[2] >= header.bounds[0] + header.bounds[2]
    assert "Systems" in _svg_text(rendered, header.scene_id)


def test_default_table_header_keeps_its_existing_table_origin(tmp_path):
    parts = _parts(placement="table")
    parts["view"]["body"]["grouping"].pop("headerPlacement")
    rendered = sr.render(tmp_path, _project(), presentation=parts, viewport=(1200, 700))
    table = _slot(rendered, "table")
    header = _header(rendered)

    assert table.bounds[2] > 0
    assert header.slot_id == table.slot_id
    assert header.bounds[0] >= table.bounds[0]
    assert header.bounds[0] < _slot(rendered, "timeline").bounds[0]
    assert "Systems" in _svg_text(rendered, header.scene_id)


def test_timeline_unbreakable_header_uses_common_owner_floor_not_table_source(tmp_path):
    label = "IDENTITY_" * 80
    project = sr.project({
        "one": sr.span("one", date(2026, 2, 2), 8, owner=label, title="First task"),
    })
    project["entities"][label]["title"] = label
    rendered = sr.render(tmp_path, project, presentation=_parts(), viewport=(600, None))
    table, timeline = _slot(rendered, "table"), _slot(rendered, "timeline")
    header = _header(rendered, label)

    assert table.bounds[2] == 0
    assert header.slot_id == timeline.slot_id
    assert header.text == label
    assert header.bounds[0] + header.bounds[2] <= timeline.bounds[0] + timeline.bounds[2]
    warning = next(item for item in rendered.surface.fit_warnings
                   if item.placement_id == header.scene_id)
    assert warning.failure_kind == "group-header-unbreakable-inline"
    assert warning.behaviour == "grow-owner-inline"
    assert _slot(rendered, "review-surface").bounds[2] >= warning.required_inline
    assert label in _svg_text(rendered, header.scene_id)


def test_timeline_placement_rejects_vertical_group_header_theme(tmp_path):
    parts = _parts()
    tt.with_vertical_groups(parts, size=22)

    with pytest.raises(RenderFailed) as caught:
        sr.render(tmp_path, _project(), presentation=parts, viewport=(1200, 700))

    assert caught.value.code == "E_LAYOUT_GROUP_HEADER_PLACEMENT"
    assert caught.value.source_ref == "/body/grouping/headerPlacement"
