from __future__ import annotations

from chrona.presentation.layout.route_reduction import simplify_relation_route


def test_simplifies_free_s_jog_to_minimal_bend_route() -> None:
    route = ((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (5.0, 1.0), (5.0, 3.0))

    result = simplify_relation_route(route, clears=lambda candidate: True)

    assert result == ((0.0, 0.0), (5.0, 0.0), (5.0, 3.0))
    assert _bend_count(result) == 1


def test_blocked_s_jog_keeps_collinear_normalized_route() -> None:
    route = ((0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (5.0, 1.0), (5.0, 3.0))

    result = simplify_relation_route(route, clears=lambda candidate: False)

    assert result == ((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (5.0, 1.0), (5.0, 3.0))


def test_mirrored_s_jog_uses_other_parallel_run() -> None:
    route = ((0.0, 0.0), (0.0, 2.0), (1.0, 2.0), (1.0, 5.0), (3.0, 5.0))

    result = simplify_relation_route(route, clears=lambda candidate: True)

    assert result == ((0.0, 0.0), (0.0, 5.0), (3.0, 5.0))


def test_keeps_fixed_endpoints_and_does_not_shorten_terminal_runs() -> None:
    route = ((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (5.0, 1.0), (5.0, 3.0))
    accepted: list[tuple[tuple[float, float], ...]] = []

    def clears(candidate: tuple[tuple[float, float], ...]) -> bool:
        accepted.append(candidate)
        return True

    result = simplify_relation_route(route, clears=clears)

    assert result[0] == route[0]
    assert result[-1] == route[-1]
    assert _length(result[0], result[1]) >= _length(route[0], route[1])
    assert _length(result[-2], result[-1]) >= _length(route[-2], route[-1])
    assert accepted and all(candidate[0] == route[0] and candidate[-1] == route[-1] for candidate in accepted)


def test_does_not_offer_a_candidate_with_a_collinear_reversal() -> None:
    route = (
        (1.0, -3.0), (1.0, -1.0), (1.0, 0.0), (3.0, 0.0),
        (3.0, -2.0), (5.0, -2.0), (5.0, -4.0),
    )
    checked: list[tuple[tuple[float, float], ...]] = []

    def clears(candidate: tuple[tuple[float, float], ...]) -> bool:
        assert not _has_collinear_reversal(candidate)
        checked.append(candidate)
        return False

    result = simplify_relation_route(route, clears=clears)

    assert result == (
        (1.0, -3.0), (1.0, 0.0), (3.0, 0.0),
        (3.0, -2.0), (5.0, -2.0), (5.0, -4.0),
    )
    assert checked


def _bend_count(points: tuple[tuple[float, float], ...]) -> int:
    axes = []
    for start, end in zip(points, points[1:]):
        axes.append(0 if start[1] == end[1] else 1)
    return sum(first != second for first, second in zip(axes, axes[1:]))


def _length(start: tuple[float, float], end: tuple[float, float]) -> float:
    return abs(end[0] - start[0]) + abs(end[1] - start[1])


def _has_collinear_reversal(points: tuple[tuple[float, float], ...]) -> bool:
    for first, middle, last in zip(points, points[1:], points[2:]):
        if first[0] == middle[0] == last[0]:
            if (middle[1] - first[1]) * (last[1] - middle[1]) < 0:
                return True
        if first[1] == middle[1] == last[1]:
            if (middle[0] - first[0]) * (last[0] - middle[0]) < 0:
                return True
    return False
