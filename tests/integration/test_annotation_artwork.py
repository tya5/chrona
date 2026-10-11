"""#848: vector artwork behind an annotation container, end to end.

A Project with notes goes through the packaged `executive-light` bundle and the packaged `chrona-target-parts`
catalogue (`scroll-frame`, `clipping-edge`) with a Theme whose note box declares `annotationContainer.artwork`.
Synthetic Projects only; no `examples/` input.
"""
from __future__ import annotations

from math import atan2, degrees

import pytest

from chrona.presentation.scene.contrast_policy import evaluate_scene_contrast
from chrona.presentation.scene.serialization import scene_document
from tests.support import annotation_artwork as aw
from tests.support import annotation_kinds as ak
from tests.support import synthetic_review as sr

TEXT = 14  # the note text size of the fixture Theme
INSET = aw.CONTENT_INSET
SCROLL_PARTS = 6


def _render(tmp_path, *, source=None, mutate=None, notes=None, profile="chrona-output/visual/v0.6-svg",
            catalogs=None, kinds=None, **artwork):
    source = source or ak.project(("risk", "note"), text="A hanging scroll holds this note and its words.")
    parts = sr.bundle()
    ak.with_view_notes(parts, source)
    if kinds is not None:
        ak.with_kind_theme(parts, **kinds)
    aw.with_artwork(parts, **artwork)
    if mutate is not None:
        mutate(parts)
    return ak.render(tmp_path, source, parts, visual_profile=profile, **({"catalogs": catalogs} if catalogs is not None else {}))


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def _by_id(rendered):
    return {item.scene_id: item for item in rendered.surface.primitives}


def _order(rendered):
    return [item.scene_id for item in rendered.surface.primitives]


def _points(primitive):
    return [point for command in primitive.symbol.outline for point in command.points]


def _extent(primitives):
    points = [point for primitive in primitives for point in _points(primitive)]
    return (min(p[0] for p in points), min(p[1] for p in points), max(p[0] for p in points), max(p[1] for p in points))


# --- defaults ----------------------------------------------------------------------------------------------------

def test_a_container_without_artwork_renders_exactly_as_without_the_role(tmp_path):
    plain = _render(_sub(tmp_path, "plain"), artwork_declared=False, role=False)
    with_role = _render(_sub(tmp_path, "role"), artwork_declared=False, role=True)
    assert list(with_role.surface.primitives) == list(plain.surface.primitives)
    assert with_role.artifact.content == plain.artifact.content
    assert not [item for item in plain.surface.primitives if "artwork" in item.scene_id]


def test_the_artwork_adds_primitives_and_changes_nothing_else(tmp_path):
    plain = _render(_sub(tmp_path, "plain"), artwork_declared=False)
    drawn = _render(_sub(tmp_path, "drawn"))
    rest = [item for item in drawn.surface.primitives if not item.scene_id.startswith("annotation-artwork:")]
    assert rest == list(plain.surface.primitives)
    assert len(aw.artwork_parts(drawn, "view-n0")) == SCROLL_PARTS


# --- the parts, their paint and their order --------------------------------------------------------------------

def test_each_glyph_part_is_a_symbol_painted_from_the_ink_role_by_its_own_mode(tmp_path):
    rendered = _render(tmp_path)
    parts = aw.artwork_parts(rendered)
    assert [item.scene_id for item in parts] == [f"annotation-artwork:view-n0:part{index}" for index in range(SCROLL_PARTS)]
    assert all(item.kind == "Symbol" and item.visual_role == "annotation-artwork" and item.source_ref == "view-n0"
               for item in parts)
    stroked = [item for item in parts if item.paint.stroke is not None]
    filled = [item for item in parts if item.paint.fill is not None]
    assert len(stroked) == 1 and len(filled) == SCROLL_PARTS - 1          # the hanger cord is the one stroked part
    assert stroked[0].paint.fill is None and stroked[0].paint.stroke_width and stroked[0].paint.stroke_width > 0
    assert all(item.paint.stroke is None for item in filled)
    assert {item.paint.fill for item in filled} == {stroked[0].paint.stroke}   # one ink


