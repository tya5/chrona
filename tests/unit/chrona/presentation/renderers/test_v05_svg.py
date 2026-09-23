from datetime import date

from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import DropShadow, LinearGradient, ScenePaint, ScenePrimitive, SceneSurface, StrokeFinish, SurfaceScaleManifest, TextLayout


def _surface(*primitives):
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 10, 0, 10)
    return SceneSurface("s", (), (), (), scale, primitives, ScenePaint("#ffffff", None, None, (), 1))


def test_svg_serializes_completed_fill_stroke_width_dash_and_opacity():
    paint = ScenePaint("#112233", "#445566", 1.5, (2, 3), 0.4)
    output = render_v05_svg(_surface(ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (1, 2, 3, 4), paint=paint)), viewport=(10, 10))
    assert 'fill="#112233"' in output and 'stroke="#445566"' in output
    assert 'stroke-width="1.5"' in output and 'stroke-dasharray="2 3"' in output and 'opacity="0.4"' in output


def test_svg_serializes_completed_path_marker_and_commands():
    paint = ScenePaint(None, "#445566", 2, (), 1)
    primitive = ScenePrimitive("p", "Path", "a", "relation", "dependency", "dependency", (0, 0, 0, 0), shape="triangle", paint=paint, points=((1, 1), (9, 9)), path_commands=(PathCommand("move", ((1, 1),)), PathCommand("line", ((9, 9),))))
    output = render_v05_svg(_surface(primitive), viewport=(10, 10))
    assert 'marker-end="url(#marker-#445566-triangle)"' in output and 'd="M1 1L9 9"' in output


def test_svg_rejects_primitive_without_completed_paint():
    primitive = ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (1, 2, 3, 4))
    try:
        render_v05_svg(_surface(primitive), viewport=(10, 10))
    except ValueError as error:
        assert str(error) == "E_PRESENTATION_PAINT_INVALID"
    else:
        raise AssertionError("expected completed-paint rejection")


def test_svg_serializes_only_completed_rich_visual_values_with_stable_ids():
    paint = ScenePaint("#112233", "#445566", 1, (), 1,
                       LinearGradient(45, ((0, "#112233"), (1, "#778899")), "required"),
                       DropShadow("#000000", 1, 2, 3, 0.4, "required"),
                       StrokeFinish("round", "bevel", "required"))
    output = render_v05_svg(_surface(ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (1, 2, 3, 4), paint=paint)), viewport=(10, 10))
    assert '<linearGradient id="gradient-' in output and 'gradientUnits="objectBoundingBox" gradientTransform="rotate(45)"' in output
    assert '<feDropShadow dx="1" dy="2" stdDeviation="3" flood-color="#000000" flood-opacity="0.4"/>' in output
    assert 'fill="url(#gradient-' in output and 'filter="url(#shadow-' in output
    assert 'stroke-linecap="round" stroke-linejoin="bevel"' in output
