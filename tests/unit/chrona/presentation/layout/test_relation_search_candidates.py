"""Bounded constrained relation-route search, independent of corpus resources."""

from itertools import islice

import pytest

from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.route_search import (
    RouteSearchFailure, orthogonal_route_candidates,
)
from chrona.presentation.layout.routing import (
    route_orthogonal, route_quality_metrics, route_self_overlaps, select_relation_route,
)


def _index(rectangles):
    index = SurfaceObstacleIndex()
    for placement_id, rectangle in rectangles:
        index.add(SurfaceObstacle(placement_id, "mark", "timeline", ObstacleRect(*rectangle)))
    return index


def _clear(index, points):
    return all(not index.collisions(ObstacleSegment(a, b), classes=("mark",), regions=("timeline",))
               for a, b in zip(points, points[1:]))


def _bends(points):
    return route_quality_metrics(points)[2]


def test_candidates_include_an_eligible_lower_bend_route_when_weighted_shortest_is_over_budget():
    index = _index((
        ("mark:a", (15, -45, 18, 2)),
        ("mark:b", (30, -2, 33, 45)),
        ("mark:c", (45, -45, 48, 2)),
    ))
    source, target = (0, 0), (100, 0)
    bounds = (-5, -100, 105, 100)

    candidates = orthogonal_route_candidates(
        source, target, index, bounds=bounds, classes=("mark",), regions=("timeline",))
    expected = ((0, 0), (0, 47), (100, 47), (100, 0))
    eligible = next((path for path in candidates if _bends(path) <= 4
                     and route_quality_metrics(path)[0] <= 200), None)
    assert eligible is not None
    assert _bends(eligible) == 2
    assert route_quality_metrics(eligible)[1] == 100
    assert route_quality_metrics(eligible)[0] <= 200
    assert _bends(expected) == 2
    assert route_quality_metrics(expected)[:2] == (194, 100)
    assert _clear(index, expected)


def test_sparse_visibility_search_finds_clear_route_under_default_expansion_limit():
    rectangles = [("wall", (50, -100, 53, 90))]
    rectangles.extend(
        (f"tiny:{i}", (5 + ((i * 17) % 40), -85 + ((i * 37) % 165),
                         5 + ((i * 17) % 40) + 0.1, -85 + ((i * 37) % 165) + 0.1))
        for i in range(30)
    )
    index = _index(rectangles)
    expected = ((0, 0), (0, 92), (100, 92), (100, 0))

    candidates = orthogonal_route_candidates(
        (0, 0), (100, 0), index, bounds=(0, -100, 100, 100),
        classes=("mark",), regions=("timeline",))
    bounded = next((path for path in candidates if _bends(path) <= 4
                    and route_quality_metrics(path)[0] <= 300), None)
    assert bounded is not None
    assert _bends(bounded) == 2
    assert route_quality_metrics(bounded)[0] <= 284
    assert route_quality_metrics(bounded)[1:] == (100, 2)
    assert _clear(index, bounded)
    routed = route_orthogonal((0, 0), (100, 0), index,
        bounds=(0, -100, 100, 100), classes=("mark",), regions=("timeline",))
    assert routed[0] == (0, 0) and routed[-1] == (100, 0)
    assert _bends(routed) <= 4
    assert route_quality_metrics(routed)[0] <= 300
    assert _clear(index, routed)
    assert route_quality_metrics(expected) == (284, 100, 2)
    assert _clear(index, expected)

    with pytest.raises(RouteSearchFailure, match="E_PRESENTATION_ROUTE_LIMIT"):
        tuple(orthogonal_route_candidates((0, 0), (100, 0), index,
            bounds=(0, -100, 100, 100), classes=("mark",), regions=("timeline",), limit=1))


def test_candidate_enumeration_is_deterministic_and_keeps_stable_ties():
    index = _index((("middle", (4, -2, 6, 2)),))
    args = ((0, 0), (10, 0), index)
    kwargs = dict(bounds=(-2, -5, 12, 5), classes=("mark",), regions=("timeline",))

    first = tuple(islice(orthogonal_route_candidates(*args, **kwargs), 3))
    second = tuple(islice(orthogonal_route_candidates(*args, **kwargs), 3))

    assert first == second
    assert first
    assert all(path[0] == (0, 0) and path[-1] == (10, 0) for path in first)
    assert all(not route_self_overlaps(path) and _clear(index, path) for path in first)


def test_bounds_and_mark_barriers_apply_to_every_candidate():
    index = _index((("barrier", (4, -4, 6, 4)),))
    paths = islice(orthogonal_route_candidates(
        (0, 0), (10, 0), index, bounds=(-1, -6, 11, 6),
        classes=("mark",), regions=("timeline",)), 8)
    paths = tuple(paths)

    assert paths
    assert all(-1 <= x <= 11 and -6 <= y <= 6 for path in paths for x, y in path)
    assert all(_clear(index, path) for path in paths)


def test_selector_checks_corridors_and_whole_route_callback_for_alternates():
    index = _index((("middle", (4, -2, 6, 2)),))
    source = ConnectorEgress("end", (0, 0), (0, 0), ())
    target = ConnectorEgress("start", (10, 0), (10, 0), ())
    rejected_path = []

    def accept(points):
        if points[1][1] > 0:
            rejected_path.append(points)
            return False
        return True

    selected = select_relation_route(
        ((source, target),), obstacles=index, bounds=(-1, -6, 11, 6),
        source_host_id=None, target_host_id=None, relation_scene_id="relation:callback",
        max_bends=4, max_detour_ratio=2, classes=("mark",), regions=("timeline",), accept=accept)

    assert selected.selected_pair == (source, target)
    assert _clear(index, selected.points)
    assert selected.points not in rejected_path
    assert selected.attempts[0].outcome == "accepted"


