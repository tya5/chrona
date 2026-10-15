from decimal import Decimal

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.ports import (
    ConnectorEgress, connector_egress_candidates, physical_host_neighbors,
    split_route_at_physical_corridors,
)
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacleIndex, segment_length_inside_rect,
)
from chrona.presentation.layout.routing import select_relation_route
from chrona.presentation.layout.surface_routes import _stub_fragment_clears_physical_hosts
from chrona.presentation.layout.surface_quality import MarkPlacement, PhysicalMarkHost
from chrona.presentation.layout.obstacles import SurfaceObstacle


def _span():
    return MarkPlacement("planned:span", "span", Rect(Decimal(10), Decimal(20), Decimal(40), Decimal(10)),
                         (10.0, 25.0), (50.0, 25.0), mark_shape="span")


def _point(placement_id, source_ref, bounds, host_id="planned:span"):
    return MarkPlacement(placement_id, source_ref, bounds, None, None, mark_shape="point",
                         physical_host=PhysicalMarkHost(host_id, "physical-row"))


def test_hosted_point_egress_uses_only_its_exact_parent_span():
    host = _span()
    point = _point("planned:gate", "gate", Rect(Decimal(8), Decimal(23), Decimal(4), Decimal(4)))
    unrelated = _point("planned:other", "other", Rect(Decimal(30), Decimal(23), Decimal(4), Decimal(4)),
                       host_id="planned:different-span")

    neighbors = physical_host_neighbors(point, (point, host, unrelated), "at")
    assert neighbors == (host,)
    candidates = connector_egress_candidates(point, "at", (70.0, 25.0), (), explicit_neighbors=neighbors)
    end = next(candidate for candidate in candidates if candidate.side == "end")
    assert end.host_ids == (point.placement_id,)
    assert end.corridor_host_ids == (host.placement_id,)
    assert end.semantic_port == (12.0, 25.0)
    assert end.exposed_port == (50.0, 25.0)


def test_span_gets_reciprocal_authority_only_from_exact_points_covering_endpoint():
    host = _span()
    covering = _point("planned:gate", "gate", Rect(Decimal(8), Decimal(23), Decimal(4), Decimal(4)))
    other_hosted = _point("planned:other", "other", Rect(Decimal(30), Decimal(23), Decimal(4), Decimal(4)))
    neighbors = physical_host_neighbors(host, (host, covering, other_hosted), "start")
    assert neighbors == (covering,)

    candidates = connector_egress_candidates(host, "start", (0.0, 25.0), (),
                                               explicit_neighbors=neighbors)
    left = next(candidate for candidate in candidates if candidate.side == "start")
    assert left.host_ids == (host.placement_id,)
    assert left.corridor_host_ids == (covering.placement_id,)
    assert left.exposed_port == (8.0, 25.0)

    assert physical_host_neighbors(host, (host, covering, other_hosted), "end") == ()


def test_reduced_collinear_segment_is_split_at_exposed_boundary():
    host = _span()
    point = _point("planned:gate", "gate", Rect(Decimal(8), Decimal(23), Decimal(4), Decimal(4)))
    egress = next(candidate for candidate in connector_egress_candidates(
        point, "at", (70.0, 25.0), (), explicit_neighbors=(host,)) if candidate.side == "end")

    pieces = split_route_at_physical_corridors(((12.0, 25.0), (70.0, 25.0)), egress, None)
    assert pieces == (
        ((12.0, 25.0), (50.0, 25.0), (host.placement_id,)),
        ((50.0, 25.0), (70.0, 25.0), ()),
    )


def test_source_round_head_setback_keeps_corridor_authority_until_exposed_boundary():
    host = _span()
    point = _point("planned:gate", "gate", Rect(Decimal(8), Decimal(23), Decimal(4), Decimal(4)))
    egress = next(candidate for candidate in connector_egress_candidates(
        point, "at", (70.0, 25.0), (), explicit_neighbors=(host,)) if candidate.side == "end")

    pieces = split_route_at_physical_corridors(((16.0, 25.0), (50.0, 25.0), (70.0, 25.0)), egress, None)
    assert pieces == (
        ((16.0, 25.0), (50.0, 25.0), (host.placement_id,)),
        ((50.0, 25.0), (70.0, 25.0), ()),
    )


