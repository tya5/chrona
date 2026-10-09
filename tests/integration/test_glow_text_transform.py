"""Glowing transformed text keeps its completed glyph ink inside the SVG filter region (#1261)."""
from __future__ import annotations

import io
from math import cos, radians, sin
from pathlib import Path
import xml.etree.ElementTree as ET

import resvg_py
from PIL import Image, ImageFont
import pytest

from chrona.presentation.scene.model import Glow, ScenePaint, ScenePrimitive, SceneSurface, TextLayout
from chrona.presentation.renderers.v05_svg import render_v05_svg
from tests.integration.test_heading_frame_glyph_glow import SVG, _presentation, _render


ROOT = Path(__file__).resolve().parents[2]
FONT = ROOT / "src/chrona/resources/fonts/noto-sans-regular-v1.ttf"
FONT_DIR = FONT.parent
TEXT = "MMMMMMMMMM"
CANVAS = (0.0, 0.0, 720.0, 300.0)


def _transformed_parts(scale: float) -> dict:
    parts = _presentation(heading_glow=True, frame_glow=False)
    theme = parts["theme"]["body"]
    theme["values"]["test-kicker-scale"] = {"type": "number", "value": scale}
    theme["roles"]["kicker"]["horizontalScale"] = "test-kicker-scale"
    parts["view"]["body"]["heading"]["kicker"] = "THE PROGRAMME BOARD"
    return parts


def _filter_for_text(svg: bytes, scene_id: str = "kicker"):
    root = ET.fromstring(svg)
    text = next(node for node in root.iter() if node.attrib.get("data-scene-id") == scene_id)
    parents = {child: parent for parent in root.iter() for child in parent}
    return root, text, parents[text]


@pytest.mark.parametrize("scale", [0.5, 0.86, 1.0])
def test_full_pipeline_filter_is_canvas_framed_after_completed_heading_scale(tmp_path, scale):
    review = _render(tmp_path / str(scale), parts=_transformed_parts(scale), profile=SVG)
    item = next(value for value in review.surface.primitives if value.scene_id == "kicker")
    root, text, parent = _filter_for_text(review.artifact.content)
    glow = item.paint.glow
    assert item.text_layout.horizontal_scale == scale
    assert parent.tag.endswith("g") and parent.attrib.get("transform") is None
    assert parent.attrib.get("filter", "").startswith("url(#glow-")
    assert "filter" not in text.attrib
    if scale != 1:
        assert "matrix(" in text.attrib.get("transform", "")

    bx, by, bw, bh = item.bounds
    cx, cy, cw, ch = review.surface.canvas_bounds
    blur = glow.blur
    expected = (max(cx, bx - 3 * blur), max(cy, by - 3 * blur),
                min(cx + cw, bx + bw + 3 * blur) - max(cx, bx - 3 * blur),
                min(cy + ch, by + bh + 3 * blur) - max(cy, by - 3 * blur))
    assert glow.region == pytest.approx(expected)
    filter_id = parent.attrib["filter"][5:-1]
    definition = next(node for node in root.iter()
                      if node.tag.endswith("filter") and node.attrib.get("id") == filter_id)
    assert (float(definition.attrib["x"]), float(definition.attrib["y"]),
            float(definition.attrib["width"]), float(definition.attrib["height"])) == pytest.approx(expected, abs=0.001)


def _direct_text_surface(*, glow: bool, scale: float = 0.86, rotation: float = 0.0):
    font = ImageFont.truetype(str(FONT), 64)
    advance = float(font.getlength(TEXT))
    baseline = (40.0, 92.0)
    width, top, bottom = advance * scale, -68.0, 8.0
    if rotation:
        angle = radians(rotation)
        corners = tuple((baseline[0] + cos(angle) * x - sin(angle) * y,
                         baseline[1] + sin(angle) * x + cos(angle) * y)
                        for x, y in ((0, top), (width, top), (width, bottom), (0, bottom)))
        xs, ys = tuple(point[0] for point in corners), tuple(point[1] for point in corners)
        bounds = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    else:
        bounds = (baseline[0], baseline[1] + top, width, bottom - top)
    blur = 5.0
    extent = (bounds[0] - 3 * blur, bounds[1] - 3 * blur,
              bounds[2] + 6 * blur, bounds[3] + 6 * blur)
    effect = Glow("#FFD24A", blur, 0.9, "required", extent) if glow else None
    layout = TextLayout(bounds, baseline, (TEXT,), "Noto Sans", 400, 64.0,
                        1.0, "sha256:" + "0" * 64, horizontal_scale=scale,
                        rotation_degrees=rotation,
                        orientation="tilt" if rotation else "horizontal")
    primitive = ScenePrimitive("transformed-run", "Text", "fixture", "view", "headingText", "heading",
                               bounds, text=TEXT, baseline=layout.baseline, text_layout=layout,
                               paint=ScenePaint("#111111", None, None, (), 1.0, glow=effect))
    return SceneSurface("synthetic", (), (), (), None, (primitive,),
                        ScenePaint("#FFFFFF", None, None, (), 1.0), canvas_bounds=CANVAS), bounds


