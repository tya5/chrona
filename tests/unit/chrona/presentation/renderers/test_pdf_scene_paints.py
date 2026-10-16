"""PDF lowering preserves completed Scene terminal and repeat paint."""
from datetime import date
from io import BytesIO

from pypdf import PdfReader
from pypdf.generic import ContentStream
import pypdfium2
import pytest
from xml.etree import ElementTree

from chrona.presentation.layout.pattern_placement import PatternTilePrimitive
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.surface_quality import PaintClip, PathCommand
from chrona.presentation.renderers.pdf_svg import PDF_PAINT_GRAMMAR, lower_pdf_svg
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import (
    PatternGeometry,
    PatternStroke,
    ScenePaint,
    ScenePrimitive,
    SceneSurface,
    SurfaceScaleManifest,
    StrokeWobble,
    SymbolGeometry,
    completed_marker_outline,
)
from chrona.presentation.scene.stroke_wobble import complete_path_wobble


def _surface(*primitives):
    scale = SurfaceScaleManifest("surface", "primary", date(2026, 1, 1), date(2026, 1, 2),
                                 0, 100, 0, 100)
    return SceneSurface("surface", (), (), (), scale, tuple(primitives),
                        ScenePaint("#FFFFFF", None, None, (), 1),
                        canvas_bounds=(0, 0, 100, 100))


def _pdf(surface):
    from reportlab.graphics import renderPDF
    from svglib.svglib import svg2rlg

    svg = lower_pdf_svg(surface, render_v05_svg(surface, viewer_fit=False).encode())
    return renderPDF.drawToString(svg2rlg(BytesIO(svg)))


def _operations(pdf):
    reader = PdfReader(BytesIO(pdf))
    return ContentStream(reader.pages[0].get_contents(), reader).operations


def _marker_path_data(svg):
    root = ElementTree.fromstring(svg)
    return {node.attrib["data-pdf-marker"]: node.attrib["d"]
            for node in root.iter() if "data-pdf-marker" in node.attrib}


def _expected_path_data(commands):
    glyphs = {"move": "M", "line": "L", "quadratic": "Q"}
    return "".join(glyphs[command.kind] + " ".join(
        f"{value:.3f}".rstrip("0").rstrip(".") for point in command.points for value in point)
                 for command in commands)


@pytest.mark.parametrize(
    ("shape", "physical", "expected_mode", "expected_width"),
    [("triangle", True, "fill", None), ("open-triangle", True, "stroke", 2),
     ("chevron", False, "stroke", 3)],
)
def test_pdf_materializes_completed_end_marker_with_correct_paint_and_axis(
        shape, physical, expected_mode, expected_width):
    marker_facts = {"shape": shape, "headLength": 8, "headWidth": 6}
    if not physical:
        marker_facts["attachmentOffset"] = 0
    marker = marker_geometry(marker_facts, stroke_width=2 if physical else 3)
    route = ScenePrimitive(
        "relation", "Path", "rel-1", "relation", "dependency", "dependency",
        (12, 30, 50, 0), paint=ScenePaint(None, "#000000", 3, (), 1),
        path_commands=(PathCommand("move", ((12, 30),)), PathCommand("line", ((62, 30),))),
        points=((12, 30), (62, 30)), marker_end=marker,
    )
    surface = _surface(route)

    lowered = lower_pdf_svg(surface, render_v05_svg(surface, viewer_fit=False).encode())
    assert PDF_PAINT_GRAMMAR == "pdf-scene-paint-v1"
    assert b'data-pdf-marker="end"' in lowered
    assert b'marker-end="url(' not in lowered
    assert marker.paint_mode == expected_mode
    if expected_width is not None:
        assert f'stroke-width="{expected_width}"'.encode() in lowered

    pdf = _pdf(surface)
    operations = _operations(pdf)
    operators = [operator for _operands, operator in operations]
    assert b"m" in operators and b"l" in operators
    # Filled terminal faces paint with fill; open chevrons retain their
    # completed stroke-relative width and paint with stroke.
    assert (b"f" in operators or b"f*" in operators) if marker.paint_mode == "fill" else b"S" in operators
    if marker.paint_mode == "stroke":
        widths = [operands[0] for operands, operator in operations if operator == b"w"]
        assert expected_width in widths


