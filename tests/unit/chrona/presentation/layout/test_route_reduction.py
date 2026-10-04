import pytest

from chrona.presentation.layout.route_reduction import simplify_relation_route
from chrona.presentation.layout.route_reduction import terminal_runs_preserved
from chrona.presentation.layout.routing import remove_substroke_jogs
from chrona.presentation.layout.routing import route_self_overlaps


def _bends(points):
    return sum(1 for a, b, c in zip(points, points[1:], points[2:])
               if (a[0] == b[0]) != (b[0] == c[0]))


@pytest.mark.parametrize(
    ("points", "expected"),
    [
        (((0, 0), (10, 0), (10, 3), (5, 3), (5, 10), (15, 10)),
         ((0, 0), (5, 0), (5, 10), (15, 10))),
        (((0, 10), (10, 10), (10, 7), (5, 7), (5, 0), (15, 0)),
         ((0, 10), (5, 10), (5, 0), (15, 0))),
    ],
)
def test_clear_s_jog_collapses_to_two_bends_and_preserves_endpoints(points, expected):
    reduced = simplify_relation_route(points, clears=lambda _: True)
    assert reduced == expected
    assert _bends(reduced) == 2
    assert reduced[0] == points[0] and reduced[-1] == points[-1]


def test_transposed_s_jog_collapses_the_horizontal_parallel_runs():
    points = ((0, 0), (0, 10), (3, 10), (3, 5), (10, 5), (10, 15))
    assert simplify_relation_route(points, clears=lambda _: True) == (
        (0, 0), (0, 5), (10, 5), (10, 15))


def test_full_candidate_clearance_callback_can_reject_each_s_jog_rewrite():
    points = ((0, 0), (10, 0), (10, 3), (5, 3), (5, 10), (15, 10))
    seen = []

    def clears(candidate):
        seen.append(candidate)
        return False

    assert simplify_relation_route(points, clears=clears) == points
    assert len(seen) == 2
    assert all(candidate[0] == points[0] and candidate[-1] == points[-1]
               for candidate in seen)


def test_free_s_jog_can_shorten_an_arbitrary_terminal_run_but_honors_required_floor():
    points = ((0, 0), (10, 0), (10, 3), (5, 3), (5, 10), (15, 10))
    reduced = simplify_relation_route(points, clears=lambda _: True)
    assert reduced == ((0, 0), (5, 0), (5, 10), (15, 10))
    assert abs(reduced[1][0] - reduced[0][0]) == 5

    with_floor = simplify_relation_route(points, clears=lambda _: True, start_minimum=6)
    assert with_floor == ((0, 0), (10, 0), (10, 10), (15, 10))
    with_both_floors = simplify_relation_route(
        points, clears=lambda _: True, start_minimum=6, end_minimum=11)
    assert with_both_floors == points


@pytest.mark.parametrize("minimum", [-1.0, float("inf"), float("nan")])
@pytest.mark.parametrize("side", ["start_minimum", "end_minimum"])
def test_nonfinite_or_negative_terminal_floor_uses_routing_attempt_error(minimum, side):
    points = ((0, 0), (10, 0))
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID"):
        simplify_relation_route(points, clears=lambda _: True, **{side: minimum})


def test_terminal_run_predicate_supports_one_unconstrained_end():
    original = ((0, 0), (10, 0), (10, 10))
    shortened_start = ((0, 0), (5, 0), (5, 10))
    assert terminal_runs_preserved(original, shortened_start,
                                   start_minimum=None, end_minimum=None)
    assert not terminal_runs_preserved(original, shortened_start,
                                       start_minimum=6, end_minimum=None)
    assert terminal_runs_preserved(original, shortened_start,
                                   start_minimum=0, end_minimum=0)


def test_r1_substroke_pass_preserves_corridor_floor_before_s_jog_reduction():
    original = ((0, 0), (2, 0), (2, 0.5), (0.5, 0.5), (0.5, 5), (5, 5))

    def corridor_clear(candidate):
        return terminal_runs_preserved(original, candidate,
                                       start_minimum=2, end_minimum=None)

    r1 = remove_substroke_jogs(original, 1, accept=corridor_clear,
                               start_minimum=2)
    assert r1[1] == (2, 0), "the R1 cleanup must not shorten the source corridor"
    reduced = simplify_relation_route(r1, clears=lambda _: True,
                                      start_minimum=2, end_minimum=0)
    assert reduced == ((0, 0), (2, 0), (2, 5), (5, 5))
    assert abs(reduced[1][0] - reduced[0][0]) >= 2


def test_already_straight_route_is_unchanged_and_monotonic_collinear_vertices_collapse():
    straight = ((0, 0), (4, 0), (9, 0))
    assert simplify_relation_route(straight, clears=lambda _: True) == ((0, 0), (9, 0))

    route = ((0, 0), (4, 0), (4, 2), (4, 7), (9, 7))
    assert simplify_relation_route(route, clears=lambda _: True) == (
        (0, 0), (4, 0), (4, 7), (9, 7))


def test_no_s_jog_reduction_reverses_a_collinear_terminal_direction():
    points = ((0, 0), (10, 0), (10, 3), (5, 3), (5, 10), (0, 10))
    reduced = simplify_relation_route(points, clears=lambda _: True)
    assert reduced[0] == points[0] and reduced[-1] == points[-1]
    assert all(a[0] == b[0] or a[1] == b[1] for a, b in zip(reduced, reduced[1:]))
    assert not any(a[0] == b[0] == c[0] and
                   (b[1] - a[1]) * (c[1] - b[1]) < 0 or
                   a[1] == b[1] == c[1] and
                   (b[0] - a[0]) * (c[0] - b[0]) < 0
                   for a, b, c in zip(reduced, reduced[1:], reduced[2:]))


def test_clearance_callback_rejects_a_nonadjacent_shared_segment_in_full_candidate():
    points = ((0, 0), (10, 0), (10, 3), (5, 3), (5, 10), (15, 10),
              (15, 5), (10, 5), (10, 8))
    seen = []

    def clears(candidate):
        seen.append(candidate)
        # The first reduction is blocked; the mirror candidate overlaps the
        # later x=10 segment over y=5..8 and must be refused as a whole route.
        first_candidate = ((0, 0), (5, 0), (5, 10), (15, 10),
                           (15, 5), (10, 5), (10, 8))
        return candidate != first_candidate and not route_self_overlaps(candidate)

    assert simplify_relation_route(points, clears=clears) == points
    assert len(seen) == 2
    assert not route_self_overlaps(seen[0])
    assert route_self_overlaps(seen[1])
