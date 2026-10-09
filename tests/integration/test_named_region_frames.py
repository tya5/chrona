"""Layout-selected Theme roles paint named region frames through the completed Scene and SVG."""
from __future__ import annotations

from datetime import date, timedelta
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from tests.support import synthetic_review as sr


ROOT = Path(__file__).resolve().parents[2]
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
DOTS = "chrona-target-parts:ben-day-dots"
FRAME_IDS = ("region-frame:title-panel", "region-frame:review")


def _source():
    objects = {}
    for index, owner in enumerate("abc"):
        for step in range(2):
            key = f"{owner}{step}"
            objects[key] = sr.span(key, date(2026, 3, 2) + timedelta(days=index * 9 + step * 50),
                                   40, owner=owner, title=f"Synthetic task {key}")
    return sr.project(objects)


def _parts(frames, *, roles=None, bindings=None, values=None, theme_version=None):
    parts = sr.bundle("executive-light")
    if theme_version is not None:
        parts["theme"]["version"] = theme_version
    layout = parts["layout"]
    title = layout["root"]["children"][0]
    panel = {
        "id": "title-panel", "kind": "row", "inlineSize": "content", "blockSize": "content",
        "gap": {"token": "spacing.none"}, "padding": {"token": "spacing.m"},
        "alignItems": "start", "justifyContent": "start",
        "place": {"inline": "center", "block": "start", "safety": "safe"}, "children": [title],
    }
    layout["root"]["children"][0] = panel
    layout["requiredThemeTokens"] = sorted({*layout["requiredThemeTokens"], "spacing.none", "spacing.m"})
    for node_id, frame in frames.items():
        sr.find_node(layout, node_id)["frame"] = dict(frame)

    body = parts["theme"]["body"]
    body["values"].update(values or {})
    body["roles"].update(roles or {})
    body["colorBindings"].update(bindings or {})
    return parts


def _render(directory, frames, **options):
    directory.mkdir(parents=True, exist_ok=True)
    return sr.render(directory, _source(), presentation=_parts(frames, **options),
                     icon_catalogs=(CATALOGUE,) if options.get("theme_version") == "chrona/theme/v0.15" else ())


def _frames(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives
            if item.scene_id.startswith("region-frame:")}


def _svg_elements(rendered):
    root = ET.fromstring(rendered.artifact.content)
    return {node.attrib["data-scene-id"]: node for node in root.iter()
            if "data-scene-id" in node.attrib}


def _role(fill, *, stroke=None, width=None, pattern=None):
    role = {}
    if width is not None:
        role["strokeWidth"] = "frame.width"
    if pattern:
        role["pattern"] = "frame.pattern"
    return role


def _frame_theme(*, role_fills, stroke_roles=(), pattern_role=None, extra_roles=None):
    roles = {f"region-frame-{name}": _role(fill,
             stroke=(name in stroke_roles), width=2 if name in stroke_roles else None,
             pattern=(name == pattern_role)) for name, fill in role_fills.items()}
    # The older unqualified frame role remains available for declarations without `paint`.
    roles["region-frame"] = {}
    bindings = {f"region-frame-{name}.fill": intent for name, intent in role_fills.items()}
    for name in stroke_roles:
        bindings[f"region-frame-{name}.stroke"] = "neutral"
    values = {"frame.width": {"type": "number", "value": 2}}
    if pattern_role is not None:
        values["frame.pattern"] = {"type": "pattern", "value": {"kind": "catalog", "ref": DOTS}}
        bindings[f"region-frame-{pattern_role}.stroke"] = "neutral"
    roles.update(extra_roles or {})
    return roles, bindings, values


def test_sibling_named_frames_use_their_selected_scene_roles_and_svg_inks(tmp_path):
    roles, bindings, values = _frame_theme(role_fills={"title": "negative", "review": "positive"})
    rendered = _render(tmp_path, {"title-panel": {"paint": "title"}, "review": {"paint": "review"}},
                       roles=roles, bindings=bindings, values=values)

    frames = _frames(rendered)
    assert set(frames) == set(FRAME_IDS)
    assert frames["region-frame:title-panel"].visual_role == "region-frame-title"
    assert frames["region-frame:review"].visual_role == "region-frame-review"
    assert frames["region-frame:title-panel"].paint.fill != frames["region-frame:review"].paint.fill
    svg = _svg_elements(rendered)
    for scene_id, primitive in frames.items():
        assert svg[scene_id].attrib["fill"] == primitive.paint.fill


