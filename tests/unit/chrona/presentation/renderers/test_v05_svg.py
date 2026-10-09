from datetime import date
from dataclasses import replace
from hashlib import sha256
from io import BytesIO
from pathlib import Path

from PIL import Image
import pytest

from chrona.presentation.layout.surface_quality import PathCommand
from chrona.presentation.layout.pattern_placement import PatternTilePrimitive
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.scene.model import DropShadow, LinearGradient, PatternGeometry, PatternStroke, ScenePaint, ScenePrimitive, SceneSurface, StrokeFinish, SurfaceScaleManifest, SymbolGeometry, TextLayout


def _surface(*primitives):
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 10, 0, 10)
    return SceneSurface("s", (), (), (), scale, primitives, ScenePaint("#ffffff", None, None, (), 1),
                        canvas_bounds=(0, 0, 10, 10))


def test_svg_serializes_completed_fill_stroke_width_dash_and_opacity():
    paint = ScenePaint("#112233", "#445566", 1.5, (2, 3), 0.4)
    output = render_v05_svg(_surface(ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (1, 2, 3, 4), paint=paint)))
    assert 'fill="#112233"' in output and 'stroke="#445566"' in output
    assert 'stroke-width="1.5"' in output and 'stroke-dasharray="2 3"' in output and 'opacity="0.4"' in output


def test_svg_serializes_stroke_only_rect_and_symbol_with_explicit_no_fill():
    paint = ScenePaint(None, "#445566", 1, (), 1)
    outline = SymbolGeometry((PathCommand("move", ((1, 2),)), PathCommand("line", ((3, 2),)),
                              PathCommand("line", ((2, 4),)), PathCommand("line", ((1, 2),))))
    rect = ScenePrimitive("closed", "Rect", "calendar", "background", "calendar-closed", "calendar-closed",
                          (1, 2, 3, 4), paint=paint)
    symbol = ScenePrimitive("milestone", "Symbol", "gate", "object", "planned", "planned",
                            (1, 2, 3, 4), paint=paint, symbol=outline)
    output = render_v05_svg(_surface(rect, symbol))
    assert 'data-scene-id="closed"' in output and 'data-scene-id="milestone"' in output
    assert output.count('fill="none"') == 2


def test_svg_raster_preserves_an_outline_interior_as_canvas():
    resvg_py = pytest.importorskip("resvg_py")
    rect = ScenePrimitive("closed", "Rect", "calendar", "background", "calendar-closed", "calendar-closed",
                          (1, 1, 8, 8), paint=ScenePaint(None, "#000000", 1, (), 1))
    rendered = resvg_py.svg_to_bytes(svg_string=render_v05_svg(_surface(rect)), dpi=96,
                                     skip_system_fonts=True)
    image = Image.open(BytesIO(rendered)).convert("RGB")
    assert image.getpixel((5, 5)) == (255, 255, 255)


def test_svg_pattern_rect_has_one_explicit_pattern_fill():
    paint = ScenePaint(None, "#445566", 1, (), 1)
    pattern = PatternGeometry(4, 4, 45, (PatternStroke((0, 0), (4, 4), 1),))
    rect = ScenePrimitive("hatched", "Rect", "a", "object", "planned", "planned",
                          (1, 2, 3, 4), paint=paint, pattern=pattern)
    output = render_v05_svg(_surface(rect))
    line = next(line for line in output.splitlines() if 'data-scene-id="hatched"' in line)
    assert line.count('fill="url(#pattern-') == 1
    assert 'fill="none"' not in line


def test_catalogue_pattern_uses_completed_origin_substrate_and_ink_in_svg_and_png():
    pattern = PatternGeometry(
        4, 4, 0, density_basis_points=5000,
        primitives=(PatternTilePrimitive("rect", x=0, y=0, inline_size=2, block_size=4),),
        origin=(1, 1), region_bounds=(1, 1, 8, 8), clip_bounds=(1, 1, 8, 8),
        corner_radius=0,
    )
    primitive = ScenePrimitive(
        "catalogued", "Rect", "a", "object", "planned", "planned", (1, 1, 8, 8),
        paint=ScenePaint("#FFFFFF", "#000000", None, (), 1), pattern=pattern,
    )
    output = render_v05_svg(_surface(primitive))
    assert 'patternTransform="translate(1 1) rotate(0 2 2)"' in output
    assert '<rect x="0" y="0" width="4" height="4" fill="#FFFFFF"/>' in output
    assert '<rect x="0" y="0" width="2" height="4" fill="#000000"/>' in output
    resvg_py = pytest.importorskip("resvg_py")
    image = Image.open(BytesIO(resvg_py.svg_to_bytes(svg_string=output, dpi=96,
                                                     skip_system_fonts=True))).convert("RGB")
    assert image.getpixel((2, 3)) == (0, 0, 0)
    assert image.getpixel((4, 3)) == (255, 255, 255)


