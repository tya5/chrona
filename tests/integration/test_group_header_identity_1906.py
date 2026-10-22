"""Full group identity survives vertical-tag fallback in admitted row variants (#1906)."""
from __future__ import annotations

from datetime import date
import xml.etree.ElementTree as ET

from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt


def _parts():
    parts = sr.bundle("control-room-dark")
    tt.with_vertical_groups(parts, size=22)
    return parts


def _assert_full_header_in_scene_and_svg(rendered, group_id: str, label: str) -> None:
    scene_id = f"group-header:{group_id}"
    header = next(item for item in rendered.surface.primitives if item.scene_id == scene_id)
    assert " ".join(header.text.split()) == " ".join(label.split())
    assert len(header.text_layout.lines) > 1
    table = next(slot for slot in rendered.surface.slots if slot.slot_id == "table")
    assert header.bounds[0] >= table.bounds[0]
    assert header.bounds[0] + header.bounds[2] <= table.bounds[0] + table.bounds[2]

    svg = ET.fromstring(rendered.artifact.content)
    svg_text = next(item for item in svg.iter()
                    if item.tag.rsplit("}", 1)[-1] == "text"
                    and item.attrib.get("data-scene-id") == scene_id)
    svg_lines = [" ".join("".join(line.itertext()).split()) for line in svg_text
                 if line.tag.rsplit("}", 1)[-1] == "tspan"]
    scene_lines = [" ".join(line.split()) for line in header.text_layout.lines]
    assert svg_lines == scene_lines
    assert " ".join(svg_lines) == " ".join(label.split())


def test_one_row_field_group_fallback_keeps_name_absent_from_object_path(tmp_path):
    label = "Flight systems coordination and integration " * 6
    project = sr.project({
        "leaf": {"type": "task", "title": "Leaf task", "fields": {"owner": label},
                 "schedule": {"mode": "fixed-span", "start": "2026-02-02", "end": "2026-02-06"}},
    })
    project["entities"][label]["title"] = label
    parts = _parts()
    parts["view"]["body"]["grouping"] = {
        "by": "field", "field": "owner", "missing": "Unassigned", "presentation": "header",
    }

    rendered = sr.render(tmp_path, project, presentation=parts, viewport=(1600, 100))

    assert [group.group_id for group in rendered.surface.groups] == [label]
    assert len(rendered.surface.rows) == 1
    assert project["objects"]["leaf"]["title"] == "Leaf task" and project["objects"]["leaf"]["title"] not in label
    assert not any(item.scene_id.startswith(f"group-tag:{label}:") for item in rendered.surface.primitives)
    _assert_full_header_in_scene_and_svg(rendered, label, label)


def test_folded_only_group_fallback_keeps_entity_identity_in_svg(tmp_path):
    group_id = "folded-systems"
    label = "Folded systems integration and validation " * 6
    project = sr.project({"gate": sr.point("gate", date(2026, 2, 12), owner=group_id)})
    project["entities"][group_id]["title"] = label
    parts = _parts()
    parts["view"]["body"]["rows"] = {"mode": "automatic", "points": "group-header"}

    rendered = sr.render(tmp_path, project, presentation=parts, viewport=(1600, 100))

    assert rendered.surface.rows == ()
    assert [group.group_id for group in rendered.surface.groups] == [group_id]
    assert [item.scene_id for item in rendered.surface.primitives if item.purpose == "planned"] == [
        f"planned:group-header:{group_id}:gate"]
    folded_mark = next(item for item in rendered.surface.primitives if item.purpose == "planned")
    table = next(slot for slot in rendered.surface.slots if slot.slot_id == "table")
    assert folded_mark.bounds[0] >= table.bounds[0] + table.bounds[2]
    assert not any(item.scene_id.startswith(f"group-tag:{group_id}:") for item in rendered.surface.primitives)
    _assert_full_header_in_scene_and_svg(rendered, group_id, label)

