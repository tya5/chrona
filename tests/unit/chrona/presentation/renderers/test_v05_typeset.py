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
    return SceneSurface("s", (), (), (), scale, (primitive,), ScenePaint("#ffffff", None, None, (), 1))


def test_typeset_adapters_project_completed_tracking_without_font_inference():
    surface = _surface()
    typst = render_v05_typst(surface, viewport=(10, 10))
    assert "tracking: 3pt" in typst and 'number-width: "proportional"' in typst
    tikz = render_v05_tikz(surface, viewport=(10, 10))
    assert r"\usepackage{letterspace}" in tikz and r"\textls[250]{AB}" in tikz
    assert r"\usepackage{fontspec}" in tikz and r"\fontspec[Numbers=Proportional]{Test Sans}" in tikz


def test_typeset_adapters_project_the_supplied_rotation_degrees():
    surface = _surface()
    node = surface.primitives[0]
    layout = replace(node.text_layout, orientation="rotate-cw", rotation_degrees=90)
    rotated = replace(surface, primitives=(replace(node, text_layout=layout),))
    assert "#rotate(90deg" in render_v05_typst(rotated, viewport=(10, 10))
    assert "rotate=90" in render_v05_tikz(rotated, viewport=(10, 10))


def test_typeset_adapters_do_not_infer_orientation_or_measure_text() -> None:
    source = Path("src/chrona/presentation/renderers/v05_typeset.py").read_text(encoding="utf-8")
    assert ".rotation_degrees" in source
    assert "orientation" not in source
    assert "measure_text" not in source
    assert "font_metrics" not in source
