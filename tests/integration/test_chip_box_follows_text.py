"""#1141 Part 1: a filled square label chip follows its measured text in real SVG."""
from __future__ import annotations

import re
from datetime import date
from hashlib import sha256

import pytest

from chrona.presentation.model.closure import ClosureError
from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document, serialize_scene
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr
from tests.support.legacy_axis import use_legacy_six_tier_axis


def _parts(*, viewer_fit: str | None = None, radius: float = 0, physical_radius=None,
           stroke: bool = False, solid_fill: bool = True):
    parts = use_legacy_six_tier_axis(sr.bundle("executive-light"))
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
    if physical_radius is not None:
        body["values"]["chip-physical-radius"] = {"type": "radius", "value": physical_radius}
    body["roles"]["member-label-chip"] = {
        "backgroundTreatment": "fill", "chipPadding": "chip-padding", "markCornerRadius": "chip-radius",
    }
    if physical_radius is not None:
        body["roles"]["member-label-chip"]["cornerRadius"] = "chip-physical-radius"
    if solid_fill:
        body["colorBindings"]["member-label-chip.fill"] = "surfaceRaised"
    if stroke:
        body["values"]["chip-stroke-width"] = {"type": "number", "value": 1}
        body["roles"]["member-label-chip"].update(strokeWidth="chip-stroke-width")
        body["colorBindings"]["member-label-chip.stroke"] = "surfaceRaised"
    if viewer_fit is not None:
        body["roles"]["member-label-chip"]["viewerFit"] = viewer_fit
    return parts


def _render(tmp_path, name: str, *, viewer_fit: str | None = None, radius: float = 0,
            physical_radius=None, stroke: bool = False, solid_fill: bool = True):
    directory = tmp_path / name
    directory.mkdir()
    source = sr.project({
        "a": sr.span("a", date(2026, 2, 2), 30, title="Alpha"),
        "b": sr.span("b", date(2026, 3, 9), 20,
                     title="Beta Release Candidate " * 3),
    })
    for key, phase in (("a", "Build"), ("b", "Verify")):
        source["objects"][key]["fields"]["phase"] = phase
    return sr.render(directory, source, presentation=_parts(viewer_fit=viewer_fit, radius=radius,
                                                              physical_radius=physical_radius, stroke=stroke,
                                                              solid_fill=solid_fill))


def _fit_failure(call):
    with pytest.raises((RenderFailed, ClosureError)) as raised:
        call()
    error = raised.value
    return (getattr(error, "code", None) or error.diagnostic_id, error.source_ref)


def _assert_svg_chip_follows_text(rendered, chip, label):
    fit = label.text_layout.fit
    assert chip.viewer_fit == "box-follows-text"
    assert fit is not None and fit.mode == "box-follows-text" and fit.box_id == chip.scene_id
    assert fit.end_pad_spaces > 0
    scene_primitives = {item["id"]: item for surface in scene_document(rendered.scene)["surfaces"]
                        for item in surface["primitives"]}
    assert scene_primitives[chip.scene_id]["viewerFit"] == "box-follows-text"
    assert scene_primitives[label.scene_id]["textLayout"]["fit"]["boxId"] == chip.scene_id
    svg = rendered.artifact.content.decode("utf-8")
    assert f'<rect data-scene-id="{chip.scene_id}"' not in svg
    group = re.search(rf'<g data-scene-id="{re.escape(chip.scene_id)}"[^>]*>(.*?)</g>', svg, re.S)
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


def test_default_and_explicit_raw_chip_output_are_byte_identical(tmp_path):
    raw = _render(tmp_path, "raw")
    explicit_raw = _render(tmp_path, "explicit-raw", viewer_fit="raw")
    assert raw.artifact.content == explicit_raw.artifact.content
    assert sha256(raw.artifact.content).hexdigest() == "51c54350062c2774890471a04b76bd42e2e2775d04d81547523e0e92687049ef"
    assert sha256(serialize_scene(raw.scene)).hexdigest() == "445031fb33b78daae640a2c9720a9d66fa76210079eb0da978f6710334807368"
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
    for label in labels:
        chip_id = f"chip:{label.scene_id}"
        chip = chips[chip_id]
        _assert_svg_chip_follows_text(fitted, chip, label)


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


def test_physical_zero_radius_overrides_a_rounded_legacy_chip_and_is_admitted(tmp_path):
    rendered = _render(tmp_path, "physical-zero", viewer_fit="box-follows-text", radius=0.2, physical_radius=0)
    chip = next(item for item in rendered.surface.primitives
                if item.kind == "Rect" and item.visual_role == "member-label-chip")
    label = next(item for item in rendered.surface.primitives
                 if item.kind == "Text" and item.purpose == "member-label" and f"chip:{item.scene_id}" == chip.scene_id)
    assert chip.corner_radius in (None, 0)
    _assert_svg_chip_follows_text(rendered, chip, label)


