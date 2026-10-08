"""Completed canvas-overlay paint remains closed Scene data through SVG."""

from __future__ import annotations

from datetime import date
from io import BytesIO
import json
from xml.etree import ElementTree

from PIL import Image
import pytest

from chrona.presentation.layout.pattern_placement import PatternPathCommand, PatternTilePrimitive
from chrona.presentation.scene.model import (
    ContentFamilyCounts, InspectionScene, LinearGradient, PatternGeometry, RadialGradient,
    RadialGradientStop, SceneManifest, ScenePaint, ScenePrimitive, SceneProvenance,
    SceneSlot, SceneSurface,
)
from chrona.presentation.scene.serialization import (
    SceneSerializationError, scene_document, serialize_scene, validate_scene_document,
)
from chrona.presentation.renderers.v05_svg import render_v05_svg


def _scene(*primitives: ScenePrimitive) -> InspectionScene:
    slot = SceneSlot("canvas", "canvas", None, (0, 0, 20, 12))
    surface = SceneSurface(
        "surface", (slot,), (), (), None, tuple(primitives),
        canvas_paint=ScenePaint("#ffffff", None, None, (), 1), canvas_bounds=(0, 0, 20, 12),
    )
    manifest = SceneManifest("chrona/scene-manifest/v0.1", "test", (20, 12), (), (),
                             ContentFamilyCounts(0, 0, 0, 0, 0), ())
    return InspectionScene(SceneProvenance("draft", "test", ()), (20, 12), (), (surface,), manifest, ())


def _radial() -> RadialGradient:
    return RadialGradient(
        (10.5, 6.5), (8, 4),
        (RadialGradientStop(0, "#101820", 0), RadialGradientStop(0.4, "#101820", 0),
         RadialGradientStop(1, "#101820", 1)),
        "required",
    )


def _radial_primitive(*, opacity: float = 0.65) -> ScenePrimitive:
    return ScenePrimitive(
        "canvas-overlay-gradient", "Rect", "canvas-overlay-gradient", "canvas", "canvas-overlay-gradient",
        "canvas-overlay-gradient", (0, 0, 20, 12), slot_id="canvas",
        paint=ScenePaint("#101820", None, None, (), opacity, radial_gradient=_radial()),
    )


def test_radial_gradient_is_optional_scene_v07_paint_data():
    scene = _scene(_radial_primitive())
    document = scene_document(scene)
    assert document["version"] == "chrona/scene/v0.7"
    radial = document["surfaces"][0]["primitives"][0]["paint"]["radialGradient"]
    assert radial == {
        "center": [10.5, 6.5], "radii": [8, 4], "fidelity": "required",
        "stops": [
            {"offset": 0, "color": "#101820", "opacity": 0},
            {"offset": 0.4, "color": "#101820", "opacity": 0},
            {"offset": 1, "color": "#101820", "opacity": 1},
        ],
    }
    validate_scene_document(document)
    assert json.loads(serialize_scene(scene)) == document


def test_absent_radial_field_keeps_scene_v06_and_legacy_svg_bytes():
    primitive = ScenePrimitive("content", "Rect", "content", "object", "content", "content",
                               (2, 2, 5, 4), slot_id="canvas",
                               paint=ScenePaint("#445566", None, None, (), 1))
    scene = _scene(primitive)
    assert scene_document(scene)["version"] == "chrona/scene/v0.6"
    assert "radialGradient" not in scene_document(scene)["surfaces"][0]["primitives"][0]["paint"]
    assert b"radialGradient" not in serialize_scene(scene)
    assert "<radialGradient" not in render_v05_svg(scene.surfaces[0])


def test_radial_svg_uses_completed_ellipse_and_noninteractive_canvas_clip():
    surface = _scene(_radial_primitive()).surfaces[0]
    output = render_v05_svg(surface)
    assert 'gradientUnits="userSpaceOnUse" cx="0" cy="0" r="1" gradientTransform="translate(10.5 6.5) scale(8 4)"' in output
    assert '<clipPath id="canvas-overlay-clip-' in output
    assert '<rect data-scene-id="canvas-overlay-gradient"' in output
    assert 'pointer-events="none" clip-path="url(#canvas-overlay-clip-' in output
    assert 'fill="url(#radial-gradient-' in output
    resvg_py = pytest.importorskip("resvg_py")
    rendered = resvg_py.svg_to_bytes(svg_string=output, dpi=96, skip_system_fonts=True)
    image = Image.open(BytesIO(rendered)).convert("RGB")
    assert image.getpixel((10, 6)) == (255, 255, 255)
    assert image.getpixel((14, 6)) == image.getpixel((10, 8))
    assert image.getpixel((1, 6)) != (255, 255, 255)


