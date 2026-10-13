from dataclasses import replace
from datetime import date
from pathlib import Path

from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from chrona.presentation.scene.model import ScenePaint, ScenePrimitive, SceneSurface, SurfaceScaleManifest, TextLayout


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
