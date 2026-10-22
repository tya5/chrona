"""A non-fitting vertical group tag keeps the complete identity in a reserved header (#1906)."""
from __future__ import annotations

import xml.etree.ElementTree as ET

from chrona.presentation.layout.group_header_fit import GroupHeaderFitPlan
from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt


def test_mixed_vertical_fit_and_wrapped_full_name_keep_tag_plate_in_row_cell(tmp_path):
    source = sr.bunched_project(groups=2, per_group=1)
    source["entities"]["team-0"]["title"] = "X"
    long_name = "Ground segment identity " * 12
    source["entities"]["team-1"]["title"] = long_name

    parts = sr.bundle("control-room-dark")
    tt.with_vertical_groups(parts, size=22)
    body = parts["theme"]["body"]
    body["values"]["tag-gap"] = {"type": "number", "value": 3}
    body["values"]["tag-opacity"] = {"type": "number", "value": 1}
    body["roles"]["group-tab"] = {
        "backgroundTreatment": "fill", "backgroundPaintOrder": 20, "opacity": "tag-opacity",
        "tabGap": "tag-gap", "tabTarget": "tag",
    }
    body["colorBindings"]["group-tab.fill"] = "warning"

    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(1600, 900))
    primitives = {item.scene_id: item for item in rendered.surface.primitives}

    assert primitives["group-tag:team-0:0"].text == "X"
    assert not any(key.startswith("group-tag:team-1:") for key in primitives)
    fallback = primitives["group-header:team-1"]
    assert fallback.text.replace("\n", " ") == long_name
    assert "…" not in fallback.text
    assert len(fallback.text_layout.lines) > 1
    table = next(slot for slot in rendered.surface.slots if slot.slot_id == "table")
    assert fallback.bounds[0] >= table.bounds[0]
    assert fallback.bounds[0] + fallback.bounds[2] <= table.bounds[0] + table.bounds[2]

    # The explicitly declared tag plate remains in the tag cell, not behind the horizontal fallback header.
    tab = primitives["group-tab:team-1"]
    assert tab.bounds[1] >= fallback.bounds[1] + fallback.bounds[3]
    assert tab.bounds[3] > 0


def test_requested_height_is_a_minimum_when_full_group_header_needs_space(tmp_path):
    source = sr.bunched_project(groups=1, per_group=1)
    long_name = "A complete group identity " * 8
    source["entities"]["team-0"]["title"] = long_name
    parts = sr.bundle("control-room-dark")
    tt.with_vertical_groups(parts, size=22)

    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(1600, 100))
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    assert not any(key.startswith("group-tag:team-0:") for key in primitives)
    assert primitives["group-header:team-0"].text.replace("\n", " ") == long_name


def test_bounded_one_line_header_keeps_ordinary_autoheight_baseline(tmp_path):
    source = sr.bunched_project(groups=1, per_group=1)
    source["entities"]["team-0"]["title"] = "Operations"

    bounded_parts = sr.bundle("control-room-dark")
    tt.with_vertical_groups(bounded_parts, mode="horizontal")
    bounded_parts["layout"]["reviewSurface"]["backgroundExtents"]["groupHeaderBand"] = "text"
    ordinary_parts = sr.bundle("control-room-dark")
    tt.with_vertical_groups(ordinary_parts, mode="horizontal")
    ordinary_parts["layout"]["reviewSurface"]["backgroundExtents"]["groupHeaderBand"] = "both"

    bounded_dir, ordinary_dir = tmp_path / "bounded", tmp_path / "ordinary"
    bounded_dir.mkdir()
    ordinary_dir.mkdir()
    bounded = sr.render(bounded_dir, source, presentation=bounded_parts, viewport=(1600, None))
    ordinary = sr.render(ordinary_dir, source, presentation=ordinary_parts, viewport=(1600, None))

    bounded_header = next(item for item in bounded.surface.primitives if item.scene_id == "group-header:team-0")
    ordinary_header = next(item for item in ordinary.surface.primitives if item.scene_id == "group-header:team-0")
    assert bounded_header.text == ordinary_header.text == "Operations"
    assert bounded_header.text_layout.lines == ordinary_header.text_layout.lines
    assert bounded.surface.canvas_bounds[3] == ordinary.surface.canvas_bounds[3]
    assert bounded_header.bounds == ordinary_header.bounds


def test_vertical_name_fitting_raw_group_span_falls_back_after_tab_gap(tmp_path, monkeypatch):
    source = sr.bunched_project(groups=1, per_group=1)
    source["entities"]["team-0"]["title"] = "Ana"
    parts = sr.bundle("control-room-dark")
    tt.with_vertical_groups(parts, size=25)
    body = parts["theme"]["body"]
    body["values"]["tag-gap"] = {"type": "number", "value": 3}
    body["values"]["tag-opacity"] = {"type": "number", "value": 1}
    body["roles"]["group-tab"] = {
        "backgroundTreatment": "fill", "backgroundPaintOrder": 20, "opacity": "tag-opacity",
        "tabGap": "tag-gap", "tabTarget": "tag",
    }
    body["colorBindings"]["group-tab.fill"] = "warning"

    measured = []
    original = GroupHeaderFitPlan.vertical_tags_missing_full_fit

    def capture(plan, spans):
        measured.append((plan, dict(spans)))
        return original(plan, spans)

    monkeypatch.setattr(GroupHeaderFitPlan, "vertical_tags_missing_full_fit", capture)
    rendered = sr.render(tmp_path, source, presentation=parts, viewport=(1600, 900))

    plan, spans = next((plan, spans) for plan, spans in measured
                       if plan.group("team-0") is not None and plan.group("team-0").uses_vertical_tag)
    fit = plan.group("team-0")
    assert fit is not None
    # The label fits the un-inset row-group span, but not the declared tab cell after its 3px end gaps.
    assert spans["team-0"] >= fit.vertical_required_block
    assert spans["team-0"] - plan.vertical_tag_block_inset < fit.vertical_required_block

    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    fallback = primitives["group-header:team-0"]
    assert fallback.text == "Ana" and "…" not in fallback.text
    svg_root = ET.fromstring(rendered.artifact.content)
    svg_header = next(node for node in svg_root.iter()
                      if node.attrib.get("data-scene-id") == "group-header:team-0")
    assert "".join(svg_header.itertext()) == "Ana"
    group = next(item for item in rendered.surface.groups if item.group_id == "team-0")
    header = group.header_bounds
    content = group.content_bounds
    table = next(slot for slot in rendered.surface.slots if slot.slot_id == "table")
    assert header[0] >= table.bounds[0]
    assert header[0] + header[2] <= table.bounds[0] + table.bounds[2]
    assert header[0] + header[2] <= content[0]

    # The tab remains in its row cell; neither it nor the plotted mark occupies the reserved header.
    tab = primitives["group-tab:team-0"]
    mark = next(item for item in rendered.surface.primitives if item.scene_id.startswith("planned:"))

    def overlaps(left, right):
        return (left[0] < right[0] + right[2] and right[0] < left[0] + left[2]
                and left[1] < right[1] + right[3] and right[1] < left[1] + left[3])

    assert not overlaps(header, tab.bounds)
    assert not overlaps(header, mark.bounds)
