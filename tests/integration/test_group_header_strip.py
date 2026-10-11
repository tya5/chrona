"""Final group-header strips are an opt-in, independently painted ground (#1367)."""
from __future__ import annotations

from datetime import date
import xml.etree.ElementTree as ET

import pytest

from chrona.presentation.scene.serialization import scene_document, serialize_scene
from chrona.presentation.model.closure import ClosureError
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


def _source():
    source = sr.bunched_project(groups=2, per_group=2)
    for index in range(2):
        source["entities"][f"team-{index}"]["title"] = f"Group {index}"
    return source


def _parts(*, strip: bool = True, treatment: str = "fill", extent: str = "both",
           strip_order: int = 10, group_order: int = 9, header_order: int = 11,
           groups: str = "all", tint=None, pattern: bool = False,
           header_treatment: str = "fill"):
    parts = sr.bundle("control-room-dark")
    body = parts["theme"]["body"]
    body["roles"]["group-band"]["backgroundPaintOrder"] = group_order
    body["roles"]["group-header-band"]["backgroundPaintOrder"] = header_order
    body["roles"]["group-header-band"]["backgroundTreatment"] = header_treatment
    if strip:
        parts["layout"]["reviewSurface"]["backgroundExtents"]["groupHeaderStrip"] = extent
        body["values"]["header-strip.opacity"] = {"type": "number", "value": 1}
        role = {"backgroundTreatment": treatment, "backgroundPaintOrder": strip_order}
        role["opacity"] = "header-strip.opacity"
        if pattern:
            parts["theme"]["version"] = "chrona/theme/v0.15"
            body["values"]["header-strip.pattern"] = {
                "type": "pattern", "value": {"kind": "catalog", "ref": "chrona-target-parts:hazard-stripes"}}
            role["pattern"] = "header-strip.pattern"
            body["colorBindings"]["group-header-strip.stroke"] = "warning"
            body["colorBindings"]["group-header-strip.fill"] = "surface"
        else:
            body["colorBindings"]["group-header-strip.fill"] = "warning"
        body["roles"]["group-header-strip"] = role
    parts["view"]["body"]["backgroundDecoration"] = {"rows": "none", "groups": groups}
    if tint is not None:
        parts["view"]["body"]["grouping"]["tint"] = tint
    return parts


def _render(tmp_path, parts, *, source=None, name="render", icon_catalogs=()):
    output = tmp_path / name
    output.mkdir(parents=True, exist_ok=True)
    return sr.render(output, source or _source(), presentation=parts, icon_catalogs=icon_catalogs)


