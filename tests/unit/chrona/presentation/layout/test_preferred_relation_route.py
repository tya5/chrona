"""Previous route proposals are hints, never exemptions from route validation."""

import pytest

from chrona.presentation.layout import route_search, routing
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.routing import select_relation_route


def _port(side, point):
    return ConnectorEgress(side, point, point, ())


def _call(pair, *, preferred_routes=(), obstacles=None, prepare=None, max_bends=4,
          search_policy="first-fit"):
    return select_relation_route(
        (pair,), obstacles=obstacles or SurfaceObstacleIndex(), bounds=(-2, -2, 12, 12),
        source_host_id=None, target_host_id=None, relation_scene_id="relation:hint-test",
        max_bends=max_bends, max_detour_ratio=2, prepare=prepare,
        search_policy=search_policy, preferred_routes=preferred_routes,
    )


def _no_shapes(monkeypatch):
    monkeypatch.setattr(routing, "relation_shape_candidates", lambda *args, **kwargs: ())


def test_valid_preferred_route_settles_without_ordinary_search(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("a valid previous route must not start route search")

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", forbidden)
    source, target = _port("end", (0, 0)), _port("start", (10, 10))
    pair = (source, target)
    path = ((0, 0), (10, 0), (10, 10))
    result = _call(pair, preferred_routes=((pair, path),))

    assert result.selected_pair == pair
    assert result.points == path
    assert not result.search_used
    assert result.settled_by_hint
    assert result.hint_rejection is None


@pytest.mark.parametrize("case,expected_rejection", [
    ("obstacle", "E_LAYOUT_ROUTE_THROUGH_MARK"),
    ("terminal", "E_CONNECTOR_UNROUTABLE"),
    ("out-of-bounds", "E_CONNECTOR_UNROUTABLE"),
    ("self-overlap", "E_LAYOUT_ROUTE_SELF_OVERLAP"),
    ("quality", "quality-rejected"),
])
def test_rejected_preferred_route_falls_through_to_ordinary_search(
        monkeypatch, case, expected_rejection):
    _no_shapes(monkeypatch)
    source, target = _port("end", (0, 0)), _port("start", (10, 10))
    pair = (source, target)
    preferred = ((0, 0), (10, 0), (10, 10))
    fallback = ((0, 0), (0, 10), (10, 10))
    obstacles = SurfaceObstacleIndex()
    max_bends = 4
    prepare = None

    if case == "obstacle":
        obstacles.add(SurfaceObstacle("block", "mark", "timeline", ObstacleRect(4, -1, 6, 1)))
    elif case == "terminal":
        prepare = lambda points, *_: None if points == preferred else points
    elif case == "out-of-bounds":
        preferred = ((0, 0), (14, 0), (10, 10))
    elif case == "self-overlap":
        prepare = lambda points, *_: (
            ((0, 0), (8, 0), (3, 0), (10, 10)) if points == preferred else points
        )
    else:
        source, target = _port("end", (0, 0)), _port("start", (10, 0))
        pair = (source, target)
        preferred = ((0, 0), (0, 5), (10, 5), (10, 0))
        fallback = ((0, 0), (10, 0))
        max_bends = 0

    searched = []

    def ordinary_candidates(start, end, *_args, **_kwargs):
        searched.append((start, end))
        yield fallback

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", ordinary_candidates)
    result = _call(pair, preferred_routes=((pair, preferred),), obstacles=obstacles,
                   prepare=prepare, max_bends=max_bends)

    assert searched == [(source.exposed_port, target.exposed_port)]
    assert result.selected_pair == pair
    assert result.points == fallback
    assert result.search_used
    assert not result.settled_by_hint
    assert result.hint_rejection == expected_rejection


def test_first_rejected_hint_allows_next_hint_before_ordinary_search(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("a later valid previous route must not start route search")

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", forbidden)
    source, target = _port("end", (0, 0)), _port("start", (10, 10))
    pair = (source, target)
    rejected = ((0, 0), (14, 0), (10, 10))
    accepted = ((0, 0), (0, 10), (10, 10))
    result = _call(pair, preferred_routes=((pair, rejected), (pair, accepted)))

    assert result.selected_pair == pair
    assert result.points == accepted
    assert not result.search_used
    assert result.settled_by_hint


def test_best_policy_ignores_preferred_route_including_receipts(monkeypatch):
    monkeypatch.setattr(routing, "relation_shape_candidates",
                        lambda *args, **kwargs: (_ for _ in ()).throw(
                            AssertionError("best policy must not consult first-fit shapes")))
    source, target = _port("end", (0, 0)), _port("start", (10, 10))
    pair = (source, target)
    calls = []

    def candidates(start, end, *_args, **_kwargs):
        calls.append((start, end))
        yield ((0, 0), (10, 0), (10, 10))

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", candidates)
    without_hint = _call(pair, search_policy="best")
    calls_without_hint = tuple(calls)
    calls.clear()
    with_hint = _call(pair, search_policy="best",
                      preferred_routes=((pair, ((0, 0), (0, 10), (10, 10))),))

    assert with_hint == without_hint
    assert tuple(calls) == calls_without_hint
    assert not with_hint.settled_by_hint
    assert with_hint.hint_rejection is None
