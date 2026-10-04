"""SVG serialization of the viewer-fit facts of a box role (#1050), on a hand-built Scene.

The fallback face a viewer substitutes cannot be created in a test, so the rule is checked at the Scene/SVG boundary:
a text whose Layout-measured widths are far from any real face's (a metrics-bypassing stand-in) must be written with
exactly those widths. How a browser or resvg then draws them is the measured evidence recorded in the work record.
"""
from __future__ import annotations

import re
from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.layout.surface_quality import TextFit
from chrona.presentation.renderers.v05_svg import V05SvgRenderer, render_v05_svg
from chrona.presentation.scene.model import ScenePaint, ScenePrimitive, SceneSurface, SurfaceScaleManifest, TextLayout
from chrona.presentation.scene.viewer_fit import viewer_fit_fallbacks

BOX = "annotation-box:n"
PAINT = ScenePaint("#EEF2F7", None, None, (), 1)
TEXT_PAINT = ScenePaint("#101828", None, None, (), 1)


def _surface(*, lines=("Launch window 22 Oct", "missing it means Q1"), fit=None, box_fit="raw", scale=1.0,
             box_paint=PAINT, origin=30.0, extra=()):
    scene_scale = SurfaceScaleManifest("s", "primary", date(2026, 1, 1), date(2026, 1, 2), 0, 10, 0, 10)
    layout = TextLayout((origin, 20, 90, 14 * len(lines)), (origin, 30), tuple(lines), "Noto Sans, sans-serif", 400, 12,
                        1.2, "sha256:test", horizontal_scale=scale, fit=fit)
    text = ScenePrimitive("annotation-text:n", "Text", "n", "annotation", "annotation-text", "annotation-note-text",
                          (origin, 20, 90, 14 * len(lines)), text=" ".join(lines), baseline=(origin, 30),
                          text_layout=layout, paint=TEXT_PAINT, paint_order=11, contrast_treatment="required")
    box = ScenePrimitive(BOX, "Rect", "n", "annotation", "annotation-box", "annotation-note-box",
                         (20, 10, 300, 40), paint=box_paint, paint_order=10, viewer_fit=box_fit)
    return SceneSurface("s", (), (), (), scene_scale, (box, text, *extra), ScenePaint("#ffffff", None, None, (), 1),
                        canvas_bounds=(0, 0, 400, 100))


def _follow(sizes=(17.5, 9.25), adjust="spacing"):
    return TextFit("text-follows-box", adjust, sizes)


def test_raw_writes_no_fit_attribute_and_the_off_switch_is_the_raw_serialization():
    raw = render_v05_svg(_surface())
    assert "textLength" not in raw and "lengthAdjust" not in raw and "filter" not in raw and "xml:space" not in raw
    fitted = _surface(fit=_follow(), box_fit="text-follows-box")
    assert render_v05_svg(fitted, viewer_fit=False) == raw
    assert V05SvgRenderer(viewer_fit=False).render(fitted).content.decode() == raw
    assert "textLength" in V05SvgRenderer().render(fitted).content.decode()


def test_every_line_is_pinned_to_the_width_the_scene_claims_even_a_width_no_face_has():
    svg = render_v05_svg(_surface(fit=_follow(), box_fit="text-follows-box"))
    tspans = re.findall(r"<tspan [^>]*>", svg)
    assert [re.search(r'textLength="([^"]+)"', item).group(1) for item in tspans] == ["17.5", "9.25"]
    assert all('lengthAdjust="spacing"' in item for item in tspans)
    assert re.search(r"<text [^>]*textLength", svg) is None  # several lines: on each line, never on the run


def test_a_single_line_carries_the_length_on_the_text_and_the_declared_adjust():
    for adjust in ("spacing", "spacingAndGlyphs"):
        svg = render_v05_svg(_surface(lines=("Only one line",), fit=_follow((41.125,), adjust),
                                      box_fit="text-follows-box"))
        text = re.search(r"<text [^>]*>", svg).group(0)
        assert 'textLength="41.125"' in text and f'lengthAdjust="{adjust}"' in text
        assert "<tspan" not in svg