def _by_id(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def _strips(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives
            if item.scene_id.startswith("group-header-strip:")}


def _svg_element(rendered, scene_id):
    root = ET.fromstring(rendered.artifact.content)
    return next(node for node in root.iter() if node.attrib.get("data-scene-id") == scene_id)


def _assert_svg_bounds(rendered, scene_id):
    element = _svg_element(rendered, scene_id)
    scene = _by_id(rendered)[scene_id]
    for attribute, index in (("x", 0), ("y", 1), ("width", 2), ("height", 3)):
        assert float(element.attrib[attribute]) == pytest.approx(scene.bounds[index], abs=0.001)


def _install_pre_strip_behavior(monkeypatch):
    """Replay the pre-strip composition/registry while retaining current header geometry."""
    import chrona.presentation.layout.surface_composer as composer
    import chrona.presentation.scene.v05_builder as builder
    from chrona.presentation.model.semantic_registry import ContrastClass

    monkeypatch.setattr(composer, "compose_group_header_strips", lambda **_: ())
    current = builder.contrast_bindings

    def without_strip(contrast_class):
        bindings = current(contrast_class)
        if contrast_class is ContrastClass.DECORATION:
            return tuple(item for item in bindings if item.scene_role != "group-header-strip")
        return bindings

    monkeypatch.setattr(builder, "contrast_bindings", without_strip)


@pytest.mark.parametrize("extent", ["both", "table", "timeline"])
def test_strip_follows_each_final_header_block_and_declared_extent_in_scene_and_svg(tmp_path, extent):
    rendered = _render(tmp_path, _parts(extent=extent))
    strips = _strips(rendered)
    groups = {group.group_id: group for group in rendered.surface.groups}
    slots = {slot.slot_id: slot for slot in rendered.surface.slots}
    assert set(strips) == {f"group-header-strip:{group_id}" for group_id in groups}

    if extent == "table":
        left, right = slots["table"].bounds[0], slots["table"].bounds[0] + slots["table"].bounds[2]
    elif extent == "timeline":
        left, right = slots["timeline"].bounds[0], slots["timeline"].bounds[0] + slots["timeline"].bounds[2]
    else:
        left = slots["table"].bounds[0]
        right = slots["timeline"].bounds[0] + slots["timeline"].bounds[2]
    for group_id, group in groups.items():
        strip = strips[f"group-header-strip:{group_id}"]
        assert strip.bounds == pytest.approx((left, group.header_bounds[1], right - left, group.header_bounds[3]))
        assert strip.visual_role == "group-header-strip"
        _assert_svg_bounds(rendered, strip.scene_id)
    assert not any(item.scene_id.startswith("group-header-strip:row") for item in rendered.surface.primitives)


def test_strip_remains_full_width_around_a_text_sized_caption_band(tmp_path):
    parts = _parts(groups="none")
    parts["layout"]["reviewSurface"]["backgroundExtents"]["groupHeaderBand"] = "text"
    rendered = _render(tmp_path, parts)
    items = _by_id(rendered)
    caption_band = items["group-header-band:team-0"]
    strip = items["group-header-strip:team-0"]
    caption = items["group-header:team-0"]
    table = next(item.bounds for item in rendered.surface.slots if item.slot_id == "table")
    timeline = next(item.bounds for item in rendered.surface.slots if item.slot_id == "timeline")
    assert caption_band.bounds[2] == pytest.approx(caption.bounds[0] + caption.bounds[2] - caption_band.bounds[0])
    assert strip.bounds[0] == pytest.approx(table[0])
    assert strip.bounds[0] + strip.bounds[2] == pytest.approx(timeline[0] + timeline[2])
    assert strip.bounds[2] > caption_band.bounds[2]
    assert strip.bounds[1] == pytest.approx(caption_band.bounds[1])
    assert strip.bounds[3] == pytest.approx(caption_band.bounds[3])
    assert strip.paint_order < caption_band.paint_order < caption.paint_order

    root = ET.fromstring(rendered.artifact.content)
    order = [node.attrib.get("data-scene-id") for node in root.iter() if node.attrib.get("data-scene-id")]
    assert order.index(strip.scene_id) < order.index(caption_band.scene_id) < order.index(caption.scene_id)
    _assert_svg_bounds(rendered, strip.scene_id)
    _assert_svg_bounds(rendered, caption_band.scene_id)


def test_strip_uses_final_folded_header_height_without_changing_caption_or_marks(tmp_path):
    source = _source()
    source["objects"].update({
        f"point-{index}": sr.point(f"point-{index}", date(2026, 2, 2 + index), owner="team-0")
        for index in range(4)
    })

    def folded(strip):
        parts = _parts(strip=strip)
        body = parts["theme"]["body"]
        body["values"].update({"fold-size": {"type": "number", "value": 20},
                               "fold-leading": {"type": "number", "value": 1.6}})
        body["roles"]["groupHeader"].update({"fontSize": "fold-size", "lineHeight": "fold-leading"})
        parts["view"]["body"]["rows"] = {"mode": "automatic", "points": "group-header"}
        return parts

    with_strip = _render(tmp_path, folded(True), source=source, name="folded-strip")
    without_strip = _render(tmp_path, folded(False), source=source, name="folded-no-strip")
    strip = _strips(with_strip)["group-header-strip:team-0"]
    header_group = next(item for item in with_strip.surface.groups if item.group_id == "team-0")
    assert strip.bounds[1] == pytest.approx(header_group.header_bounds[1])
    assert strip.bounds[3] == pytest.approx(header_group.header_bounds[3])
    assert strip.bounds[3] > 20 * 1.6
    assert with_strip.surface.groups == without_strip.surface.groups
    captions = lambda rendered: [item for item in rendered.surface.primitives
                                 if item.scene_id.startswith("group-header:")]
    assert captions(with_strip) == captions(without_strip)
    marks = lambda rendered: [item for item in rendered.surface.primitives
                              if item.kind.value == "Symbol" and item.source_ref.startswith("point-")]
    assert marks(with_strip) == marks(without_strip)
    _assert_svg_bounds(with_strip, strip.scene_id)


def test_strip_selection_is_independent_of_caption_band_selection(tmp_path):
    rendered = _render(tmp_path, _parts(groups="alternate"))
    baseline = _render(tmp_path, _parts(strip=False, groups="alternate"), name="without-strip")
    ids = set(_by_id(rendered))
    assert {value for value in ids if value.startswith("group-header-strip:")} == {
        "group-header-strip:team-0", "group-header-strip:team-1"}
    caption_band_ids = lambda values: {value for value in values
                                      if value.startswith(("group:", "group-header-band:"))}
    assert caption_band_ids(ids) == caption_band_ids(set(_by_id(baseline)))


def test_strip_uses_its_own_role_paint_not_the_group_tint(tmp_path):
    plain = _render(tmp_path, _parts(), name="plain")
    tinted = _render(tmp_path, _parts(tint={"scale": "series"}), name="tinted")
    assert {key: item.paint.fill for key, item in _strips(plain).items()} == {
        key: item.paint.fill for key, item in _strips(tinted).items()}
    assert _by_id(plain)["group:team-0"].paint.fill != _by_id(tinted)["group:team-0"].paint.fill


@pytest.mark.parametrize(("groups", "group_order", "header_order", "strip_order"), [
    ("all", 10, 11, 10),       # strip must follow an emitted group band
    ("none", 9, 10, 10),       # strip must follow an emitted header band
])
def test_emitted_strip_order_conflicts_name_role_property_pointer(
        tmp_path, groups, group_order, header_order, strip_order):
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, _parts(groups=groups, group_order=group_order,
                                header_order=header_order, strip_order=strip_order,
                                header_treatment="fill"))
    assert (raised.value.code, raised.value.source_ref) == (
        "E_LAYOUT_GROUP_HEADER_STRIP_ORDER", "/body/roles/group-header-strip/backgroundPaintOrder")
    assert "group-header-strip" in raised.value.message and "order=" in raised.value.message


