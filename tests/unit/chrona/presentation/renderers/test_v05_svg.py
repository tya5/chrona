from datetime import date

from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.mark_geometry import marker_geometry
from chrona.presentation.scene.model import DropShadow, LinearGradient, ScenePaint, ScenePrimitive, SceneSurface, StrokeFinish, SurfaceScaleManifest, SymbolGeometry, TextLayout


def _surface(*primitives):
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 10, 0, 10)
    return SceneSurface("s", (), (), (), scale, primitives, ScenePaint("#ffffff", None, None, (), 1))


def test_svg_serializes_completed_fill_stroke_width_dash_and_opacity():
    paint = ScenePaint("#112233", "#445566", 1.5, (2, 3), 0.4)
    output = render_v05_svg(_surface(ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (1, 2, 3, 4), paint=paint)), viewport=(10, 10))
    assert 'fill="#112233"' in output and 'stroke="#445566"' in output
    assert 'stroke-width="1.5"' in output and 'stroke-dasharray="2 3"' in output and 'opacity="0.4"' in output


def test_svg_projects_nondefault_measured_text_treatment_without_remeasuring():
    layout = TextLayout((1, 2, 8, 4), (1, 6), ("AB",), "Test Sans", 400, 12, 1.2,
                        "sha256:test", 3, "uppercase", "tabular")
    primitive = ScenePrimitive("label", "Text", "a", "label", "label", "label", (1, 2, 8, 4),
                               text="AB", baseline=(1, 6), text_layout=layout,
                               paint=ScenePaint("#112233", None, None, (), 1))
    output = render_v05_svg(_surface(primitive), viewport=(10, 10))
    assert 'letter-spacing="3"' in output
    assert 'font-variant-numeric="tabular-nums"' in output


def test_svg_serializes_completed_path_marker_and_commands():
    paint = ScenePaint(None, "#445566", 2, (), 1)
    primitive = ScenePrimitive("p", "Path", "a", "relation", "dependency", "dependency", (0, 0, 0, 0),
                               marker_start=marker_geometry({"shape": "circle", "headLength": 10, "headWidth": 10, "attachmentOffset": 1}),
                               marker_end=marker_geometry({"shape": "triangle", "headLength": 10, "headWidth": 10, "attachmentOffset": 1}),
                               paint=paint, points=((1, 1), (9, 9)), path_commands=(PathCommand("move", ((1, 1),)), PathCommand("line", ((9, 9),))))
    output = render_v05_svg(_surface(primitive), viewport=(10, 10))
    assert 'marker-start="url(#marker-' in output and 'marker-end="url(#marker-' in output
    assert 'Q10 0 10 5' in output and 'd="M1 1L9 9"' in output


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
                       LinearGradient((1, 2), (4, 5), ((0, "#112233"), (1, "#778899")), "required"),
                       DropShadow("#000000", 1, 2, 3, 0.4, "required"),
                       StrokeFinish("round", "bevel", "required"))
    output = render_v05_svg(_surface(ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (1, 2, 3, 4), paint=paint)), viewport=(10, 10))
    assert '<linearGradient id="gradient-' in output and 'gradientUnits="userSpaceOnUse" x1="1" y1="2" x2="4" y2="5"' in output
    assert '<feDropShadow dx="1" dy="2" stdDeviation="3" flood-color="#000000" flood-opacity="0.4"/>' in output
    assert 'fill="url(#gradient-' in output and 'filter="url(#shadow-' in output
    assert 'stroke-linecap="round" stroke-linejoin="bevel"' in output


def test_svg_projects_completed_mark_paint_order_clip_and_link_interaction_separately():
    host = ScenePrimitive("host", "Rect", "a", "object", "planned", "planned", (1, 2, 8, 4),
                          slot_id="timeline", paint=ScenePaint("#112233", None, None, (), 1),
                          corner_radius=2, paint_order=1, href="https://example.test/a")
    fill = ScenePrimitive("fill", "Rect", "a", "object", "progress-fill", "progress-fill", (1, 2, 3, 4),
                          slot_id="timeline", paint=ScenePaint("#445566", None, None, (), 1),
                          clip_source_id="host", paint_order=2)
    output = render_v05_svg(_surface(host, fill), viewport=(10, 10))
    assert '<clipPath id="clip-host"><rect x="1" y="2" width="8" height="4" rx="2" ry="2"/></clipPath>' in output
    assert 'clip-path="url(#clip-host)"' in output
    assert '<g data-layer="mark-paint" aria-hidden="true">' in output
    assert '<g data-layer="mark-interaction"><a href="https://example.test/a"' in output


def test_svg_projects_layout_owned_open_symbol_and_uses_it_as_a_progress_clip_host():
    outline = (PathCommand("move", ((1, 2),)), PathCommand("line", ((7, 2),)),
               PathCommand("line", ((9, 4),)), PathCommand("line", ((7, 6),)),
               PathCommand("line", ((1, 6),)), PathCommand("line", ((1, 2),)))
    host = ScenePrimitive("actual:open", "Symbol", "a", "object", "actual", "actual", (1, 2, 8, 4),
                          slot_id="timeline", symbol=SymbolGeometry(outline), paint=ScenePaint("#112233", None, None, (), 1),
                          paint_order=1, end_treatment="open")
    fill = ScenePrimitive("progress:open", "Rect", "a", "object", "progress-fill", "progress-fill", (1, 2, 3, 4),
                          slot_id="timeline", paint=ScenePaint("#445566", None, None, (), 1),
                          clip_source_id="actual:open", paint_order=2)
    output = render_v05_svg(_surface(host, fill), viewport=(10, 10))
    assert '<clipPath id="clip-actual:open"><path d="M1 2L7 2L9 4L7 6L1 6L1 2"/></clipPath>' in output
    assert 'data-scene-id="actual:open"' in output and 'd="M1 2L7 2L9 4L7 6L1 6L1 2"' in output
    assert 'clip-path="url(#clip-actual:open)"' in output
