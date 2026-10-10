from __future__ import annotations

from types import SimpleNamespace

import pytest

import chrona.presentation.layout.filled_contour as contour
from chrona.presentation.layout.filled_contour import ContourUnionError, union_filled_contours
from chrona.presentation.layout.surface_quality import PathCommand as C, is_closed_stroke_contour


def _rect(x0: float, y0: float, x1: float, y1: float, *, reverse: bool = False):
    points = ((x0, y0), (x1, y0), (x1, y1), (x0, y1))
    if reverse:
        points = tuple(reversed(points))
    return (C("move", (points[0],)), *(C("line", (point,)) for point in points[1:]),
            C("line", (points[0],)))


def _subpaths(commands):
    paths = []
    for command in commands:
        if command.kind == "move":
            paths.append([command.points[0]])
        else:
            paths[-1].extend(command.points)
    return paths


def _bounds(commands):
    values = [point for command in commands for point in command.points]
    return (min(point[0] for point in values), min(point[1] for point in values),
            max(point[0] for point in values), max(point[1] for point in values))


def test_one_fill_with_overlapping_subpaths_returns_only_the_union_boundary():
    left = _rect(0, 0, 8, 8)
    right = _rect(4, 0, 12, 8)

    result = union_filled_contours((left + right,))

    assert _bounds(result) == (0, 0, 12, 8)
    assert len(_subpaths(result)) == 1
    current = None
    for command in result:
        if command.kind == "move":
            current = command.points[0]
        elif command.kind == "line":
            endpoint = command.points[0]
            assert current is not None
            assert (current[0] == endpoint[0] and current[0] in {0, 12}) or (
                current[1] == endpoint[1] and current[1] in {0, 8}
            )
            current = endpoint
    assert is_closed_stroke_contour(result)


def test_single_contour_with_self_overlapping_square_loops_has_no_seam():
    points = ((0, 0), (8, 0), (8, 8), (0, 8), (0, 0), (4, 0),
              (12, 0), (12, 8), (4, 8), (4, 0), (0, 0))
    contour_path = (C("move", (points[0],)), *(C("line", (point,)) for point in points[1:]))

    result = union_filled_contours((contour_path,))

    assert _bounds(result) == (0, 0, 12, 8)
    assert len(_subpaths(result)) == 1
    current = None
    for command in result:
        if command.kind == "move":
            current = command.points[0]
        elif command.kind == "line":
            endpoint = command.points[0]
            assert current is not None
            assert (current[0] == endpoint[0] and current[0] in {0, 12}) or (
                current[1] == endpoint[1] and current[1] in {0, 8}
            )
            current = endpoint


def test_overlapping_and_adjacent_parts_form_one_outline_and_are_permutation_stable():
    first, second, third = _rect(0, 0, 8, 8), _rect(4, 0, 12, 8), _rect(12, 0, 16, 8)

    outputs = {union_filled_contours(order) for order in (
        (first, second, third), (third, second, first), (second, first, third),
        (first, third, second), (second, third, first), (third, first, second),
    )}

    assert len(outputs) == 1
    result = next(iter(outputs))
    assert _bounds(result) == (0, 0, 16, 8)
    assert len(_subpaths(result)) == 1


def test_disjoint_parts_remain_separate_closed_contours():
    result = union_filled_contours((_rect(0, 0, 2, 2), _rect(5, 0, 7, 2)))

    assert len(_subpaths(result)) == 2
    assert _bounds(result) == (0, 0, 7, 2)
    assert is_closed_stroke_contour(result)


def test_opposite_winding_subpath_hole_is_preserved():
    outer, hole = _rect(0, 0, 12, 12), _rect(3, 3, 9, 9, reverse=True)

    result = union_filled_contours((outer + hole,))

    assert len(_subpaths(result)) == 2
    assert _bounds(result) == (0, 0, 12, 12)
    assert is_closed_stroke_contour(result)


def test_same_geometry_with_opposite_winding_cancels_to_empty_error():
    with pytest.raises(ContourUnionError) as caught:
        union_filled_contours((_rect(0, 0, 4, 4) + _rect(0, 0, 4, 4, reverse=True),))

    assert (caught.value.stage, caught.value.reason) == ("output", "empty")
    assert len(str(caught.value)) < 80


def test_quadratic_boundary_stays_exact_quadratic_without_flattening():
    curved = (C("move", ((0, 0),)), C("quadratic", ((5, -4), (10, 0))),
              C("line", ((10, 8),)), C("line", ((0, 8),)), C("line", ((0, 0),)))

    result = union_filled_contours((curved,))

    assert C("quadratic", ((5.0, -4.0), (10.0, 0.0))) in result
    assert all(command.kind in {"move", "line", "quadratic"} for command in result)
    assert is_closed_stroke_contour(result)


def test_closed_all_quadratic_contour_uses_exact_implicit_start():
    path = SimpleNamespace(segments=(
        ("qCurveTo", ((0.0, 0.0), (0.0, 8.0), (8.0, 8.0), (8.0, 0.0), None)),
        ("closePath", ()),
    ))

    result = contour._from_pathops(path)

    assert result == (
        C("move", ((4.0, 0.0),)),
        C("quadratic", ((0.0, 0.0), (0.0, 4.0))),
        C("quadratic", ((0.0, 8.0), (4.0, 8.0))),
        C("quadratic", ((8.0, 8.0), (8.0, 4.0))),
        C("quadratic", ((8.0, 0.0), (4.0, 0.0))),
    )
    assert is_closed_stroke_contour(result)


