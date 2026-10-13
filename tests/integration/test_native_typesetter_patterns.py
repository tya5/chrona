"""Opt-in native grammar checks for completed synthetic pattern primitives."""
from datetime import date
import os
import subprocess

import pytest

from chrona.presentation.layout.pattern_placement import PatternPathCommand, PatternTilePrimitive
from chrona.presentation.renderers.v05_typeset import render_v05_typst, render_v05_tikz
from chrona.presentation.scene.model import PatternGeometry, ScenePaint, ScenePrimitive, SceneSurface, SurfaceScaleManifest


def pattern_surface(angle):
    primitives = (
        PatternTilePrimitive("circle", cx=2, cy=2, radius=1),
        PatternTilePrimitive("circle", cx=4, cy=4, radius=1, fill_channel="substrate", stroke_width=0.5),
        PatternTilePrimitive("rect", x=6, y=0, inline_size=1, block_size=3),
        PatternTilePrimitive("path", paint="stroke", stroke_width=0.5, line_cap="round", line_join="bevel",
                             commands=(PatternPathCommand("move", ((0, 6),)),
                                       PatternPathCommand("quadratic", ((4, 4), (8, 6))))),
        PatternTilePrimitive("path", paint="fill", commands=(
            PatternPathCommand("move", ((4, 0),)), PatternPathCommand("line", ((5, 1),)),
            PatternPathCommand("line", ((3, 1),)), PatternPathCommand("close", ()))),
    )
    bounds = (10, 10, 40, 40)
    pattern = PatternGeometry(8, 8, angle, density_basis_points=5000, primitives=primitives,
                              origin=(10, 10), region_bounds=bounds, clip_bounds=bounds, corner_radius=3)
    node = ScenePrimitive("catalogue-pattern", "Rect", "synthetic", "object", "planned", "planned", bounds,
                          pattern=pattern, corner_radius=3, paint=ScenePaint("#ffffff", "#112233", None, (), 1))
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 60, 0, 60)
    return SceneSurface("s", (), (), (), scale, (node,), ScenePaint("#ffffff", None, None, (), 1),
                        canvas_bounds=(0, 0, 60, 60))


@pytest.mark.parametrize("target,angle", [(target, angle) for target in ("typst", "tikz") for angle in (0, 45, 90)])
def test_native_compiler_accepts_completed_pattern_geometry(tmp_path, target, angle):
    executable = os.environ.get("CHRONA_TYPST" if target == "typst" else "CHRONA_TECTONIC")
    if not executable:
        pytest.skip("native engine path not supplied; run the opt-in typesetter-compile workflow")
    source = tmp_path / ("pattern.typ" if target == "typst" else "pattern.tex")
    renderer = render_v05_typst if target == "typst" else render_v05_tikz
    source.write_text(renderer(pattern_surface(angle)), encoding="utf-8")
    pdf = tmp_path / "pattern.pdf"
    command = [executable, "compile", str(source), str(pdf)] if target == "typst" else [executable, "--outdir", str(tmp_path), "--keep-logs", str(source)]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    assert pdf.is_file() and pdf.stat().st_size > 0
