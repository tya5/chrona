"""Physical terminal reference completion and adapter projection (#1148)."""
from dataclasses import replace
from datetime import date
from io import BytesIO
from math import hypot
from xml.etree import ElementTree as ET

import pytest
from PIL import Image

from chrona.presentation.layout.relation_fan_in import terminal_style
from chrona.presentation.layout.relation_terminals import (
    SHAPES, _outline_tip, centred_on_route, complete_centred_terminals, marker_geometry, terminal_length, terminal_run,
)
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import ScenePaint, ScenePrimitive, SceneSurface, SurfaceScaleManifest
from chrona.presentation.scene.serialization import _marker


def token(shape, **extra):
    return {"shape": shape, "headLength": 12, "headWidth": 10, **extra}


@pytest.mark.parametrize("shape", sorted(SHAPES - {"none", "circle", "open-circle", "dot"}))
@pytest.mark.parametrize("stroke", [0.5, 1, 3])
def test_derived_reference_puts_visible_tip_at_port(shape, stroke):
    marker = marker_geometry(token(shape), stroke_width=stroke)
    tip = _outline_tip(marker.outline)
    if marker.paint_mode == "stroke":
        run = 7.2 if shape == "double-chevron" else 12
        ratio = hypot(run, 5) / 5
        tip += stroke / 2 * ratio
    reference = marker.head_length - marker.attachment_offset
    assert tip - reference == pytest.approx(0)
    assert marker.physical_units
    assert marker.stroke_width == (stroke if marker.paint_mode == "stroke" else None)


def test_beveled_acute_head_uses_the_visible_join_not_an_unbounded_miter():
    marker = marker_geometry({"shape": "chevron", "headLength": 40, "headWidth": 4}, stroke_width=2)
    ratio = hypot(40, 2) / 2
    assert marker.head_length - marker.attachment_offset == pytest.approx(40 + 1 / ratio)


def test_rounded_head_uses_quadratic_extremum_not_its_control_point():
    marker = marker_geometry(token("rounded-triangle"))
    assert 0 < marker.attachment_offset < 12
    assert _outline_tip(marker.outline) < max(point[0] for command in marker.outline for point in command.points)


@pytest.mark.parametrize("shape", ["circle", "open-circle", "dot"])
def test_derived_round_heads_stay_centred_on_both_original_ports(shape):
    marker = marker_geometry(token(shape), stroke_width=2)
    start, end = centred_on_route(marker, "source"), centred_on_route(marker, "target")
    points, start, end = complete_centred_terminals(((20, 10), (50, 10)), start, end, 2)
    assert points[0][0] + start.attachment_offset - start.head_length / 2 == 20
    assert points[-1][0] + end.attachment_offset - end.head_length / 2 == 50


def surface(marker):
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 60, 0, 30)
    path = ScenePrimitive("p", "Path", "a", "relation", "dependency", "dependency", (0, 0, 0, 0),
                          marker_end=marker, paint=ScenePaint(None, "#000000", 3, (), 1),
                          points=((10, 15), (50, 15)))
    return SceneSurface("s", (), (), (), scale, (path,), ScenePaint("#ffffff", None, None, (), 1),
                        canvas_bounds=(0, 0, 60, 30))


def test_svg_projects_completed_units_reference_and_stroke_without_derivation():
    marker = marker_geometry(token("chevron"), stroke_width=3)
    root = ET.fromstring(render_v05_svg(surface(marker)))
    element = root.find(".//{http://www.w3.org/2000/svg}marker")
    assert element.get("markerUnits") == "userSpaceOnUse"
    assert element.get("overflow") == "visible"
    assert float(element.get("refX")) == pytest.approx(12 - marker.attachment_offset, abs=1e-6)
    stroke = element.find("{http://www.w3.org/2000/svg}path")
    assert stroke.get("stroke-width") == "3"
    assert stroke.get("stroke-linejoin") == "miter"
    assert stroke.get("stroke-miterlimit") == "4"
    assert _marker(marker)["units"] == "userSpaceOnUse"
    assert _marker(marker)["strokeWidth"] == 3


