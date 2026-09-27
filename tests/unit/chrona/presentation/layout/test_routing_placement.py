import json

import pytest

from chrona.presentation.layout.routing import (
    RouteAttemptEvidence, RouteSuppressionEvidence, place_relation_route,
    relation_route_quality, route_quality_attempt,
)


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