def test_the_order_is_box_then_artwork_then_kind_frame_then_text(tmp_path):
    rendered = _render(tmp_path, kinds={"bar": True, "stamp": "end-top"})
    order, ids = _order(rendered), _by_id(rendered)
    box, art = order.index("annotation-box:view-n0"), order.index("annotation-artwork:view-n0:part0")
    bar, stamp = order.index("annotation-kind-bar:view-n0"), order.index("annotation-kind-stamp:view-n0:part0")
    header, body = order.index("annotation-kind-text:view-n0:0"), order.index("annotation-text:view-n0")
    assert box < art < bar < stamp < header < body
    assert ids["annotation-box:view-n0"].paint_order == ids["annotation-artwork:view-n0:part5"].paint_order == 400
    assert ids["annotation-text:view-n0"].paint_order > 400 and ids["annotation-kind-text:view-n0:0"].paint_order > 400
    # The artwork parts keep their glyph order among themselves.
    assert [ids[f"annotation-artwork:view-n0:part{i}"].paint_order for i in range(SCROLL_PARTS)] == sorted(
        ids[f"annotation-artwork:view-n0:part{i}"].paint_order for i in range(SCROLL_PARTS))


def test_the_box_keeps_painting_the_paper_under_the_artwork(tmp_path):
    rendered = _render(tmp_path)
    box = _by_id(rendered)["annotation-box:view-n0"]
    assert box.kind == "Rect" and box.paint.fill is not None
    for part in aw.artwork_parts(rendered):
        assert (part.paint.fill or part.paint.stroke) != box.paint.fill


# --- size and inset rules ------------------------------------------------------------------------------------

def test_the_artwork_is_stretched_to_the_paint_box_and_the_text_lies_in_the_content_inset(tmp_path):
    rendered = _render(tmp_path)
    ids = _by_id(rendered)
    bx, by, bw, bh = ids["annotation-box:view-n0"].bounds
    left, top, right, bottom = bx, by, bx + bw, by + bh
    x0, y0, x1, y1 = _extent(aw.artwork_parts(rendered))
    # The rods and the frame reach the box edges; the hanger rises to the box top.
    assert (x0, x1) == pytest.approx((left, right), abs=0.5)
    # (the glyph's own margins: two viewport units at the bottom rod, a little at the hanger)
    assert y1 == pytest.approx(bottom, abs=3.0) and y0 == pytest.approx(top, abs=3.0)
    assert all(part.bounds == ids["annotation-box:view-n0"].bounds for part in aw.artwork_parts(rendered))
    tx, ty, tw, th = ids["annotation-text:view-n0"].bounds
    assert tx >= left + INSET["left"] * TEXT - 1e-6 and tx + tw <= right - INSET["right"] * TEXT + 1e-6
    assert ty >= top + INSET["top"] * TEXT - 1e-6 and ty + th <= bottom - INSET["bottom"] * TEXT + 1e-6


def test_the_artwork_does_not_change_the_box_the_search_uses(tmp_path):
    plain = _render(_sub(tmp_path, "plain"), artwork_declared=False)      # same content inset, no artwork
    drawn = _render(_sub(tmp_path, "drawn"))
    for note in ("view-n0", "view-n1"):
        assert _by_id(drawn)[f"annotation-box:{note}"].bounds == _by_id(plain)[f"annotation-box:{note}"].bounds
        assert _by_id(drawn)[f"annotation-text:{note}"].bounds == _by_id(plain)[f"annotation-text:{note}"].bounds


def test_fixed_borders_keep_their_size_while_the_middle_grows_with_the_text(tmp_path):
    unit = 0.09 * TEXT
    short = _render(_sub(tmp_path, "short"), source=ak.project(("risk",), text="Short."))
    long = _render(_sub(tmp_path, "long"), source=ak.project(("risk",), text="A much longer note with a good many more words in it."))
    widths = []
    for rendered in (short, long):
        box = _by_id(rendered)["annotation-box:view-n0"]
        ring = _by_id(rendered)["annotation-artwork:view-n0:part2"]          # the frame ring: outer edge and a hole
        xs = sorted({round(point[0], 3) for point in _points(ring)})
        # The hole's left edge is 8.2 viewport units in from the ring's outer left edge (4.5): a fixed border.
        outer_left, inner_left = xs[0], xs[1]
        assert inner_left - outer_left == pytest.approx((8.2 - 4.5) * unit, abs=1e-3)
        assert outer_left - box.bounds[0] == pytest.approx(4.5 * unit, abs=1e-3)
        widths.append(box.bounds[2])
    assert widths[1] > widths[0] + 20