def test_explicit_attachment_keeps_legacy_serialization_and_marker_units():
    legacy = marker_geometry(token("chevron", attachmentOffset=1), stroke_width=3)
    assert not legacy.physical_units and legacy.stroke_width is None
    assert "units" not in _marker(legacy) and "strokeWidth" not in _marker(legacy)
    svg = render_v05_svg(surface(legacy))
    assert "markerUnits" not in svg and "overflow" not in svg
    assert 'refX="11"' in svg
    assert repr(legacy) == repr(replace(legacy, physical_units=True, stroke_width=3))
    assert render_v05_svg(surface(replace(legacy, physical_units=True, stroke_width=3))) != svg


def test_different_physical_strokes_are_not_shared_as_one_fan_in_terminal():
    first = marker_geometry(token("open-circle"), stroke_width=1)
    second = marker_geometry(token("open-circle"), stroke_width=3)
    assert terminal_style(first) != terminal_style(second)


def test_equal_legacy_repr_physical_markers_have_stable_distinct_definitions():
    first = marker_geometry(token("open-circle"), stroke_width=1)
    second = marker_geometry(token("open-circle"), stroke_width=3)
    assert repr(first) == repr(second) and first != second
    original = surface(first)
    other = replace(original.primitives[0], scene_id="q", marker_end=second)
    forward = render_v05_svg(replace(original, primitives=(*original.primitives, other)))
    backward = render_v05_svg(replace(original, primitives=(other, *original.primitives)))
    assert forward.split("</defs>")[0] == backward.split("</defs>")[0]
    definitions = ET.fromstring(forward).findall(".//{http://www.w3.org/2000/svg}marker")
    assert len({marker.get("id") for marker in definitions}) == 2


@pytest.mark.parametrize("shape", ["triangle", "rounded-triangle", "chevron", "open-triangle", "double-chevron"])
@pytest.mark.parametrize("width", [0.5, 3])
@pytest.mark.parametrize("head_width", [4, 10])
def test_rendered_head_never_protrudes_past_the_actual_port(shape, width, head_width):
    resvg = pytest.importorskip("resvg_py")
    marker = marker_geometry({**token(shape), "headWidth": head_width}, stroke_width=width)
    document = ET.fromstring(render_v05_svg(surface(marker)))
    # Hide only the relation body, retaining the adapter's marker definition
    # and reference unchanged, so the line cannot conceal a detached tip.
    for path in document.findall("{http://www.w3.org/2000/svg}path"):
        path.set("stroke", "none")
    svg = ET.tostring(document, encoding="unicode")
    zoom = 16
    pixels = Image.open(BytesIO(bytes(resvg.svg_to_bytes(svg_string=svg, zoom=zoom)))).convert("RGB")
    # Inspect real adapter output, not only the reference arithmetic.
    occupied = [x for x in range(48 * zoom, 53 * zoom) for y in range(10 * zoom, 20 * zoom)
                if max(pixels.getpixel((x, y))) < 128]
    assert occupied
    assert 49.6 <= max(occupied) / zoom < 50.1


@pytest.mark.parametrize("shape", ["chevron", "open-triangle", "double-chevron"])
def test_routing_reserves_completed_painted_reach_not_nominal_head_length(shape):
    marker = marker_geometry(token(shape), stroke_width=3)
    ratio = hypot(7.2 if shape == "double-chevron" else 12, 5) / 5
    rear_overhang = 1.5 if shape == "open-triangle" else 1.5 / ratio
    expected = marker.head_length - marker.attachment_offset + rear_overhang
    assert expected > marker.head_length
    assert terminal_length(marker) == pytest.approx(expected)
    assert terminal_run(marker) == pytest.approx(expected)
    legacy = marker_geometry(token(shape, attachmentOffset=1), stroke_width=3)
    assert terminal_length(legacy) == terminal_run(legacy) == 12


@pytest.mark.parametrize("width", [True, -1, float("nan"), float("inf")])
def test_invalid_derived_stroke_width_is_rejected(width):
    with pytest.raises(ValueError, match="E_THEME_TOKEN_TYPE"):
        marker_geometry(token("chevron"), stroke_width=width)
