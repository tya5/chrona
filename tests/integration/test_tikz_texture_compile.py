"""Compile the TikZ pattern lowering with Tectonic (opt-in: CHRONA_TECTONIC, the typesetter-compile workflow; #1551).

The whole titlecard slide used to exceed TeX's main memory (`TeX capacity exceeded`, 5 000 000 words) because its canvas
texture was thousands of tiles. It is one pgf pattern now. A second test holds the one pattern to the per-tile expansion it
replaces: same lattice phase, same ink, on a surface small enough for the expansion to compile.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from PIL import Image, ImageChops
import pytest

from chrona.presentation.fonts.installed import InstalledFontIndex, use_installed_fonts
from chrona.presentation.layout.pattern_placement import PatternPathCommand, PatternTilePrimitive
from chrona.presentation.renderers import v05_typeset
from chrona.presentation.renderers.v05_typeset import render_v05_tikz
from chrona.presentation.scene.model import PatternGeometry, ScenePaint, ScenePrimitive, SceneSurface, SurfaceScaleManifest
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from tests.integration.test_tikz_font_resolution import needs_cjk
from tests.support import typeset_compile as tc

HALCYON = Path(__file__).resolve().parents[2] / "examples" / "halcyon-1"


def _titlecard() -> str:
    with use_installed_fonts(InstalledFontIndex((), files=())):
        rendered = render_draft(DraftRenderRequest(
            project=HALCYON / "project.yaml", actual=HALCYON / "actual.yaml", target_kind="tikz", preset="titlecard",
            visual_profile="chrona-output/visual/v0.5-baseline", typesetter_engine="tectonic", typesetter_version="0.17.0",
            typesetter_adapter_grammar="chrona-tikz/v0.1"))
    return rendered.artifact.content.decode("utf-8")


@needs_cjk
def test_the_whole_titlecard_slide_compiles_and_shows_the_lattice(tmp_path):
    tc.engine("tikz")
    source = _titlecard()
    assert source.count(r"\pgfdeclarepatterninherentlycolored") == 1 and len(source) < 400_000
    image, _compiled = tc.compile_to_image("tikz", source, tmp_path, "titlecard", (1600, 874))
    # A strip of canvas beside the heading holds only ground and lattice: dark, with faint lines above the ground.
    crop = image.crop((int(700 * 4), int(2 * 4), int(1100 * 4), int(25 * 4))).convert("L")
    low, high = crop.getextrema()
    assert high < 60 and high - low > 8, (low, high)


def _synthetic(bounds, corner=0):
    items = (PatternTilePrimitive("path", paint="stroke", stroke_width=0.9, line_cap="round", line_join="round",
                                  commands=(PatternPathCommand("move", ((6.06, 3.5),)), PatternPathCommand("line", ((12.12, 7.0),)),
                                            PatternPathCommand("line", ((12.12, 14.0),)), PatternPathCommand("line", ((6.06, 17.5),)))),
             PatternTilePrimitive("circle", cx=3, cy=10, radius=1.2))
    pattern = PatternGeometry(12.12, 21.0, 0.0, density_basis_points=1455, primitives=items, origin=bounds[:2],
                              region_bounds=bounds, clip_bounds=bounds, corner_radius=corner)
    node = ScenePrimitive("texture", "Rect", "synthetic", "object", "planned", "planned", bounds, pattern=pattern,
                          corner_radius=corner, paint=ScenePaint("#050505", "#C0C0C0", None, (), 1))
    scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 120, 0, 90)
    return SceneSurface("s", (), (), (), scale, (node,), ScenePaint("#ffffff", None, None, (), 1), canvas_bounds=(0, 0, 120, 90))


SCALE = 32  # px per point; pdfium rounds a pattern cell to whole pixels, so the cell is compared where that is a 1/32 pt error


def _fine(compiled: Path):
    return tc._pdf_image(compiled.with_suffix(".pdf"), SCALE).convert("L").resize((120 * 2, 90 * 2), Image.BOX)


def _changed(first, second) -> float:
    histogram = ImageChops.difference(first, second).histogram()
    return sum(histogram[49:]) / sum(histogram)


def _both(tmp_path, monkeypatch, surface, other=None):
    """The raster of the one-pattern lowering and of the per-tile expansion it replaces (of `other`, when given)."""
    declared = render_v05_tikz(surface)
    assert r"\pgfdeclarepatterninherentlycolored" in declared
    _, one = tc.compile_to_image("tikz", declared, tmp_path / "one", "one", (120, 90))
    monkeypatch.setattr(v05_typeset, "_declarable_tikz_pattern", lambda node: False)
    expanded = render_v05_tikz(other or surface)
    assert r"\pgfdeclarepatterninherentlycolored" not in expanded
    _, many = tc.compile_to_image("tikz", expanded, tmp_path / "many", "many", (120, 90))
    return _fine(one), _fine(many)


@pytest.mark.parametrize("corner", [0, 4])
def test_the_one_pattern_draws_the_same_lattice_as_the_per_tile_expansion(tmp_path, monkeypatch, corner):
    tc.engine("tikz")
    one, many = _both(tmp_path, monkeypatch, _synthetic((7, 5, 100, 70), corner))
    assert _changed(one, many) < 0.01, f"{_changed(one, many):.4f} of pixels differ by more than 48/255"
    # Not a blank pass: the lattice is there, bright against the substrate.
    assert one.crop((20, 20, 190, 130)).getextrema()[1] > 150


def test_a_phase_error_of_the_lattice_would_fail_that_comparison(tmp_path, monkeypatch):
    tc.engine("tikz")
    surface = _synthetic((7, 5, 100, 70))
    moved = _synthetic((7, 5, 100, 70))
    object.__setattr__(moved.primitives[0].pattern, "origin", (8.5, 5.0))  # past Scene's own phase validation, on purpose
    one, many = _both(tmp_path, monkeypatch, surface, moved)
    assert _changed(one, many) > 0.03