def test_a_strip_is_fixed_to_the_top_edge_and_stretched_along_it(tmp_path):
    rendered = _render(tmp_path, glyph=aw.CLIPPING, insets=aw.CLIPPING_TOP, unit_em=0.12,
                       content={"top": 0.9, "right": 0.8, "bottom": 0.8, "left": 0.8})
    (strip,) = aw.artwork_parts(rendered)
    box = _by_id(rendered)["annotation-box:view-n0"]
    x0, y0, x1, y1 = _extent([strip])
    assert (x0, x1) == pytest.approx((box.bounds[0], box.bounds[0] + box.bounds[2]), abs=2.0)  # the ribbon's own margin
    assert y0 >= box.bounds[1] - 1e-6 and y1 <= box.bounds[1] + 8 * 0.12 * TEXT + 1e-6   # within the fixed 8-unit strip


def test_the_unit_scales_the_whole_artwork(tmp_path):
    small = _render(_sub(tmp_path, "small"), unit_em=0.05)
    large = _render(_sub(tmp_path, "large"), unit_em=0.09)
    def left_border(rendered):
        ring = _by_id(rendered)["annotation-artwork:view-n0:part2"]
        xs = sorted({round(point[0], 3) for point in _points(ring)})
        return xs[1] - xs[0]
    assert left_border(large) / left_border(small) == pytest.approx(0.09 / 0.05, rel=1e-3)


# --- tilt, kind frame ------------------------------------------------------------------------------------------

def test_a_tilted_note_carries_its_artwork_rigidly(tmp_path):
    rendered = _render(tmp_path, extra={"tiltDegrees": [4]})
    ids = _by_id(rendered)
    box = ids["annotation-box:view-n0"]
    assert box.kind == "Symbol"                                              # the rotated polygon
    assert {part.scene_id for part in aw.artwork_parts(rendered)} == {
        f"annotation-artwork:view-n0:part{i}" for i in range(SCROLL_PARTS)}
    # The top edge of the frame ring runs at the note's angle.
    ring = ids["annotation-artwork:view-n0:part2"]
    first, second = _points(ring)[0], _points(ring)[1]
    assert degrees(atan2(second[1] - first[1], second[0] - first[0])) == pytest.approx(4.0, abs=1e-3)
    assert ids["annotation-text:view-n0"].text_layout.orientation == "tilt"
    # The artwork is warped into the unrotated frame, not into the larger bounds of the rotated one: it stays inside
    # the rotated box (the polygon) and reaches it to within the glyph's own margins.
    polygon = _extent([box])
    art = _extent(aw.artwork_parts(rendered))
    assert polygon[0] - 0.5 <= art[0] and art[2] <= polygon[2] + 0.5
    assert polygon[1] - 0.5 <= art[1] and art[3] <= polygon[3] + 0.5
    assert art[0] - polygon[0] < 8 and polygon[2] - art[2] < 8
    # Untilted note of the same declaration: same part count, upright edge.
    flat = _render(_sub(tmp_path, "flat"))
    ring0 = _by_id(flat)["annotation-artwork:view-n0:part2"]
    a, b = _points(ring0)[0], _points(ring0)[1]
    assert atan2(b[1] - a[1], b[0] - a[0]) == pytest.approx(0.0, abs=1e-9)


def test_the_kind_bar_and_header_sit_inside_the_artwork_on_a_rectangle(tmp_path):
    rendered = _render(tmp_path, kinds={"bar": True})
    ids = _by_id(rendered)
    box, bar = ids["annotation-box:view-n0"], ids["annotation-kind-bar:view-n0"]
    assert bar.bounds[0] >= box.bounds[0] + INSET["left"] * TEXT - 1e-6
    assert bar.bounds[1] >= box.bounds[1] + INSET["top"] * TEXT - 1e-6
    assert len(aw.artwork_parts(rendered)) == SCROLL_PARTS


# --- declaration errors --------------------------------------------------------------------------------------

def test_a_balloon_cannot_take_artwork(tmp_path):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, outline="balloon")
    assert "E_THEME_TOKEN_TYPE" in str(failure.value) or "E_THEME_SCHEMA" in str(failure.value)


def test_artwork_without_a_content_inset_is_rejected(tmp_path):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, content=None)
    assert "E_THEME_TOKEN_TYPE" in str(failure.value) or "E_THEME_SCHEMA" in str(failure.value)


def test_artwork_without_the_ink_role_is_a_role_required_error(tmp_path):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, role=False)
    assert failure.value.code == "E_THEME_ROLE_REQUIRED" and failure.value.source_ref == "/body/roles/annotation-artwork"