def test_catalogue_circle_channels_render_in_declared_order_with_native_stroke():
    pattern = PatternGeometry(
        10, 10, 0, density_basis_points=4000,
        primitives=(
            PatternTilePrimitive("circle", cx=5, cy=5, radius=4, fill_channel="substrate"),
            PatternTilePrimitive("circle", cx=5, cy=5, radius=3,
                                 fill_channel="none", stroke_width=0.5),
        ),
        origin=(0, 0), region_bounds=(0, 0, 10, 10), clip_bounds=(0, 0, 10, 10),
        corner_radius=0,
    )
    rect = ScenePrimitive("circles", "Rect", "a", "object", "planned", "planned", (0, 0, 10, 10),
                          paint=ScenePaint("#FFFFFF", "#202020", None, (), 1), pattern=pattern)
    output = render_v05_svg(_surface(rect))
    first = '<circle cx="5" cy="5" r="4" fill="#FFFFFF"/>'
    second = '<circle cx="5" cy="5" r="3" fill="none" stroke="#202020" stroke-width="0.5"/>'
    assert first in output and second in output and output.index(first) < output.index(second)


def test_catalogue_circle_substrate_requires_completed_fill_with_actionable_detail():
    pattern = PatternGeometry(
        4, 4, 0, density_basis_points=1000,
        primitives=(PatternTilePrimitive("circle", cx=2, cy=2, radius=1,
                                         fill_channel="substrate"),),
        origin=(0, 0), region_bounds=(0, 0, 4, 4), clip_bounds=(0, 0, 4, 4),
        corner_radius=0,
    )
    primitive = ScenePrimitive(
        "substrate", "Rect", "a", "object", "planned", "planned", (0, 0, 4, 4),
        paint=ScenePaint(None, "#202020", None, (), 1), pattern=pattern,
    )
    with pytest.raises(ValueError) as error:
        render_v05_svg(_surface(primitive))
    assert str(error.value).startswith("E_PRESENTATION_PAINT_INVALID:")
    assert "pattern circle at (2, 2)" in str(error.value)
    assert "fillChannel='substrate'" in str(error.value)
    assert "completed ScenePaint has no fill" in str(error.value)


def test_catalogue_circle_invalid_channel_reports_value_and_allowed_channels():
    # Deliberately bypass the validated Layout DTO to exercise the SVG
    # adapter's defensive branch for an impossible completed Scene value.
    item = PatternTilePrimitive("circle", cx=2, cy=2, radius=1)
    object.__setattr__(item, "fill_channel", "other")
    pattern = PatternGeometry(
        4, 4, 0, density_basis_points=1000,
        primitives=(item,), origin=(0, 0), region_bounds=(0, 0, 4, 4),
        clip_bounds=(0, 0, 4, 4), corner_radius=0,
    )
    primitive = ScenePrimitive(
        "bad-channel", "Rect", "a", "object", "planned", "planned", (0, 0, 4, 4),
        paint=ScenePaint("#FFFFFF", "#202020", None, (), 1), pattern=pattern,
    )
    with pytest.raises(ValueError) as error:
        render_v05_svg(_surface(primitive))
    assert str(error.value).startswith("E_PRESENTATION_PRIMITIVE_INVALID:")
    assert "fillChannel 'other'" in str(error.value)
    assert "expected 'ink', 'substrate', or 'none'" in str(error.value)


def test_svg_serializes_the_completed_canvas_not_a_caller_supplied_viewport():
    surface = replace(_surface(), canvas_bounds=(3, 4, 17, 19))
    output = render_v05_svg(surface)
    assert 'width="17" height="19" viewBox="3 4 17 19"' in output
    assert '<rect x="3" y="4" width="17" height="19"' in output


