"""A resolved relation's deterministic work allowance does not reset per pair."""
from collections import Counter

import pytest

from chrona.presentation.layout import route_search as search, routing
from chrona.presentation.layout.obstacles import (
    ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.ports import ConnectorEgress


def _select(pairs, obstacles=None, *, accept=None):
    return routing.select_relation_route(
        pairs, obstacles=obstacles or SurfaceObstacleIndex(),
        bounds=(-2, -3, 12, 3), source_host_id=None, target_host_id=None,
        relation_scene_id="relation:synthetic", max_bends=8, max_detour_ratio=4,
        rank=lambda points, source, target: (0,),
        accept=accept,
    )


def _pair():
    return (ConnectorEgress("end", (0, 0), (0, 0), ()),
            ConnectorEgress("start", (10, 0), (10, 0), ()))


def _remember_limits(monkeypatch):
    limits = []

    def candidate(source, target, **kwargs):
        limits.append(kwargs["limit"])
        points = (source.semantic_port, target.semantic_port)
        return routing.route_quality_attempt(
            source.side, target.side, points, max_bends=8, max_detour_ratio=4,
        ), points

    monkeypatch.setattr(routing, "_select_pair_candidate", candidate)
    return limits


@pytest.mark.parametrize("pair_count", (1, 3, 20))
def test_all_pairs_share_exactly_the_relation_allowance(monkeypatch, pair_count):
    limits = _remember_limits(monkeypatch)
    selected = _select((_pair(),) * pair_count)
    quota, remainder = divmod(routing.RELATION_SEARCH_EXPANSIONS, pair_count)
    assert limits == [quota + int(index < remainder) for index in range(pair_count)]
    assert sum(limits) == 4096
    assert [attempt.outcome for attempt in selected.attempts] == (
        ["accepted"] + ["eligible-not-selected"] * (pair_count - 1))


def test_blocked_pair_does_not_transfer_its_unused_allowance(monkeypatch):
    limits = _remember_limits(monkeypatch)
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("blocking-mark", "mark", "timeline",
                                  ObstacleRect(-0.5, -0.5, 0.5, 0.5)))
    obstacles.add(SurfaceObstacle("source-host", "mark", "timeline",
                                  ObstacleRect(-1.2, -0.2, -0.8, 0.2)))
    source, target = _pair()
    blocked = ConnectorEgress("end", (-1, 0), (1, 0), ("source-host",))
    selected = _select(((blocked, target), (source, target), (source, target)), obstacles)
    assert limits == [1365, 1365]
    assert selected.attempts[0].outcome == "egress-collision"
    assert selected.attempts[1].outcome == "accepted"


def test_zero_allowance_is_search_limited_not_geometrically_impossible(monkeypatch):
    limits = _remember_limits(monkeypatch)
    monkeypatch.setattr(routing, "RELATION_SEARCH_EXPANSIONS", 2)
    selected = _select((_pair(),) * 3)
    assert limits == [1, 1]
    assert selected.attempts[-1].search_failure == "E_PRESENTATION_ROUTE_LIMIT"
    assert selected.attempts[-1].outcome == "no-route-found"


@pytest.mark.parametrize("relation_count", (0, 10, 50, 200))
def test_generated_relation_work_is_bounded_without_a_timing_gate(monkeypatch, relation_count):
    """One Layout selection pass of generated, obstacle-blocked instances.

    Five passes multiply these bounds by five: at most100R generator calls,
    81920R frontier pops (including stale/over-limit discoveries), and
    20R*4096**2 exact history predicates. Graph reverse-Dijkstra pops are
    deliberately separate, rather than claiming they consume frontier quota.
    """
    counts = Counter()
    original_candidates = search.orthogonal_route_candidates
    original_intersects = search._history_segments_intersect
    original_pop = search.heappop

    def candidates(*args, **kwargs):
        counts["generators"] += 1
        yield from original_candidates(*args, **kwargs)

    def intersects(*args):
        counts["history_predicates"] += 1
        return original_intersects(*args)

    def pop(queue):
        entry = original_pop(queue)
        state = entry[-1]
        if isinstance(state, tuple) and len(state) == 6:
            counts["frontier_pops"] += 1
        else:
            counts["graph_pops"] += 1
        return entry

    monkeypatch.setattr(search, "orthogonal_route_candidates", candidates)
    monkeypatch.setattr(search, "_history_segments_intersect", intersects)
    monkeypatch.setattr(search, "heappop", pop)
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("obstacle", "mark", "timeline", ObstacleRect(4, -1, 6, 1)))
    # Repeated endpoint geometry is intentional: cache hits must not create
    # a new allowance, change the work bound, or change route selection.
    generated = tuple((_pair(),) * 20 for _ in range(relation_count))
    # Exercise genuine exhaustion as well as early accepted routes. The
    # predicate models a completed-terminal rejection, not unsafe admission.
    completed = [_select(pairs, obstacles, accept=(lambda points: False)
                         if index % 50 == 0 else None)
                 for index, pairs in enumerate(generated)]
    assert counts["generators"] <= 20 * relation_count
    assert counts["frontier_pops"] <= 4 * 4096 * relation_count
    assert counts["history_predicates"] <= 4 * 4096**2 * relation_count
    assert all((result.selected_pair is None) == (index % 50 == 0)
               for index, result in enumerate(completed))
    if relation_count:
        assert counts["history_predicates"] > 0
        assert all(result == completed[0] for index, result in enumerate(completed)
                   if index % 50 == 0)
        assert all(result == completed[1] for index, result in enumerate(completed)
                   if index % 50 != 0)
    print(f"R={relation_count}: {dict(counts)}")
