"""Relation terminal geometry (#1042): open-triangle is a closed stroked outline, chevron an open V."""
from datetime import date
from io import BytesIO

import pytest
from PIL import Image

from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import ScenePaint, ScenePrimitive, SceneSurface, SurfaceScaleManifest

TOKEN = {"headLength": 12, "headWidth": 10, "attachmentOffset": 1}


def _outline(shape):
    return marker_geometry({"shape": shape, **TOKEN})


def test_open_triangle_closes_its_outline_and_chevron_stays_open():
    opened, hollow = _outline("chevron"), _outline("open-triangle")
    assert [c.kind for c in opened.outline] == ["move", "line", "line"]
    assert [c.kind for c in hollow.outline] == ["move", "line", "line", "line"]
    assert hollow.outline[-1] == PathCommand("line", ((0.0, 0.0),))
    assert hollow.outline[-1].points[-1] == hollow.outline[0].points[0]
    assert opened.outline != hollow.outline


def test_open_triangle_is_stroked_not_filled_and_triangle_is_filled():
    assert _outline("open-triangle").paint_mode == "stroke"
    assert _outline("chevron").paint_mode == "stroke"
    assert _outline("triangle").paint_mode == "fill"
    assert _outline("triangle").outline == _outline("open-triangle").outline


def _surface(shape):
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 40, 0, 20)
    path = ScenePrimitive("p", "Path", "a", "relation", "dependency", "dependency", (0, 0, 0, 0),
                          marker_end=_outline(shape), paint=ScenePaint(None, "#000000", 1, (), 1),
                          points=((2, 10), (28, 10)))
    return SceneSurface("s", (), (), (), scale, (path,), ScenePaint("#ffffff", None, None, (), 1),
                        canvas_bounds=(0, 0, 40, 20))


def test_rendered_svg_and_png_show_the_two_shapes_differently():
    chevron, hollow = render_v05_svg(_surface("chevron")), render_v05_svg(_surface("open-triangle"))
    assert "L0 0" not in chevron.split("<marker")[1].split("</marker>")[0]
    assert "L0 0" in hollow.split("<marker")[1].split("</marker>")[0]
    resvg = pytest.importorskip("resvg_py")
    images = [Image.open(BytesIO(bytes(resvg.svg_to_bytes(svg_string=svg, zoom=8)))).convert("L")
              for svg in (chevron, hollow)]
    assert images[0].tobytes() != images[1].tobytes()
    # the closing edge is the vertical back of the head: ink on it for the hollow triangle only
    column = 8 * 17
    ink = [sum(1 for y in range(image.height) if image.getpixel((column, y)) < 128) for image in images]
    assert ink[1] > ink[0]
