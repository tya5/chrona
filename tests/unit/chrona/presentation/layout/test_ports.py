"""Finite connector boundary ports are Layout geometry, not Scene offsets."""
from __future__ import annotations

from decimal import Decimal

import pytest

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.ports import (
    coincident_endpoint_port_ids, connector_boundary_port, connector_boundary_ports,
    connector_egress_candidates,
)
from chrona.presentation.layout.surface_quality import MarkPlacement


def _mark(shape: str) -> MarkPlacement:
    bounds = Rect(Decimal(10), Decimal(20), Decimal(8), Decimal(8))
    return MarkPlacement("planned:item", "item", bounds, (10, 24), (18, 24), mark_shape=shape)


def test_span_start_finish_are_fixed_completed_ports() -> None:
    mark = _mark("span")
    assert connector_boundary_ports(mark, "start", (100, 100)) == (("start", (10, 24)),)
    assert connector_boundary_ports(mark, "finish", (0, 0)) == (("end", (18, 24)),)
    assert connector_boundary_ports(mark, "end", (0, 0)) == (("end", (18, 24)),)


@pytest.mark.parametrize(("endpoint", "start", "finish", "expected"), [
    ("start", None, (18, 24), ()),
    ("finish", (10, 24), None, ()),
    ("end", (10, 24), None, ()),
    ("finish", None, (18, 24), (("end", (18, 24)),)),
    ("start", (10, 24), None, (("start", (10, 24)),)),
])
def test_temporally_unavailable_span_endpoint_has_no_boundary_candidate(
        endpoint, start, finish, expected):
    mark = MarkPlacement("actual:item", "item", Rect(Decimal(10), Decimal(20), Decimal(8), Decimal(8)),
                         start, finish)
    assert connector_boundary_ports(mark, endpoint, (0, 0)) == expected
    candidates = connector_egress_candidates(mark, endpoint, (0, 0), ())
    if not expected:
        assert candidates == ()
    else:
        semantic = expected[0][1]
        assert candidates and all(candidate.semantic_port == semantic for candidate in candidates)


def test_direct_temporal_port_helper_raises_bounded_anchor_diagnostic_when_absent():
    mark = MarkPlacement("actual:item", "item", Rect(Decimal(10), Decimal(20), Decimal(8), Decimal(8)),
                         None, (18, 24))
    with pytest.raises(LayoutError) as caught:
        connector_boundary_port(mark, "start", (0, 0))
    assert caught.value.diagnostic_id == "E_PRESENTATION_ANCHOR_MISSING"
    assert caught.value.path == "/layout/connectorPort"


def test_point_ports_are_finite_deterministic_and_not_center() -> None:
    mark = _mark("point")
    candidates = connector_boundary_ports(mark, "at", (30, 40))
    assert len(candidates) == 4
    assert candidates[0] == ("end", (18, 24))
    assert candidates[1] == ("below", (14, 28))
    assert (14, 24) not in [port for _, port in candidates]
    assert candidates == connector_boundary_ports(mark, "at", (30, 40))


def test_body_port_uses_same_finite_boundary_policy() -> None:
    assert connector_boundary_ports(_mark("span"), "body", (14, 0))[0] == ("above", (14, 20))


def test_overlapping_comparison_sibling_exposes_temporal_endpoint_without_moving_it() -> None:
    current = MarkPlacement("planned:item", "item", Rect(Decimal(10), Decimal(20), Decimal(20), Decimal(8)),
                            (10, 24), (30, 24))
    scenario = MarkPlacement("planned:scenario:item", "item",
                             Rect(Decimal(5), Decimal(20), Decimal(30), Decimal(8)), (5, 24), (35, 24))
    unrelated = MarkPlacement("planned:other", "other",
                              Rect(Decimal(30), Decimal(20), Decimal(15), Decimal(8)), (30, 24), (45, 24))
    candidates = connector_egress_candidates(current, "end", (50, 40), (scenario, unrelated))
    assert len(candidates) == 3
    assert candidates[0].semantic_port == (30, 24)
    assert candidates[0].exposed_port == (35, 24)
    assert candidates[0].host_ids == ("planned:item", "planned:scenario:item")
    assert {candidate.side for candidate in candidates} == {"end", "above", "below"}
    assert all(candidate.semantic_port == (30, 24) for candidate in candidates)


def test_span_start_candidates_mirror_the_finish_and_keep_the_temporal_port() -> None:
    mark = _mark("span")
    candidates = connector_egress_candidates(mark, "start", (-20, 24), ())
    assert {candidate.side for candidate in candidates} == {"start", "above", "below"}
    assert all(candidate.semantic_port == (10, 24) for candidate in candidates)
    assert next(candidate for candidate in candidates if candidate.side == "start").exposed_port == (10, 24)


@pytest.mark.parametrize(("endpoint", "side", "semantic", "exposed", "blocker"), (
    ("start", "above", (10, 24), (10, 20), (9.5, 21.5, 10.5, 22.5)),
    ("start", "below", (10, 24), (10, 28), (9.5, 25.5, 10.5, 26.5)),
    ("end", "above", (18, 24), (18, 20), (17.5, 21.5, 18.5, 22.5)),
    ("end", "below", (18, 24), (18, 28), (17.5, 25.5, 18.5, 26.5)),
))
def test_span_above_and_below_corridors_are_checked_against_shared_obstacle_index(
        endpoint, side, semantic, exposed, blocker) -> None:
    mark = _mark("span")
    candidates = connector_egress_candidates(mark, endpoint, (50, 40), ())
    candidate = next(item for item in candidates if item.side == side)
    assert candidate.semantic_port == semantic
    assert candidate.exposed_port == exposed

    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle(mark.placement_id, "mark", "timeline",
                              ObstacleRect(10, 20, 18, 28)))
    index.add(SurfaceObstacle("blocking-label", "label", "timeline", ObstacleRect(*blocker)))
    assert index.egress_collisions(ObstacleSegment(candidate.semantic_port, candidate.exposed_port),
                                   host_ids=(mark.placement_id,),
                                   classes=("mark", "label")) == (
        index.select(classes=("label",))[0],)


def test_coincident_port_aliases_are_exact_and_host_scoped() -> None:
    index = SurfaceObstacleIndex()
    for placement_id, x in (("port:planned:item:end", 18),
                            ("port:planned:scenario:item:start", 18),
                            ("port:planned:other:end", 18),
                            ("port:planned:item:above", 14)):
        index.add(SurfaceObstacle(placement_id, "port", "timeline",
                                  ObstacleRect(x - 0.01, 24 - 0.01, x + 0.01, 24 + 0.01)))
    assert coincident_endpoint_port_ids(index, (18, 24),
                                         ("planned:item", "planned:scenario:item")) == (
        "port:planned:item:end", "port:planned:scenario:item:start")
