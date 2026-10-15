from dataclasses import replace
from decimal import Decimal

import pytest

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_marks import complete_progress_shape
from chrona.presentation.layout.mark_geometry import SymbolPartPlacement
from chrona.presentation.layout.surface_quality import MarkPlacement, PathCommand


def _rect(left, top, right, bottom):
    points = ((left, top), (right, top), (right, bottom), (left, bottom), (left, top))
    return (PathCommand("move", (points[0],)),
            *(PathCommand("line", (point,)) for point in points[1:]))


def _bounds(left=0, top=0, width=10, height=10):
    return Rect(*(Decimal(str(value)) for value in (left, top, width, height)))


def _point(parts, bounds=None):
    return MarkPlacement("actual:gate:gate", "gate", bounds or _bounds(),
                         (5, 5), (5, 5), mark_shape="point", semantic_id="actual",
                         slot_id="timeline", symbol_parts=parts)


def _filled_parts():
    # The interiors overlap; declaration order must not affect the union.
    return (SymbolPartPlacement(_rect(1, 2, 7, 8), "fill"),
            SymbolPartPlacement(_rect(5, 1, 9, 9), "fill"))


def _extent(commands):
    points = tuple(point for command in commands for point in command.points)
    return (min(x for x, _ in points), min(y for _, y in points),
            max(x for x, _ in points), max(y for _, y in points))


@pytest.mark.parametrize(("fraction", "expected_right"), [(0.6, 6.0), (1.0, 9.0)])
def test_multipart_point_progress_is_clipped_to_union_of_filled_parts(fraction, expected_right):
    mark = _point(_filled_parts())
    progress = complete_progress_shape(mark, original_host=mark, fraction=fraction,
                                       inset_ratio=Decimal(0), radius_ratio=Decimal(0))
    assert progress is not None
    assert progress.kind == "Symbol" and progress.path_commands
    assert progress.clip_host_id is None
    assert progress.host_placement_id == mark.placement_id
    left, top, right, bottom = _extent(progress.path_commands)
    assert left == pytest.approx(1.0) and top == pytest.approx(1.0)
    assert right == pytest.approx(expected_right) and bottom == pytest.approx(9.0)


def test_multipart_point_fill_union_is_independent_of_part_order_and_zero_omits():
    first = _point(_filled_parts())
    second = _point(tuple(reversed(_filled_parts())))
    a = complete_progress_shape(first, original_host=first, fraction=0.6,
                                inset_ratio=Decimal(0), radius_ratio=Decimal(0))
    b = complete_progress_shape(second, original_host=second, fraction=0.6,
                                inset_ratio=Decimal(0), radius_ratio=Decimal(0))
    assert a is not None and b is not None and a.path_commands == b.path_commands
    assert complete_progress_shape(first, original_host=first, fraction=0,
                                   inset_ratio=Decimal(0), radius_ratio=Decimal(0)) is None


def test_multipart_progress_uses_original_fraction_before_visible_window_clip():
    original = _point(_filled_parts())
    # A window-clipped visible point has already-completed part contours and a
    # narrower visible bounds; the fraction remains measured on the original.
    visible_parts = (SymbolPartPlacement(_rect(1, 2, 6, 8), "fill"),
                    SymbolPartPlacement(_rect(5, 1, 6, 9), "fill"))
    visible = replace(original, bounds=_bounds(width=6), symbol_parts=visible_parts)
    progress = complete_progress_shape(visible, original_host=original, fraction=0.8,
                                       inset_ratio=Decimal(0), radius_ratio=Decimal(0))
    assert progress is not None
    assert _extent(progress.path_commands)[2] == 6.0
    assert progress.host_placement_id == visible.placement_id


def test_stroke_only_point_glyph_has_no_fillable_progress_submark():
    mark = _point((SymbolPartPlacement(_rect(1, 1, 9, 9), "stroke"),))
    assert complete_progress_shape(mark, original_host=mark, fraction=0.6,
                                   inset_ratio=Decimal(0), radius_ratio=Decimal(0)) is None
