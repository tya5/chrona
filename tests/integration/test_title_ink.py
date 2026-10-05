"""A Theme can give View heading lines their own ink without affecting their shared text style."""
from __future__ import annotations

from datetime import date
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast, policy_member_of
from chrona.presentation.scene.serialization import scene_document
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": "2026-02-20", "observations": []}}
INK_VALUE = "heading-ink-opacity"


def _source():
    source = sr.project({"alpha": sr.span("alpha", date(2026, 2, 2), 20, title="Alpha")})
    source["project"]["title"] = "Quarterly review"
    return source


def _parts(*, fills: dict[str, str] | None = None, opacities: dict[str, float] | None = None,
           policy: str | None = None, unsupported_stroke: bool = False):
    parts = sr.bundle("control-room-dark")
    body = parts["theme"]["body"]
    # This preset ships a muted subtitle fill. The test exercises the new
    # title/subtitle fallback contract, so remove existing fills explicitly.
    body["colorBindings"].pop("subtitle.fill", None)
    for role in ("heading", "subtitle"):
        if isinstance(body["roles"].get(role), dict):
            body["roles"][role].pop("fill", None)
    parts["view"]["body"]["heading"] = {"title": "{project}", "subtitle": "Review status"}
    for role, intent in (fills or {}).items():
        body["colorBindings"][f"{role}.fill"] = intent
    for role, opacity in (opacities or {}).items():
        token = f"{role}-opacity"
        body["values"][token] = {"type": "number", "value": opacity}
        body["roles"].setdefault(role, {})["opacity"] = token
    if unsupported_stroke:
        body["colorBindings"]["heading.stroke"] = "text"
    if policy is not None:
        body["contrastPolicy"] = {"groundText": policy}
    return parts


def _render(directory, **options):
    directory.mkdir(parents=True, exist_ok=True)
    return sr.render(directory, _source(), presentation=_parts(**options), actual=ACTUAL)


def _network_parts(**options):
    parts = _parts(**options)
    layout = parts["layout"]
    layout["requiredThemeTokens"] = ["spacing.l", "spacing.m"]
    title_slot = sr.find_node(layout, "title")
    layout["root"]["children"] = [title_slot, {
        "id": "network", "kind": "slot", "source": "network", "inlineSize": "fill", "blockSize": "fill",
        "place": {"inline": "stretch", "block": "stretch", "safety": "strict"},
        "priority": "required", "overflow": "visible-overflow",
    }]
    body = parts["view"]["body"]
    body["surface"] = "dependency-network"
    for key in ("tableColumns", "hierarchyColumn", "backgroundDecoration", "axis", "markers", "shading",
                "timePresentation", "annotations", "annotationPresentation"):
        body.pop(key, None)
    body["rows"] = {"mode": "automatic"}
    body["grouping"] = {"by": "none", "missing": "ungrouped"}
    body["visibility"] = {"labels": False, "relations": "semantic", "annotations": "none"}
    return parts


def _texts(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives
            if item.scene_id in {"title", "subtitle"}}


def _svg_texts(rendered):
    root = ET.fromstring(rendered.artifact.content)
    return {node.attrib["data-scene-id"]: node for node in root.iter()
            if node.attrib.get("data-scene-id") in {"title", "subtitle"}}


def _geometry_signature(primitive):
    layout = primitive.text_layout
    return primitive.bounds, layout.lines, layout.asset_identity, layout.font_size, layout.family


def test_heading_fill_paints_both_lines_in_scene_and_svg_without_moving_or_retypesetting(tmp_path):
    plain = _render(tmp_path / "plain")
    painted = _render(tmp_path / "painted", fills={"heading": "accent", "subtitle": "negative"},
                      opacities={"heading": 0.65, "subtitle": 0.8})

    before, after = _texts(plain), _texts(painted)
    assert set(before) == set(after) == {"title", "subtitle"}
    assert before["title"].text == "Quarterly review" and before["subtitle"].text == "Review status"
    for key, role in (("title", "heading"), ("subtitle", "subtitle")):
        assert after[key].visual_role == role
        assert after[key].paint.fill != before[key].paint.fill
        assert after[key].paint.opacity == pytest.approx(0.65 if key == "title" else 0.8)
        assert _geometry_signature(after[key]) == _geometry_signature(before[key])

    svg = _svg_texts(painted)
    assert set(svg) == {"title", "subtitle"}
    assert svg["title"].attrib["fill"] == after["title"].paint.fill
    assert svg["subtitle"].attrib["fill"] == after["subtitle"].paint.fill
    assert float(svg["title"].attrib["opacity"]) == pytest.approx(0.65)
    assert float(svg["subtitle"].attrib["opacity"]) == pytest.approx(0.8)


def test_no_fill_including_opacity_only_keeps_scene_and_svg_bytes_unchanged(tmp_path):
    plain = _render(tmp_path / "plain")
    opacity_only = _render(tmp_path / "opacity-only", opacities={"heading": 0.4, "subtitle": 0.7})

    # Provenance and diagnostics are not shared text output: opacity without a
    # fill must leave the completed text primitives and serialized SVG exact.
    assert _texts(opacity_only) == _texts(plain)
    assert opacity_only.artifact.content == plain.artifact.content
    assert {key: primitive.paint.fill for key, primitive in _texts(opacity_only).items()} == {
        key: primitive.paint.fill for key, primitive in _texts(plain).items()}


