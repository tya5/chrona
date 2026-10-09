"""Synthetic row rules are completed in Layout, then projected as ordinary Scene paths."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest

from chrona.usecases.render_review import RenderFailed
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from tests.support import synthetic_review as sr


def _project():
    source = sr.bunched_project(groups=2, per_group=2)
    source["entities"]["team-0"]["title"] = "Team 0"
    source["entities"]["team-1"]["title"] = "Team 1"
    return source


def _parts(*, rows="rules", groups="all", group_order=9, row_band_order=10,
           header_band_order=11, row_rule=True, row_rule_stroke="warning"):
    parts = sr.bundle("control-room-dark")
    body = parts["theme"]["body"]
    body["roles"]["group-band"]["backgroundPaintOrder"] = group_order
    body["roles"]["row-band"]["backgroundPaintOrder"] = row_band_order
    body["roles"]["group-header-band"]["backgroundPaintOrder"] = header_band_order
    parts["view"]["body"]["backgroundDecoration"] = {"rows": rows, "groups": groups}
    if row_rule:
        body["values"]["row-rule.width"] = {"type": "number", "value": 1}
        body["roles"]["row-rule"] = {"strokeWidth": "row-rule.width"}
        body["colorBindings"]["row-rule.stroke"] = row_rule_stroke
    return parts


def _rules(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives
            if item.kind.value == "Path" and item.scene_id.startswith("row-rule:")}


def test_rule_per_item_row_uses_bottom_and_full_table_to_timeline_extent_in_scene_and_svg(tmp_path):
    rendered = sr.render(tmp_path, _project(), presentation=_parts())

    rules = _rules(rendered)
    assert len(rules) == len(rendered.surface.rows) == 4
    row_by_id = {row.row_id: row for row in rendered.surface.rows}
    slots = {slot.slot_id: slot for slot in rendered.surface.slots}
    table_start = slots["table"].bounds[0]
    timeline_end = slots["timeline"].bounds[0] + slots["timeline"].bounds[2]
    for placement_id, rule in rules.items():
        row_id = placement_id.removeprefix("row-rule:")
        row = row_by_id[row_id]
        assert rule.bounds[1] == pytest.approx(row.bounds[1] + row.bounds[3], abs=0.01)
        assert rule.bounds[0] == pytest.approx(table_start, abs=0.01)
        assert rule.bounds[0] + rule.bounds[2] == pytest.approx(
            timeline_end, abs=0.01)

    root = ET.fromstring(rendered.artifact.content)
    svg_paths = {node.attrib.get("data-scene-id"): node for node in root.iter()
                 if node.tag.rsplit("}", 1)[-1] == "path" and node.attrib.get("data-scene-id", "").startswith("row-rule:")}
    assert set(svg_paths) == set(rules)
    for placement_id, rule in rules.items():
        points = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", svg_paths[placement_id].attrib["d"])]
        assert points == pytest.approx([rule.points[0][0], rule.points[0][1],
                                        rule.points[1][0], rule.points[1][1]], abs=0.01)


def test_missing_row_rule_role_fails_at_view_selection_pointer(tmp_path):
    with pytest.raises(RenderFailed) as raised:
        sr.render(tmp_path, _project(), presentation=_parts(row_rule=False))
    assert (raised.value.code, raised.value.source_ref) == (
        "E_THEME_ROLE_REQUIRED", "/body/backgroundDecoration/rows")
    assert "/body/roles/row-rule" in raised.value.message


@pytest.mark.parametrize(("groups", "group_order", "header_order", "offending_role"), [
    ("all", 10, 11, "group-band"),
    ("none", 9, 10, "group-header-band"),
])
def test_only_emitted_band_orders_that_conflict_with_rules_are_rejected(
        tmp_path, groups, group_order, header_order, offending_role):
    with pytest.raises(RenderFailed) as raised:
        sr.render(tmp_path, _project(), presentation=_parts(
            groups=groups, group_order=group_order, header_band_order=header_order))
    assert (raised.value.code, raised.value.source_ref) == (
        "E_LAYOUT_ROW_RULE_ORDER", "/body/backgroundDecoration/rows")
    assert offending_role in raised.value.message and "order=" in raised.value.message and "required <10" in raised.value.message


def test_unused_high_order_row_band_role_does_not_block_rules(tmp_path):
    rendered = sr.render(tmp_path, _project(), presentation=_parts(row_band_order=1000))
    assert len(_rules(rendered)) == len(rendered.surface.rows) == 4


def test_low_contrast_row_rules_remain_warning_only_decoration(tmp_path):
    rendered = sr.render(tmp_path, _project(), presentation=_parts(row_rule_stroke="surface"))

    findings = [item for item in evaluate_scene_contrast(scene_document(rendered.scene))
                if item.primitive_id.startswith("row-rule:")]
    assert findings
    assert all(item.code == "W_SCENE_DECORATION_CONTRAST" and item.severity == "warning" for item in findings)
    assert rendered.artifact.content


def test_omitted_and_explicit_none_row_decoration_are_byte_identical(tmp_path):
    source = _project()
    baseline_dir, none_dir = tmp_path / "default", tmp_path / "none"
    baseline_dir.mkdir(); none_dir.mkdir()
    baseline_parts = sr.bundle("control-room-dark")
    baseline_parts["view"]["body"].pop("backgroundDecoration")
    baseline = sr.render(baseline_dir, source, presentation=baseline_parts)
    parts = sr.bundle("control-room-dark")
    parts["view"]["body"]["backgroundDecoration"] = {"rows": "none", "groups": "all"}
    explicit_none = sr.render(none_dir, source, presentation=parts)

    assert explicit_none.artifact.content == baseline.artifact.content
    assert explicit_none.surface == baseline.surface