@pytest.mark.parametrize("strip_order", [300, 301])
def test_strip_must_paint_before_header_text_even_without_caption_band(tmp_path, strip_order):
    parts = _parts(groups="none", strip_order=strip_order, header_treatment="none")
    with pytest.raises(RenderFailed) as raised:
        _render(tmp_path, parts)
    assert (raised.value.code, raised.value.source_ref) == (
        "E_LAYOUT_GROUP_HEADER_STRIP_ORDER", "/body/roles/group-header-strip/backgroundPaintOrder")
    assert "group-header:team-0" in raised.value.message and "order=" in raised.value.message


def test_strip_order_200_is_valid_before_header_text_without_caption_band(tmp_path):
    parts = _parts(groups="none", strip_order=200, header_treatment="none")
    rendered = _render(tmp_path, parts)
    text = _by_id(rendered)["group-header:team-0"]
    strip = _strips(rendered)["group-header-strip:team-0"]
    assert (strip.paint_order, text.paint_order) == (200, 300)


@pytest.mark.parametrize(("caption_extent", "folded"), [
    ("both", False), ("text", False), ("both", True), ("text", True),
])
def test_absent_strip_role_replays_pre_strip_scene_and_svg_bytes(tmp_path, monkeypatch, caption_extent, folded):
    source = _source()
    if folded:
        source["objects"].update({
            f"point-{index}": sr.point(f"point-{index}", date(2026, 2, 2 + index), owner="team-0")
            for index in range(4)
        })

    def parts():
        value = _parts(strip=False)
        if caption_extent == "text":
            value["view"]["body"]["backgroundDecoration"]["groups"] = "none"
        value["layout"]["reviewSurface"]["backgroundExtents"]["groupHeaderBand"] = caption_extent
        if folded:
            value["theme"]["body"]["values"].update({
                "fold-size": {"type": "number", "value": 20},
                "fold-leading": {"type": "number", "value": 1.6},
            })
            value["theme"]["body"]["roles"]["groupHeader"].update(
                {"fontSize": "fold-size", "lineHeight": "fold-leading"})
            value["view"]["body"]["rows"] = {"mode": "automatic", "points": "group-header"}
        return value

    current = _render(tmp_path, parts(), source=source, name="current")
    _install_pre_strip_behavior(monkeypatch)
    legacy = _render(tmp_path, parts(), source=source, name="legacy")
    assert scene_document(current.scene) == scene_document(legacy.scene)
    assert serialize_scene(current.scene) == serialize_scene(legacy.scene)
    assert current.artifact.content == legacy.artifact.content