def test_svg_uses_negative_completed_origin_without_adapter_repositioning():
    surface = replace(_surface(), canvas_bounds=(-12, -4, 112, 54))
    output = render_v05_svg(surface)
    assert 'width="112" height="54" viewBox="-12 -4 112 54"' in output
    assert '<rect x="-12" y="-4" width="112" height="54"' in output


def test_canvas_overlay_rejects_bounds_that_differ_from_completed_canvas_with_details():
    overlay = ScenePrimitive("overlay", "Rect", "canvas-overlay-gradient", "decoration",
                             "canvas-overlay-gradient", "canvas-overlay-gradient", (1, 2, 3, 4),
                             paint=ScenePaint("#101820", None, None, (), 1))
    with pytest.raises(ValueError, match=r"E_PRESENTATION_PRIMITIVE_INVALID: canvas overlay 'overlay'.*"
                       r"canvasBounds=\(0, 0, 10, 10\).*bounds=\(1, 2, 3, 4\)"):
        render_v05_svg(_surface(overlay))


def test_svg_projects_nondefault_measured_text_treatment_without_remeasuring():
    layout = TextLayout((1, 2, 8, 4), (1, 6), ("AB",), "Test Sans", 400, 12, 1.2,
                        "sha256:test", 3, "uppercase", "tabular")
    primitive = ScenePrimitive("label", "Text", "a", "label", "label", "label", (1, 2, 8, 4),
                               text="AB", baseline=(1, 6), text_layout=layout,
                               paint=ScenePaint("#112233", None, None, (), 1))
    output = render_v05_svg(_surface(primitive))
    assert 'letter-spacing="3"' in output
    assert 'font-variant-numeric="tabular-nums"' in output


def test_svg_projects_proportional_figures_explicitly_after_layout_measurement():
    layout = TextLayout((1, 2, 8, 4), (1, 6), ("12",), "Test Sans", 400, 12, 1.2,
                        "sha256:test")
    primitive = ScenePrimitive("label", "Text", "a", "label", "label", "label", (1, 2, 8, 4),
                               text="12", baseline=(1, 6), text_layout=layout,
                               paint=ScenePaint("#112233", None, None, (), 1))
    assert 'font-variant-numeric="proportional-nums"' in render_v05_svg(_surface(primitive))


def test_svg_projects_the_layout_selected_rotation_about_the_supplied_baseline():
    layout = TextLayout((1, 2, 4, 8), (1, 6), ("AB",), "Test Sans", 400, 12, 1.2,
                        "sha256:test", orientation="rotate-cw", rotation_degrees=90)
    primitive = ScenePrimitive("label", "Text", "a", "label", "label", "label", layout.bounds,
                               text="AB", baseline=layout.baseline, text_layout=layout,
                               paint=ScenePaint("#112233", None, None, (), 1))
    assert 'transform="rotate(90 1 6)"' in render_v05_svg(_surface(primitive))


@pytest.mark.parametrize("scale,digest", [
    (0.5, "2d5fd667caa797a22ad407bb70d88a12c4996ac66c7334df657ed21a06a120a5"),
    (0.86, "ee86f80cca9d115d153f254880855328eca65d608c3dcc11c6d39dc4eaebb95a"),
    (1.0, "91363e781d81c753db08c9bb3f06636e4eb637359b32fbf2367a1e48b85f8428"),
])
def test_non_glow_text_bytes_match_the_published_1261_baseline(scale, digest):
    # Captured from public main 510fd5f9 before changing glow serialization.
    layout = TextLayout((30, 40, 100 * scale, 24), (30, 60), ("ENDING D",),
                        "Noto Sans", 400, 24, 1.2, "sha256:synthetic", horizontal_scale=scale)
    node = ScenePrimitive("run", "Text", "synthetic", "heading", "heading", "heading", layout.bounds,
                          text="ENDING D", baseline=layout.baseline, text_layout=layout,
                          paint=ScenePaint("#111111", None, None, (), 1))
    output = render_v05_svg(replace(_surface(node), canvas_bounds=(0, 0, 400, 200)))
    assert sha256(output.encode()).hexdigest() == digest


def test_svg_adapter_does_not_infer_orientation_or_measure_text() -> None:
    source = Path("src/chrona/presentation/renderers/v05_svg.py").read_text(encoding="utf-8")
    assert ".rotation_degrees" in source
    assert "orientation" not in source
    assert "measure_text" not in source
    assert "font_metrics" not in source