def test_pdf_materializes_start_marker_on_the_completed_route_axis():
    marker = marker_geometry({"shape": "triangle", "headLength": 8, "headWidth": 6,
                             "attachmentOffset": 0})
    route = ScenePrimitive(
        "start-relation", "Path", "rel-2", "relation", "dependency", "dependency",
        (12, 30, 50, 0), paint=ScenePaint(None, "#000000", 1, (), 1),
        path_commands=(PathCommand("move", ((12, 30),)), PathCommand("line", ((62, 30),))),
        points=((12, 30), (62, 30)), marker_start=marker,
    )
    surface = _surface(route)

    lowered = lower_pdf_svg(surface, render_v05_svg(surface, viewer_fit=False).encode())
    assert b'data-pdf-marker="start"' in lowered
    assert b'marker-start="url(' not in lowered
    assert b'd="M4 27L12 30L4 33L4 27"' in lowered
    operators = [operator for _operands, operator in _operations(_pdf(surface))]
    assert b"f" in operators or b"f*" in operators


@pytest.mark.parametrize("side", ["start", "end"])
def test_pdf_wobbled_marker_uses_completed_first_or_last_subpath_tangent(side):
    commands = (
        PathCommand("move", ((12.0, 30.0),)), PathCommand("line", ((62.0, 30.0),)),
        PathCommand("move", ((100.0, 60.0),)),
        PathCommand("quadratic", ((120.0, 10.0), (140.0, 60.0))),
    )
    outline = complete_path_wobble(
        "wobbly-relation", commands, (), amplitude=8, wavelength=15, seed=0)
    wobble = StrokeWobble(8, 15, 0, "required", outline=outline)
    marker = marker_geometry({"shape": "triangle", "headLength": 8, "headWidth": 6,
                              "attachmentOffset": 0})
    path = ScenePrimitive(
        "wobbly-relation", "Path", "rel-wobble", "relation", "dependency", "dependency",
        (12, 10, 128, 50), paint=ScenePaint(None, "#000000", 1, (), 1, wobble=wobble),
        path_commands=commands, points=((12, 30), (62, 30), (100, 60), (140, 60)),
        **{f"marker_{side}": marker},
    )
    surface = _surface(path)

    lowered = lower_pdf_svg(surface, render_v05_svg(surface, viewer_fit=False).encode())
    points = outline[0] if side == "start" else outline[-1]
    expected = completed_marker_outline(marker, side=side, points=points,
                                        path_commands=(), stroke_width=1)
    actual = _marker_path_data(lowered)[side]
    assert actual == _expected_path_data(expected)
    nominal = completed_marker_outline(marker, side=side, points=path.points,
                                       path_commands=commands, stroke_width=1)
    assert actual != _expected_path_data(nominal)
    operators = [operator for _operands, operator in _operations(_pdf(surface))]
    assert b"f" in operators or b"f*" in operators


def test_pdf_nominal_multisubpath_markers_use_quadratic_tangents_without_flattening():
    commands = (
        PathCommand("move", ((10.0, 20.0),)),
        PathCommand("quadratic", ((20.0, 0.0), (30.0, 20.0))),
        PathCommand("quadratic", ((35.0, 30.0), (40.0, 20.0))),
        PathCommand("move", ((100.0, 80.0),)), PathCommand("line", ((110.0, 80.0),)),
        PathCommand("quadratic", ((120.0, 70.0), (130.0, 80.0))),
    )
    marker = marker_geometry({"shape": "triangle", "headLength": 8, "headWidth": 6,
                              "attachmentOffset": 0})
    path = ScenePrimitive(
        "quadratic-relation", "Path", "rel-quadratic", "relation", "dependency", "dependency",
        (10, 0, 120, 80), paint=ScenePaint(None, "#000000", 1, (), 1),
        path_commands=commands, points=((10, 20), (30, 20), (40, 20), (100, 80), (130, 80)),
        marker_start=marker, marker_end=marker,
    )
    surface = _surface(path)

    lowered = lower_pdf_svg(surface, render_v05_svg(surface, viewer_fit=False).encode())
    actual = _marker_path_data(lowered)
    assert set(actual) == {"start", "end"}
    for side in ("start", "end"):
        expected = completed_marker_outline(marker, side=side, points=path.points,
                                            path_commands=commands, stroke_width=1)
        assert actual[side] == _expected_path_data(expected)
    root = ElementTree.fromstring(lowered)
    route = next(node for node in root.iter() if node.get("data-scene-id") == path.scene_id)
    assert "Q" in route.get("d", "")
    operators = [operator for _operands, operator in _operations(_pdf(surface))]
    assert b"f" in operators or b"f*" in operators