def test_the_length_is_in_the_pre_transform_frame_so_a_compression_divides_it():
    svg = render_v05_svg(_surface(lines=("Squeezed",), fit=_follow((60.0,)), scale=0.75, box_fit="text-follows-box"))
    text = re.search(r"<text [^>]*>", svg).group(0)
    assert 'textLength="80"' in text and "matrix(0.75 0 0 1 " in text


def test_a_box_that_follows_its_text_has_no_static_rect_and_one_filter_group():
    fit = TextFit("box-follows-text", box_id=BOX, end_pad_spaces=3)
    svg = render_v05_svg(_surface(fit=fit, box_fit="box-follows-text"))
    assert f'<rect data-scene-id="{BOX}"' not in svg  # no static background rect
    assert re.findall(r'<filter id="(fit-[0-9a-f]{12})" x="0" y="0" width="1" height="1">', svg)
    filter_id = re.search(r'<filter id="(fit-[0-9a-f]{12})"', svg).group(1)
    assert 'filterUnits' not in svg.split("<filter", 1)[1].split(">", 1)[0]  # object bounding box, the default
    assert '<feFlood flood-color="#EEF2F7" flood-opacity="1" result="bg"/>' in svg
    group = re.search(r"<g [^>]*data-viewer-fit=\"box-follows-text\"[^>]*>", svg).group(0)
    assert f'filter="url(#{filter_id})"' in group and f'data-scene-id="{BOX}"' in group
    # the invisible rect pins the start (box start to the text start), top and bottom (the box block extent)
    assert f'<rect data-scene-id="{BOX}-extent" x="20" y="10" width="10" height="40" fill="none"/>' in svg
    body = svg.split("</g>", 1)[0]
    assert 'xml:space="preserve"' in body
    lines = re.findall(r">([^<>]*?)</tspan>", body)
    assert lines == ["Launch window 22 Oct   ", "missing it means Q1   "]  # every line ends with the end inset
    assert "textLength" not in svg


def test_a_single_line_box_that_follows_its_text_pads_the_text_run():
    svg = render_v05_svg(_surface(lines=("One",), fit=TextFit("box-follows-text", box_id=BOX, end_pad_spaces=2),
                                  box_fit="box-follows-text"))
    assert ">One  </text>" in svg and 'xml:space="preserve"' in svg


def test_a_box_without_a_start_inset_still_gets_a_positive_extent_rect():
    svg = render_v05_svg(_surface(origin=20.0, fit=TextFit("box-follows-text", box_id=BOX), box_fit="box-follows-text"))
    assert f'<rect data-scene-id="{BOX}-extent" x="20" y="10" width="1" height="40" fill="none"/>' in svg


def test_a_transparent_box_that_follows_its_text_writes_no_flood():
    svg = render_v05_svg(_surface(fit=TextFit("box-follows-text", box_id=BOX), box_fit="box-follows-text",
                                  box_paint=ScenePaint(None, None, None, (), 1)))
    assert "<filter" not in svg and "filter=" not in svg and f'data-scene-id="{BOX}-extent"' in svg


def test_the_flood_carries_the_box_opacity_and_one_filter_serves_every_box_of_one_fill():
    paint = ScenePaint("#EEF2F7", None, None, (), 0.5)
    svg = render_v05_svg(_surface(fit=TextFit("box-follows-text", box_id=BOX), box_fit="box-follows-text",
                                  box_paint=paint))
    assert 'flood-opacity="0.5"' in svg and svg.count("<filter ") == 1


