"""Finite connector boundary ports are Layout geometry, not Scene offsets."""
from __future__ import annotations

from decimal import Decimal

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.ports import (
    coincident_endpoint_port_ids, connector_boundary_ports, connector_egress_candidates,
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
    assert len(candidates) == 4
    assert candidates[0].semantic_port == (30, 24)
    assert candidates[0].exposed_port == (35, 24)
    assert candidates[0].host_ids == ("planned:item", "planned:scenario:item")
    assert {candidate.side for candidate in candidates} == {"end", "start", "above", "below"}
    assert all(candidate.semantic_port == (30, 24) for candidate in candidates)


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