@pytest.mark.parametrize("physical_radius", [3.0, "capsule"])
def test_positive_or_capsule_physical_radius_is_refused_at_its_declaration(tmp_path, physical_radius):
    code, source_ref = _fit_failure(lambda: _render(
        tmp_path, "invalid-radius", viewer_fit="box-follows-text", physical_radius=physical_radius))
    assert code == "E_THEME_TOKEN_TYPE"
    assert source_ref == "/body/roles/member-label-chip/cornerRadius"


def test_a_chip_without_a_solid_fill_is_refused_at_its_fill_declaration(tmp_path):
    code, source_ref = _fit_failure(lambda: _render(
        tmp_path, "missing-fill", viewer_fit="box-follows-text", solid_fill=False))
    assert code == "E_THEME_ROLE_REQUIRED"
    assert source_ref == "/body/roles/member-label-chip/fill"


def _other_chip_render(tmp_path, name, family, *, viewer_fit=None):
    if family == "period-label-chip":
        # Reuse the published named-period synthetic fixture so its View and source contracts stay authoritative.
        from tests.integration.test_named_periods import _labelled, _parts as period_parts, _render as period_render, _source

        parts = _labelled(period_parts(), "top", chip=True)
        if viewer_fit is not None:
            parts["theme"]["body"]["roles"][family]["viewerFit"] = viewer_fit
        return period_render(tmp_path, _source(window={"title": "Launch window", "start": "2026-02-01",
                                                       "end": "2026-03-01"}), parts, name=name)

    parts = sr.bundle("executive-light")
    body = parts["theme"]["body"]
    body["values"]["other-chip-padding"] = {"type": "number", "value": 0.75}
    body["roles"][family] = {"backgroundTreatment": "fill", "chipPadding": "other-chip-padding"}
    body["colorBindings"][f"{family}.fill"] = "surfaceRaised" if family == "finish-delta-chip" else "warning"
    if viewer_fit is not None:
        body["roles"][family]["viewerFit"] = viewer_fit

    source = sr.project({"a": sr.span("a", date(2026, 2, 2), 30, title="Alpha")})
    if family == "as-of-label-chip":
        actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
                  "body": {"asOf": "2026-02-20", "observations": []}}
    else:
        parts["view"]["body"]["rows"] = {"mode": "automatic"}
        parts["view"]["body"]["visibility"]["labels"]["content"] = ["title"]
        actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
                  "body": {"asOf": "2026-04-30", "observations": [{
                      "id": "a-observed", "sequence": 1, "projectObjectId": "a",
                      "actual": {"start": "2026-02-02", "finish": "2026-03-10", "progress": 1.0}}]}}
    directory = tmp_path / name
    directory.mkdir()
    return sr.render(directory, source, presentation=parts, actual=actual)


def _other_chip_label(rendered, family):
    label_id = {"as-of-label-chip": "as-of-label", "finish-delta-chip": "finish-delta",
                "period-label-chip": "period-label"}[family]
    return next(item for item in rendered.surface.primitives if item.kind == "Text"
                and (item.scene_id == label_id if family == "as-of-label-chip" else item.purpose == label_id))


@pytest.mark.parametrize("family", ["as-of-label-chip", "finish-delta-chip", "period-label-chip"])
def test_other_chip_families_have_real_raw_svg_box_and_label_pairs(tmp_path, family):
    rendered = _other_chip_render(tmp_path, "raw", family)
    labels = [_other_chip_label(rendered, family)]
    chips = [item for item in rendered.surface.primitives
             if item.kind == "Rect" and item.visual_role == family]
    assert len(labels) == len(chips) == 1
    label, chip = labels[0], chips[0]
    assert chip.scene_id == f"chip:{label.scene_id}" and chip.paint.fill
    svg = rendered.artifact.content.decode("utf-8")
    assert f'<rect data-scene-id="{chip.scene_id}"' in svg
    assert f'<text data-scene-id="{label.scene_id}"' in svg


@pytest.mark.parametrize("family", ["as-of-label-chip", "finish-delta-chip", "period-label-chip"])
def test_other_chip_families_accept_box_follows_text(tmp_path, family):
    raw = _other_chip_render(tmp_path, "raw", family)
    rendered = _other_chip_render(tmp_path, "fitted", family, viewer_fit="box-follows-text")
    assert [(item.scene_id, item.bounds, item.paint) for item in rendered.surface.primitives] == [
        (item.scene_id, item.bounds, item.paint) for item in raw.surface.primitives]
    assert evaluate_scene_contrast(scene_document(rendered.scene)) == evaluate_scene_contrast(scene_document(raw.scene))
    label = _other_chip_label(rendered, family)
    chip = next(item for item in rendered.surface.primitives if item.kind == "Rect"
                and item.visual_role == family)
    _assert_svg_chip_follows_text(rendered, chip, label)
