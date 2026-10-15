"""The TikZ lowering writes a repeated catalogue pattern as one pgf pattern, not one scope per tile (#1551).

The canvas texture of `titlecard` is one Rect over 1600 x 874 with a 12.12 x 21 tile; the expansion wrote about 2000 tiles
(7.5 MB) and Tectonic ran out of main memory. These tests use a synthetic surface of the same shape.
"""
from __future__ import annotations

from dataclasses import replace
from datetime import date
import re

import pytest

from chrona.presentation.layout.pattern_placement import PatternPathCommand, PatternTilePrimitive
from chrona.presentation.renderers.v05_typeset import render_v05_tikz
from chrona.presentation.scene.model import PatternGeometry, ScenePaint, ScenePrimitive, SceneSurface, SurfaceScaleManifest


def lattice(bounds=(0, 0, 1600, 874), angle=0.0, origin=(0.0, 0.0), tile=(12.12, 21.0), stroke="#1B1A18", fill="#050505", opacity=1,
            name="canvas-texture") -> ScenePrimitive:
    items = (PatternTilePrimitive("path", paint="stroke", stroke_width=0.9, line_cap="round", line_join="round",
                                  commands=(PatternPathCommand("move", ((6.06, 3.5),)), PatternPathCommand("line", ((12.12, 7.0),)))),
             PatternTilePrimitive("circle", cx=3, cy=3, radius=0.5))
    pattern = PatternGeometry(tile[0], tile[1], angle, density_basis_points=1455, primitives=items, origin=origin,
                              region_bounds=bounds, clip_bounds=bounds, corner_radius=0)
    return ScenePrimitive(name, "Rect", "canvas", "decoration", name, name, bounds, pattern=pattern,
                          paint=ScenePaint(fill, stroke, None, (), opacity))


def surface(*nodes: ScenePrimitive, canvas=(0, 0, 1600, 874)) -> SceneSurface:
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 60, 0, 60)
    return SceneSurface("s", (), (), (), scale, nodes, ScenePaint("#050505", None, None, (), 1), canvas_bounds=canvas)


def test_a_full_canvas_texture_is_one_declaration_and_one_fill():
    tikz = render_v05_tikz(surface(lattice()))
    assert tikz.count(r"\pgfdeclarepatterninherentlycolored") == 1
    assert len(re.findall(r"^\\path\[pattern=", tikz, re.M)) == 1
    assert r"\usetikzlibrary{patterns}" in tikz
    assert tikz.count(r"\begin{scope}") == 0  # no per-tile scope
    assert len(tikz) < 20_000, len(tikz)  # the expansion of the same surface is about 7.5 MB


def test_the_output_does_not_grow_with_the_canvas_and_is_deterministic():
    small = render_v05_tikz(surface(lattice((0, 0, 100, 80)), canvas=(0, 0, 100, 80)))
    large = render_v05_tikz(surface(lattice((0, 0, 4000, 3000)), canvas=(0, 0, 4000, 3000)))
    assert abs(len(large) - len(small)) < 200
    assert render_v05_tikz(surface(lattice())) == render_v05_tikz(surface(lattice()))


def test_the_declaration_precedes_the_picture_and_nothing_nests_a_box():
    tikz = render_v05_tikz(surface(lattice()))
    declaration = tikz[tikz.index(r"\pgfdeclarepatterninherentlycolored"):tikz.index(r"\noindent")]
    assert tikz.index(r"\begin{document}") < tikz.index(r"\pgfdeclarepatterninherentlycolored")
    # A tikzpicture, node or box in the body leaks into the page when pgf runs it (an overfull line shifted the slide).
    assert not re.search(r"tikzpicture|\\node|\\hbox|\\pgftext", declaration)


def test_phase_values_follow_the_anchor_at_the_page_corner():
    # page 60 high, origin (10, 10), tile 8 x 8: u0 = 10 mod 8 = 2, v0 = (60 - 10) mod 8 = 2
    tikz = render_v05_tikz(surface(lattice((10, 10, 40, 40), origin=(10.0, 10.0), tile=(8.0, 8.0)), canvas=(0, 0, 60, 60)))
    found = re.findall(r"\\pgftransformcm\{1\}\{0\}\{0\}\{-1\}\{\\pgfpoint\{([^}]*)\}\{([^}]*)\}\}", tikz)
    assert sorted(found) == sorted([("2pt", "2pt"), ("2pt", "10pt"), ("-6pt", "2pt"), ("-6pt", "10pt")])


def test_equal_textures_share_one_declaration_and_different_paint_gets_its_own():
    same = render_v05_tikz(surface(lattice(name="a"), lattice(name="b")))
    assert same.count(r"\pgfdeclarepatterninherentlycolored") == 1 and same.count(r"\path[pattern=chronaPatterna]") == 2
    other = render_v05_tikz(surface(lattice(name="a"), lattice(name="b", stroke="#336699")))
    assert other.count(r"\pgfdeclarepatterninherentlycolored") == 2 and "chronaPatternb" in other


@pytest.mark.parametrize("variant", [{"angle": 45.0}, {"opacity": 0.5, "fill": None}])
def test_a_rotated_or_translucent_pattern_keeps_the_exact_per_tile_expansion(variant):
    tikz = render_v05_tikz(surface(lattice((0, 0, 40, 40), **variant), canvas=(0, 0, 60, 60)))
    assert r"\pgfdeclarepatterninherentlycolored" not in tikz and r"\usetikzlibrary{patterns}" not in tikz
    assert tikz.count(r"\begin{scope}") > 2