def test_no_groups_means_no_header_strips(tmp_path):
    parts = _parts()
    parts["view"]["body"]["grouping"] = {"by": "none", "missing": "ungrouped"}
    rendered = _render(tmp_path, parts)
    assert _strips(rendered) == {}


def test_role_without_background_treatment_and_order_is_inactive(tmp_path):
    baseline = _render(tmp_path, _parts(strip=False), name="baseline")
    inactive = _parts(strip=False)
    inactive["theme"]["body"]["values"]["inactive-strip.opacity"] = {"type": "number", "value": 1}
    inactive["theme"]["body"]["roles"]["group-header-strip"] = {"opacity": "inactive-strip.opacity"}
    rendered = _render(tmp_path, inactive, name="inactive")
    assert _strips(rendered) == {}
    assert rendered.surface.primitives == baseline.surface.primitives
    assert rendered.artifact.content == baseline.artifact.content


def test_omitted_strip_extent_defaults_to_both_byte_for_byte(tmp_path):
    explicit = _parts(extent="both")
    omitted = _parts(extent="both")
    omitted["layout"]["reviewSurface"]["backgroundExtents"].pop("groupHeaderStrip")
    left = _render(tmp_path, explicit, name="explicit-both")
    right = _render(tmp_path, omitted, name="omitted-default")
    assert left.surface.primitives == right.surface.primitives
    assert left.artifact.content == right.artifact.content


def test_strip_extent_does_not_accept_caption_only_text_value(tmp_path):
    with pytest.raises(ClosureError) as raised:
        _render(tmp_path, _parts(extent="text"))
    error = raised.value
    assert error.diagnostic_id == "E_LAYOUT_PROFILE_SCHEMA"
    assert "groupHeaderStrip" in error.source_ref


def test_explicit_none_strip_is_disclosed_but_draws_no_strip(tmp_path):
    absent = _render(tmp_path, _parts(strip=False), name="absent")
    explicit_none = _render(tmp_path, _parts(treatment="none"), name="none")
    assert explicit_none.artifact.content == absent.artifact.content
    assert not _strips(explicit_none)
    dispositions = {item.visual_role: item.disposition for item in explicit_none.surface.decoration_dispositions}
    assert dispositions.get("group-header-strip") == "absent"


def test_patterned_strip_uses_its_own_clip_and_emits_svg_pattern(tmp_path):
    from pathlib import Path

    catalogue = Path(__file__).resolve().parents[2] / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
    rendered = _render(tmp_path, _parts(pattern=True), icon_catalogs=(catalogue,))
    strips = _strips(rendered)
    assert strips
    assert all(item.pattern is not None and item.pattern.primitives for item in strips.values())
    assert all(tuple(float(value) for value in item.pattern.clip_bounds) == pytest.approx(item.bounds)
               for item in strips.values())
    root = ET.fromstring(rendered.artifact.content)
    assert any(node.tag.rsplit("}", 1)[-1] == "pattern" for node in root.iter())
    for item in strips.values():
        _assert_svg_bounds(rendered, item.scene_id)
