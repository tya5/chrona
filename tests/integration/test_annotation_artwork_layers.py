"""Synthetic end-to-end coverage for per-layer annotation artwork (#1167).

These tests deliberately use the packaged target-parts glyphs and the ordinary synthetic review
fixture; artwork is Theme-owned and never comes from a product example or a corpus override.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
from math import cos, radians, sin
from pathlib import Path
from xml.etree import ElementTree

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from tests.integration.test_annotation_artwork import BASELINE, SCROLL_PARTS, _by_id, _render, _sub
from tests.support import annotation_artwork as aw
from tests.support import annotation_kinds as ak

ROOT = Path(__file__).resolve().parents[2]
ANNOTATION_CATALOG = ROOT / "src/chrona/resources/icons/chrona-annotation-parts-v2026-10-09.yaml"


def _failure_code(error):
    return getattr(error, "code", getattr(error, "diagnostic_id", ""))


def _failure_path(error):
    return getattr(error, "source_ref", getattr(error, "path", ""))


def _roles(parts, roles):
    theme = parts["theme"]["body"]
    for entry in roles:
        slug, fill = entry[:2]
        stroke = entry[2] if len(entry) > 2 else None
        fidelity = entry[3] if len(entry) > 3 else None
        # Each selected role has its own paint and admission facts.  Equal slugs in two layers
        # intentionally resolve to one Theme role, but remain distinct typed layer instances.
        role_name = f"annotation-artwork-{slug}"
        theme["roles"][role_name] = {}
        theme["colorBindings"][f"{role_name}.fill"] = fill
        if stroke is not None:
            theme["colorBindings"][f"{role_name}.stroke"] = stroke
        if fidelity is not None:
            value_name = f"artwork-fidelity-{slug}"
            theme["values"][value_name] = {"type": "fidelity", "value": fidelity}
            theme["roles"][role_name]["artworkFidelity"] = value_name


def _layers(parts, layers):
    assert parts["theme"]["version"] == "chrona/theme/v0.15"
    token = parts["theme"]["body"]["values"]["artwork-container"]["value"]
    token["artwork"] = deepcopy(layers)


def _layer(glyph, role, *, insets=None, unit_em=0.09):
    return {"glyph": glyph, "sliceInsets": deepcopy(insets or aw.SCROLL_INSETS), "unitEm": unit_em,
            "role": f"annotation-artwork-{role}"}


def _layer_parts(rendered, note="view-n0", index=None):
    prefix = f"annotation-artwork:{note}:layer{index}:part" if index is not None else f"annotation-artwork:{note}:layer"
    return [item for item in rendered.surface.primitives if item.scene_id.startswith(prefix)]


def _paths_by_scene_id(svg):
    root = ElementTree.fromstring(svg)
    return [element for element in root.iter() if element.attrib.get("data-scene-id", "").startswith("annotation-artwork:")]


def test_legacy_single_object_remains_byte_and_scene_identical(tmp_path):
    before = _render(_sub(tmp_path, "before"))

    def equivalent_single_object(parts):
        token = parts["theme"]["body"]["values"]["artwork-container"]["value"]
        token["artwork"] = deepcopy(token["artwork"])

    after = _render(_sub(tmp_path, "after"), mutate=equivalent_single_object)
    assert list(after.surface.primitives) == list(before.surface.primitives)
    assert after.artifact.content == before.artifact.content
    assert [item.scene_id for item in aw.artwork_parts(after)] == [
        f"annotation-artwork:view-n0:part{index}" for index in range(SCROLL_PARTS)]


def test_ordered_layers_keep_independent_roles_and_actual_svg_ink(tmp_path):
    clipping = _layer(aw.CLIPPING, "ribbon", insets=aw.CLIPPING_TOP, unit_em=0.12)
    scroll = _layer(aw.SCROLL, "frame")

    def declare(parts):
        _layers(parts, [clipping, scroll])
        _roles(parts, [("ribbon", "warning"), ("frame", "accent", "accent")])

    rendered = _render(tmp_path, mutate=declare)
    ids = _by_id(rendered)
    first = _layer_parts(rendered, index=0)
    second = _layer_parts(rendered, index=1)
    assert len(first) == 1 and len(second) == SCROLL_PARTS
    assert all(item.kind == "Symbol" and item.visual_role == "annotation-artwork-ribbon" for item in first)
    assert all(item.visual_role == "annotation-artwork-frame" for item in second)
    assert first[0].paint.fill == "#8D530F" and first[0].paint.stroke is None
    assert {item.paint.fill for item in second if item.paint.fill is not None} == {"#3986E6"}
    assert {item.paint.stroke for item in second if item.paint.stroke is not None} == {"#3986E6"}
    ordered_ids = [item.scene_id for item in rendered.surface.primitives]
    box = ordered_ids.index("annotation-box:view-n0")
    border = next((i for i, value in enumerate(ordered_ids) if value.startswith("annotation-border:view-n0")), None)
    text = ordered_ids.index("annotation-text:view-n0")
    assert box < ordered_ids.index(first[0].scene_id) < ordered_ids.index(second[0].scene_id) < text
    assert border is None or ordered_ids.index(second[-1].scene_id) < border < text

    svg_paths = [path for path in _paths_by_scene_id(rendered.artifact.content)
                 if path.attrib["data-scene-id"].startswith("annotation-artwork:view-n0:")]
    svg_ids = [path.attrib["data-scene-id"] for path in svg_paths]
    assert svg_ids == [item.scene_id for item in first + second]
    assert svg_paths[0].attrib.get("fill") == "#8D530F"
    assert all(path.attrib.get("fill") == "#3986E6" or path.attrib.get("stroke") == "#3986E6"
               for path in svg_paths[1:])


def test_list_layer_missing_role_reports_its_indexed_container_pointer(tmp_path):
    def declare(parts):
        _layers(parts, [_layer(aw.CLIPPING, "missing", insets=aw.CLIPPING_TOP, unit_em=0.12)])

    with pytest.raises(Exception) as failure:
        _render(tmp_path, mutate=declare)
    assert _failure_code(failure.value) == "E_THEME_ROLE_REQUIRED", repr(vars(failure.value))
    assert _failure_path(failure.value) == "/body/roles/annotation-note-box/annotationContainer/artwork/0"


def test_unknown_glyph_in_a_list_layer_keeps_the_indexed_asset_failure(tmp_path):
    def declare(parts):
        _layers(parts, [_layer("chrona-target-parts:not-a-glyph", "missing-glyph")])
        _roles(parts, [("missing-glyph", "warning")])

    with pytest.raises(Exception) as failure:
        _render(tmp_path, mutate=declare)
    assert _failure_code(failure.value) == "E_THEME_ASSET_REFERENCE"
    assert "/artwork/0" in _failure_path(failure.value)


def test_invalid_list_role_syntax_is_reported_at_its_indexed_member(tmp_path):
    def declare(parts):
        malformed = _layer(aw.CLIPPING, "bad")
        malformed["role"] = "annotation-artwork-not a role slug"
        _layers(parts, [malformed])

    with pytest.raises(Exception) as failure:
        _render(tmp_path, mutate=declare)
    assert _failure_code(failure.value) == "E_THEME_SCHEMA"
    assert _failure_path(failure.value) == "/body/values/artwork-container/value/artwork"


def test_same_role_layers_have_independent_baseline_fidelity_admission(tmp_path):
    def declare(parts):
        _layers(parts, [
            _layer(aw.CLIPPING, "shared", insets=aw.CLIPPING_TOP, unit_em=0.12),
            _layer(aw.SCROLL, "shared"),
        ])
        _roles(parts, [("shared", "text", "text", "decorative-optional")])

    rendered = _render(tmp_path, profile=BASELINE, mutate=declare)
    assert [item.scene_id for item in _layer_parts(rendered, index=0)] == [
        "annotation-artwork:view-n0:layer0:part0"]
    assert not _layer_parts(rendered, index=1)
    assert _by_id(rendered)["annotation-artwork:view-n0:layer0:part0"].paint.fill == "#172033"
    omissions = [item for item in rendered.info_diagnostics
                 if getattr(item, "treatment", None) == "annotation-artwork"]
    assert omissions and all(item.role == "annotation-artwork-shared" for item in omissions)
    assert not any("layer0" in item.source_ref for item in omissions)


def test_tilt_rotates_each_layer_rigidly_and_keeps_authored_order(tmp_path):
    def declare(parts):
        _layers(parts, [
            _layer(aw.CLIPPING, "ribbon", insets=aw.CLIPPING_TOP, unit_em=0.12),
            _layer(aw.SCROLL, "frame"),
        ])
        _roles(parts, [("ribbon", "warning"), ("frame", "accent", "accent")])

    tilted = _render(_sub(tmp_path, "tilted"), mutate=declare, extra={"tiltDegrees": [4]})
    flat = _render(_sub(tmp_path, "flat"), mutate=declare)
    flat_box = _by_id(flat)["annotation-box:view-n0"].bounds
    tilted_box = _by_id(tilted)["annotation-box:view-n0"].bounds
    pivot = (flat_box[0] + flat_box[2] / 2, flat_box[1] + flat_box[3] / 2)
    tilted_pivot = (tilted_box[0] + tilted_box[2] / 2, tilted_box[1] + tilted_box[3] / 2)
    translation = (tilted_pivot[0] - pivot[0], tilted_pivot[1] - pivot[1])
    cosine, sine = cos(radians(4)), sin(radians(4))

    def points(primitives):
        return [point for primitive in primitives for command in primitive.symbol.outline for point in command.points]

    for layer_index in (0, 1):
        tilted_parts = _layer_parts(tilted, index=layer_index)
        flat_parts = _layer_parts(flat, index=layer_index)
        assert len(tilted_parts) == len(flat_parts) > 0
        assert [item.scene_id for item in tilted_parts] == [item.scene_id for item in flat_parts]
        plain_points, rotated_points = points(flat_parts), points(tilted_parts)
        assert len(plain_points) == len(rotated_points)
        for (x, y), (actual_x, actual_y) in zip(plain_points, rotated_points, strict=True):
            dx, dy = x - pivot[0], y - pivot[1]
            assert actual_x == pytest.approx(pivot[0] + dx * cosine - dy * sine + translation[0], abs=1e-6)
            assert actual_y == pytest.approx(pivot[1] + dx * sine + dy * cosine + translation[1], abs=1e-6)


@pytest.mark.parametrize("worst_layer", [0, 1])
def test_text_contrast_uses_each_touched_layer_as_ink(tmp_path, worst_layer):
    # The left inset is zero so text touches both overlaid scroll frames. Swap the two inks so
    # each layer is independently selected as the worst ground; the evaluator reports only that
    # worst ground for this text primitive.
    def declare(parts):
        _layers(parts, [_layer(aw.SCROLL, "underlay"), _layer(aw.SCROLL, "frame")])
        content = parts["theme"]["body"]["values"]["artwork-container"]["value"]["contentInsetEm"]
        content["left"] = 0.0
        parts["scheme"]["body"]["colors"].update({"warning": "#172033", "accent": "#FFFFFF"})
        fills = ([ ("underlay", "warning", "warning"), ("frame", "accent", "accent") ]
                 if worst_layer == 0 else
                 [ ("underlay", "accent", "accent"), ("frame", "warning", "warning") ])
        _roles(parts, fills)

    rendered = _render(tmp_path, mutate=declare)
    findings = evaluate_scene_contrast(scene_document(rendered.scene))
    text_findings = [item for item in findings if item.primitive_id == "annotation-text:view-n0"]
    assert text_findings
    grounds = {item.ground_id for item in text_findings if item.ground_kind == "artwork-ink"}
    assert any(value.startswith(f"annotation-artwork:view-n0:layer{worst_layer}:") for value in grounds), repr(
        [(item.ground_id, item.severity, item.contrast_ratio) for item in text_findings])


def test_two_single_part_layers_emit_two_symbols_in_order_with_distinct_svg_inks(tmp_path):
    def declare(parts):
        _layers(parts, [
            _layer(aw.CLIPPING, "first", insets=aw.CLIPPING_TOP, unit_em=0.12),
            _layer(aw.CLIPPING, "second", insets=aw.CLIPPING_TOP, unit_em=0.1),
        ])
        _roles(parts, [("first", "warning"), ("second", "accent")])

    rendered = _render(tmp_path, mutate=declare)
    layer0, layer1 = _layer_parts(rendered, index=0), _layer_parts(rendered, index=1)
    assert len(layer0) == len(layer1) == 1
    assert [item.scene_id for item in layer0 + layer1] == [
        "annotation-artwork:view-n0:layer0:part0", "annotation-artwork:view-n0:layer1:part0"]
    assert [item.paint.fill for item in layer0 + layer1] == ["#8D530F", "#3986E6"]
    svg_paths = [path for path in _paths_by_scene_id(rendered.artifact.content)
                 if path.attrib["data-scene-id"].startswith("annotation-artwork:view-n0:")]
    assert [path.attrib["data-scene-id"] for path in svg_paths] == [item.scene_id for item in layer0 + layer1]
    assert [path.attrib.get("fill") for path in svg_paths] == ["#8D530F", "#3986E6"]


def test_pinned_annotation_catalogue_projects_mounting_then_rods_without_mutating_source(tmp_path):
    mounting = _layer("chrona-annotation-parts:scroll-mounting", "mounting")
    rods = _layer("chrona-annotation-parts:scroll-rods", "rods")

    def declare(parts):
        _layers(parts, [mounting, rods])
        _roles(parts, [("mounting", "warning", "warning"), ("rods", "accent")])

    before = sha256(ANNOTATION_CATALOG.read_bytes()).hexdigest()
    rendered = _render(tmp_path, mutate=declare, catalogs=(ak.TARGET_PARTS, ANNOTATION_CATALOG))
    assert sha256(ANNOTATION_CATALOG.read_bytes()).hexdigest() == before
    first, second = _layer_parts(rendered, index=0), _layer_parts(rendered, index=1)
    assert len(first) == 2 and len(second) == 4
    assert [item.scene_id for item in first] == [
        "annotation-artwork:view-n0:layer0:part0", "annotation-artwork:view-n0:layer0:part1"]
    assert [item.scene_id for item in second] == [
        f"annotation-artwork:view-n0:layer1:part{index}" for index in range(4)]
    assert [item.paint.fill for item in first if item.paint.fill is not None] == ["#8D530F"]
    assert [item.paint.stroke for item in first if item.paint.stroke is not None] == ["#8D530F"]
    assert all(item.paint.fill == "#3986E6" for item in second)
    paths = [path for path in _paths_by_scene_id(rendered.artifact.content)
             if path.attrib["data-scene-id"].startswith("annotation-artwork:view-n0:")]
    assert [path.attrib["data-scene-id"] for path in paths] == [item.scene_id for item in first + second]
    assert [path.attrib.get("stroke") for path in paths[:2]] == ["#8D530F", None]
    assert all(path.attrib.get("fill") == "#3986E6" for path in paths[2:])


def test_layering_preserves_every_non_artwork_completed_primitive(tmp_path):
    def declare(parts):
        _layers(parts, [
            _layer(aw.CLIPPING, "ribbon", insets=aw.CLIPPING_TOP, unit_em=0.12),
            _layer(aw.SCROLL, "frame"),
        ])
        _roles(parts, [("ribbon", "warning"), ("frame", "accent", "accent")])

    plain = _render(_sub(tmp_path, "plain"), artwork_declared=False)
    layered = _render(_sub(tmp_path, "layered"), mutate=declare)
    assert [item for item in layered.surface.primitives if item.purpose != "annotation-artwork"] == list(
        plain.surface.primitives)