def test_target_round_head_setback_mirrors_source_corridor_authority():
    host = _span()
    point = _point("planned:gate", "gate", Rect(Decimal(8), Decimal(23), Decimal(4), Decimal(4)))
    egress = ConnectorEgress("start", (12.0, 25.0), (10.0, 25.0), ("planned:gate",),
                             corridor_host_ids=(point.placement_id,))

    pieces = split_route_at_physical_corridors(((0.0, 25.0), (10.0, 25.0), (11.0, 25.0)), None, egress)
    assert pieces == (
        ((0.0, 25.0), (10.0, 25.0), ()),
        ((10.0, 25.0), (11.0, 25.0), (point.placement_id,)),
    )


def test_route_that_leaves_and_reenters_corridor_gets_no_physical_authority():
    host = _span()
    point = _point("planned:gate", "gate", Rect(Decimal(8), Decimal(23), Decimal(4), Decimal(4)))
    egress = next(candidate for candidate in connector_egress_candidates(
        point, "at", (70.0, 25.0), (), explicit_neighbors=(host,)) if candidate.side == "end")

    path = ((12.0, 25.0), (20.0, 25.0), (20.0, 30.0), (50.0, 30.0), (50.0, 25.0))
    pieces = split_route_at_physical_corridors(path, egress, None)
    assert all(not physical_ids for _, _, physical_ids in pieces)


def test_no_physical_authority_when_reduction_loses_the_recorded_corridor():
    host = _span()
    point = _point("planned:gate", "gate", Rect(Decimal(8), Decimal(23), Decimal(4), Decimal(4)))
    egress = next(candidate for candidate in connector_egress_candidates(
        point, "at", (70.0, 25.0), (), explicit_neighbors=(host,)) if candidate.side == "end")
    assert split_route_at_physical_corridors(((12.0, 25.0), (12.0, 10.0), (70.0, 10.0)), egress, None)
    assert all(not physical_ids for _, _, physical_ids in
               split_route_at_physical_corridors(((12.0, 25.0), (12.0, 10.0), (70.0, 10.0)), egress, None))


def test_unchanged_primary_crossing_is_rejected_by_final_acceptance_guard():
    source = ConnectorEgress("end", (0.0, 5.0), (0.0, 5.0), ())
    target = ConnectorEgress("start", (10.0, 5.0), (10.0, 5.0), ())
    unsafe = ((0.0, 5.0), (10.0, 5.0))
    primary_interior = ObstacleRect(4.0, 1.0, 6.0, 9.0)

    result = select_relation_route(((source, target),), obstacles=SurfaceObstacleIndex(),
        bounds=(-1.0, -1.0, 11.0, 11.0), source_host_id=None, target_host_id=None,
        relation_scene_id="relation:primary-crossing", max_bends=2, max_detour_ratio=2.0,
        preferred_routes=(((source, target), unsafe),),
        accept=lambda path: all(segment_length_inside_rect(ObstacleSegment(a, b), primary_interior) <= 1e-9
                                for a, b in zip(path, path[1:])))

    assert result.selected_pair is None


def test_stub_physical_check_is_inactive_without_explicit_host_corridor():
    ordinary = ConnectorEgress("end", (0.0, 5.0), (2.0, 5.0), ("planned:gate",))
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("planned:gate", "mark", "timeline", ObstacleRect(-1, 3, 1, 7)))

    assert _stub_fragment_clears_physical_hosts(((0.0, 5.0), (2.0, 5.0)), ordinary,
        source=True, obstacles=obstacles)


def test_source_stub_post_boundary_crossing_of_physical_span_is_rejected():
    point = ConnectorEgress("end", (0.0, 5.0), (5.0, 5.0), ("planned:gate",),
                            corridor_host_ids=("planned:span",))
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("planned:gate", "mark", "timeline", ObstacleRect(-1, 3, 1, 7)))
    obstacles.add(SurfaceObstacle("planned:span", "mark", "timeline", ObstacleRect(1, 0, 5, 10)))

    assert not _stub_fragment_clears_physical_hosts(((0.0, 5.0), (5.0, 5.0), (3.0, 5.0)),
        point, source=True, obstacles=obstacles)


def test_reciprocal_target_stub_post_boundary_crossing_of_hosted_point_is_rejected():
    span = ConnectorEgress("start", (10.0, 5.0), (8.0, 5.0), ("planned:span",),
                           corridor_host_ids=("planned:gate",))
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("planned:span", "mark", "timeline", ObstacleRect(10, 0, 20, 10)))
    obstacles.add(SurfaceObstacle("planned:gate", "mark", "timeline", ObstacleRect(8, 3, 12, 7)))

    assert not _stub_fragment_clears_physical_hosts(((14.0, 5.0), (8.0, 5.0), (10.0, 5.0)),
        span, source=False, obstacles=obstacles)