def test_same_pair_retains_distinct_prefixes_until_path_dependent_acceptance():
    index = _index((("middle", (4, -2, 6, 2)),))
    source = ConnectorEgress("end", (0, 0), (0, 0), ())
    target = ConnectorEgress("start", (10, 0), (10, 0), ())
    examined = []

    def accept(points):
        examined.append(points)
        return not any(y < 0 for _, y in points)

    selected = select_relation_route(
        ((source, target),), obstacles=index, bounds=(-1, -6, 11, 6),
        source_host_id=None, target_host_id=None, relation_scene_id="relation:path-history",
        max_bends=2, max_detour_ratio=3, classes=("mark",), regions=("timeline",), accept=accept)

    assert selected.selected_pair == (source, target)
    assert len(examined) >= 2
    assert any(any(y < 0 for _, y in path) for path in examined)
    assert all(y >= 0 for _, y in selected.points)
    assert _bends(selected.points) == 2
    assert route_quality_metrics(selected.points)[0] <= 30
    assert _clear(index, selected.points)


def test_selector_rejects_a_blocked_terminal_corridor_before_searching_body_candidates():
    index = _index((
        ("source-host", (-0.5, -0.5, 0.5, 0.5)),
        ("corridor-blocker", (0.8, -0.2, 1.2, 0.2)),
    ))
    source = ConnectorEgress("end", (0, 0), (2, 0), ("source-host",))
    target = ConnectorEgress("start", (10, 0), (10, 0), ())

    selected = select_relation_route(
        ((source, target),), obstacles=index, bounds=(-1, -6, 11, 6),
        source_host_id=None, target_host_id=None, relation_scene_id="relation:corridor",
        max_bends=4, max_detour_ratio=2, classes=("mark",), regions=("timeline",))

    assert selected.selected_pair is None
    assert selected.attempts[0].outcome == "egress-collision"
    assert selected.attempts[0].blocker_ids == ("corridor-blocker",)


def test_selector_rejects_safe_candidates_that_exceed_declared_quality():
    index = _index((
        ("mark:a", (15, -45, 18, 2)),
        ("mark:b", (30, -2, 33, 45)),
        ("mark:c", (45, -45, 48, 2)),
    ))
    source = ConnectorEgress("start", (0, 0), (0, 0), ())
    target = ConnectorEgress("start", (100, 0), (100, 0), ())
    kwargs = dict(
        port_pairs=((source, target),), obstacles=index, bounds=(-5, -100, 105, 100),
        source_host_id=None, target_host_id=None, relation_scene_id="relation:quality-exception",
        max_bends=1, max_detour_ratio=2, classes=("mark",), regions=("timeline",),
        accept=lambda points: _clear(index, points),
    )

    strict = select_relation_route(**kwargs)
    assert strict.selected_pair is None
    attempt = strict.attempts[0]
    assert attempt.outcome == "quality-rejected"
    assert attempt.search_disposition in {
        "bounded-candidates-exhausted", "expansion-limit",
    }
    assert attempt.bends > attempt.max_bends
    assert attempt.length <= attempt.direct_length * attempt.max_detour_ratio


def test_within_budget_alternative_is_accepted():
    index = _index((
        ("mark:a", (15, -45, 18, 2)),
        ("mark:b", (30, -2, 33, 45)),
        ("mark:c", (45, -45, 48, 2)),
    ))
    source = ConnectorEgress("start", (0, 0), (0, 0), ())
    target = ConnectorEgress("start", (100, 0), (100, 0), ())

    selected = select_relation_route(
        ((source, target),), obstacles=index, bounds=(-5, -100, 105, 100),
        source_host_id=None, target_host_id=None, relation_scene_id="relation:within-budget",
        max_bends=4, max_detour_ratio=2, classes=("mark",), regions=("timeline",),
        accept=lambda points: _clear(index, points))

    assert selected.selected_pair == (source, target)
    assert selected.attempts[0].outcome == "accepted"
    assert _bends(selected.points) <= 4


def test_all_candidates_still_require_mark_callback_clearance():
    index = _index((
        ("mark:a", (15, -45, 18, 2)),
        ("mark:b", (30, -2, 33, 45)),
        ("mark:c", (45, -45, 48, 2)),
    ))
    source = ConnectorEgress("start", (0, 0), (0, 0), ())
    target = ConnectorEgress("start", (100, 0), (100, 0), ())
    checked = []

    def reject(points):
        checked.append(points)
        return False

    selected = select_relation_route(
        ((source, target),), obstacles=index, bounds=(-5, -100, 105, 100),
        source_host_id=None, target_host_id=None, relation_scene_id="relation:unsafe-exception",
        max_bends=1, max_detour_ratio=2, classes=("mark",), regions=("timeline",),
        accept=reject)

    assert selected.selected_pair is None
    assert checked


def test_candidate_search_reports_outside_endpoint_bounds_as_unroutable():
    with pytest.raises(RouteSearchFailure, match="E_CONNECTOR_UNROUTABLE"):
        next(orthogonal_route_candidates(
            (0, 0), (10, 0), SurfaceObstacleIndex(), bounds=(-1, -1, 9, 1)))


def test_coincident_endpoints_do_not_skip_invalid_port_exemption_validation():
    index = _index((("mark", (-1, -1, 1, 1)),))

    with pytest.raises(ValueError, match="E_LAYOUT_OBSTACLE_EXEMPTION_INVALID"):
        next(orthogonal_route_candidates(
            (0, 0), (0, 0), index, port_ids=("missing-port",),
            classes=("mark",), regions=("timeline",)))