def test_pdf_lowers_legacy_hatch_to_clipped_repeat_vector_paint():
    hatch = ScenePrimitive(
        "legacy-hatch", "Rect", "calendar-day", "object", "planned", "planned",
        (8, 8, 20, 16),
        pattern=PatternGeometry(6, 6, 0, (PatternStroke((0, 0), (6, 6), 1),)),
        paint=ScenePaint(None, "#202020", 1, (), 1),
    )
    surface = _surface(hatch)

    lowered = lower_pdf_svg(surface, render_v05_svg(surface, viewer_fit=False).encode())
    assert b"pdf-pattern-host-0" in lowered and b"pdf-pattern-tile-0" in lowered
    assert lowered.count(b"clip-path=") >= 2
    pdf = _pdf(surface)
    operations = _operations(pdf)
    operators = [operator for _operands, operator in operations]
    assert b"W" in operators or b"W*" in operators
    assert operators.count(b"S") >= 2


@pytest.mark.parametrize("angle", [0, 45])
def test_pdf_catalogue_pattern_preserves_phase_rotation_and_host_clip(angle):
    pattern = PatternGeometry(
        8, 8, angle, density_basis_points=2500,
        primitives=(PatternTilePrimitive("circle", cx=2, cy=2, radius=1),),
        origin=(12, 14), region_bounds=(12, 14, 20, 18), clip_bounds=(12, 14, 20, 18),
        corner_radius=0,
    )
    patterned = ScenePrimitive(
        "catalogue", "Rect", "task", "object", "planned", "planned", (12, 14, 20, 18),
        pattern=pattern, paint=ScenePaint("#FFFFFF", "#000000", 1, (), 1),
    )
    surface = _surface(patterned)

    lowered = lower_pdf_svg(surface, render_v05_svg(surface, viewer_fit=False).encode())
    assert b"pdf-pattern-host-0" in lowered and b"pdf-pattern-tile-0" in lowered
    assert b"translate(" in lowered and f"rotate({angle})".encode() in lowered
    assert b"cx=\"2\" cy=\"2\" r=\"1\"" in lowered

    pdf = _pdf(surface)
    operations = _operations(pdf)
    operators = [operator for _operands, operator in operations]
    assert b"W" in operators or b"W*" in operators
    assert b"cm" in operators and b"f" in operators
    document = pypdfium2.PdfDocument(BytesIO(pdf))
    # SVG scene units are CSS px, while PDF uses points (72/96); scale back
    # to the authored 100x100 viewport for direct coordinate assertions.
    image = document[0].render(scale=4 / 3).to_pil().convert("RGB")
    pixels = image.load()
    assert any(pixels[x, y] != (255, 255, 255)
               for x in range(14, 30) for y in range(16, 30))
    assert all(pixels[x, y] == (255, 255, 255)
               for x in range(image.width) for y in range(image.height)
               if x < 11 or x > 32 or y < 13 or y > 33)


def test_pdf_refuses_patterned_symbol_hosts_with_all_primitive_identities():
    bounds = (0, 0, 8, 8)
    outline = SymbolGeometry((PathCommand("move", ((0, 0),)), PathCommand("line", ((8, 0),)),
                             PathCommand("line", ((8, 8),)), PathCommand("line", ((0, 8),)),
                             PathCommand("line", ((0, 0),))))
    pattern = PatternGeometry(
        8, 8, 0, density_basis_points=1000,
        primitives=(PatternTilePrimitive("circle", cx=2, cy=2, radius=1),),
        origin=(0, 0), region_bounds=bounds, clip_bounds=bounds, corner_radius=0,
    )
    symbols = tuple(ScenePrimitive(
        scene_id, "Symbol", "task", "object", "progress-fill", "progress-fill", bounds,
        pattern=pattern, symbol=outline, paint_clip=PaintClip((0, 0, 8, 8)),
        paint=ScenePaint("#FFFFFF", "#000000", 1, (), 1),
    ) for scene_id in ("unsupported-a", "unsupported-b"))
    surface = _surface(*symbols)

    with pytest.raises(ValueError, match="E_VISUAL_CAPABILITY_UNSUPPORTED") as error:
        lower_pdf_svg(surface, render_v05_svg(surface, viewer_fit=False).encode())
    assert "count=2" in str(error.value)
    assert "unsupported-a" in str(error.value) and "unsupported-b" in str(error.value)