def test_the_off_switch_draws_a_box_that_follows_its_text_as_the_ordinary_rect_and_text():
    surface = _surface(fit=TextFit("box-follows-text", box_id=BOX, end_pad_spaces=4), box_fit="box-follows-text")
    svg = render_v05_svg(surface, viewer_fit=False)
    assert f'<rect data-scene-id="{BOX}"' in svg and "<g " not in svg and "filter" not in svg
    assert svg == render_v05_svg(_surface())  # the raw serialization


def test_a_scene_whose_box_and_text_do_not_name_each_other_is_refused():
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        _surface(fit=TextFit("box-follows-text", box_id="annotation-box:other"), box_fit="box-follows-text")
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        _surface(fit=TextFit("box-follows-text", box_id=BOX), box_fit="raw")
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        _surface(fit=None, box_fit="box-follows-text")


def test_a_text_fit_must_match_its_lines_and_be_positive():
    with pytest.raises(ValueError, match="E_PRESENTATION_TEXT_LAYOUT_INVALID"):
        _surface(fit=_follow((17.5,)), box_fit="text-follows-box")  # two lines, one width
    with pytest.raises(ValueError, match="E_PRESENTATION_TEXT_LAYOUT_INVALID"):
        TextFit("text-follows-box", "spacing", (0.0,))
    with pytest.raises(ValueError, match="E_PRESENTATION_TEXT_LAYOUT_INVALID"):
        TextFit("text-follows-box", "justify", (3.0,))
    with pytest.raises(ValueError, match="E_PRESENTATION_TEXT_LAYOUT_INVALID"):
        TextFit("box-follows-text", box_id=BOX, end_pad_spaces=-1)
    with pytest.raises(ValueError, match="E_PRESENTATION_TEXT_LAYOUT_INVALID"):
        TextFit("box-follows-text", line_inline_sizes=(3.0,), box_id=BOX)
    with pytest.raises(ValueError, match="E_PRESENTATION_TEXT_LAYOUT_INVALID"):
        TextFit("raw")


def test_a_box_that_follows_its_text_must_be_a_plain_rect():
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        ScenePrimitive("t", "Text", "n", "annotation", "annotation-text", "annotation-note-text", (0, 0, 1, 1),
                       viewer_fit="text-follows-box")
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        ScenePrimitive("b", "Rect", "n", "annotation", "annotation-box", "annotation-note-box", (0, 0, 1, 1),
                       viewer_fit="sideways")
    with pytest.raises(ValueError, match="E_PRESENTATION_PRIMITIVE_INVALID"):
        ScenePrimitive("b", "Rect", "n", "annotation", "annotation-box", "annotation-note-box", (0, 0, 1, 1),
                       clip_source_id="x", viewer_fit="box-follows-text")


def test_a_target_that_cannot_honour_a_mode_names_the_box_role():
    surface = _surface(fit=_follow(), box_fit="text-follows-box")
    assert viewer_fit_fallbacks(surface, "typst") == ("W_VIEWER_FIT_NOT_HONOURED:annotation-note-box:typst",
                                                      "W_VIEWER_FIT_NOT_HONOURED:annotation-note-text:typst")
    assert viewer_fit_fallbacks(surface, "tikz")[0] == "W_VIEWER_FIT_NOT_HONOURED:annotation-note-box:tikz"
    assert viewer_fit_fallbacks(surface, "svg") == () and viewer_fit_fallbacks(surface, "png") == ()
    assert viewer_fit_fallbacks(surface, "pdf") == ()
    assert viewer_fit_fallbacks(_surface(), "typst") == ()


def test_a_text_run_that_carries_a_fit_without_a_box_member_also_names_its_role_for_a_typeset_target():
    """#1096: a legend, cell or chip label has `fit` on the text and no `viewerFit` on any box."""
    surface = _surface(fit=_follow())
    assert all(item.viewer_fit == "raw" for item in surface.primitives)
    assert viewer_fit_fallbacks(surface, "typst") == ("W_VIEWER_FIT_NOT_HONOURED:annotation-note-text:typst",)
    assert viewer_fit_fallbacks(surface, "svg") == ()