def test_an_unknown_glyph_is_an_asset_reference_error(tmp_path):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, glyph="chrona-target-parts:nope")
    assert "E_THEME_ASSET_REFERENCE" in str(failure.value)


def test_a_glyph_from_an_unpinned_set_is_an_asset_reference_error(tmp_path):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, glyph="elsewhere:scroll-frame")
    assert "E_THEME_ASSET_REFERENCE" in str(failure.value)


@pytest.mark.parametrize("insets", [{"top": 40, "right": 0, "bottom": 30, "left": 0},
                                    {"top": 0, "right": 30, "bottom": 0, "left": 20}])
def test_insets_larger_than_the_glyph_are_a_token_type_error(tmp_path, insets):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, insets=insets)
    assert "E_THEME_TOKEN_TYPE" in str(failure.value)


@pytest.mark.parametrize("change", [{"unitEm": 0}, {"unitEm": -1}, {"unitEm": "x"},
                                    {"sliceInsets": {"top": -1, "right": 0, "bottom": 0, "left": 0}}])
def test_a_malformed_artwork_object_is_rejected_by_the_theme_schema(tmp_path, change):
    def invalid(parts):
        parts["theme"]["body"]["values"]["artwork-container"]["value"]["artwork"].update(change)

    with pytest.raises(Exception) as failure:
        _render(tmp_path, mutate=invalid)
    assert "E_THEME_SCHEMA" in str(failure.value)


# --- profiles --------------------------------------------------------------------------------------------------

BASELINE = "chrona-output/visual/v0.5-baseline"


def test_baseline_fails_a_required_artwork_with_stroked_parts(tmp_path):
    with pytest.raises(Exception) as failure:
        _render(tmp_path, profile=BASELINE)
    assert "E_VISUAL_CAPABILITY_UNSUPPORTED" in str(failure.value)


def test_baseline_omits_the_whole_decorative_optional_artwork_and_reports_it_once(tmp_path):
    omitted = _render(_sub(tmp_path, "omitted"), profile=BASELINE, fidelity="decorative-optional")
    plain = _render(_sub(tmp_path, "plain"), profile=BASELINE, artwork_declared=False)
    assert not aw.artwork_parts(omitted, "view-n0") and not aw.artwork_parts(omitted, "view-n1")
    assert list(omitted.surface.primitives) == list(plain.surface.primitives)    # box and text exactly as with the artwork
    reported = [item for item in omitted.info_diagnostics if getattr(item, "treatment", None) == "annotation-artwork"]
    assert len(reported) == 1 and reported[0].role == "annotation-artwork"
    assert reported[0].visual_profile == BASELINE and reported[0].source_ref == "/body/roles/annotation-artwork/artworkFidelity"


def test_baseline_paints_a_fill_only_glyph_without_any_omission(tmp_path):
    rendered = _render(tmp_path, profile=BASELINE, glyph=aw.CLIPPING, insets=aw.CLIPPING_TOP, unit_em=0.12,
                       content={"top": 0.9, "right": 0.8, "bottom": 0.8, "left": 0.8})
    assert len(aw.artwork_parts(rendered)) == 1
    assert not [item for item in rendered.info_diagnostics if getattr(item, "treatment", None) == "annotation-artwork"]


def test_a_rich_profile_never_omits(tmp_path):
    rendered = _render(tmp_path, fidelity="decorative-optional")
    assert len(aw.artwork_parts(rendered)) == SCROLL_PARTS
    assert not [item for item in rendered.info_diagnostics if getattr(item, "treatment", None) == "annotation-artwork"]


CLIPPING = {"glyph": aw.CLIPPING, "insets": aw.CLIPPING_TOP, "unit_em": 0.12,
            "content": {"top": 0.9, "right": 0.8, "bottom": 0.8, "left": 0.8}}


def test_typst_and_tikz_draw_every_artwork_part_a_filled_or_a_stroked_outline(tmp_path):
    from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst

    scroll = _render(_sub(tmp_path, "scroll"))
    clipping = _render(_sub(tmp_path, "clipping"), **CLIPPING)
    for rendered in (scroll, clipping):
        typst, tikz = render_v05_typst(rendered.surface), render_v05_tikz(rendered.surface)
        assert "annotation-artwork:view-n0:part0" in typst and "annotation-artwork:view-n0:part0" in tikz  # #1308: symbols are drawn
    assert "stroke: (paint: " in render_v05_typst(scroll.surface)   # the scroll's stroked cord has no fill, only a stroke


