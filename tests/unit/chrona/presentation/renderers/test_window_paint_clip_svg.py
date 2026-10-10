from dataclasses import replace
from io import BytesIO
from xml.etree import ElementTree as ET

from PIL import Image
import pytest

from chrona.presentation.layout.surface_quality import PaintClip, StrokeClip
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import DropShadow, Glow, ScenePaint, ScenePrimitive, SceneSurface


NS = "{http://www.w3.org/2000/svg}"


def _surface(node):
    return SceneSurface("surface", (), (), (), None, (node,),
                        canvas_paint=ScenePaint("#FFFFFF", None, None, (), 1),
                        canvas_bounds=(0, 0, 100, 100))


def _node(effect=None, *, aligned=False):
    paint = ScenePaint("#FF0000", "#000000", 20, (), 1,
                       shadow=DropShadow("#000000", 15, 15, 3, 1, "required")
                       if effect == "shadow" else None,
                       glow=Glow("#00FF00", 5, 1, "required", (0, 0, 100, 100))
                       if effect == "glow" else None)
    return ScenePrimitive("mark", "Rect", "task", "object", "planned", "planned",
                          (20, 20, 60, 60), paint=paint,
                          paint_clip=PaintClip((20, 20, 60, 60)),
                          stroke_clip=StrokeClip((), False, (0, 0, 100, 100), 20)
                          if aligned else None)


@pytest.mark.parametrize("effect", [None, "shadow", "glow"])
@pytest.mark.parametrize("aligned", [False, True])
def test_supplied_plot_clip_contains_stroke_and_effects_in_svg_and_png(effect, aligned):
    node = _node(effect, aligned=aligned)
    output = render_v05_svg(_surface(node))
    tree = ET.fromstring(output)
    outer = next(child for child in tree if child.tag == NS + "g")
    assert outer.attrib["clip-path"].startswith("url(#paint-clip-")
    clip_id = outer.attrib["clip-path"][5:-1]
    clip = next(element for element in tree.iter(NS + "clipPath")
                if element.attrib["id"] == clip_id)
    assert clip.attrib["clipPathUnits"] == "userSpaceOnUse"
    assert clip[0].attrib == {"x": "20", "y": "20", "width": "60", "height": "60"}
    assert any(element.attrib.get("data-scene-id") == "mark" for element in outer.iter())
    if effect:
        assert any("filter" in element.attrib for element in outer.iter())
    if aligned:
        assert any("mask" in element.attrib for element in outer.iter())

    resvg_py = pytest.importorskip("resvg_py")
    image = Image.open(BytesIO(resvg_py.svg_to_bytes(svg_string=output, dpi=96,
                                                    skip_system_fonts=True))).convert("RGB")
    assert image.size == (100, 100)
    assert all(image.getpixel((x, y)) == (255, 255, 255)
               for y in range(100) for x in range(100)
               if not (20 <= x < 80 and 20 <= y < 80))
    assert image.getpixel((50, 50)) != (255, 255, 255)


def test_absent_clip_emits_no_clip_definition_or_outer_wrapper():
    node = replace(_node(), paint_clip=None)
    output = render_v05_svg(_surface(node))
    tree = ET.fromstring(output)
    assert "paint-clip-" not in output
    assert not any(child.tag == NS + "g" for child in tree)
    assert tree[-1].attrib["data-scene-id"] == "mark"
