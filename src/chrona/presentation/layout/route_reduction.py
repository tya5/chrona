"""Small, obstacle-checked reductions for completed orthogonal routes."""

from __future__ import annotations

from collections.abc import Callable

Point = tuple[float, float]
Route = tuple[Point, ...]


def simplify_relation_route(
    points: Route,
    *,
    clears: Callable[[Route], bool],
) -> Route:
    """Remove monotonic collinear points and clearable interior S-jogs.

    Candidate jog reductions move one of the parallel runs to the other run's
    coordinate. Endpoints and the terminal entry/exit directions are kept,
    and neither terminal run may become shorter. ``clears`` is evaluated on
    the complete candidate route so callers can apply their full obstacle
    policy consistently.
    """
    current = _collapse_collinear(tuple(points))
    while True:
        replacement = _collapse_one_jog(current, clears)
        if replacement is None:
            return current
        current = replacement


def _collapse_one_jog(points: Route, clears: Callable[[Route], bool]) -> Route | None:
    # Four points form two parallel runs separated by an orthogonal jog:
    # a--b (run), b--c (jog), c--d (run).
    for index in range(1, len(points) - 2):
        a, b, c, d = points[index - 1:index + 3]
        run_axis = _segment_axis(a, b)
        jog_axis = _segment_axis(b, c)
        if run_axis is None or jog_axis is None or run_axis == jog_axis:
            continue
        if _segment_axis(c, d) != run_axis:
            continue
        if _direction(a, b, run_axis) != _direction(c, d, run_axis):
            continue

        # First shift the run after the jog onto the run before it, then try
        # the mirrored operation. Moving only interior vertices leaves both
        # semantic endpoints and their terminal segments untouched.
        options = (
            _shift_pair(points, index + 1, index + 2, jog_axis, b[jog_axis]),
            _shift_pair(points, index - 1, index, jog_axis, c[jog_axis]),
        )
        for shifted in options:
            candidate = _collapse_collinear(shifted)
            if len(candidate) >= len(points):
                continue
            if candidate[0] != points[0] or candidate[-1] != points[-1]:
                continue
            if any(_segment_axis(start, end) is None for start, end in zip(candidate, candidate[1:])):
                continue
            if not _terminal_preserved(points, candidate):
                continue
            if _has_collinear_reversal(candidate):
                continue
            if clears(candidate):
                return candidate
    return None


def _shift_pair(points: Route, first: int, second: int, axis: int, value: float) -> Route:
    moved = list(points)
    for index in (first, second):
        point = moved[index]
        moved[index] = (value, point[1]) if axis == 0 else (point[0], value)
    return tuple(moved)


def _collapse_collinear(points: Route) -> Route:
    result: list[Point] = []
    for point in points:
        if result and point == result[-1]:
            continue
        while len(result) >= 2:
            before, middle = result[-2:]
            if before[0] == middle[0] == point[0]:
                first, second = middle[1] - before[1], point[1] - middle[1]
            elif before[1] == middle[1] == point[1]:
                first, second = middle[0] - before[0], point[0] - middle[0]
            else:
                break
            if first * second <= 0:
                break
            result.pop()
        result.append(point)
    return tuple(result)


def _segment_axis(start: Point, end: Point) -> int | None:
    if start == end:
        return None
    if start[0] == end[0]:
        return 1
    if start[1] == end[1]:
        return 0
    return None


def _direction(start: Point, end: Point, axis: int) -> int:
    delta = end[axis] - start[axis]
    return 1 if delta > 0 else -1


def _terminal_preserved(original: Route, candidate: Route) -> bool:
    if len(original) < 2 or len(candidate) < 2:
        return len(original) == len(candidate)
    for start, end, new_start, new_end in (
        (original[0], original[1], candidate[0], candidate[1]),
        (original[-2], original[-1], candidate[-2], candidate[-1]),
    ):
        axis = _segment_axis(start, end)
        new_axis = _segment_axis(new_start, new_end)
        if axis is None or new_axis != axis:
            return False
        if _direction(start, end, axis) != _direction(new_start, new_end, axis):
            return False
        if abs(new_end[axis] - new_start[axis]) < abs(end[axis] - start[axis]):
            return False
    return True


def _has_collinear_reversal(points: Route) -> bool:
    for first, middle, last in zip(points, points[1:], points[2:]):
        axis = _segment_axis(first, middle)
        if axis is not None and _segment_axis(middle, last) == axis:
            if _direction(first, middle, axis) != _direction(middle, last, axis):
                return True
    return False