def test_real_backend_implicit_quadratic_contours_preserve_the_hole():
    outer = (
        C("move", ((10, 0),)), C("quadratic", ((20, 0), (20, 10))),
        C("quadratic", ((20, 20), (10, 20))),
        C("quadratic", ((0, 20), (0, 10))),
        C("quadratic", ((0, 0), (10, 0))), C("line", ((10, 0),)),
    )
    hole = (
        C("move", ((10, 5),)), C("quadratic", ((5, 5), (5, 10))),
        C("quadratic", ((5, 15), (10, 15))),
        C("quadratic", ((15, 15), (15, 10))),
        C("quadratic", ((15, 5), (10, 5))), C("line", ((10, 5),)),
    )
    native = contour._simplify_operand(outer + hole)
    assert any(verb == "qCurveTo" and points[-1] is None
               for verb, points in native.segments)
    assert not native.contains((10, 10))
    assert native.contains((2, 10))

    result = union_filled_contours((outer + hole,))

    assert len(_subpaths(result)) == 2
    assert is_closed_stroke_contour(result)
    assert any(command.kind == "quadratic" for command in result)
    decoded = contour._to_pathops(result)
    assert not decoded.contains((10, 10))
    assert decoded.contains((2, 10))


def test_multicontrol_qcurve_uses_exact_implied_midpoint(monkeypatch):
    segments = (("moveTo", ((0.0, 0.0),)),
                ("qCurveTo", ((2.0, 0.0), (4.0, 2.0), (6.0, 0.0))),
                ("lineTo", ((6.0, 6.0),)), ("lineTo", ((0.0, 6.0),)),
                ("lineTo", ((0.0, 0.0),)), ("closePath", ()))
    monkeypatch.setattr(contour, "_simplify_operand", lambda _operand: SimpleNamespace(segments=segments))

    result = union_filled_contours((_rect(0, 0, 1, 1),))

    quadratics = tuple(command for command in result if command.kind == "quadratic")
    assert quadratics == (C("quadratic", ((2.0, 0.0), (3.0, 1.0))),
                          C("quadratic", ((4.0, 2.0), (6.0, 0.0))))


@pytest.mark.parametrize("operand,reason", [
    ((), "empty"),
    ((C("move", ((0, 0),)), C("line", ((1, 0),))), "open"),
    ((C("move", ((0, 0),)), C("line", ((1, 0),)), C("line", ((0, 0),))), "degenerate"),
    ((C("move", ((0, 0),)), C("line", ((float("nan"), 0),)), C("line", ((0, 0),))), "nonfinite"),
])
def test_invalid_source_contours_fail_with_bounded_reason(operand, reason):
    with pytest.raises(ContourUnionError) as caught:
        union_filled_contours((operand,))

    assert caught.value.stage == "input"
    assert caught.value.reason == reason
    assert len(str(caught.value)) < 80


@pytest.mark.parametrize("segments,reason", [
    ((), "empty"),
    ((("moveTo", ((0.0, 0.0),)), ("lineTo", ((2.0, 0.0),))), "open"),
    ((("moveTo", ((0.0, 0.0),)), ("lineTo", ((1.0, 0.0),)), ("lineTo", ((0.0, 0.0),))), "degenerate"),
    ((("moveTo", ((0.0, 0.0),)), ("cubicTo", ((0.0, 1.0), (1.0, 1.0), (1.0, 0.0))),
      ("lineTo", ((1.0, 1.0),)), ("lineTo", ((0.0, 1.0),)), ("lineTo", ((0.0, 0.0),))), "unsupported-verb"),
    ((("moveTo", ((0.0, 0.0),)), ("lineTo", ((float("inf"), 0.0),)),
      ("lineTo", ((0.0, 0.0),))), "nonfinite"),
    (( ("moveTo", ((0.0, 0.0),)), ("lineTo", (None,)) ), "operation-failed"),
    ((("moveTo", ((0.0, 0.0),)), ("lineTo", (("not-a-number", 1.0),))), "operation-failed"),
    ((("moveTo", ((0.0, 0.0),)), ("lineTo", ((1.0, 2.0, 3.0),))), "unsupported-verb"),
])
def test_invalid_pathops_output_fails_closed(monkeypatch, segments, reason):
    monkeypatch.setattr(contour, "_simplify_operand", lambda _operand: SimpleNamespace(segments=segments))

    with pytest.raises(ContourUnionError) as caught:
        union_filled_contours((_rect(0, 0, 1, 1),))

    assert caught.value.stage == "output"
    assert caught.value.reason == reason


def test_pathops_failure_is_reported_with_operation_stage(monkeypatch):
    def fail(_path):
        raise RuntimeError("large backend-specific detail should not escape")

    monkeypatch.setattr(contour, "_simplify_operand", fail)
    with pytest.raises(ContourUnionError) as caught:
        union_filled_contours((_rect(0, 0, 1, 1),))

    assert (caught.value.stage, caught.value.reason) == ("simplify", "operation-failed")
    assert "backend-specific" not in str(caught.value)


def test_union_failure_is_reported_with_operation_stage(monkeypatch):
    def fail(_left, _right):
        raise RuntimeError("backend detail must not escape")

    monkeypatch.setattr(contour, "_union_pair", fail)
    with pytest.raises(ContourUnionError) as caught:
        union_filled_contours((_rect(0, 0, 2, 2), _rect(1, 0, 3, 2)))

    assert (caught.value.stage, caught.value.reason) == ("union", "operation-failed")
    assert "backend detail" not in str(caught.value)
