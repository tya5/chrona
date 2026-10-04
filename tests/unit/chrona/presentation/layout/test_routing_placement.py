import json

import pytest

from chrona.presentation.layout.routing import (
    RouteAttemptEvidence, RouteSuppressionEvidence, place_relation_route,
    relation_route_quality, route_quality_attempt, select_relation_route,
)
from chrona.presentation.layout.obstacles import SurfaceObstacleIndex
from chrona.presentation.layout.ports import ConnectorEgress


def test_place_relation_route_returns_completed_orthogonal_points():
    points = place_relation_route(source_port=(1, 1), target_port=(9, 9), obstacles=(), bounds=(0, 0, 10, 10))
    assert points[0] == (1, 1) and points[-1] == (9, 9)


def test_relation_quality_applies_declared_bend_and_detour_limits():
    route = ((1, 1), (1, 9), (9, 9))
    assert relation_route_quality(route, max_bends=1, max_detour_ratio=1.0)
    assert not relation_route_quality(route, max_bends=0, max_detour_ratio=2.0)


def test_lane_route_attempts_retain_measured_quality_and_primary_suppression_cause():
    path = ((0.0, 0.0), (0.0, 10.0), (10.0, 10.0))
    rejected = route_quality_attempt("right", "left", path, max_bends=0, max_detour_ratio=1.5)
    assert (rejected.outcome, rejected.length, rejected.direct_length, rejected.bends) == (
        "quality-rejected", 20.0, 20.0, 1)
    evidence = RouteSuppressionEvidence("r1", (
        RouteAttemptEvidence("top", "top", "egress-collision", blocker_ids=("name:task",)),
        RouteAttemptEvidence("bottom", "bottom", "no-route-found",
                             search_failure="E_CONNECTOR_UNROUTABLE"),
        rejected,
    ))
    assert evidence.primary_cause == "quality-rejected"
    assert evidence.diagnostic.startswith("I_LAYOUT_LANE_ROUTE_CAUSE:")
    payload = json.loads(evidence.diagnostic.removeprefix("I_LAYOUT_LANE_ROUTE_CAUSE:"))
    assert payload["relationId"] == "r1"
    assert payload["primaryCause"] == "quality-rejected"
    assert payload["attempts"][0]["blockerIds"] == ["name:task"]
    assert payload["attempts"][1]["searchFailure"] == "E_CONNECTOR_UNROUTABLE"
    assert payload["attempts"][2]["length"] == 20.0
    assert payload["attempts"][2]["maxBends"] == 0


def test_route_attempt_rejects_unmeasured_or_falsely_classified_quality():
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID"):
        RouteAttemptEvidence("top", "bottom", "egress-collision")
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID"):
        RouteAttemptEvidence("top", "bottom", "accepted", length=20, direct_length=10,
                             bends=1, max_bends=0, max_detour_ratio=1.0)
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID"):
        RouteSuppressionEvidence("r1", (route_quality_attempt(
            "top", "bottom", ((0, 0), (10, 0)), max_bends=1, max_detour_ratio=1.0),))


def test_lane_port_pair_search_retains_rejected_and_accepted_measured_attempts():
    source = ConnectorEgress("end", (0, 0), (0, 0), ())
    target = ConnectorEgress("start", (10, 10), (10, 10), ())
    inputs = dict(port_pairs=((source, target),), obstacles=SurfaceObstacleIndex(),
                  bounds=(-1, -1, 11, 11), source_host_id=None, target_host_id=None,
                  relation_scene_id="relation:r1", max_detour_ratio=1.0)
    rejected = select_relation_route(**inputs, max_bends=0)
    assert rejected.selected_pair is None
    assert rejected.attempts[0].outcome == "quality-rejected"
    assert RouteSuppressionEvidence("r1", rejected.attempts).primary_cause == "quality-rejected"
    accepted = select_relation_route(**inputs, max_bends=1)
    assert accepted.selected_pair == (source, target)
    assert accepted.points[0] == (0, 0) and accepted.points[-1] == (10, 10)
    assert accepted.attempts[0].outcome == "accepted"


def test_lane_selection_retains_primary_mark_rejection_and_tries_the_next_pair():
    source = ConnectorEgress("end", (0, 0), (0, 0), ())
    blocked = ConnectorEgress("start", (10, 0), (10, 0), ())
    safe = ConnectorEgress("above", (10, 10), (10, 10), ())
    selection = select_relation_route(((source, blocked), (source, safe)),
        obstacles=SurfaceObstacleIndex(), bounds=(-1, -1, 11, 11), source_host_id=None, target_host_id=None,
        relation_scene_id="relation:dep", max_bends=4, max_detour_ratio=2,
        accept=lambda points: points[-1] != blocked.semantic_port)
    assert selection.selected_pair == (source, safe)
    assert selection.attempts[0].search_failure == "E_LAYOUT_ROUTE_THROUGH_MARK"
    assert selection.attempts[1].outcome == "accepted"


def _pair(name, start, end):
    source = ConnectorEgress(f"{name}-source", start, start, ())
    target = ConnectorEgress(f"{name}-target", end, end, ())
    return source, target


def _select_ranked(pairs, rank, **kwargs):
    return select_relation_route(
        pairs,
        obstacles=SurfaceObstacleIndex(),
        bounds=(-1, -1, 11, 11),
        source_host_id=None,
        target_host_id=None,
        relation_scene_id="relation:ranked",
        max_bends=4,
        max_detour_ratio=2,
        rank=rank,
        **kwargs,
    )


def test_ranked_selection_chooses_the_best_eligible_pair_even_when_declared_later():
    first = _pair("first", (0, 0), (10, 0))
    best = _pair("best", (0, 2), (10, 2))
    last = _pair("last", (0, 4), (10, 4))

    selection = _select_ranked(
        (first, best, last),
        rank=lambda _points, source, _target: (0 if source.side == "best-source" else 1,),
    )

    assert selection.selected_pair == best
    assert [attempt.outcome for attempt in selection.attempts] == [
        "eligible-not-selected", "accepted", "eligible-not-selected",
    ]
    assert sum(attempt.outcome == "accepted" for attempt in selection.attempts) == 1
    assert sum(attempt.outcome == "eligible-not-selected" for attempt in selection.attempts) == 2


def test_ranked_selection_keeps_the_first_declared_pair_for_stable_ties():
    first = _pair("first", (0, 0), (10, 0))
    second = _pair("second", (0, 2), (10, 2))

    selection = _select_ranked((first, second), rank=lambda _points, _source, _target: (1,))

    assert selection.selected_pair == first
    assert [attempt.outcome for attempt in selection.attempts] == ["accepted", "eligible-not-selected"]


def test_primary_mark_guard_rejects_a_higher_ranked_candidate_before_ranking():
    unsafe = _pair("unsafe", (0, 0), (10, 0))
    safe = _pair("safe", (0, 2), (10, 2))

    selection = _select_ranked(
        (unsafe, safe),
        rank=lambda _points, source, _target: (0 if source.side == "unsafe-source" else 1,),
        accept=lambda points: points[-1] != unsafe[1].semantic_port,
    )

    assert selection.selected_pair == safe
    assert selection.attempts[0].outcome == "no-route-found"
    assert selection.attempts[0].search_failure == "E_LAYOUT_ROUTE_THROUGH_MARK"
    assert selection.attempts[1].outcome == "accepted"
