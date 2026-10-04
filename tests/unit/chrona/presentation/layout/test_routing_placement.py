import json

import pytest

from chrona.presentation.layout.routing import (
    RouteAttemptEvidence, RouteSuppressionEvidence, place_relation_route,
    relation_route_quality, repair_self_reversal, route_quality_attempt, select_relation_route,
)
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex, segment_length_inside_rect,
)
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


@pytest.mark.parametrize("ranked", [True, False])
def test_ranked_selection_retains_one_winner_and_stable_eligible_ties(ranked):
    source = ConnectorEgress("end", (0, 0), (0, 0), ())
    first = ConnectorEgress("start", (10, 0), (10, 0), ())
    second = ConnectorEgress("above", (10, 10), (10, 10), ())
    selection = select_relation_route(((source, first), (source, second)),
        obstacles=SurfaceObstacleIndex(), bounds=(-1, -1, 11, 11), source_host_id=None, target_host_id=None,
        relation_scene_id="relation:dep", max_bends=4, max_detour_ratio=2,
        rank=lambda points, left, right: (int(ranked and right is first),))
    assert selection.selected_pair == (source, second if ranked else first)
    assert [item.outcome for item in selection.attempts] == (
        ["eligible-not-selected", "accepted"] if ranked else ["accepted", "eligible-not-selected"])


def test_node_preference_cannot_admit_a_high_ranked_unsafe_or_over_budget_route():
    source = ConnectorEgress("end", (0, 0), (0, 0), ())
    over_budget = ConnectorEgress("above", (10, 10), (10, 10), ())
    unsafe = ConnectorEgress("below", (9, 0), (9, 0), ())
    safe = ConnectorEgress("start", (10, 0), (10, 0), ())
    ranked = []
    def score(points, left, right):
        ranked.append(right)
        return (int(right is safe),)
    selection = select_relation_route(tuple((source, target) for target in (over_budget, unsafe, safe)),
        obstacles=SurfaceObstacleIndex(), bounds=(-1, -1, 11, 11), source_host_id=None, target_host_id=None,
        relation_scene_id="relation:dep", max_bends=0, max_detour_ratio=2,
        accept=lambda points: points[-1] != unsafe.semantic_port, rank=score)
    assert selection.selected_pair == (source, safe)
    assert ranked == [safe]
    assert selection.attempts[0].outcome == "quality-rejected"
    assert selection.attempts[1].search_failure == "E_LAYOUT_ROUTE_THROUGH_MARK"


def test_rank_floor_skips_only_candidates_that_cannot_improve_the_selected_route():
    source = ConnectorEgress("end", (0, 0), (0, 0), ())
    target = ConnectorEgress("start", (10, 0), (10, 0), ())
    selection = select_relation_route(((source, target), (source, target)),
        obstacles=SurfaceObstacleIndex(), bounds=(-1, -1, 11, 11), source_host_id=None, target_host_id=None,
        relation_scene_id="relation:dep", max_bends=0, max_detour_ratio=1,
        rank=lambda *args: (False, 0), rank_floor=(False, 0))
    assert selection.selected_pair == (source, target)
    assert len(selection.attempts) == 1


REVERSING_TARGET_APPROACH = ((20.0, 110.0), (0.0, 110.0), (0.0, 90.0), (0.0, 95.0))


def _repair_target(right=10.0):
    bounds = ObstacleRect(0.0, 90.0, right, 100.0)
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("target", "mark", "timeline", bounds))

    def clear(points):
        return all(segment_length_inside_rect(ObstacleSegment(a, b), bounds) == 0
                   for a, b in zip(points, points[1:]))

    return obstacles, clear


def test_reversal_repair_skips_an_unsafe_first_jog_before_committing_a_later_safe_one():
    obstacles, clear = _repair_target()
    inputs = dict(classes=("mark",), regions=("timeline",), host_ids=("target",))
    unvalidated = repair_self_reversal(REVERSING_TARGET_APPROACH, obstacles, **inputs)
    assert unvalidated == ((20.0, 110.0), (8.0, 110.0), (8.0, 90.0), (0.0, 90.0), (0.0, 95.0))
    assert not clear(unvalidated), "the blanket host exemption admits the unsafe first jog"

    repaired = repair_self_reversal(REVERSING_TARGET_APPROACH, obstacles, **inputs, accept=clear)
    assert repaired == ((20.0, 110.0), (12.0, 110.0), (12.0, 90.0), (0.0, 90.0), (0.0, 95.0))
    assert clear(repaired)
    assert repaired[-2:] == REVERSING_TARGET_APPROACH[-2:], "the authorized terminal corridor stays exact"
    assert len(obstacles.all()) == 1, "private candidate checks do not add geometry"


def test_an_already_compliant_first_repair_keeps_its_exact_geometry():
    obstacles, clear = _repair_target(right=6.0)
    inputs = dict(classes=("mark",), regions=("timeline",), host_ids=("target",))
    before = repair_self_reversal(REVERSING_TARGET_APPROACH, obstacles, **inputs)
    after = repair_self_reversal(REVERSING_TARGET_APPROACH, obstacles, **inputs, accept=clear)
    assert clear(before)
    assert after == before


def test_lane_selection_recovers_the_same_port_pair_with_its_next_safe_repair(monkeypatch):
    import chrona.presentation.layout.routing as routing

    obstacles, clear = _repair_target()
    calls = []

    def body_route(**kwargs):
        calls.append(kwargs)
        return REVERSING_TARGET_APPROACH[:-1]

    monkeypatch.setattr(routing, "place_relation_route", body_route)
    source = ConnectorEgress("end", (20.0, 110.0), (20.0, 110.0), ())
    target = ConnectorEgress("above", (0.0, 95.0), (0.0, 90.0), ("target",))
    selected = select_relation_route(((source, target),), obstacles=obstacles,
        bounds=(-10.0, 80.0, 30.0, 120.0), source_host_id=None, target_host_id="target",
        relation_scene_id="relation:neutral", max_bends=4, max_detour_ratio=2,
        classes=("mark",), regions=("timeline",), accept=clear)

    assert len(calls) == 1
    assert selected.selected_pair == (source, target)
    assert selected.points == ((20.0, 110.0), (12.0, 110.0), (12.0, 90.0), (0.0, 90.0), (0.0, 95.0))
    assert [item.outcome for item in selected.attempts] == ["accepted"]
