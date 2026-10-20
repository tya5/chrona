"""Deadline rule-pair keys share the Theme's completed dash with ticks and runs (#1847)."""
from copy import deepcopy
from xml.etree import ElementTree

from tests.support import synthetic_review as sr
from tests.integration.test_deadline_mark import MIXED, _parts, _source


def _render(tmp_path, *, dash, shape="rule-pair", capture=None):
    parts = deepcopy(_parts())
    theme = parts["theme"]["body"]
    if dash:
        theme["values"]["deadline-dash"] = {"type": "dashPattern", "value": [5, 3]}
        theme["roles"]["deadline-mark"]["dash"] = "deadline-dash"
    # Both keys use the same stroke ink; only the deadline key is dashed.
    parts["scheme"]["body"]["colors"]["accent"] = "#2F81F7"
    parts["view"]["body"]["deadlines"] = {"show": "all"}
    detail = {"version": "chrona/review-detail-profile/v0.1", "id": "deadline-dash-detail",
              "body": {"legend": [
                  {"role": "planned", "label": "Planned", "swatchShape": "rule-pair"},
                  {"role": "deadlineMark", "label": "Deadline", "swatchShape": shape},
              ]}}

    return sr.render(tmp_path, sr.with_calendar(_source(**MIXED)),
                      presentation=parts, detail=detail)


def _elements(rendered):
    svg = ElementTree.fromstring(rendered.artifact.content)
    return {node.attrib.get("data-scene-id"): node for node in svg.iter()}


def test_deadline_rule_pair_key_matches_tick_and_run_dash(tmp_path):
    rendered = _render(tmp_path, dash=True)

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

    elements = _elements(rendered)
    for scene_id in (*[item.scene_id for item in deadline_marks], key.scene_id):
        assert elements[scene_id].attrib["stroke-dasharray"] == "5 3"
    assert "stroke-dasharray" not in elements[planned_key.scene_id].attrib
    assert not any(item.payload["code"] == "W_LEGEND_SWATCH_COLLISION"
                   and {subject["title"] for subject in item.payload.get("sourceSubjects", ())}
                   == {"Planned (planned)", "Deadline (deadlineMark)"}
                   for item in rendered.warning_records)


def test_dashless_theme_keeps_solid_default(tmp_path):
    rendered = _render(tmp_path, dash=False)
    elements = _elements(rendered)
    ids = [item.scene_id for item in rendered.surface.primitives
           if item.visual_role == "deadline-mark"] + ["legend-swatch:deadlineMark"]
    assert all(item.paint.dash == () for item in rendered.surface.primitives
               if item.visual_role == "deadline-mark")
    assert all("stroke-dasharray" not in elements[scene_id].attrib for scene_id in ids)


def test_explicit_circle_swatch_stays_flat_with_dashed_role(tmp_path):
    rendered = _render(tmp_path, dash=True, shape="circle")
    key = next(item for item in rendered.surface.primitives if item.scene_id == "legend-swatch:deadlineMark")
    assert key.paint.dash == ()
    assert "stroke-dasharray" not in _elements(rendered)["legend-swatch:deadlineMark"].attrib
    ticks = [item for item in rendered.surface.primitives if item.scene_id.startswith("deadline-tick:")]
    assert ticks and all(item.paint.dash == (5.0, 3.0) for item in ticks)


def test_completed_key_stroke_is_exposed_typed(tmp_path, monkeypatch):
    from chrona.presentation.layout import legend_diagnostics as ld
    captured = {}
    original = ld._colour_pair_diagnostics

    def spy(key_entries, figures, color_vision=()):
        captured.update(figures)
        return original(key_entries, figures, color_vision)

    monkeypatch.setattr(ld, "_colour_pair_diagnostics", spy)
    rendered = _render(tmp_path, dash=True)
    key = next(item for item in rendered.surface.primitives if item.scene_id == "legend-swatch:deadlineMark")
    strokes = {source: ld.completed_figure_strokes(figure) for source, figure in captured.items()}
    dashed = [stroke for values in strokes.values() for stroke in values if stroke.dash]
    assert dashed and all(isinstance(stroke, ld.CompletedKeyStroke) for stroke in dashed)
    assert {stroke.dash for stroke in dashed} == {(5.0, 3.0)}
    assert {stroke.colour for stroke in dashed} == {key.paint.stroke.upper()}
    assert {float(stroke.width) for stroke in dashed} == {key.paint.stroke_width}
    undashed = [stroke for values in strokes.values() for stroke in values if not stroke.dash]
    assert undashed


def test_dash_leaves_the_deadline_key_in_the_separability_check(tmp_path):
    for dash in (False, True):
        rendered = _render(tmp_path, dash=dash)
        assert any(item.payload["code"] == "W_LEGEND_COLOR_NOT_SEPARABLE"
                   and {subject["title"] for subject in item.payload["sourceSubjects"]}
                   == {"Planned (planned)", "Deadline (deadlineMark)"}
                   for item in rendered.warning_records)
