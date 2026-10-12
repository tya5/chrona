"""Route corridors reserved for member names (#687, I687-1): the class, the index copy and the empty plan."""
from chrona.presentation.layout.obstacles import (
    ROUTE_RESERVE_CLASS, ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.routing import ROUTE_GRID_OFFSET, route_orthogonal
from chrona.presentation.layout.surface_lane_route_plan import LaneRoutePlan

ROUTE_CLASSES = ("mark", "text", "label-visual")
NAME_CLASSES = ("mark", "text", "label-visual", "dependency-route", ROUTE_RESERVE_CLASS)
CORRIDOR = SurfaceObstacle("route-reserve:r:segment:0", ROUTE_RESERVE_CLASS, "timeline",
                           ObstacleSegment((50.0, 0.0), (50.0, 100.0), 1.5 + 2 * ROUTE_GRID_OFFSET))


def test_a_corridor_blocks_a_name_but_is_invisible_to_routes_and_other_classes():
    index = SurfaceObstacleIndex()
    index.add(CORRIDOR)
    name = ObstacleRect(45.0, 10.0, 80.0, 30.0)
    assert index.collisions(name, classes=NAME_CLASSES) == (CORRIDOR,)
    assert index.collisions(name, classes=ROUTE_CLASSES) == ()
    assert index.collisions(name, classes=("mark", "text", "label-visual", "dependency-route")) == ()
    assert index.collisions(ObstacleSegment((0.0, 20.0), (100.0, 20.0)), classes=ROUTE_CLASSES) == ()


def test_the_router_ignores_a_corridor_and_keeps_its_straight_route():
    index = SurfaceObstacleIndex()
    index.add(CORRIDOR)
    path = route_orthogonal((0.0, 20.0), (100.0, 20.0), index, bounds=(0.0, 0.0, 100.0, 100.0),
                            classes=ROUTE_CLASSES, regions=("timeline", "group-header"))
    assert path == ((0.0, 20.0), (100.0, 20.0))


def test_a_copy_is_independent_of_the_index_it_came_from():
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("a", "mark", "timeline", ObstacleRect(0.0, 0.0, 10.0, 10.0)))
    clone = index.copy()
    clone.add(CORRIDOR)
    index.add(SurfaceObstacle("b", "text", "timeline", ObstacleRect(20.0, 0.0, 30.0, 10.0)))
    assert [item.placement_id for item in clone.all()] == ["a", CORRIDOR.placement_id]
    assert [item.placement_id for item in index.all()] == ["a", "b"]
    assert clone.has("a") and not index.has(CORRIDOR.placement_id)


def test_an_empty_plan_reserves_nothing():
    assert LaneRoutePlan().reservations == () and LaneRoutePlan().protected == ()


def test_budget_hit_facts_survive_rejected_lane_reservation_rehearsal(monkeypatch):
    from types import SimpleNamespace
    from chrona.presentation.layout import surface_lane_route_plan as plan
    from chrona.presentation.layout.surface_routes import SurfaceRoutesContext, SurfaceRoutesBatch
    from chrona.presentation.layout.surface_member_labels import SurfaceMemberLabelsBatch
    from chrona.presentation.model.info_diagnostics import RelationSearchBudgetHit
    names = SurfaceMemberLabelsBatch((), (), (), (), (), (), (), frozenset())
    facts = []
    def batch(pass_name, suppressed):
        fact = RelationSearchBudgetHit("table-timeline", "relation:r", pass_name, 2, 2)
        facts.append(fact)
        return SurfaceRoutesBatch((SimpleNamespace(relation_id="relation:r", suppressed=suppressed),),
                                  (), {}, {}, {}, (), (fact,))
    def rehearse(context, reservations, progress_pass="lane-rehearsal"):
        return names, batch(progress_pass, True)
    monkeypatch.setattr(plan, "_rehearse", rehearse)
    monkeypatch.setattr(plan, "compose_surface_routes", lambda context: batch(context.progress_pass, False))
    monkeypatch.setattr(plan, "_corridor", lambda item, context: ())
    context = plan.LaneRoutePlanContext(
        SimpleNamespace(request=SimpleNamespace(surface_content=SimpleNamespace(relations=(1,))),
                        projection=SimpleNamespace(lane_membership=object())),
        (SimpleNamespace(semantic_id="memberLabel"),), (), SurfaceObstacleIndex(),
        lambda obstacles, text: SurfaceRoutesContext(None, None, (), (), (), (),
            (0, 0, 0, 0), None, {}, text, obstacles))
    result = plan.plan_lane_route_reservations(context)
    assert result.reservations == result.protected == ()
    assert result.routing_info == tuple(facts)
    assert [fact.pass_name for fact in facts] == [
        "lane-rehearsal", "lane-reference", "lane-reservation-rehearsal"]