def test_unpainted_frame_keeps_the_existing_base_role_and_svg_bytes(tmp_path):
    base_roles = {"region-frame": {}}
    base_bindings = {"region-frame.fill": "neutral"}
    baseline = _render(tmp_path / "baseline", {"review": {}}, roles=base_roles, bindings=base_bindings)
    extended_roles, extended_bindings, values = _frame_theme(role_fills={"unused": "negative"})
    extended = _render(tmp_path / "extended", {"review": {}},
                       roles=extended_roles, bindings={**extended_bindings, **base_bindings}, values=values)

    assert _frames(baseline)["region-frame:review"].visual_role == "region-frame"
    assert _frames(extended)["region-frame:review"].visual_role == "region-frame"
    assert tuple(item for item in baseline.surface.primitives if item.scene_id.startswith("region-frame:")) == \
        tuple(item for item in extended.surface.primitives if item.scene_id.startswith("region-frame:"))
    assert baseline.artifact.content == extended.artifact.content


def test_patterned_inner_frame_composes_inside_a_stroked_outer_frame_in_svg(tmp_path):
    roles, bindings, values = _frame_theme(role_fills={"outer": "surface", "inner": "surface"},
                                           stroke_roles=("outer",), pattern_role="inner")
    rendered = _render(tmp_path, {"review": {"paint": "outer"},
                                  "timeline-stack": {"paint": "inner"}},
                       roles=roles, bindings=bindings, values=values,
                       theme_version="chrona/theme/v0.15")

    outer, inner = (_frames(rendered)[scene_id] for scene_id in
                    ("region-frame:review", "region-frame:timeline-stack"))
    ox, oy, ow, oh = outer.bounds
    half_stroke = (outer.paint.stroke_width or 0) / 2
    ox, oy, ow, oh = (ox - half_stroke, oy - half_stroke,
                      ow + 2 * half_stroke, oh + 2 * half_stroke)
    ix, iy, iw, ih = inner.bounds
    assert ix >= ox and iy >= oy and ix + iw <= ox + ow and iy + ih <= oy + oh
    svg = rendered.artifact.content.decode()
    elements = _svg_elements(rendered)
    assert "<pattern " in svg
    assert "stroke" in elements[outer.scene_id].attrib
    assert elements[inner.scene_id].attrib.get("fill", "").startswith("url(#")


def test_a_missing_named_role_omits_only_its_frame_without_a_base_role(tmp_path):
    roles, bindings, values = _frame_theme(role_fills={"available": "accent"})
    roles.pop("region-frame")
    rendered = _render(tmp_path, {"title-panel": {"paint": "available"},
                                  "review": {"paint": "missing"}},
                       roles=roles, bindings=bindings, values=values)

    assert set(_frames(rendered)) == {"region-frame:title-panel"}
    assert _frames(rendered)["region-frame:title-panel"].paint.fill
    assert "region-frame:review" not in _svg_elements(rendered)


def test_named_frame_fill_is_the_ground_for_text_and_named_roles_have_precise_usage_warnings(tmp_path):
    roles, bindings, values = _frame_theme(role_fills={"panel": "text", "unused": "accent"})
    rendered = _render(tmp_path, {"title-panel": {"paint": "panel"}},
                       roles=roles, bindings=bindings, values=values)

    findings = [item for item in evaluate_scene_contrast(scene_document(rendered.scene))
                if item.ground_id == "region-frame:title-panel"]
    assert findings and any(item.primitive_id == "title" for item in findings)
    unread = [item for item in rendered.surface.diagnostics if item.startswith("W_THEME_ROLE_UNREAD:")]
    assert unread == ["W_THEME_ROLE_UNREAD:/body/roles/region-frame-unused"]


def test_malformed_frame_paint_uses_the_shared_slug_schema_error(tmp_path):
    with pytest.raises(Exception) as caught:
        _render(tmp_path, {"review": {"paint": "not_a_slug"}})

    error = caught.value
    assert getattr(error, "diagnostic_id", getattr(error, "code", None)) == "E_LAYOUT_PROFILE_SCHEMA"
    assert getattr(error, "source_ref", None)  # the schema reports a typed profile-resource failure
