"""Actual cut-contour SVG/PNG preserves the original repeat phase."""
from dataclasses import replace
from io import BytesIO
from xml.etree import ElementTree as ET

from PIL import Image
import pytest

from chrona.presentation.layout.pattern_placement import PatternTilePrimitive
from chrona.presentation.layout.surface_quality import PaintClip, PathCommand, StrokeClip
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import PatternGeometry, ScenePaint, ScenePrimitive, SceneSurface, SymbolGeometry


NS = "{http://www.w3.org/2000/svg}"
ORIGINAL = (10, 20, 80, 40)
VISIBLE = (30, 20, 60, 40)
OUTLINE = tuple(PathCommand(kind, points) for kind, points in (
    ("move", ((30, 20),)), ("line", ((90, 20),)), ("line", ((90, 60),)),
    ("line", ((30, 60),)), ("line", ((30, 50),)), ("line", ((38, 40),)),
    ("line", ((30, 30),)), ("line", ((30, 20),))))


def _node(*, cut, angle, substrate):
    region = VISIBLE if cut else ORIGINAL
    pattern = PatternGeometry(8, 8, angle, density_basis_points=1250,
                              primitives=(PatternTilePrimitive("circle", cx=2, cy=2, radius=1.5),),
                              origin=(10, 20), region_bounds=region, clip_bounds=region, corner_radius=0)
    return ScenePrimitive("mark", "Symbol" if cut else "Rect", "task", "object",
                          "progress-fill", "progress-fill", region, pattern=pattern,
                          paint=ScenePaint("#FFFF00" if substrate else None, "#000000", 1, (), 1),
                          symbol=SymbolGeometry(OUTLINE) if cut else None,
                          paint_clip=PaintClip((30, 0, 60, 100)) if cut else None)


def _surface(node):
    return SceneSurface("surface", (), (), (), None, (node,),
                        canvas_paint=ScenePaint("#FFFFFF", None, None, (), 1),
                        canvas_bounds=(0, 0, 100, 100))


@pytest.mark.parametrize("angle", [0, 45])
@pytest.mark.parametrize("substrate", [False, True])
def test_cut_symbol_svg_and_png_keep_phase_and_clear_notch(angle, substrate):
    output = render_v05_svg(_surface(_node(cut=True, angle=angle, substrate=substrate)))
    tree = ET.fromstring(output)
    pattern = next(tree.iter(NS + "pattern"))
    assert pattern.attrib["patternTransform"].startswith("translate(10 20) ")
    path = next(element for element in tree.iter(NS + "path")
                if element.attrib.get("data-scene-id") == "mark")
    assert path.attrib["fill"].startswith("url(#pattern-")
    assert path.attrib.get("stroke", "none") == "none"
    assert "L38 40" in path.attrib["d"]
    resvg = pytest.importorskip("resvg_py")
    def raster(svg):
        return Image.open(BytesIO(resvg.svg_to_bytes(svg_string=svg, dpi=96,
                                                     skip_system_fonts=True))).convert("RGB")
    image = raster(output)
    original = raster(render_v05_svg(_surface(_node(cut=False, angle=angle, substrate=substrate))))
    assert all(image.getpixel((x, y)) == original.getpixel((x, y))
               for y in range(21, 59) for x in range(40, 89))
    assert all(image.getpixel((x, y)) == (255, 255, 255)
               for y in range(100) for x in range(100)
               if not (30 <= x < 90 and 20 <= y < 60))
    assert image.getpixel((31, 40)) == (255, 255, 255)
    assert any(image.getpixel((x, y)) != (255, 255, 255)
               for y in range(21, 59) for x in range(40, 89))


def test_aligned_symbol_uses_pattern_fill_on_its_completed_contour():
    node = _node(cut=True, angle=0, substrate=False)
    node = replace(node, stroke_clip=StrokeClip(OUTLINE, False, (0, 0, 100, 100), 1))
    tree = ET.fromstring(render_v05_svg(_surface(node)))
    fill_path = next(element for element in tree.iter(NS + "path")
                     if element.attrib.get("fill", "").startswith("url(#pattern-"))
    assert "L38 40" in fill_path.attrib["d"]
    assert fill_path.attrib.get("stroke", "none") == "none"
    assert any("mask" in element.attrib for element in tree.iter(NS + "path"))
