"""#1141 Part 1: a filled square label chip follows its measured text in real SVG."""
from __future__ import annotations

import re
from hashlib import sha256
from datetime import date

import pytest

from chrona.presentation.model.closure import ClosureError
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document, serialize_scene
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


def _parts(*, viewer_fit: str | None = None, radius: float = 0, stroke: bool = False):
    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    body_view = parts["view"]["body"]
    for key in ("selection", "grouping", "ordering"):
        body_view.pop(key, None)
    body_view["rows"] = {"mode": "explicit", "items": [
        {"id": "row-a", "depth": 0, "tableSubject": "a",
         "items": [{"id": "a", "source": {"kind": "primary", "object": "a"}}]},
        {"id": "row-b", "depth": 0, "tableSubject": "b",
         "items": [{"id": "b", "source": {"kind": "primary", "object": "b"},
                    "presentation": {"text": {"wrap": "allow"}}}]},
    ]}
    parts["view"]["body"]["tableColumns"] = [
        {"id": "Work package", "source": "title", "missing": "em-dash", "align": "start",
         "width": "content", "headerOrientation": "horizontal"},
        {"id": "Phase", "source": {"field": "phase"}, "missing": "em-dash", "align": "start",
         "width": "content", "headerOrientation": "horizontal"},
    ]
    body["values"]["chip-padding"] = {"type": "number", "value": 0.75}
    body["values"]["chip-radius"] = {"type": "number", "value": radius}
    body["roles"]["member-label-chip"] = {
        "backgroundTreatment": "fill", "chipPadding": "chip-padding", "markCornerRadius": "chip-radius",
    }
    body["colorBindings"]["member-label-chip.fill"] = "surfaceRaised"
    if stroke:
        body["values"]["chip-stroke-width"] = {"type": "number", "value": 1}
        body["roles"]["member-label-chip"].update(strokeWidth="chip-stroke-width")
        body["colorBindings"]["member-label-chip.stroke"] = "surfaceRaised"
    if viewer_fit is not None:
        body["roles"]["member-label-chip"]["viewerFit"] = viewer_fit
    return parts


def _render(tmp_path, name: str, *, viewer_fit: str | None = None, radius: float = 0, stroke: bool = False):
    directory = tmp_path / name
    directory.mkdir()
    source = sr.project({
        "a": sr.span("a", date(2026, 2, 2), 30, title="Alpha"),
        "b": sr.span("b", date(2026, 3, 9), 20,
                     title="Beta Release Candidate " * 3),
    })
    for key, phase in (("a", "Build"), ("b", "Verify")):
        source["objects"][key]["fields"]["phase"] = phase
    return sr.render(directory, source, presentation=_parts(viewer_fit=viewer_fit, radius=radius, stroke=stroke))


def _fit_failure(call):
    with pytest.raises((RenderFailed, ClosureError)) as raised:
        call()
    error = raised.value
    return (getattr(error, "code", None) or error.diagnostic_id, error.source_ref)


def test_default_and_explicit_raw_chip_output_are_byte_identical(tmp_path):
    raw = _render(tmp_path, "raw")
    explicit_raw = _render(tmp_path, "explicit-raw", viewer_fit="raw")
    assert raw.artifact.content == explicit_raw.artifact.content
    assert sha256(raw.artifact.content).hexdigest() == "51c54350062c2774890471a04b76bd42e2e2775d04d81547523e0e92687049ef"
    assert sha256(serialize_scene(raw.scene)).hexdigest() == "3b2b6d88cf8415ea3938f3413a1aa0f5283f18ed0812dacf6039a07ce81cfac5"
    labels = [item for item in raw.surface.primitives if item.kind == "Text" and item.purpose == "member-label"]
    assert labels and any(len(item.text_layout.lines) > 1 for item in labels)
    assert "<tspan" in raw.artifact.content.decode("utf-8")


def test_a_square_filled_chip_tracks_multiline_text_in_svg_without_scene_or_contrast_change(tmp_path):
    raw = _render(tmp_path, "raw")
    fitted = _render(tmp_path, "fitted", viewer_fit="box-follows-text")
    raw_primitives = raw.surface.primitives
    fitted_primitives = fitted.surface.primitives
    assert [(item.scene_id, item.bounds, item.paint) for item in fitted_primitives] == [
        (item.scene_id, item.bounds, item.paint) for item in raw_primitives]
    assert evaluate_scene_contrast(scene_document(fitted.scene)) == evaluate_scene_contrast(scene_document(raw.scene))

    chips = {item.scene_id: item for item in fitted_primitives
             if item.kind == "Rect" and item.visual_role == "member-label-chip"}
    labels = [item for item in fitted_primitives if item.kind == "Text" and item.purpose == "member-label"]
    assert chips and labels
    assert any(len(item.text_layout.lines) > 1 for item in labels)
    svg = fitted.artifact.content.decode("utf-8")
    for label in labels:
        chip_id = f"chip:{label.scene_id}"
        chip = chips[chip_id]
        fit = label.text_layout.fit
        assert chip.viewer_fit == "box-follows-text"
        assert fit is not None and fit.mode == "box-follows-text" and fit.box_id == chip_id
        assert fit.end_pad_spaces > 0
        assert f'<rect data-scene-id="{chip_id}"' not in svg
        group = re.search(rf'<g data-scene-id="{re.escape(chip_id)}"[^>]*>(.*?)</g>', svg, re.S)
        assert group and f'data-scene-id="{label.scene_id}"' in group.group(1)
        assert 'filter="url(#fit-' in group.group(0)
        rendered_lines = re.findall(r"<tspan\b[^>]*>(.*?)</tspan>", group.group(1), re.S)
        if not rendered_lines:
            direct_text = re.search(r"<text\b[^>]*>(.*?)</text>", group.group(1), re.S)
            assert direct_text
            rendered_lines = [direct_text.group(1)]
        assert len(rendered_lines) == len(label.text_layout.lines)
        assert all(line.endswith(" " * fit.end_pad_spaces) for line in rendered_lines)
        assert 'xml:space="preserve"' in group.group(1)


@pytest.mark.parametrize(
    ("options", "expected_code", "pointer"),
    [
        ({"radius": 0.2}, "E_THEME_TOKEN_TYPE", "/body/roles/member-label-chip/markCornerRadius"),
        ({"stroke": True}, "E_PRESENTATION_VIEWER_FIT_PAINT", "/body/roles/member-label-chip"),
    ],
)
def test_non_square_or_stroked_chip_is_refused_at_its_theme_declaration(tmp_path, options, expected_code, pointer):
    code, source_ref = _fit_failure(
        lambda: _render(tmp_path, "invalid", viewer_fit="box-follows-text", **options))
    assert (code, source_ref) == (expected_code, pointer)
