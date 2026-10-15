"""Compile the Typst and TikZ small-caps runs and measure the ink against Layout's bounds and baseline (#1532).

Opt-in: needs CHRONA_TYPST / CHRONA_TECTONIC (the typesetter-compile workflow). Synthetic Project, no `examples/`.
"""
from __future__ import annotations

from datetime import date, timedelta
import os
from pathlib import Path
import shutil

from PIL import Image, ImageChops
import pytest

from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst
from tests.integration.test_small_caps import _parts
from tests.support import synthetic_review as sr
from tests.support import typeset_compile as tc

EVIDENCE = os.environ.get("CHRONA_SCALE_EVIDENCE")
TITLES = {"imaging": "Imaging Team", "tea": "tea"}  # "tea" has no capital: every run is a small run


def _source() -> dict:
    objects = {f"t-{owner}": sr.span(f"t-{owner}", date(2026, 1, 5) + timedelta(days=index * 20), 12, owner=owner)
               for index, owner in enumerate(TITLES)}
    source = sr.project(objects)
    for owner, title in TITLES.items():
        source["entities"][owner]["title"] = title
    return source


def _ink(image: Image.Image, canvas, bounds) -> tuple[float, float, float, float]:
    """Ink box of the pixels in the text's row band, in surface units (x0, top, x1, bottom)."""
    sx, sy = image.width / canvas[0], image.height / canvas[1]
    x, y, w, h = bounds
    top, bottom = max(0, round((y - 3) * sy)), min(image.height, round((y + h + 3) * sy))
    left, right = max(0, round((x - 6) * sx)), min(image.width, round((x + w + 6) * sx))
    crop = image.crop((left, top, right, bottom))
    mask = ImageChops.difference(crop, Image.new("RGB", crop.size, crop.getpixel((0, 0)))).convert("L").point(
        lambda value: 255 if value > 35 else 0)
    box = mask.getbbox()
    assert box is not None, "the text must leave raster ink"
    return ((left + box[0]) / sx, (top + box[1]) / sy, (left + box[2]) / sx, (top + box[3]) / sy)


def _compiled(tmp_path, target, name, titles, parts):
    (tmp_path / name).mkdir()
    source = _source()
    for owner, title in titles.items():
        source["entities"][owner]["title"] = title
    rendered = sr.render(tmp_path / name, source, presentation=parts)
    surface = rendered.scene.surfaces[0]
    canvas = surface.canvas_bounds[2:]
    text = (render_v05_typst if target == "typst" else render_v05_tikz)(surface)
    image, compiled = tc.compile_to_image(target, text, tmp_path / f"{name}-out", name, canvas)
    if EVIDENCE:
        destination = Path(EVIDENCE) / f"small-caps-{target}"
        destination.mkdir(parents=True, exist_ok=True)
        image.save(destination / f"{name}.png")
        shutil.copy2(compiled, destination / compiled.name)
    return surface, image, canvas


@pytest.mark.parametrize("target", ["typst", "tikz"])
def test_compiled_small_caps_ink_matches_the_measured_width_and_sits_on_the_unmarked_baseline(tmp_path, target):
    tc.engine(target)
    surface, image, canvas = _compiled(tmp_path, target, "caps", TITLES, _parts())
    # Control: the same words as plain capitals at the role size, through the same adapter.
    control, control_image, control_canvas = _compiled(
        tmp_path, target, "plain", {key: value.upper() for key, value in TITLES.items()}, _parts(transform=None, scale=None))
    for owner in TITLES:
        node = next(item for item in surface.primitives if item.scene_id == f"group-header:{owner}")
        plain = next(item for item in control.primitives if item.scene_id == f"group-header:{owner}")
        assert node.text_layout.runs and len({run.font_size for run in node.text_layout.runs[0]}) >= (2 if owner == "imaging" else 1)
        left, _top, right, bottom = _ink(image, canvas, node.bounds)
        _left, _top, _right, plain_bottom = _ink(control_image, control_canvas, plain.bounds)
        # Layout's inline size is the sum of its run widths; the ink lies inside it by at most the side bearings.
        assert abs(left - node.bounds[0]) <= 2.5, (owner, left, node.bounds)
        assert node.bounds[2] - 4.5 <= right - left <= node.bounds[2] + 1.5, (owner, right - left, node.bounds)
        # The capitals share the baseline of the unmarked text, whatever their run size (a line of only small runs too);
        # the offset of that baseline from Layout's own is the adapter's, identical with and without runs.
        assert abs((bottom - node.baseline[1]) - (plain_bottom - plain.baseline[1])) <= 1.5, (owner, bottom, plain_bottom)