def _raster(svg: str) -> Image.Image:
    data = resvg_py.svg_to_bytes(svg_string=svg, dpi=96,
                                 font_dirs=[str(FONT_DIR)], skip_system_fonts=True)
    return Image.open(io.BytesIO(bytes(data))).convert("RGB")


@pytest.mark.parametrize("scale", [0.5, 0.86, 1.0])
def test_scaled_text_filter_preserves_final_packaged_font_glyph_ink(tmp_path, scale):
    glowing_surface, bounds = _direct_text_surface(glow=True, scale=scale, rotation=0.0)
    plain_surface, _ = _direct_text_surface(glow=False, scale=scale, rotation=0.0)
    glowing = render_v05_svg(glowing_surface)
    plain = render_v05_svg(plain_surface)
    glow_pixels, plain_pixels = _raster(glowing), _raster(plain)
    glow_pixels.save(tmp_path / "glowing.png")
    plain_pixels.save(tmp_path / "plain.png")

    # Compare dark SourceGraphic pixels, not the larger gold halo. The last M is in this
    # rightmost portion of the completed run; its far edge must survive the effect.
    final_glyph = (int(bounds[0] + bounds[2] * 0.88), int(bounds[1]),
                   int(bounds[0] + bounds[2]) + 2, int(bounds[1] + bounds[3]))
    dark = lambda pixel: max(pixel) < 100
    glowing_ink = {(x, y) for y in range(final_glyph[1], final_glyph[3])
                   for x in range(final_glyph[0], final_glyph[2]) if dark(glow_pixels.getpixel((x, y)))}
    plain_ink = {(x, y) for y in range(final_glyph[1], final_glyph[3])
                 for x in range(final_glyph[0], final_glyph[2]) if dark(plain_pixels.getpixel((x, y)))}
    assert plain_ink and glowing_ink
    assert max(x for x, _ in glowing_ink) >= max(x for x, _ in plain_ink) - 1
    # Opaque source pixels must all survive, not merely the final bounding-box edge.
    # Filter compositing can change the exact RGB through its linear-RGB conversion.
    opaque_source = {point for point in plain_ink if plain_pixels.getpixel(point) == (17, 17, 17)}
    assert opaque_source and opaque_source <= glowing_ink


def test_rotated_text_uses_untransformed_parent_filter_and_rotated_completed_bounds():
    rotated_surface, bounds = _direct_text_surface(glow=True, scale=0.86, rotation=11.0)
    svg_root = ET.fromstring(render_v05_svg(rotated_surface))
    nodes = {child: parent for parent in svg_root.iter() for child in parent}
    text = next(node for node in svg_root.iter() if node.attrib.get("data-scene-id") == "transformed-run")
    parent = nodes[text]
    assert "rotate(11" in text.attrib.get("transform", "")
    assert parent.tag.endswith("g") and parent.attrib.get("transform") is None
    assert parent.attrib.get("filter", "").startswith("url(#glow-")
    assert "filter" not in text.attrib
    glow = rotated_surface.primitives[0].paint.glow
    bx, by, bw, bh = bounds
    expected = (bx - 3 * glow.blur, by - 3 * glow.blur,
                bw + 6 * glow.blur, bh + 6 * glow.blur)
    filter_id = parent.attrib["filter"][5:-1]
    definition = next(node for node in svg_root.iter()
                      if node.tag.endswith("filter") and node.attrib.get("id") == filter_id)
    assert (float(definition.attrib["x"]), float(definition.attrib["y"]),
            float(definition.attrib["width"]), float(definition.attrib["height"])) == pytest.approx(expected, abs=0.001)
