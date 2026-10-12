"""#1300: actual Scene/SVG revision evidence from project-independent fixtures."""
from datetime import date, timedelta
import xml.etree.ElementTree as ET
import yaml

from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.support import synthetic_review as sr


def _render(directory, *, shift=0, append=False):
    directory.mkdir()
    move = timedelta(days=shift)
    source = sr.with_calendar(sr.project({
        "source": sr.span("source", date(2027, 1, 4) + move, 10),
        "target": sr.span("target", date(2027, 2, 1) + move, 10),
    }, [{"id": "source-target", "type": "dependency", "lag": "0d",
         "from": {"object": "source", "endpoint": "end"},
         "to": {"object": "target", "endpoint": "start"}}]))
    if append:
        source["objects"]["unrelated"] = sr.span("unrelated", date(2027, 1, 20), 5)
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "actuals", "body": {
        "asOf": (date(2027, 2, 20) + move).isoformat(), "observations": [
            {"id": "source-done", "sequence": 1, "projectObjectId": "source", "actual": {
                "start": (date(2027, 1, 4) + move).isoformat(),
                "finish": (date(2027, 1, 17) + move).isoformat(), "progress": 1}},
            {"id": "target-done", "sequence": 1, "projectObjectId": "target", "actual": {
                "start": (date(2027, 2, 1) + move).isoformat(),
                "finish": (date(2027, 2, 9) + move).isoformat(), "progress": 1}},
        ]}}
    project_path, actual_path = directory / "project.yaml", directory / "actual.yaml"
    project_path.write_text(yaml.safe_dump(source, sort_keys=False), encoding="utf-8")
    actual_path.write_text(yaml.safe_dump(actual, sort_keys=False), encoding="utf-8")
    return render_draft(DraftRenderRequest(project_path, "svg", actual=actual_path)).rendered


def _anchor_sides(rendered):
    primitives = {item.scene_id: item for item in rendered.surface.primitives}
    sides = {}
    for identity, delta in primitives.items():
        if not identity.startswith("variance:") or delta.kind != "Text":
            continue
        object_id = identity.removeprefix("variance:")
        mark = primitives.get(f"actual:{object_id}") or primitives[f"planned:{object_id}"]
        x, y, width, height = delta.bounds
        left, top, inline, block = mark.bounds
        if x >= left + inline:
            side = "end"
        elif x + width <= left:
            side = "start"
        elif y + height <= top:
            side = "above"
        elif y >= top + block:
            side = "below"
        else:
            raise AssertionError(f"detached/overlapping delta {identity}: {delta.bounds}, {mark.bounds}")
        sides[identity] = side
    assert set(sides) == {"variance:source:source", "variance:target:target"}
    return sides


def _suppressed_relations(rendered):
    return {item for item in rendered.scene.diagnostics if item.startswith("W_LAYOUT_RELATION_SUPPRESSED:")}


def test_default_preset_delta_anchors_and_route_class_survive_translation_and_unrelated_append(tmp_path):
    baseline = _render(tmp_path / "baseline")
    shifted = _render(tmp_path / "shifted", shift=7)
    appended = _render(tmp_path / "appended", append=True)
    for rendered in (baseline, shifted, appended):
        svg = ET.fromstring(rendered.artifact.content)
        content = "".join(svg.itertext())
        assert "+3d" in content and "-2d" in content
        assert not [item for item in rendered.scene.diagnostics if item.startswith("E_")]
    assert _anchor_sides(baseline) == _anchor_sides(shifted) == _anchor_sides(appended)
    assert _suppressed_relations(baseline) == _suppressed_relations(shifted) == _suppressed_relations(appended)
