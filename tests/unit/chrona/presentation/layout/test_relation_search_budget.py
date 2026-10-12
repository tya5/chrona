"""A resolved relation's deterministic work allowance does not reset per pair."""
from collections import Counter

import pytest

from chrona.presentation.layout import route_search as search, routing
from chrona.presentation.layout.obstacles import (
    ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.ports import ConnectorEgress


def _select(pairs, obstacles=None, *, accept=None, **kwargs):
    return routing.select_relation_route(
        pairs, obstacles=obstacles or SurfaceObstacleIndex(),
        bounds=(-2, -3, 12, 3), source_host_id=None, target_host_id=None,
        relation_scene_id="relation:synthetic", max_bends=8, max_detour_ratio=4,
        rank=lambda points, source, target: (0,),
        accept=accept,
        **kwargs,
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


@pytest.mark.parametrize("invalid", (0, -1, True, 1.5, "2"))
def test_explicit_budget_rejects_invalid_internal_values(invalid):
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_SEARCH_INPUT"):
        _select((_pair(),), search_budget=invalid)


def test_budget_charges_seed_before_yield_and_retains_accepted_route(monkeypatch):
    calls = []
    original = search.orthogonal_route_candidates

    def observed(*args, **kwargs):
        calls.append(kwargs["budget"])
        yield from original(*args, **kwargs)

    monkeypatch.setattr(search, "orthogonal_route_candidates", observed)
    selected = _select((_pair(),) * 3, search_budget=1)
    assert selected.selected_pair == _pair()
    assert selected.points == ((0, 0), (10, 0))
    assert selected.budget_hit and selected.search_expansions == 1
    assert len(selected.attempts) == len(calls) == 1


def test_shared_budget_is_not_reset_per_pair_and_preserves_best_found():
    selected = _select((_pair(),) * 4, search_budget=2)
    assert selected.budget_hit and selected.search_expansions == 2
    assert [item.outcome for item in selected.attempts] == ["accepted", "eligible-not-selected"]
    assert selected.selected_pair == _pair()


def test_nonbinding_budget_preserves_legacy_best_candidate_and_attempt_bytes():
    legacy = _select((_pair(),) * 3)
    explicit = _select((_pair(),) * 3, search_budget=10000)
    assert (explicit.selected_pair, explicit.points, explicit.attempts) == (
        legacy.selected_pair, legacy.points, legacy.attempts)
    assert explicit.search_expansions == 3 and not explicit.budget_hit


def test_each_selection_has_a_fresh_budget_and_immutable_receipt():
    first = _select((_pair(),) * 3, search_budget=1)
    second = _select((_pair(),) * 3, search_budget=1)
    assert first == second
    from dataclasses import FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        first.search_expansions = 0


def test_budget_exhaustion_without_accepted_route_is_limited_not_impossible():
    selected = _select((_pair(),) * 3, accept=lambda points: False,
                       search_budget=1)
    assert selected.selected_pair is None
    assert selected.budget_hit and selected.search_expansions == 1
    assert len(selected.attempts) == 1
    assert selected.attempts[0].search_failure == "E_PRESENTATION_ROUTE_LIMIT"


def test_frontier_accounting_and_graph_cache_hits_charge_equally():
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("obstacle", "mark", "timeline", ObstacleRect(4, -1, 6, 1)))
    receipts = []
    for _ in range(2):
        budget = search.RelationExpansionBudget(8)
        with pytest.raises(search.RouteSearchFailure, match="E_PRESENTATION_ROUTE_LIMIT"):
            list(search.orthogonal_route_candidates((0, 0), (10, 0), obstacles,
                bounds=(-2, -3, 12, 3), budget=budget))
        receipts.append((budget.expansions, budget.hit))
    assert receipts == [(8, True), (8, True)]


def test_early_iterator_close_has_no_hidden_or_deferred_charge():
    budget = search.RelationExpansionBudget(2)
    candidates = search.orthogonal_route_candidates((0, 0), (10, 0), (), budget=budget)
    assert next(candidates) == ((0, 0), (10, 0))
    assert budget.expansions == 1
    candidates.close()
    assert budget.expansions == 1 and not budget.hit


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
