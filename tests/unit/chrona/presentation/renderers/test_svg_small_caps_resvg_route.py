"""A small-caps heading fitted with `textLength` keeps its text inside its Scene bounds when rasterised from the SVG (#1869).

README's PNG route rasterises the public SVG with `resvg_py`. resvg lays out a `<text>` that carries one `textLength`
over mixed-size `<tspan>` runs differently from the measured runs, so the adapter fits each run instead.
"""
from datetime import date
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from chrona.presentation.layout.surface_quality import TextFit
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.scene.model import (
    ScenePaint, ScenePrimitive, SceneSurface, SurfaceScaleManifest, TextLayout, TextRun,
)
from chrona.presentation.model.theme_tokens import TEXT_FOLLOWS_BOX

FONT = Path(__file__).resolve().parents[5] / "src" / "chrona" / "resources" / "fonts" / "noto-sans-regular-v1.ttf"
# The measured runs of the "Δ VS PLAN" column heading of trial 15 (Noto Sans 13, small caps, letter spacing 0.52).
RUNS = (TextRun("Δ ", 13, 12.207), TextRun("VS", 10.4, 12.47), TextRun(" ", 13, 3.38), TextRun("PLAN", 10.4, 27.851))
WIDTH = sum(run.inline_size for run in RUNS)


def _surface(*, fit) -> SceneSurface:
    layout = TextLayout(
        bounds=(20, 18, WIDTH, 16.9), baseline=(20, 30), lines=("Δ VS PLAN",), family="Noto Sans", weight=400,
        font_size=13, line_height=1.3, asset_identity="sha256:noto", letter_spacing=0.52,
        text_transform="small-caps", runs=(RUNS,), fit=fit)
    primitive = ScenePrimitive("heading", "Text", "heading-source", "label", "label", "label", (20, 18, WIDTH, 16.9),
                               text="Δ VS PLAN", baseline=(20, 30), text_layout=layout,
                               paint=ScenePaint("#000000", None, None, (), 1))
    scale = SurfaceScaleManifest("surface", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 200, 0, 60)
    return SceneSurface("surface", (), (), (), scale, (primitive,), ScenePaint("#FFFFFF", None, None, (), 1),
                        canvas_bounds=(0, 0, 200, 60))


def _ink_extent(svg: str, zoom: int = 4) -> tuple[float, float]:
    resvg = pytest.importorskip("resvg_py")
    data = resvg.svg_to_bytes(svg_string=svg, zoom=zoom, font_files=[str(FONT)], skip_system_fonts=True)
    image = Image.open(BytesIO(bytes(data))).convert("L")
    dark = [x for x in range(image.width) for y in range(image.height) if image.getpixel((x, y)) < 128]
    assert dark, "resvg drew no text: the packaged face was not loaded"
    return min(dark) / zoom, (max(dark) + 1) / zoom


def test_fitted_small_caps_heading_stays_inside_its_scene_bounds_in_resvg():
    fit = TextFit(TEXT_FOLLOWS_BOX, "spacing", (67.028,))  # the full-size line, as Layout stamped it
    svg = render_v05_svg(_surface(fit=fit), viewer_fit=True)

    left, right = _ink_extent(svg)

    assert left >= 20 - 1.5 and right <= 20 + WIDTH + 1.5, (left, right, svg)


def test_each_run_is_fitted_to_its_own_measured_size_and_the_whole_line_is_not():
    fit = TextFit(TEXT_FOLLOWS_BOX, "spacing", (67.028,))
    svg = render_v05_svg(_surface(fit=fit), viewer_fit=True)

    assert svg.count("textLength=") == len(RUNS)
    assert 'textLength="67.028"' not in svg
    assert '<tspan font-size="10.4" textLength="12.47" lengthAdjust="spacing">VS</tspan>' in svg


def test_the_unfitted_public_svg_is_unchanged_by_per_run_fitting():
    svg = render_v05_svg(_surface(fit=None), viewer_fit=True)

    assert "textLength" not in svg
    assert '<tspan font-size="10.4">VS</tspan>' in svg
