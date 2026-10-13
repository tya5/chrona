from dataclasses import replace
from datetime import date
from pathlib import Path
from hashlib import sha256
import pytest

from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.model import ScenePaint, ScenePrimitive, SceneSurface, SurfaceScaleManifest, TextLayout, PatternGeometry, PatternStroke
from chrona.presentation.layout.pattern_placement import PatternTilePrimitive, PatternPathCommand


def _surface() -> SceneSurface:
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 10, 0, 10)
    layout = TextLayout((1, 2, 8, 4), (1, 6), ("AB",), "Test Sans", 400, 12, 1.2,
                        "sha256:test", 3, "uppercase", "proportional")
    primitive = ScenePrimitive("label", "Text", "a", "label", "label", "label", (1, 2, 8, 4),
                               text="AB", baseline=(1, 6), text_layout=layout,
                               paint=ScenePaint("#112233", None, None, (), 1))
    return SceneSurface("s", (), (), (), scale, (primitive,), ScenePaint("#ffffff", None, None, (), 1),
                        canvas_bounds=(0, 0, 10, 10))


def test_typeset_adapters_project_completed_tracking_without_font_inference():
    surface = _surface()
    typst = render_v05_typst(surface)
    assert "tracking: 3pt" in typst and 'number-width: "proportional"' in typst
    tikz = render_v05_tikz(surface)
    assert r"\usepackage{letterspace}" not in tikz and r"\textls" not in tikz
    assert r"\addfontfeatures{LetterSpace=25}AB" in tikz
    assert r"\usepackage{fontspec}" in tikz and r"\fontspec[Numbers=Proportional]{Test Sans}" in tikz


def test_typeset_adapters_use_the_completed_canvas_not_a_caller_supplied_viewport():
    surface = replace(_surface(), canvas_bounds=(0, 0, 17, 19))
    assert "#set page(width: 17pt, height: 19pt" in render_v05_typst(surface)
    assert r"\usepackage[paperwidth=17pt,paperheight=19pt,margin=0pt]{geometry}" in render_v05_tikz(surface)


def test_typeset_adapters_project_the_supplied_rotation_degrees():
    surface = _surface()
    node = surface.primitives[0]
    layout = replace(node.text_layout, orientation="rotate-cw", rotation_degrees=90)
    rotated = replace(surface, primitives=(replace(node, text_layout=layout),))
    assert "#rotate(90deg" in render_v05_typst(rotated)
    assert "rotate=90" in render_v05_tikz(rotated)


def test_typeset_adapters_preserve_completed_global_paint_order():
    later = ScenePrimitive("later", "Rect", "a", "object", "planned", "planned", (1, 2, 8, 4),
                           paint=ScenePaint("#112233", None, None, (), 1), paint_order=20)
    first = ScenePrimitive("first", "Rect", "a", "object", "planned", "planned", (1, 2, 8, 4),
                           paint=ScenePaint("#445566", None, None, (), 1), paint_order=10)
    surface = replace(_surface(), primitives=(later, first))
    assert render_v05_typst(surface).index("scene-id: first") < render_v05_typst(surface).index("scene-id: later")
    assert render_v05_tikz(surface).index("scene-id: first") < render_v05_tikz(surface).index("scene-id: later")


def test_typeset_adapters_do_not_infer_orientation_or_measure_text() -> None:
    source = Path("src/chrona/presentation/renderers/v05_typeset.py").read_text(encoding="utf-8")
    assert ".rotation_degrees" in source
    assert "orientation" not in source
    assert "measure_text" not in source
    assert "font_metrics" not in source


def test_typst_uses_native_placement_font_list_and_literal_text():
    surface = _surface()
    node = surface.primitives[0]
    layout = replace(node.text_layout, family="Noto Sans, sans-serif", lines=("[*raw*]", "next"))
    result = render_v05_typst(replace(surface, primitives=(replace(node, text_layout=layout),)))
    assert '#place(top + left, dx: 1pt, dy:' in result
    assert 'font: ("Noto Sans", "sans-serif",)' in result
    assert '#("[*raw*]")#linebreak()#("next")' in result
    assert 'left:' not in result and 'top:' not in result


def test_tikz_projects_native_hex_color_and_multiplies_alpha():
    node = ScenePrimitive("rect", "Rect", "a", "object", "planned", "planned", (1, 2, 8, 4),
                          paint=ScenePaint("#1238", "#abcdef80", 2, (), 0.5))
    result = render_v05_tikz(replace(_surface(), primitives=(node,)))
    assert 'fill={rgb,255:red,17;green,34;blue,51}' in result
    assert 'draw={rgb,255:red,171;green,205;blue,239}' in result
    assert 'fill opacity=0.267' in result and 'draw opacity=0.251' in result
    assert 'fill=#' not in result


def test_pattern_support_keeps_compiler_correct_no_pattern_bytes():
    assert sha256(render_v05_typst(_surface()).encode()).hexdigest() == "5b6a897c2582237c719f15cf0e4a45f75982778cc554ae4fd4acc547ce17ab91"
    assert sha256(render_v05_tikz(_surface()).encode()).hexdigest() == "0951ea495c7f72bbbdae44566611b49a3df55bd0337a191d014ba6b0ea209b44"


@pytest.mark.parametrize("angle", [0, 45, 90])
def test_typeset_draws_completed_catalogue_tile_channels_and_clip(angle):
    items = (PatternTilePrimitive("circle", cx=2, cy=2, radius=1),
             PatternTilePrimitive("circle", cx=3, cy=3, radius=0.5, fill_channel="substrate", stroke_width=0.2),
             PatternTilePrimitive("rect", x=0, y=0, inline_size=1, block_size=2),
             PatternTilePrimitive("path", paint="stroke", stroke_width=0.3, line_cap="round", line_join="bevel",
                                  commands=(PatternPathCommand("move", ((0, 0),)), PatternPathCommand("quadratic", ((1, 2), (4, 4))))))
    pattern = PatternGeometry(4, 4, angle, density_basis_points=5000, primitives=items,
                              origin=(1, 2), region_bounds=(1, 2, 8, 8), clip_bounds=(1, 2, 8, 8), corner_radius=1)
    node = ScenePrimitive("pattern", "Rect", "a", "object", "planned", "planned", (1, 2, 8, 8),
                          pattern=pattern, corner_radius=1, paint=ScenePaint("#ffffff", "#112233", None, (), 1))
    surface = replace(_surface(), primitives=(node,), canvas_bounds=(0, 0, 12, 12))
    typst, tikz = render_v05_typst(surface), render_v05_tikz(surface)
    assert "clip: true" in typst and "radius: 1pt" in typst and "#circle" in typst
    assert 'curve.quad' in typst and 'cap: "round"' in typst and 'join: "bevel"' in typst
    assert r"\clip[rounded corners=1pt]" in tikz and "circle[radius=1pt]" in tikz
    assert "line cap=round" in tikz and "line join=bevel" in tikz
    assert "controls (0.667,1.333) and (2,2.667) .. (4,4)" in tikz


def test_typeset_draws_legacy_line_tile():
    pattern = PatternGeometry(4, 4, 45, (PatternStroke((0, 0), (4, 4), 0.5),))
    node = ScenePrimitive("legacy", "Rect", "a", "object", "planned", "planned", (1, 2, 8, 8),
                          pattern=pattern, paint=ScenePaint(None, "#112233", 0.5, (), 1))
    surface = replace(_surface(), primitives=(node,))
    assert "thickness: 0.5pt" in render_v05_typst(surface)
    assert "line width=0.5pt" in render_v05_tikz(surface)