def test_ink_only_catalog_pattern_has_no_substrate_and_paints_all_shapes_with_ink_once():
    pattern = PatternGeometry(
        8, 4, 0, density_basis_points=1000,
        primitives=(
            PatternTilePrimitive("rect", x=0, y=0, inline_size=2, block_size=4),
            PatternTilePrimitive("path", paint="fill", commands=(
                PatternPathCommand("move", ((3, 0),)), PatternPathCommand("line", ((5, 0),)),
                PatternPathCommand("line", ((5, 2),)), PatternPathCommand("close", ()),
            )),
            PatternTilePrimitive("path", paint="stroke", commands=(
                PatternPathCommand("move", ((6, 0),)), PatternPathCommand("line", ((8, 4),)),
            ), stroke_width=0.4, line_cap="round", line_join="round"),
        ),
        origin=(0, 0), region_bounds=(0, 0, 20, 12), clip_bounds=(0, 0, 20, 12), corner_radius=0,
    )
    overlay = ScenePrimitive(
        "canvas-overlay", "Rect", "canvas-overlay", "canvas", "canvas-overlay", "canvas-overlay",
        (0, 0, 20, 12), slot_id="canvas", pattern=pattern,
        paint=ScenePaint(None, "#D0A080", None, (), 0.35),
    )
    output = render_v05_svg(_scene(overlay).surfaces[0])
    root = ElementTree.fromstring(output)
    ns = {"s": "http://www.w3.org/2000/svg"}
    tile = root.find(".//s:pattern", ns)
    assert tile is not None
    assert tile.get("patternTransform") == "translate(0 0) rotate(0 4 2)"
    rect_shapes = tile.findall("s:rect", ns)
    assert len(rect_shapes) == 1 and rect_shapes[0].get("width") == "2"
    path_shapes = tile.findall("s:path", ns)
    assert len(path_shapes) == 2
    assert all(shape.get("fill") == "#D0A080" or shape.get("stroke") == "#D0A080"
               for shape in path_shapes)
    host = next(item for item in root.iter() if item.get("data-scene-id") == "canvas-overlay")
    assert host.get("opacity") == "0.35"
    assert host.get("pointer-events") == "none"
    assert output.count('opacity="0.35"') == 1


def test_radial_paint_rejects_competing_linear_gradient_and_pattern():
    base = _radial_primitive()
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        ScenePrimitive(**{
            **base.__dict__,
            "paint": ScenePaint("#101820", None, None, (), 1,
                                LinearGradient((0, 0), (20, 0), ((0, "#000"), (1, "#fff")), "required"),
                                radial_gradient=_radial()),
        })
    pattern = PatternGeometry(4, 4, 0, density_basis_points=1000,
                              primitives=(PatternTilePrimitive("rect", x=0, y=0,
                                                               inline_size=2, block_size=4),),
                              origin=(0, 0), region_bounds=(0, 0, 20, 12),
                              clip_bounds=(0, 0, 20, 12), corner_radius=0)
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        ScenePrimitive(**{**base.__dict__, "pattern": pattern})
    document = scene_document(_scene(base))
    radial_paint = document["surfaces"][0]["primitives"][0]["paint"]
    radial_paint["gradient"] = {"start": [0, 0], "end": [20, 0],
                                 "stops": [{"offset": 0, "color": "#000"},
                                           {"offset": 1, "color": "#fff"}], "fidelity": "required"}
    with pytest.raises(SceneSerializationError, match="E_SCENE_SERIALIZATION"):
        validate_scene_document(document)


def test_radial_gradient_is_forbidden_on_background_canvas_paint():
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        SceneSurface("surface", (), (), (), None, (),
                     canvas_paint=ScenePaint("#101820", None, None, (), 1,
                                             radial_gradient=_radial()),
                     canvas_bounds=(0, 0, 20, 12))
    document = scene_document(_scene(_radial_primitive()))
    document["surfaces"][0]["canvasPaint"]["radialGradient"] = {
        "center": [10.5, 6.5], "radii": [8, 4],
        "stops": [{"offset": 0, "color": "#101820", "opacity": 0},
                  {"offset": 1, "color": "#101820", "opacity": 1}],
        "fidelity": "required",
    }
    with pytest.raises(SceneSerializationError, match="E_SCENE_SERIALIZATION"):
        validate_scene_document(document)


def test_radial_gradient_model_rejects_unbounded_or_noncontract_stop_data():
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        RadialGradient((0, 0), (1, 1),
                       (RadialGradientStop(0, "#000000", 0),
                        RadialGradientStop(0.5, "#ffffff", 0),
                        RadialGradientStop(1, "#000000", 1)), "required")
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        RadialGradient((0, 0), (1, 0),
                       (RadialGradientStop(0, "#000000", 0),
                        RadialGradientStop(1, "#000000", 1)), "required")