def test_an_omitted_artwork_leaves_a_scene_typst_still_compiles(tmp_path):
    omitted = _render(_sub(tmp_path, "omitted"), profile=BASELINE, fidelity="decorative-optional")
    from chrona.presentation.renderers.v05_typeset import render_v05_tikz, render_v05_typst

    assert "annotation-artwork" not in render_v05_typst(omitted.surface)
    assert "annotation-artwork" not in render_v05_tikz(omitted.surface)


# --- contrast --------------------------------------------------------------------------------------------------

def _findings(rendered, **options):
    return evaluate_scene_contrast(scene_document(rendered.scene), **options)


def test_the_note_text_is_judged_on_the_paper_not_on_the_frame_around_it(tmp_path):
    rendered = _render(tmp_path)
    prose = [item for item in _findings(rendered) if item.primitive_id == "annotation-text:view-n0"]
    assert [(item.ground_id, item.ground_kind, item.severity) for item in prose] == [
        ("annotation-box:view-n0", "flat", "info")]


def test_every_artwork_part_is_judged_as_decoration_against_the_paper(tmp_path):
    rendered = _render(tmp_path)
    parts = [item for item in _findings(rendered) if item.visual_role == "annotation-artwork"
             and item.primitive_id.startswith("annotation-artwork:view-n0")]
    assert len(parts) == SCROLL_PARTS
    assert {item.ground_id for item in parts} == {"annotation-box:view-n0"}
    assert all(item.severity == "info" and item.severity_class == "decoration" for item in parts)


def test_ink_the_colour_of_the_paper_is_a_decoration_warning_not_a_text_error(tmp_path):
    rendered = _render(tmp_path, ink="surface", ink_stroke="surface")
    parts = [item for item in _findings(rendered) if item.visual_role == "annotation-artwork"
             and item.primitive_id.startswith("annotation-artwork:view-n0")]
    assert parts and all(item.code == "W_SCENE_DECORATION_CONTRAST" and item.severity == "warning" for item in parts)
    blocking = _findings(rendered, decoration_severity="error")
    assert [item for item in blocking if item.severity == "error" and item.visual_role == "annotation-artwork"]


def test_text_that_reaches_the_frame_is_judged_on_the_ink_and_blocks_when_it_vanishes_there(tmp_path):
    # A left content inset smaller than the frame's border puts the text on the ink: dark ink, dark text.
    rendered = _render(tmp_path, content={"top": 1.9, "right": 1.1, "bottom": 1.5, "left": 0.0})
    (prose,) = [item for item in _findings(rendered) if item.primitive_id == "annotation-text:view-n0"]
    assert (prose.code, prose.severity, prose.ground_kind) == ("E_SCENE_STATE_TEXT_CONTRAST", "error", "artwork-ink")
    assert prose.ground_id.startswith("annotation-artwork:view-n0:part")


def test_text_that_reaches_pale_ink_is_legible_on_both_grounds_and_passes(tmp_path):
    rendered = _render(tmp_path, content={"top": 1.9, "right": 1.1, "bottom": 1.5, "left": 0.0}, ink="neutral",
                       ink_stroke="neutral")
    prose = [item for item in _findings(rendered) if item.primitive_id == "annotation-text:view-n0"]
    assert len(prose) == 1 and prose[0].severity == "info"
    assert prose[0].ground_kind == "artwork-ink"


# --- determinism, adapters -------------------------------------------------------------------------------------

def test_rendering_twice_gives_the_same_bytes(tmp_path):
    first = _render(_sub(tmp_path, "a"), extra={"tiltDegrees": [3, -2]})
    second = _render(_sub(tmp_path, "b"), extra={"tiltDegrees": [3, -2]})
    assert first.artifact.content == second.artifact.content


def test_the_svg_draws_every_part_as_a_path_and_the_frame_keeps_its_hole(tmp_path):
    rendered = _render(tmp_path)
    paths = [line for line in rendered.artifact.content.decode("utf-8").splitlines()
             if line.startswith('<path data-scene-id="annotation-artwork:view-n0:part')]
    assert len(paths) == SCROLL_PARTS
    ring = next(line for line in paths if 'part2"' in line)
    assert ring.count("M") == 2 and "fill-rule" not in ring     # outer edge and a hole wound the other way
