"""Deadline rule-pair keys share the Theme's completed dash with ticks and runs (#1847)."""
from copy import deepcopy
from xml.etree import ElementTree

from tests.support import synthetic_review as sr
from tests.integration.test_deadline_mark import MIXED, _parts, _source


def test_deadline_rule_pair_key_matches_tick_and_run_dash_and_remains_in_separability_check(tmp_path):
    parts = deepcopy(_parts())
    theme = parts["theme"]["body"]
    theme["values"]["deadline-dash"] = {"type": "dashPattern", "value": [5, 3]}
    theme["roles"]["deadline-mark"]["dash"] = "deadline-dash"
    # Both keys use the same stroke ink; only the deadline key is dashed.
    parts["scheme"]["body"]["colors"]["accent"] = "#2F81F7"
    parts["view"]["body"]["deadlines"] = {"show": "all"}
    detail = {"version": "chrona/review-detail-profile/v0.1", "id": "deadline-dash-detail",
              "body": {"legend": [
                  {"role": "planned", "label": "Planned", "swatchShape": "rule-pair"},
                  {"role": "deadlineMark", "label": "Deadline", "swatchShape": "rule-pair"},
              ]}}

    rendered = sr.render(tmp_path, sr.with_calendar(_source(**MIXED)),
                         presentation=parts, detail=detail)

    deadline_marks = [item for item in rendered.surface.primitives if item.visual_role == "deadline-mark"
                      and item.scene_id.startswith(("deadline-tick:", "deadline-run:"))]
    key = next(item for item in rendered.surface.primitives if item.scene_id == "legend-swatch:deadlineMark")
    planned_key = next(item for item in rendered.surface.primitives if item.scene_id == "legend-swatch:planned")
    assert deadline_marks and key.kind == "Path"
    assert {item.scene_id.split(":", 1)[0] for item in deadline_marks} == {"deadline-tick", "deadline-run"}
    assert all(item.paint.dash == (5.0, 3.0) for item in deadline_marks)
    assert key.paint.dash == (5.0, 3.0)
    assert planned_key.paint.dash == ()
    assert key.paint.stroke == planned_key.paint.stroke

    svg = ElementTree.fromstring(rendered.artifact.content)
    elements = {node.attrib.get("data-scene-id"): node for node in svg.iter()}
    for scene_id in (*[item.scene_id for item in deadline_marks], key.scene_id):
        assert elements[scene_id].attrib["stroke-dasharray"] == "5 3"
    assert "stroke-dasharray" not in elements[planned_key.scene_id].attrib
    assert any(item.payload["code"] == "W_LEGEND_COLOR_NOT_SEPARABLE"
               and item.payload["diagnostic"].startswith("W_LEGEND_COLOR_NOT_SEPARABLE:deuteranopia:")
               and {subject["title"] for subject in item.payload["sourceSubjects"]}
               == {"Planned (planned)", "Deadline (deadlineMark)"}
               for item in rendered.warning_records)
    assert not any(item.payload["code"] == "W_LEGEND_SWATCH_COLLISION"
                   and {subject["title"] for subject in item.payload.get("sourceSubjects", ())}
                   == {"Planned (planned)", "Deadline (deadlineMark)"}
                   for item in rendered.warning_records)
