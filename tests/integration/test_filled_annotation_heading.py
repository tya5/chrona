"""Filled heading closure on synthetic Projects (#1347), through Scene and SVG."""
from copy import deepcopy
from xml.etree import ElementTree as ET

import pytest

from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

SUBJECT = "word " * 7 + "words"


def _render(path, *, title=SUBJECT, fill=True, forbid=False, tilt=0, stamp=None, rail=True):
    path.mkdir(parents=True, exist_ok=True)
    source = ak.project(("risk",), text="Short body.")
    source["objects"]["t0"]["title"] = title
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    sr.with_note_rail(parts, 300)
    ak.with_kind_theme(parts, stamp=stamp, border_side="start", border_width=6)
    theme = parts["theme"]["body"]
    theme["annotationKinds"]["risk"]["title"] = "{label}"
    theme["annotationKinds"]["risk"]["heading"] = "{subject}"
    theme["roles"]["annotation-heading"] = deepcopy(theme["roles"]["annotation-kind-label"])
    theme["roles"]["annotation-heading"]["fontSize"] = "heading-size"
    theme["values"]["heading-size"] = {"type": "number", "value": 24}
    theme["colorBindings"]["annotation-heading.fill"] = "text"
    container = {"outline": "rectangle", "cornerRadius": 0,
                 "inlineSize": "fill" if fill else "content",
                 "contentInsetEm": {"top": 0.5, "bottom": 0.5, "left": 0.5, "right": 0.5},
                 "border": {"start": {"width": 6, "paint": "kind"}}}
    if tilt:
        container["tiltDegrees"] = [tilt]
    theme["values"]["note-container"] = {"type": "annotationContainer", "value": container}
    theme["roles"]["annotation-note-box"]["annotationContainer"] = "note-container"
    parts["view"]["body"]["annotations"][0]["candidates"] = [sr.candidate(
        "rail", region={"kind": "slot", "source": "annotations"}, search_kind="row-aligned",
        connector="none")]
    parts["view"]["body"]["visibility"]["annotations"]["marker"] = "none"
    if not rail:
        parts["view"]["body"]["annotations"][0]["candidates"] = [sr.candidate("plot", connector="none")]
    if forbid:
        for key in ("selection", "grouping", "ordering"):
            parts["view"]["body"].pop(key, None)
        parts["view"]["body"]["rows"] = {"mode": "explicit", "items": [
            {"id": key, "depth": 0, "items": [{"id": key, "source": {"kind": "primary", "object": key},
                "presentation": {"text": {"wrap": "forbid"}}}]} for key in source["objects"]]}
    result = ak.render(path, source, parts)
    ids = {p.scene_id: p for p in result.scene.surfaces[0].primitives}
    return result, ids["annotation-box:view-n0"], ids["annotation-heading:view-n0"], ids["annotation-text:view-n0"]


@pytest.mark.parametrize("tilt,stamp", [(0, None), (0, "start-top"), (0, "end-top"), (4, None)])
def test_filled_subject_wraps_and_keeps_actual_svg_viewport(tmp_path, tilt, stamp):
    assert len(SUBJECT) == 40
    result, box, heading, body = _render(tmp_path, tilt=tilt, stamp=stamp)
    assert len(heading.text_layout.lines) >= 2
    assert heading.text == SUBJECT
    assert box.bounds[2] == pytest.approx(300, abs=0.01)
    assert heading.bounds[0] >= box.bounds[0] - 0.01
    assert heading.bounds[0] + heading.bounds[2] <= box.bounds[0] + box.bounds[2] + 0.01
    if not tilt:
        assert body.bounds[1] >= heading.bounds[1] + heading.bounds[3] - 0.01
    svg = ET.fromstring(result.artifact.content)
    assert svg.attrib["viewBox"] == "0 0 1600 900"
    actual = next(p for p in svg.iter() if p.get("data-scene-id") == heading.scene_id)
    assert len(list(actual)) >= 2
    assert not any(w.payload["code"] == "W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT" for w in result.warning_records)


@pytest.mark.parametrize("options", [{"title": "X" * 40}, {"forbid": True}, {"fill": False}, {"rail": False}])
def test_nonwrappable_or_content_heading_keeps_natural_line(tmp_path, options):
    _, box, heading, _ = _render(tmp_path, **options)
    assert len(heading.text_layout.lines) == 1
    assert box.bounds[2] > 300


def test_short_filled_heading_remains_one_line(tmp_path):
    _, box, heading, body = _render(tmp_path, title="Short")
    assert len(heading.text_layout.lines) == 1
    assert box.bounds[2] == pytest.approx(300)
    assert body.bounds[1] >= heading.bounds[1] + heading.bounds[3] - 0.01


def test_fitting_heading_keeps_scene_and_svg_bytes(tmp_path, monkeypatch):
    from chrona.presentation.layout import surface_annotations
    with monkeypatch.context() as context:
        context.setattr(surface_annotations, "complete_kind_heading", lambda measure, **kwargs: measure)
        before, *_ = _render(tmp_path / "before", title="Short")
    after, *_ = _render(tmp_path / "after", title="Short")
    assert before.scene.surfaces == after.scene.surfaces
    assert before.artifact.content == after.artifact.content