def test_svg_serializes_completed_path_marker_and_commands():
    paint = ScenePaint(None, "#445566", 2, (), 1)
    primitive = ScenePrimitive("p", "Path", "a", "relation", "dependency", "dependency", (0, 0, 0, 0),
                               marker_start=marker_geometry({"shape": "circle", "headLength": 10, "headWidth": 10, "attachmentOffset": 1}),
                               marker_end=marker_geometry({"shape": "triangle", "headLength": 10, "headWidth": 10, "attachmentOffset": 1}),
                               paint=paint, points=((1, 1), (9, 9)), path_commands=(PathCommand("move", ((1, 1),)), PathCommand("line", ((9, 9),))))
    output = render_v05_svg(_surface(primitive))
    assert 'marker-start="url(#marker-' in output and 'marker-end="url(#marker-' in output
    assert 'Q10 0 10 5' in output and 'd="M1 1L9 9"' in output


def test_svg_rejects_primitive_without_completed_paint():
    primitive = ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (1, 2, 3, 4))
    try:
        render_v05_svg(_surface(primitive))
    except ValueError as error:
        assert str(error).startswith("E_PRESENTATION_PAINT_INVALID:")
        assert "scene_id='p'" in str(error) and "no completed paint" in str(error)
    else:
        raise AssertionError("expected completed-paint rejection")


def test_svg_serializes_only_completed_rich_visual_values_with_stable_ids():
    paint = ScenePaint("#112233", "#445566", 1, (), 1,
                       LinearGradient((1, 2), (4, 5), ((0, "#112233"), (1, "#778899")), "required"),
                       DropShadow("#000000", 1, 2, 3, 0.4, "required"),
                       StrokeFinish("round", "bevel", "required"))
    output = render_v05_svg(_surface(ScenePrimitive("p", "Rect", "a", "object", "planned", "planned", (1, 2, 3, 4), paint=paint)))
    assert '<linearGradient id="gradient-' in output and 'gradientUnits="userSpaceOnUse" x1="1" y1="2" x2="4" y2="5"' in output
    assert '<feDropShadow dx="1" dy="2" stdDeviation="3" flood-color="#000000" flood-opacity="0.4"/>' in output
    assert 'fill="url(#gradient-' in output and 'filter="url(#shadow-' in output
    assert 'stroke-linecap="round" stroke-linejoin="bevel"' in output


def test_svg_projects_completed_global_paint_order_clip_and_link_interaction_separately():
    host = ScenePrimitive("host", "Rect", "a", "object", "planned", "planned", (1, 2, 8, 4),
                          slot_id="timeline", paint=ScenePaint("#112233", None, None, (), 1),
                          corner_radius=2, paint_order=1, href="https://example.test/a")
    fill = ScenePrimitive("fill", "Rect", "a", "object", "progress-fill", "progress-fill", (1, 2, 3, 4),
                          slot_id="timeline", paint=ScenePaint("#445566", None, None, (), 1),
                          clip_source_id="host", paint_order=2)
    text = ScenePrimitive("label", "Text", "a", "review", "label", "label", (1, 2, 8, 4),
                          slot_id="timeline", text="Label", baseline=(1, 6),
                          text_layout=TextLayout((1, 2, 8, 4), (1, 6), ("Label",), "Test Sans", 400, 12, 1.2,
                                                 "sha256:test"),
                          paint=ScenePaint("#ffffff", None, None, (), 1), paint_order=3,
                          host_placement_id="host")
    output = render_v05_svg(_surface(text, fill, host))
    assert '<clipPath id="clip-host"><rect x="1" y="2" width="8" height="4" rx="2" ry="2"/></clipPath>' in output
    assert 'clip-path="url(#clip-host)"' in output
    assert '<g data-layer="mark-paint"' not in output
    assert output.index('data-scene-id="host"') < output.index('data-scene-id="fill"') < output.index('data-scene-id="label"')
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
    output = render_v05_svg(_surface(host, fill))
    assert '<clipPath id="clip-actual:open"><path d="M1 2L7 2L9 4L7 6L1 6L1 2"/></clipPath>' in output
    assert 'data-scene-id="actual:open"' in output and 'd="M1 2L7 2L9 4L7 6L1 6L1 2"' in output
    assert 'clip-path="url(#clip-actual:open)"' in output
