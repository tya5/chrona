from decimal import Decimal

import pytest

import chrona.presentation.layout.filled_contour as contour
from chrona.presentation.layout.filled_contour import (
    ContourUnionError,
    filled_contours_cover_rectangle,
)
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import PathCommand


def _rect(x, y, right, bottom, *, reverse=False):
    points = ((x, y), (right, y), (right, bottom), (x, bottom))
    if reverse:
        points = tuple(reversed(points))
    return (PathCommand("move", (points[0],)),
            *(PathCommand("line", (point,)) for point in points[1:]),
            PathCommand("line", (points[0],)))


def _box(x, y, width, height):
    return Rect(Decimal(str(x)), Decimal(str(y)),
                Decimal(str(width)), Decimal(str(height)))


def test_exact_rectangle_cover_and_empty_operand_set():
    assert filled_contours_cover_rectangle((_rect(0, 0, 10, 8),), _box(0, 0, 10, 8))
    assert not filled_contours_cover_rectangle((), _box(0, 0, 10, 8))


def test_hole_and_sparse_fill_leave_text_uncovered():
    donut = _rect(0, 0, 10, 10) + _rect(4, 4, 6, 6, reverse=True)
    assert not filled_contours_cover_rectangle((donut,), _box(4, 4, 2, 2))
    assert not filled_contours_cover_rectangle((_rect(0, 0, 4, 10),), _box(0, 0, 10, 10))


def test_union_of_overlapping_fill_parts_covers_rectangle():
    assert filled_contours_cover_rectangle(
        (_rect(0, 0, 6, 10), _rect(4, 0, 10, 10)), _box(0, 0, 10, 10))


def test_each_operand_uses_nonzero_fill_independent_of_orientation():
    assert filled_contours_cover_rectangle(
        (_rect(0, 0, 5, 5), _rect(5, 0, 10, 5, reverse=True)), _box(0, 0, 10, 5))


def test_quadratic_paths_are_checked_without_flattening():
    rounded = (
        PathCommand("move", ((0.0, 2.0),)),
        PathCommand("line", ((2.0, 0.0),)),
        PathCommand("quadratic", ((4.0, 0.0), (4.0, 2.0))),
        PathCommand("line", ((4.0, 6.0),)),
        PathCommand("quadratic", ((4.0, 8.0), (2.0, 8.0))),
        PathCommand("line", ((0.0, 6.0),)),
        PathCommand("line", ((0.0, 2.0),)),
    )
    assert filled_contours_cover_rectangle((rounded,), _box(1, 3, 2, 2))
    assert not filled_contours_cover_rectangle((rounded,), _box(0, 0, 4, 8))


@pytest.mark.parametrize(
    ("rectangle", "stage", "reason"),
    [
        (Rect(Decimal(0), Decimal(0), Decimal(0), Decimal(2)), "input", "degenerate"),
        (Rect(Decimal(0), Decimal(0), Decimal(2), Decimal(-1)), "input", "degenerate"),
        (Rect(Decimal(0), Decimal(0), Decimal("Infinity"), Decimal(1)), "input", "nonfinite"),
    ],
)
def test_invalid_rectangle_fails_with_bounded_error(rectangle, stage, reason):
    with pytest.raises(ContourUnionError) as caught:
        filled_contours_cover_rectangle((_rect(0, 0, 2, 2),), rectangle)
    assert (caught.value.stage, caught.value.reason) == (stage, reason)


def test_open_and_nonfinite_operands_fail_closed():
    with pytest.raises(ContourUnionError) as opened:
        filled_contours_cover_rectangle(
            ((PathCommand("move", ((0.0, 0.0),)), PathCommand("line", ((1.0, 0.0),))),),
            _box(0, 0, 1, 1),
        )
    assert (opened.value.stage, opened.value.reason) == ("input", "open")

    with pytest.raises(ContourUnionError) as nonfinite:
        filled_contours_cover_rectangle((_rect(0, 0, float("inf"), 1),), _box(0, 0, 1, 1))
    assert (nonfinite.value.stage, nonfinite.value.reason) == ("input", "nonfinite")


def test_pathops_difference_failure_is_bounded_and_fails_closed(monkeypatch):
    def fail(*_args, **_kwargs):
        raise RuntimeError("backend detail must not escape")

    monkeypatch.setattr(contour.pathops, "op", fail)
    with pytest.raises(ContourUnionError) as caught:
        filled_contours_cover_rectangle((_rect(0, 0, 2, 2),), _box(0, 0, 1, 1))
    assert (caught.value.stage, caught.value.reason) == ("difference", "operation-failed")
    assert "backend detail" not in str(caught.value)
