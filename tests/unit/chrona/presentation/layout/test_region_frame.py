"""Completed region frames: bounds, gutter, omission, corner reduction, order (#889).

Synthetic decisions and a stub Theme only: nothing here reads `examples/`.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutDecision, LayoutError, Rect, RegionFrame
from chrona.presentation.layout.region_frame import (
    REGION_FRAME_ROLE, complete_region_frames, region_frame_placement_id, region_frame_slot_id,
)

D = Decimal
CATALOG = {"kind": "catalog", "ref": "local:dots", "tile": {"inlineSize": 8, "blockSize": 8}, "angle": 0,
           "densityBasisPoints": 1000, "primitives": [{"kind": "path", "paint": "stroke", "strokeWidth": 1, "lineCap": "round",
                                                       "lineJoin": "round", "commands": [
                                                           {"kind": "move", "points": [0, 0]}, {"kind": "line", "points": [4, 4]}]}]}


class Tokens:
    """The four reads Layout makes of the `region-frame` role."""

    def __init__(self, *, role: bool = True, stroke: str | None = "#111111", width: str | None = "3",
                 radius: str | None = None, pattern: dict | None = None) -> None:
        self.role, self.stroke, self.width, self.radius, self.pattern = role, stroke, width, radius, pattern

    def has_role(self, name: str) -> bool:
        return self.role and name == REGION_FRAME_ROLE

    def optional_color(self, role: str, prop: str) -> str | None:
        return self.stroke if prop == "stroke" else None

    def optional_number(self, role: str, prop: str) -> Decimal | None:
        value = {"strokeWidth": self.width, "frameCornerRadius": self.radius}[prop]
        return None if value is None else D(value)

    def optional_pattern(self, role: str) -> dict | None:
        return self.pattern


def decision(node_id: str, rect: tuple, *, inset: str = "0", populated: bool = True, kind: str = "row") -> LayoutDecision:
    return LayoutDecision(node_id, kind, Rect(*(D(item) for item in rect)), frame=RegionFrame(D(inset), populated))


def only(frames):
    assert len(frames.shapes) == 1
    return frames.shapes[0]


def test_a_theme_without_the_role_or_a_profile_without_frames_completes_nothing() -> None:
    framed = (decision("a", (0, 0, 100, 100)),)
    plain = (LayoutDecision("a", "row", Rect(D(0), D(0), D(100), D(100))),)

    assert complete_region_frames(Tokens(role=False), framed) == complete_region_frames(Tokens(), plain)
    assert complete_region_frames(Tokens(role=False), framed).shapes == ()
    assert complete_region_frames(Tokens(role=False), framed).diagnostics == ()
    assert complete_region_frames(Tokens(), plain).slots == ()


@pytest.mark.parametrize(("inset", "stroke", "width", "expected"), [
    ("0", "#111111", "3", (D("101.5"), D("51.5"), D("397"), D("197"))),
    ("4", "#111111", "3", (D("105.5"), D("55.5"), D("389"), D("189"))),
    ("4", None, "3", (D(104), D(54), D(392), D(192))),
    ("0", None, None, (D(100), D(50), D(400), D(200))),
    ("2.5", "#111111", "1", (D(103), D(53), D(394), D(194))),
])
def test_the_frame_is_the_node_deflated_by_inset_and_half_the_stroke(inset, stroke, width, expected) -> None:
    frames = complete_region_frames(Tokens(stroke=stroke, width=width), (decision("a", (100, 50, 400, 200), inset=inset),))

    assert (lambda r: (r.inline, r.block, r.inline_size, r.block_size))(only(frames).bounds) == expected


def test_the_outer_edge_of_the_stroke_stands_the_inset_inside_the_node() -> None:
    node = Rect(D(100), D(50), D(400), D(200))
    frame = only(complete_region_frames(Tokens(width="6"), (decision("a", (100, 50, 400, 200), inset="5"),)))

    half = D(3)
    assert frame.bounds.inline - half == node.inline + 5
    assert frame.bounds.inline + frame.bounds.inline_size + half == node.inline + node.inline_size - 5
    assert frame.bounds.block - half == node.block + 5
    assert frame.bounds.block + frame.bounds.block_size + half == node.block + node.block_size - 5


def test_the_gutter_between_two_panels_is_the_parent_gap_plus_the_two_insets() -> None:
    gap, inset, width = D(16), D(2), D(4)
    left = decision("left", (0, 0, 392, 100), inset=str(inset))
    right = decision("right", (392 + 16, 0, 392, 100), inset=str(inset))

    first, second = complete_region_frames(Tokens(width=str(width)), (left, right)).shapes
    outer_right = first.bounds.inline + first.bounds.inline_size + width / 2
    outer_left = second.bounds.inline - width / 2
    assert outer_left - outer_right == gap + 2 * inset
    # The rectangles themselves (the stroke centre lines) stand a half stroke further apart on each side.
    assert second.bounds.inline - (first.bounds.inline + first.bounds.inline_size) == gap + 2 * (inset + width / 2)


def test_regions_that_do_not_tile_leave_the_rest_as_canvas() -> None:
    # Two nodes with a free strip between them and free margins around them, and a third inside the first.
    nodes = (decision("a", (20, 20, 200, 100)), decision("b", (300, 20, 100, 100)), decision("inner", (40, 40, 60, 40), kind="slot"))

    shapes = complete_region_frames(Tokens(width="2"), nodes).shapes

    assert [item.placement_id for item in shapes] == ["region-frame:a", "region-frame:b", "region-frame:inner"]
    union = [(item.bounds.inline, item.bounds.inline + item.bounds.inline_size) for item in shapes[:2]]
    assert union == [(D(21), D(219)), (D(301), D(399))]
    # Nothing is drawn in the strip between a and b, nor before the first or after the last.
    assert not any(start < D(250) < end for start, end in union) and union[0][0] > 0


def test_frames_keep_the_profile_pre_order_and_a_child_follows_its_parent() -> None:
    nodes = (decision("page", (0, 0, 500, 500)), decision("panel", (10, 10, 200, 200)), decision("slot", (20, 20, 50, 50), kind="slot"),
             decision("late", (300, 10, 100, 100)))

    frames = complete_region_frames(Tokens(), nodes)

    assert [item.placement_id for item in frames.shapes] == [region_frame_placement_id(n) for n in ("page", "panel", "slot", "late")]
    assert [item.slot_id for item in frames.shapes] == [region_frame_slot_id(n) for n in ("page", "panel", "slot", "late")]
    assert {item.placement_id: item.bounds for item in frames.shapes}["region-frame:panel"].inline == D("11.5")


def test_each_frame_is_an_ordinary_rect_owned_by_its_own_pseudo_slot_at_paint_order_zero() -> None:
    frames = complete_region_frames(Tokens(), (decision("a", (0, 0, 100, 60)),))
    shape, slot = only(frames), frames.slots[0]

    assert (shape.kind, shape.paint_order, shape.semantic_id, shape.slot_id) == ("Rect", 0, "regionFrame", "frame:a")
    assert shape.source_ref == "layout-node:a" and shape.corner_radius == 0
    assert (slot.slot_id, slot.source_ref, slot.bounds) == ("frame:a", "frame:a", shape.bounds)


def test_a_panel_with_no_slot_beneath_it_is_omitted_and_recorded() -> None:
    frames = complete_region_frames(Tokens(), (decision("empty", (0, 0, 100, 100), populated=False),
                                               decision("full", (0, 0, 100, 100))))

    assert [item.placement_id for item in frames.shapes] == ["region-frame:full"]
    assert frames.diagnostics == ("I_LAYOUT_REGION_FRAME_OMITTED:empty:no-content",)


@pytest.mark.parametrize("rect", [(0, 0, 4, 100), (0, 0, 100, 4), (0, 0, 3, 3), (0, 0, 0, 0)])
def test_a_panel_the_stroke_and_inset_consume_is_omitted_and_recorded(rect) -> None:
    frames = complete_region_frames(Tokens(width="4"), (decision("thin", rect),))

    assert frames.shapes == () and frames.slots == ()
    assert frames.diagnostics == ("I_LAYOUT_REGION_FRAME_OMITTED:thin:too-small",)


def test_a_panel_just_larger_than_what_the_stroke_consumes_is_drawn() -> None:
    frames = complete_region_frames(Tokens(width="4"), (decision("thin", (0, 0, D("4.5"), 100)),))

    assert only(frames).bounds.inline_size == D("0.5") and frames.diagnostics == ()


def test_a_corner_radius_is_a_pixel_value_reduced_to_half_the_shorter_side_with_a_record() -> None:
    fits = complete_region_frames(Tokens(width=None, stroke=None, radius="10"), (decision("a", (0, 0, 100, 40)),))
    reduced = complete_region_frames(Tokens(width=None, stroke=None, radius="30"), (decision("a", (0, 0, 100, 40)),))
    exact = complete_region_frames(Tokens(width=None, stroke=None, radius="20"), (decision("a", (0, 0, 100, 40)),))

    assert (only(fits).corner_radius, fits.diagnostics) == (10.0, ())
    assert (only(reduced).corner_radius, reduced.diagnostics) == (20.0, ("W_LAYOUT_REGION_FRAME_CORNER_REDUCED:a",))
    assert (only(exact).corner_radius, exact.diagnostics) == (20.0, ())


def test_a_radius_is_reduced_against_the_deflated_rect_not_the_node() -> None:
    frames = complete_region_frames(Tokens(width="4", radius="19"), (decision("a", (0, 0, 100, 44), inset="0"),))

    assert only(frames).corner_radius == 19.0 and frames.diagnostics == ()
    tighter = complete_region_frames(Tokens(width="4", radius="19"), (decision("a", (0, 0, 100, 44), inset="2"),))
    assert only(tighter).corner_radius == 18.0 and tighter.diagnostics == ("W_LAYOUT_REGION_FRAME_CORNER_REDUCED:a",)


def test_a_negative_radius_fails_at_its_exact_theme_pointer() -> None:
    with pytest.raises(LayoutError) as error:
        complete_region_frames(Tokens(radius="-1"), (decision("a", (0, 0, 100, 40)),))

    assert (error.value.diagnostic_id, error.value.path) == ("E_THEME_TOKEN_TYPE", "/body/roles/region-frame/frameCornerRadius")


def test_a_catalogue_pattern_is_placed_in_the_frame_and_an_inline_pattern_is_not() -> None:
    placed = complete_region_frames(Tokens(pattern=CATALOG), (decision("a", (0, 0, 100, 60)),))
    inline = complete_region_frames(Tokens(pattern={"kind": "diagonal-hatch"}), (decision("a", (0, 0, 100, 60)),))

    assert [item.placement_id for item in placed.patterns] == ["region-frame:a"]
    assert inline.patterns == () and len(inline.shapes) == 1


def test_the_extent_a_frame_paints_in_includes_its_whole_stroke_and_stops_at_the_inset() -> None:
    frames = complete_region_frames(Tokens(width="6"), (decision("a", (100, 50, 400, 200), inset="5"),))

    extent = frames.extents[0]
    assert (extent.inline, extent.block, extent.inline_size, extent.block_size) == (D(105), D(55), D(390), D(190))
    flat = complete_region_frames(Tokens(stroke=None), (decision("a", (100, 50, 400, 200), inset="5"),))
    assert flat.extents[0] == flat.shapes[0].bounds