def test_heading_stroke_is_rejected_at_the_binding_pointer(tmp_path):
    with pytest.raises(Exception) as caught:
        _render(tmp_path, unsupported_stroke=True)

    error = caught.value
    assert getattr(error, "diagnostic_id", getattr(error, "code", None)) == "E_THEME_ROLE_PROPERTY_UNSUPPORTED"
    assert getattr(error, "source_ref", None) == "/body/colorBindings/heading.stroke"


@pytest.mark.parametrize("severity", ["warning", "none"])
def test_low_contrast_heading_and_subtitle_are_classified_as_ground_text(tmp_path, severity):
    rendered = _render(tmp_path, fills={"heading": "surface", "subtitle": "surface"}, policy=severity)
    findings = [item for item in evaluate_scene_contrast(
        scene_document(rendered.scene), policy={"groundText": severity})
                if item.primitive_id in {"title", "subtitle"}]

    if severity == "warning":
        assert {(item.primitive_id, item.severity, item.severity_class, policy_member_of(item))
                for item in findings} == {
            ("title", "warning", "legibility", "groundText"),
            ("subtitle", "warning", "legibility", "groundText")}
        assert {item.ground_id for item in findings} == {"canvas"}
        records = [record.payload for record in rendered.warning_records
                   if record.payload["code"] == "W_SCENE_STATE_TEXT_CONTRAST"]
        assert {primitive_id for payload in records for primitive_id in payload["primitiveIds"]} == {
            "title", "subtitle"}
        assert all(payload["severity"] == "warning" for payload in records)
    else:
        assert {(item.primitive_id, item.severity, policy_member_of(item)) for item in findings} == {
            ("title", "info", "groundText"), ("subtitle", "info", "groundText")}
        assert not [warning for warning in rendered.warning_records
                    if warning.payload["code"] == "W_SCENE_STATE_TEXT_CONTRAST"]


def test_low_contrast_heading_and_subtitle_can_be_made_blocking(tmp_path):
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, fills={"heading": "surface", "subtitle": "surface"}, policy="error")

    assert caught.value.code == "E_SCENE_STATE_TEXT_CONTRAST"
    assert caught.value.source_ref == "/body/contrastPolicy/groundText"


@pytest.mark.parametrize("role", ["heading", "subtitle"])
def test_view_text_role_keeps_heading_roles_in_ground_text_policy(tmp_path, role):
    parts = _parts(fills={role: "surface"}, policy="warning")
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["tableColumns"] = [{
        "id": "Task", "source": "title", "missing": "em-dash", "align": "start",
        "width": "content", "headerOrientation": "horizontal", "textRole": role,
    }]
    rendered = sr.render(tmp_path, _source(), presentation=parts, actual=ACTUAL)

    cell = next(item for item in rendered.surface.primitives
                if item.purpose == "table-cell" and item.source_ref == "alpha")
    assert cell.visual_role == role
    findings = [item for item in evaluate_scene_contrast(
        scene_document(rendered.scene), policy={"groundText": "warning"})
        if item.primitive_id == cell.scene_id]
    assert len(findings) == 1
    (finding,) = findings
    assert (finding.severity, finding.severity_class, policy_member_of(finding), finding.ground_id) == (
        "warning", "legibility", "groundText", "row-band:alpha")
    assert any(record.payload["code"] == "W_SCENE_STATE_TEXT_CONTRAST"
               and cell.scene_id in record.payload["primitiveIds"]
               for record in rendered.warning_records)


def test_dependency_network_title_uses_shared_fill_opt_in_and_opacity_fallback(tmp_path):
    def render(name, **options):
        directory = tmp_path / name
        directory.mkdir()
        return sr.render(directory, _source(), presentation=_network_parts(**options), actual=ACTUAL)

    plain = render("plain")
    opacity_only = render("opacity-only", opacities={"heading": 0.4, "subtitle": 0.7})
    explicitly_painted = render("painted", fills={"heading": "accent"})

    assert _texts(plain)
    assert _texts(opacity_only) == _texts(plain)
    assert opacity_only.artifact.content == plain.artifact.content
    assert _texts(explicitly_painted)["title"].visual_role == "heading"
    assert _texts(explicitly_painted)["title"].paint.fill != _texts(plain)["title"].paint.fill
    assert _geometry_signature(_texts(explicitly_painted)["title"]) == _geometry_signature(_texts(plain)["title"])
    plain_labels = {item.scene_id: item for item in plain.surface.primitives
                    if item.source_kind == "network" and item.scene_id != "title" and item.kind == "Text"}
    painted_labels = {item.scene_id: item for item in explicitly_painted.surface.primitives
                      if item.source_kind == "network" and item.scene_id != "title" and item.kind == "Text"}
    assert plain_labels
    assert painted_labels == plain_labels
    assert all(item.visual_role == "text" for item in painted_labels.values())
