from dataclasses import replace
from datetime import date
from io import BytesIO
from xml.etree import ElementTree as ET

import pytest
from PIL import Image

from chrona.presentation.layout.surface_quality import PathCommand, StrokeClip
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.model import (
    DropShadow, ImageFill, ImageTile, PatternGeometry, PatternStroke,
    ScenePaint, ScenePrimitive, SceneSurface, SurfaceScaleManifest, TEXT_FOLLOWS_BOX,
)


def _surface(primitive: ScenePrimitive) -> SceneSurface:
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 20, 0, 20)
    return SceneSurface("s", (), (), (), scale, (primitive,), ScenePaint("#ffffff", None, None, (), 1),
                        canvas_bounds=(0, 0, 20, 20))


def _box(*, outside: bool, **kwargs) -> ScenePrimitive:
    outline = (
        PathCommand("move", ((2, 3),)), PathCommand("line", ((10, 3),)),
        PathCommand("line", ((10, 9),)), PathCommand("line", ((2, 9),)),
        PathCommand("line", ((2, 3),)),
    )
    kind = kwargs.pop("kind", "Rect")
    symbol = kwargs.pop("symbol", None)
    return ScenePrimitive("stroke-box", kind, "a", "object", "planned", "planned", (2, 3, 8, 6),
                          symbol=symbol,
                          paint=ScenePaint("#224466", "#112233", 4, (), 0.6,
                                           shadow=DropShadow("#000000", 1, 1, 1, 0.5, "required")),
                          stroke_clip=StrokeClip(outline, outside, (0, 0, 20, 20), 4), **kwargs)


@pytest.mark.parametrize(("outside", "background", "contour"), [
    (False, "black", "white"), (True, "white", "black"),
])
def test_svg_masks_only_completed_stroke_inside_or_outside_exact_contour(outside, background, contour):
    primitive = _box(outside=outside)
    root = ET.fromstring(render_v05_svg(_surface(primitive)))
    ns = {"s": "http://www.w3.org/2000/svg"}
    mask = root.find(".//s:mask", ns)
    assert mask is not None
    assert mask.get("maskUnits") == "userSpaceOnUse"
    assert mask.get("x") == "0" and mask.get("y") == "0"
    assert mask.get("width") == "20" and mask.get("height") == "20"
    mask_rect, mask_contour = list(mask)
    assert mask_rect.get("fill") == background
    assert mask_contour.tag.endswith("rect") and mask_contour.get("fill") == contour

    group = root.find('.//s:g[@data-scene-id="stroke-box"]', ns)
    assert group is not None
    assert group.get("opacity") == "0.6"
    assert group.get("filter") is None
    inner = group.find("s:g", ns)
    assert inner is not None and inner.get("filter", "").startswith("url(#shadow-")
    fill = inner.find("s:rect[@fill='#224466']", ns)
    stroke = inner.find("s:rect[@mask]", ns)
    assert fill is not None and fill.get("stroke") is None
    assert fill.get("opacity") is None
    assert stroke is not None and stroke.get("fill") == "none"
    assert stroke.get("stroke") == "#112233" and stroke.get("stroke-width") == "4"
    assert stroke.get("opacity") is None


@pytest.mark.parametrize("outside", [False, True])
def test_svg_mask_renders_stroke_only_on_the_selected_side_of_the_contour(outside):
    resvg = pytest.importorskip("resvg_py")
    primitive = _box(outside=outside)
    primitive = replace(primitive, paint=ScenePaint("#224466", "#112233", 4, (), 1))
    svg = render_v05_svg(_surface(primitive))
    pixels = Image.open(BytesIO(bytes(resvg.svg_to_bytes(svg_string=svg, zoom=8)))).convert("RGB")
    # The contour's left edge is x=2: x=1.5 is outside, x=2.5 is inside.
    outside_pixel = pixels.getpixel((12, 48))
    inside_pixel = pixels.getpixel((20, 48))
    stroke = (17, 34, 51)
    fill = (34, 68, 102)
    if outside:
        assert outside_pixel == stroke
        assert inside_pixel == fill
    else:
        assert outside_pixel != stroke
        assert inside_pixel == stroke


def test_svg_retains_outer_host_clip_and_symbol_contour_for_masked_stroke():
    commands = (PathCommand("move", ((2, 3),)), PathCommand("line", ((10, 3),)),
                PathCommand("line", ((10, 9),)), PathCommand("line", ((2, 9),)),
                PathCommand("line", ((2, 3),)))
    from chrona.presentation.scene.model import SymbolGeometry
    primitive = _box(outside=True, kind="Symbol", symbol=SymbolGeometry(commands), clip_source_id="host")
    host = ScenePrimitive("host", "Rect", "a", "object", "planned", "planned", (0, 0, 20, 20),
                          paint=ScenePaint("#ffffff", None, None, (), 1))
    surface = replace(_surface(host), primitives=(host, primitive))
    root = ET.fromstring(render_v05_svg(surface))
    ns = {"s": "http://www.w3.org/2000/svg"}
    group = root.find('.//s:g[@data-scene-id="stroke-box"]', ns)
    assert group is not None and group.get("clip-path") == "url(#clip-host)"
    mask = root.find(".//s:mask", ns)
    assert mask is not None and list(mask)[1].get("d") == "M2 3L10 3L10 9L2 9L2 3"
    stroke = root.find(".//s:path[@mask]", ns)
    assert stroke is not None and stroke.get("d") == "M2 3L10 3L10 9L2 9L2 3"


def test_svg_stroke_clip_allows_text_follows_box():
    primitive = _box(outside=False, viewer_fit=TEXT_FOLLOWS_BOX)
    output = render_v05_svg(_surface(primitive))
    assert 'mask="url(#stroke-clip-' in output


