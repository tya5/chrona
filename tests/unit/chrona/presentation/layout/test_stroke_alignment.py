from decimal import Decimal
from types import MappingProxyType, SimpleNamespace

import pytest

from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.stroke_alignment import complete_aligned_strokes, complete_stroke_clip
from chrona.presentation.layout.surface_quality import MarkPlacement, PathCommand


def contour():
    return (PathCommand("move", ((0, 0),)), PathCommand("line", ((20, 0),)),
            PathCommand("quadratic", ((20, 10), (10, 10))),
            PathCommand("line", ((0, 0),)))


@pytest.mark.parametrize("alignment", ["inside", "outside"])
def test_layout_completes_physical_width_and_exact_unscaled_contour(alignment):
    outline = contour()
    clip = complete_stroke_clip(alignment=alignment, bounds=(0, 0, 20, 10), outline=outline, stroke_width=3)
    assert clip.outline is outline
    assert clip.stroke_width == 6
    assert clip.outside == (alignment == "outside")
    assert clip.region == (-12, -12, 44, 34)


def test_native_rect_keeps_its_native_contour_and_center_is_exact_noop():
    assert complete_stroke_clip(alignment="center", bounds=(0, 0, 0, 0), stroke_width=0) is None
    clip = complete_stroke_clip(alignment="inside", bounds=(1, 2, 20, 8), stroke_width=1, rectangle=True)
    assert clip.outline == ()


@pytest.mark.parametrize("outline", [(), contour()[:-1], (
    PathCommand("move", ((0, 0),)), PathCommand("line", ((10, 10),)),
    PathCommand("line", ((20, 20),)), PathCommand("line", ((0, 0),)),
)])
def test_open_and_degenerate_contours_are_refused(outline):
    with pytest.raises(LayoutError, match="E_LAYOUT_STROKE_ALIGNMENT_INVALID"):
        complete_stroke_clip(alignment="inside", bounds=(0, 0, 20, 10), outline=outline, stroke_width=1)


def test_compound_curves_and_holes_are_not_flattened_or_reoriented():
    outer = contour()
    # A closed triangular hole with opposite winding, separate from the curved outer path.
    inner = (PathCommand("move", ((2, 1),)), PathCommand("line", ((2, 3),)),
             PathCommand("line", ((4, 1),)), PathCommand("line", ((2, 1),)))
    clip = complete_stroke_clip(alignment="outside", bounds=(0, 0, 20, 10), outline=outer + inner, stroke_width=1)
    assert clip.outline == outer + inner


class Tokens:
    def __init__(self, alignment="inside", *, pattern=None):
        self.alignment, self.pattern = alignment, pattern

    def optional_choice(self, role, prop, allowed):
        return self.alignment if prop == "strokeAlign" else None

    def optional_number(self, role, prop):
        return Decimal(1) if prop == "strokeWidth" else None

    def optional_color(self, role, prop):
        return "#000000"

    def optional_pattern(self, role):
        return self.pattern

    def has_role(self, role):
        return False


def test_exact_lane_and_multipart_primitive_ids_are_completed_by_layout():
    mark = MarkPlacement("planned:a", "a", Rect(Decimal(0), Decimal(0), Decimal(20), Decimal(10)),
                         (0, 5), (20, 5), mark_shape="point", symbol_parts=(
                             SymbolPartPlacement(contour(), paint_mode="fill"),
                             SymbolPartPlacement(contour(), paint_mode="stroke", stroke_width=2),
                         ))
    emission = SimpleNamespace(placement_type="mark", placement_id="planned:a", facets=(
        SimpleNamespace(primitive_id="lane:a:fill", part_index=0),
        SimpleNamespace(primitive_id="lane:a:stroke", part_index=1),
    ))
    strokes = complete_aligned_strokes((mark,), (), (emission,), Tokens())
    assert [item.primitive_id for item in strokes] == ["lane:a:stroke"]
    assert strokes[0].clip.stroke_width == 4
    assert complete_aligned_strokes((mark,), (), (emission,), Tokens("center")) == ()
    outlined = complete_aligned_strokes((mark,), (), (emission,), Tokens(pattern=MappingProxyType({"kind": "outline"})))
    assert [item.primitive_id for item in outlined] == ["lane:a:fill", "lane:a:stroke"]
    assert [item.clip.stroke_width for item in outlined] == [2, 2]
