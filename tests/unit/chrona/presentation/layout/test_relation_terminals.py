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


# --- #1044: five new terminal shapes -------------------------------------------------------------------------

NEW_SHAPES = ["stealth", "rounded-triangle", "dot", "half", "double-chevron"]


def _kinds(shape):
    return [c.kind for c in _outline(shape).outline]


def _points(shape):
    return [p for c in _outline(shape).outline for p in c.points]


def test_the_five_new_shapes_are_accepted_and_the_old_ones_keep_their_geometry():
    for shape in NEW_SHAPES:
        assert marker_geometry({"shape": shape, **TOKEN}).head_length > 0
    with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
        marker_geometry({"shape": "arrow", **TOKEN})
    assert _kinds("triangle") == ["move", "line", "line", "line"] and _kinds("chevron") == ["move", "line", "line"]
    assert _kinds("circle") == ["move", "quadratic", "quadratic", "quadratic", "quadratic"]


def test_stealth_has_a_notch_between_two_barbs_and_is_filled():
    marker = _outline("stealth")
    assert marker.paint_mode == "fill"
    coords = [c.points[0] for c in marker.outline]
    assert coords[:3] == [(0.0, 0.0), (12.0, 5.0), (0.0, 10.0)]  # barb, tip, barb
    assert coords[3] == (pytest.approx(0.3 * 12), 5.0)  # the notch, on the axis, inside the head
    assert coords[-1] == coords[0]  # closed


def test_rounded_triangle_rounds_every_corner_and_stays_inside_the_head_box():
    marker = _outline("rounded-triangle")
    assert marker.paint_mode == "fill"
    assert _kinds("rounded-triangle").count("quadratic") == 3
    controls = {c.points[0] for c in marker.outline if c.kind == "quadratic"}
    assert controls == {(0.0, 0.0), (12.0, 5.0), (0.0, 10.0)}  # the triangle's corners are the control points
    assert all(-1e-9 <= x <= 12 + 1e-9 and -1e-9 <= y <= 10 + 1e-9 for x, y in _points("rounded-triangle"))
    start = marker.outline[0].points[0]
    assert start != (0.0, 0.0) and 0 < abs(start[1]) < 5  # the corner is cut, not kept


def test_dot_is_a_filled_circle_of_the_declared_diameter_and_circle_is_unchanged():
    dot, circle = _outline("dot"), _outline("circle")
    assert dot.paint_mode == "fill" and dot.head_length == dot.head_width == 10  # min(12, 10)
    assert dot.outline == circle.outline and dot.centred and circle.centred
    small = marker_geometry({"shape": "dot", "headLength": 4, "headWidth": 6, "attachmentOffset": 0})
    assert small.head_length == small.head_width == 4


def test_half_is_a_single_barb_on_the_left_of_the_direction():
    marker = _outline("half")
    assert marker.paint_mode == "fill"
    coords = [c.points[0] for c in marker.outline]
    assert coords[:3] == [(12.0, 5.0), (0.0, 0.0), (0.0, 5.0)]  # tip on the axis, one barb at the top (left of +x)
    assert all(y <= 5.0 for _, y in coords)  # nothing on the right-hand side of the line


def test_double_chevron_is_two_stroked_open_chevrons_one_behind_the_other():
    marker = _outline("double-chevron")
    assert marker.paint_mode == "stroke"
    assert _kinds("double-chevron") == ["move", "line", "line", "move", "line", "line"]  # two open V's, no closing edge
    tips = [c.points[0] for c in marker.outline if c.kind == "line" and c.points[0][1] == 5.0]
    assert len(tips) == 2 and max(x for x, _ in tips) == pytest.approx(12.0) and tips[0][0] < tips[1][0]


def _data(command):
    letter = {"move": "M", "line": "L", "quadratic": "Q"}[command.kind]
    return letter + " ".join(f"{round(x, 3) + 0:g} {round(y, 3) + 0:g}" for x, y in command.points)  # the adapter's 3 decimals


def test_every_shape_renders_in_svg_and_png_and_the_adapter_draws_exactly_the_layout_outline():
    resvg = pytest.importorskip("resvg_py")
    for shape in ["triangle", "open-triangle", "chevron", "circle", "open-circle", *NEW_SHAPES]:
        svg = render_v05_svg(_surface(shape))
        marker = svg.split("<marker")[1].split("</marker>")[0]
        assert f'd="{"".join(_data(c) for c in _outline(shape).outline)}"' in marker
        image = Image.open(BytesIO(bytes(resvg.svg_to_bytes(svg_string=svg, zoom=8)))).convert("L")
        assert min(image.getdata()) < 128  # PNG (resvg of this SVG) shows ink
    assert len({render_v05_svg(_surface(shape)) for shape in NEW_SHAPES}) == len(NEW_SHAPES)


@pytest.mark.parametrize("shape", NEW_SHAPES)
def test_the_legend_key_draws_the_same_terminal_as_the_relation(shape):
    from tests.unit.chrona.presentation.scene.test_v05_builder import _legend_surface, _theme
    theme = _theme()
    theme["body"]["values"]["dependency-marker"] = {"type": "marker", "value": {"shape": shape, **TOKEN}}
    theme["body"]["roles"]["dependency"] = {**theme["body"]["roles"]["dependency"], "marker": "dependency-marker"}
    swatch = next(node for node in _legend_surface((("dependency", "Dependency"),), theme).primitives
                  if node.scene_id == "legend-swatch:dependency")
    assert swatch.marker_end.outline == _outline(shape).outline
    assert swatch.marker_end.paint_mode == _outline(shape).paint_mode