def test_svg_stroke_clip_preserves_fill_for_closed_path_container():
    commands = (PathCommand("move", ((2, 3),)), PathCommand("line", ((10, 3),)),
                PathCommand("line", ((10, 9),)), PathCommand("line", ((2, 9),)),
                PathCommand("line", ((2, 3),)))
    primitive = ScenePrimitive("filled-path", "Path", "a", "annotation", "annotation-box", "annotation-note-box",
        (2, 3, 8, 6), path_commands=commands,
        points=((2, 3), (10, 3), (10, 9), (2, 9), (2, 3)),
        paint=ScenePaint("#224466", "#112233", 4, (), 1),
        stroke_clip=StrokeClip(commands, False, (0, 0, 20, 20), 4))
    root = ET.fromstring(render_v05_svg(_surface(primitive)))
    ns = {"s": "http://www.w3.org/2000/svg"}
    fill = root.find('.//s:path[@fill="#224466"]', ns)
    stroke = root.find('.//s:path[@mask]', ns)
    assert fill is not None and fill.get("stroke") is None
    assert stroke is not None and stroke.get("fill") == "none"


@pytest.mark.parametrize("kind", ["Symbol", "Path"])
@pytest.mark.parametrize("outside", [False, True])
def test_svg_renders_curved_compound_contour_stroke_on_correct_side_of_outer_and_hole(kind, outside):
    resvg = pytest.importorskip("resvg_py")
    commands = (
        # Clockwise curved outer contour. At (13, 4) the true quadratic lies
        # inside the straight chord from (10, 2) to (18, 10).
        PathCommand("move", ((10, 2),)),
        PathCommand("quadratic", ((18, 2), (18, 10))),
        PathCommand("quadratic", ((18, 18), (10, 18))),
        PathCommand("quadratic", ((2, 18), (2, 10))),
        PathCommand("quadratic", ((2, 2), (10, 2))),
        # Counter-clockwise rectangular hole, so nonzero fill preserves it.
        PathCommand("move", ((8, 8),)),
        PathCommand("line", ((8, 12),)),
        PathCommand("line", ((12, 12),)),
        PathCommand("line", ((12, 8),)),
        PathCommand("line", ((8, 8),)),
    )
    from chrona.presentation.scene.model import SymbolGeometry
    shared = {"paint": ScenePaint("#224466", "#112233", 4, (), 1),
              "stroke_clip": StrokeClip(commands, outside, (0, 0, 20, 20), 4)}
    if kind == "Symbol":
        primitive = ScenePrimitive("compound-symbol", kind, "a", "object", "planned", "planned", (2, 2, 16, 16),
                                   symbol=SymbolGeometry(commands), **shared)
    else:
        points = tuple(command.points[-1] for command in commands)
        primitive = ScenePrimitive("compound-path", kind, "a", "annotation", "annotation-box",
                                   "annotation-note-box", (2, 2, 16, 16), points=points,
                                   path_commands=commands, **shared)
    svg = render_v05_svg(_surface(primitive))
    assert "Q18 2 18 10" in svg
    assert "M8 8L8 12L12 12L12 8L8 8" in svg
    pixels = Image.open(BytesIO(bytes(resvg.svg_to_bytes(svg_string=svg, zoom=16)))).convert("RGB")
    stroke = (17, 34, 51)

    def near_color(point):
        px, py = (round(point[0] * 16), round(point[1] * 16))
        return any(pixels.getpixel((px + dx, py + dy)) == stroke
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1))

    # This point is 1.6 px inside the actual quadratic but outside its chord;
    # it guards against flattening the completed contour in either mask or stroke.
    assert near_color((13, 4)) is (not outside)
    # The smooth top of the outer curve has horizontal tangent at (10, 2).
    assert near_color((10, 3)) is (not outside)
    assert near_color((10, 1)) is outside
    # At the hole's left edge, inside alignment paints the solid-shape side;
    # outside alignment paints into the hole instead.
    assert near_color((7, 10)) is (not outside)
    assert near_color((9, 10)) is outside


def test_svg_keeps_pattern_and_image_fill_before_the_independently_masked_stroke():
    primitive = _box(outside=False)
    pattern = PatternGeometry(4, 4, 45, (PatternStroke((0, 0), (4, 4), 1),))
    patterned = replace(primitive, paint=ScenePaint(None, "#112233", 4, (), 1), pattern=pattern)
    pattern_root = ET.fromstring(render_v05_svg(_surface(patterned)))
    ns = {"s": "http://www.w3.org/2000/svg"}
    pattern_rect = next((item for item in pattern_root.findall(".//s:rect", ns)
                         if item.get("fill", "").startswith("url(#pattern-")), None)
    pattern_stroke = pattern_root.find('.//s:rect[@mask]', ns)
    assert pattern_rect is not None and pattern_rect.get("fill", "").startswith("url(#pattern-")
    assert pattern_stroke is not None and pattern_stroke.get("stroke") == "#112233"

    image = ImageFill("sha256:test", (2, 2), b"image-bytes",
                      (ImageTile((0, 0, 2, 2), (2, 3, 8, 6)),))
    image_primitive = replace(primitive, paint=replace(primitive.paint, image=image))
    image_svg = render_v05_svg(_surface(image_primitive))
    assert image_svg.index('data-scene-id="stroke-box-image"') < image_svg.index('mask="url(#stroke-clip-')


@pytest.mark.parametrize("renderer", [render_v05_typst, render_v05_tikz])
def test_typeset_adapters_refuse_stroke_clip_until_supported(renderer):
    with pytest.raises(ValueError, match="E_VISUAL_CAPABILITY_UNSUPPORTED"):
        renderer(_surface(_box(outside=False)))
