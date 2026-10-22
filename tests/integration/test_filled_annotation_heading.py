"""Filled heading closure on synthetic Projects (#1347), through Scene and SVG."""
from copy import deepcopy
from xml.etree import ElementTree as ET

import pytest

from tests.support import annotation_border as ab
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

SUBJECT = "word " * 7 + "words"
KIND_TITLE_40 = "Kind " * 7 + "Title"


def _render(path, *, title=SUBJECT, kind_title="RISK", kind_secondary="WARNING",
            secondary_size=11, fill=True, forbid=False, tilt=0, stamp=None, rail=True, cjk=False):
    path.mkdir(parents=True, exist_ok=True)
    source = ak.project(("risk",), text="Short body.")
    source["objects"]["t0"]["title"] = title
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    sr.with_note_rail(parts, 300)
    ak.with_kind_theme(parts, stamp=stamp, border_side="start", border_width=6)
    theme = parts["theme"]["body"]
    theme["annotationKinds"]["risk"]["title"] = "{label}"
    theme["annotationKinds"]["risk"]["label"] = kind_title
    theme["annotationKinds"]["risk"]["secondary"] = kind_secondary
    theme["annotationKinds"]["risk"]["heading"] = "{subject}"
    theme["roles"]["annotation-heading"] = deepcopy(theme["roles"]["annotation-kind-label"])
    theme["roles"]["annotation-heading"]["fontSize"] = "heading-size"
    if cjk:
        theme["values"]["cjk-kind-family"] = {
            "type": "fontFamily", "value": "Noto Sans JP, sans-serif"}
        for role in ("annotation-kind-label", "annotation-kind-secondary", "annotation-heading"):
            theme["roles"][role]["fontFamily"] = "cjk-kind-family"
    theme["values"]["kind-secondary-size"]["value"] = secondary_size
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
    parts["view"]["body"]["annotations"][0]["candidates"] = ab.border_candidates()
    parts["view"]["body"]["visibility"]["annotations"]["marker"] = "none"
    if not rail:
        parts["view"]["body"]["annotations"][0]["candidates"] = [sr.candidate("plot", connector="none")]
    if forbid:
        for key in ("selection", "grouping", "ordering"):
            parts["view"]["body"].pop(key, None)
        parts["view"]["body"]["rows"] = {"mode": "explicit", "items": [
            {"id": key, "depth": 0, "items": [{"id": key, "source": {"kind": "primary", "object": key},
                "presentation": {"text": {"wrap": "forbid"}}}]} for key in source["objects"]]}
    if cjk:
        pytest.importorskip("chrona_fonts_noto_cjk", reason="requires the optional local CJK font provider")
        from tests.support import text_treatments
        result = text_treatments.render(path, source, parts, cjk=True)
    else:
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
    result, box, heading, _ = _render(tmp_path, **options)
    assert len(heading.text_layout.lines) == 1
    assert box.bounds[2] > 300
    if options.get("rail", True):
        assert any(warning.payload.get("code") == "W_LAYOUT_LABEL_OVERFLOW"
                   and warning.payload.get("placementId") == "annotation-heading:view-n0"
                   and warning.payload.get("behaviour") == "visible-overflow"
                   for warning in result.warning_records)


def test_short_filled_heading_remains_one_line(tmp_path):
    result, box, heading, body = _render(tmp_path, title="Short")
    assert len(heading.text_layout.lines) == 1
    assert box.bounds[2] == pytest.approx(300)
    assert body.bounds[1] >= heading.bounds[1] + heading.bounds[3] - 0.01
    assert not any(warning.payload.get("code") == "W_LAYOUT_LABEL_OVERFLOW"
                   for warning in result.warning_records)


def test_filled_kind_title_and_secondary_wrap_with_their_own_role_metrics(tmp_path):
    assert len(KIND_TITLE_40) == 40
    result, box, heading, body = _render(
        tmp_path, title="Short", kind_title=KIND_TITLE_40,
        kind_secondary=KIND_TITLE_40, secondary_size=40)
    primitives = {item.scene_id: item for item in result.scene.surfaces[0].primitives}
    title_line = primitives["annotation-kind-text:view-n0:0"]
    secondary_line = primitives["annotation-kind-text:view-n0:1"]
    bar = primitives["annotation-kind-bar:view-n0"]

    assert title_line.text == KIND_TITLE_40
    assert title_line.text_layout.font_size == 16
    assert len(title_line.text_layout.lines) >= 2
    assert secondary_line.text == KIND_TITLE_40
    assert secondary_line.text_layout.font_size == 40
    assert len(secondary_line.text_layout.lines) > len(title_line.text_layout.lines)
    assert box.bounds[2] == pytest.approx(300, abs=0.01)
    assert bar.bounds[3] > 2 * 16 * 1.2
    assert body.bounds[1] >= heading.bounds[1] + heading.bounds[3] - 0.01
    svg = ET.fromstring(result.artifact.content)
    assert svg.attrib["viewBox"] == "0 0 1600 900"
    for scene_id in (title_line.scene_id, secondary_line.scene_id):
        node = next(item for item in svg.iter() if item.get("data-scene-id") == scene_id)
        assert len(list(node)) >= 2
    assert not any(w.payload["code"] == "W_LAYOUT_CANVAS_EXCEEDS_VIEWPORT" for w in result.warning_records)


@pytest.mark.parametrize("options", [{"fill": False}, {"forbid": True}, {"kind_title": "X" * 40}])
def test_kind_title_stays_single_line_when_note_is_content_sized_or_wrap_forbidden(tmp_path, options):
    render_options = dict(options)
    kind_title = render_options.pop("kind_title", KIND_TITLE_40)
    result, box, _, _ = _render(tmp_path, title="Short", kind_title=kind_title, **render_options)
    # Only a fill-enabled, wrapping annotation rung gets the filled-slot rule.
    # The old natural width is kept and the existing visible-overflow path owns it.
    title_line = next(item for item in result.scene.surfaces[0].primitives
                      if item.scene_id == "annotation-kind-text:view-n0:0")
    assert len(title_line.text_layout.lines) == 1
    assert box.bounds[2] > 300


@pytest.mark.parametrize("kind_title,kind_secondary,cjk", [
    ("RISK REPORT", "WARNING", False),
    ("報告 REPORT", "警告 WARNING", True),
])
def test_fitting_heading_keeps_scene_and_svg_bytes(tmp_path, monkeypatch, kind_title, kind_secondary, cjk):
    from chrona.presentation.layout import annotation_card_measurement
    with monkeypatch.context() as context:
        context.setattr(annotation_card_measurement, "complete_kind_frame", lambda measure, **kwargs: measure)
        before, *_ = _render(tmp_path / "before", title="Short", kind_title=kind_title,
                             kind_secondary=kind_secondary, cjk=cjk)
    after, *_ = _render(tmp_path / "after", title="Short", kind_title=kind_title,
                        kind_secondary=kind_secondary, cjk=cjk)
    assert before.scene.surfaces == after.scene.surfaces
    assert before.artifact.content == after.artifact.content
