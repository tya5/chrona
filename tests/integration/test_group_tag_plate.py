"""A Theme may paint the per-group cell behind a vertical group tag (#1166)."""
from __future__ import annotations

from datetime import date, timedelta
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr
from tests.support import text_treatments as tt

ROOT = tt.ROOT
CATALOGUE = ROOT / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
STRIPES = "chrona-target-parts:hazard-stripes"
GROUPS = ("team-0", "team-1", "team-2")
FONT_SIZE = 22
LINE_HEIGHT = 1.15


def _source(*, cjk_labels: bool = True):
    source = sr.bunched_project(groups=len(GROUPS), per_group=6)
    labels = ("東京", "Mission Alpha", "試験A") if cjk_labels else ("Mission Alpha", "Payload Team", "Ground Ops")
    for group, label in zip(GROUPS, labels, strict=True):
        source["entities"][group]["title"] = label
    return source


def _parts(*, target: str | None = None, gap: float | None = None, pattern: bool = False,
           opacity: float | None = None, treatment: str = "fill", vertical: bool = True,
           explicit_size: str | None = None, cjk: bool = False):
    parts = sr.bundle("control-room-dark")
    parts["theme"]["version"] = "chrona/theme/v0.15"
    if vertical:
        tt.with_vertical_groups(parts, size=FONT_SIZE, family=tt.JP if cjk else None,
                                header_text="東京Alpha" if cjk else None)
    else:
        tt.with_vertical_groups(parts, mode="horizontal")

    body = parts["theme"]["body"]
    role = {"backgroundTreatment": treatment, "backgroundPaintOrder": 20, "opacity": "tag.opacity"}
    body["values"]["tag.opacity"] = {"type": "number", "value": 1 if opacity is None else opacity}
    if target is not None:
        role["tabTarget"] = target
    if not vertical and target != "tag":
        body["values"]["tag.inline"] = {"type": "number", "value": 40}
        role["tabInlineSize"] = "tag.inline"
    if gap is not None:
        body["values"]["tag.gap"] = {"type": "number", "value": gap}
        role["tabGap"] = "tag.gap"
    if explicit_size == "inline":
        body["values"]["tag.inline"] = {"type": "number", "value": 40}
        role["tabInlineSize"] = "tag.inline"
    elif explicit_size == "block":
        body["values"]["tag.block"] = {"type": "number", "value": 20}
        role["tabBlockSize"] = "tag.block"
    elif explicit_size == "position":
        role["tabPosition"] = "end"
    body["roles"]["group-tab"] = role
    body["colorBindings"]["group-tab.fill"] = "warning"
    if pattern:
        body["values"]["tag.pattern"] = {
            "type": "pattern", "value": {"kind": "catalog", "ref": STRIPES}}
        role["pattern"] = "tag.pattern"
        body["colorBindings"]["group-tab.stroke"] = "surface"
    return parts


def _render(directory, parts, *, cjk: bool = False, source=None):
    directory.mkdir(parents=True, exist_ok=True)
    return tt.render(directory, source or _source(cjk_labels=cjk), parts, cjk=cjk,
                     viewport=(1600, 900))


def _by_id(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def _texts(rendered):
    return {key: value for key, value in _by_id(rendered).items() if value.kind.value == "Text"}


def _tag_texts(rendered, group):
    return [item for key, item in sorted(_texts(rendered).items()) if key.startswith(f"group-tag:{group}:")]


def _svg(rendered):
    return ET.fromstring(rendered.artifact.content)


def test_header_target_default_is_byte_identical_and_keeps_horizontal_tabs(tmp_path):
    source = _source(cjk_labels=False)
    omitted = _render(tmp_path / "omitted", _parts(vertical=False, gap=6), cjk=False, source=source)
    explicit = _render(tmp_path / "explicit", _parts(vertical=False, target="header", gap=6), cjk=False,
                       source=source)

    assert [item.scene_id for item in omitted.surface.primitives] == [item.scene_id for item in explicit.surface.primitives]
    assert scene_document(omitted.scene)["surfaces"] == scene_document(explicit.scene)["surfaces"]
    assert omitted.artifact.content == explicit.artifact.content
    assert {key for key in _by_id(omitted) if key.startswith("group-tab:")} == {
        f"group-tab:{group}" for group in GROUPS}


@pytest.mark.skipif(not tt.cjk_available(), reason="requires the optional Noto Sans JP package")
@pytest.mark.parametrize("gap", [0, 4])
def test_tag_target_paints_one_inset_group_span_and_contains_cjk_and_rotated_latin(tmp_path, gap):
    rendered = _render(tmp_path, _parts(target="tag", gap=gap, cjk=True), cjk=True,
                       source=_source(cjk_labels=False))
    found = _by_id(rendered)
    groups = {item.group_id: item for item in rendered.surface.groups}
    assert {key for key in found if key.startswith("group-tab:")} == {
        f"group-tab:{group}" for group in GROUPS}

    parts = _parts(target="tag", gap=gap, cjk=True)
    body = parts["theme"]["body"]
    line_height_id = body["roles"]["groupHeader"]["lineHeight"]
    expected_inner_width = FONT_SIZE * body["values"][line_height_id]["value"]
    all_tag_texts = []
    for group_id in GROUPS:
        plate = found[f"group-tab:{group_id}"]
        group = groups[group_id]
        x, y, width, height = plate.bounds
        content = group.content_bounds
        assert width == pytest.approx(expected_inner_width)
        assert y == pytest.approx(float(content[1]) + gap)
        assert height == pytest.approx(float(content[3]) - 2 * gap)
        assert plate.kind.value == "Rect"

        texts = _tag_texts(rendered, group_id)
        assert texts
        all_tag_texts.extend(texts)
        for text in texts:
            tx, ty, tw, th = text.bounds
            assert tx >= x - 1e-6 and ty >= y - 1e-6
            assert tx + tw <= x + width + 1e-6 and ty + th <= y + height + 1e-6

    # The fixture deliberately includes upright CJK and a sideways Latin run.
    assert any(text.text == "東" for text in all_tag_texts)
    assert any(text.text == "京" for text in all_tag_texts)
    assert any(text.text_layout.orientation == "rotate-cw" and text.text == "Alpha" for text in all_tag_texts)

    svg = _svg(rendered)
    elements = {item.attrib.get("data-scene-id"): item for item in svg.iter()
                if item.attrib.get("data-scene-id")}
    for group_id in GROUPS:
        node = elements[f"group-tab:{group_id}"]
        assert node.attrib.get("fill")

    for group_id in GROUPS:
        findings = [item for item in evaluate_scene_contrast(scene_document(rendered.scene))
                    if item.primitive_id == f"group-tab:{group_id}"]
        assert findings and any(item.ground_id == f"group:{group_id}" for item in findings)
        tag_findings = [item for item in evaluate_scene_contrast(scene_document(rendered.scene))
                        if item.primitive_id.startswith(f"group-tag:{group_id}:")]
        assert tag_findings and all(item.ground_id == f"group-tab:{group_id}" for item in tag_findings)


def test_tag_opacity_is_serialized_on_the_actual_group_rect(tmp_path):
    rendered = _render(tmp_path, _parts(target="tag", gap=3, opacity=0.65), cjk=False,
                       source=_source(cjk_labels=False))
    found = _by_id(rendered)
    elements = {item.attrib.get("data-scene-id"): item for item in _svg(rendered).iter()
                if item.attrib.get("data-scene-id")}
    for group_id in GROUPS:
        assert found[f"group-tab:{group_id}"].paint.opacity == pytest.approx(0.65)
        assert float(elements[f"group-tab:{group_id}"].attrib["opacity"]) == pytest.approx(0.65)


def test_tag_pattern_is_painted_on_the_actual_group_rect(tmp_path):
    parts = _parts(target="tag", gap=2, pattern=True)
    rendered = sr.render(tmp_path, _source(cjk_labels=False), presentation=parts,
                         icon_catalogs=(CATALOGUE,), viewport=(1600, 900))
    found = _by_id(rendered)
    root = _svg(rendered)
    elements = {item.attrib.get("data-scene-id"): item for item in root.iter()
                if item.attrib.get("data-scene-id")}
    for group_id in GROUPS:
        assert found[f"group-tab:{group_id}"].pattern is not None
        assert elements[f"group-tab:{group_id}"].attrib.get("fill", "").startswith("url(#")
    assert len([node for node in root.iter() if node.tag.endswith("pattern")]) == len(GROUPS)


@pytest.mark.parametrize("property_name", ["inline", "block", "position"])
def test_tag_target_rejects_header_geometry_fields_even_when_not_drawn(tmp_path, property_name):
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, _parts(target="tag", treatment="none", explicit_size=property_name),
                cjk=False, source=_source(cjk_labels=False))

    assert caught.value.code == "E_THEME_TOKEN_TYPE"
    path = {"inline": "tabInlineSize", "block": "tabBlockSize", "position": "tabPosition"}[property_name]
    assert caught.value.source_ref == f"/body/roles/group-tab/{path}"


def test_horizontal_group_header_rejects_tag_target_even_when_treatment_is_none(tmp_path):
    with pytest.raises(RenderFailed) as caught:
        _render(tmp_path, _parts(target="tag", treatment="none", vertical=False),
                cjk=False, source=_source(cjk_labels=False))

    assert caught.value.code == "E_THEME_TOKEN_TYPE"
    assert caught.value.source_ref == "/body/roles/group-tab/tabTarget"
