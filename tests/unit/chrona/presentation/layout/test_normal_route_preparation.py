"""The normal port-pair domains are prepared once, in route-selection order."""
from dataclasses import replace

from chrona.presentation.layout import surface_routes
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle
from chrona.presentation.layout.relation_routing_order import dependency_routing_order
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.model.surface_content import RelationPresentationFact
from tests.unit.chrona.presentation.layout.test_window_lane_completion import _request
from tests.unit.chrona.presentation.layout.test_window_relation_completion import _surviving_relation_request


def _relation(relation_id, source, target):
    return RelationPresentationFact(relation_id, source, "end", target, "start", 0, None, "dependency")


def test_exact_prepared_normal_pairs_are_passed_to_the_first_route_selection(monkeypatch):
    batches = []
    selections = []
    prepare = surface_routes.prepare_normal_relation_routes
    select = surface_routes.select_relation_route

    def capture_prepared(context):
        batch = prepare(context)
        batches.append((context, batch))
        return batch

    def capture_selection(pairs, **kwargs):
        selections.append(pairs)
        return select(pairs, **kwargs)

    monkeypatch.setattr(surface_routes, "prepare_normal_relation_routes", capture_prepared)
    monkeypatch.setattr(surface_routes, "select_relation_route", capture_selection)
    compose_surface_layout(_surviving_relation_request())

    assert batches and selections
    first_batch = batches[0][1]
    first_occurrence = next(occurrence for entry in first_batch.entries
                             for occurrence in entry.occurrences if occurrence.port_pairs)
    assert first_batch.total_potential_port_pairs == sum(
        len(occurrence.port_pairs) for entry in first_batch.entries for occurrence in entry.occurrences)
    assert selections[0] is first_occurrence.port_pairs


def test_suppressed_endpoint_entries_keep_their_order_and_contribute_no_pairs(monkeypatch):
    relations = (_relation("active", "object-4", "object-4"),
                 _relation("outside", "object-1", "object-4"))
    request = _request()
    request = replace(request, surface_content=replace(request.surface_content, relations=relations))
    batches = []
    prepare = surface_routes.prepare_normal_relation_routes

    def capture(context):
        result = prepare(context)
        batches.append(result)
        return result

    monkeypatch.setattr(surface_routes, "prepare_normal_relation_routes", capture)
    placement = compose_surface_layout(request).placement
    batch = batches[-1]
    expected = dependency_routing_order(relations)
    assert [(entry.declared_index, entry.relation.relation_id) for entry in batch.entries] == [
        (index, relation.relation_id) for index, relation in expected]
    outside = next(entry for entry in batch.entries if entry.relation.relation_id == "outside")
    assert outside.occurrences
    assert all(item.window_endpoint_absences and item.port_pairs == () for item in outside.occurrences)
    assert batch.total_potential_port_pairs == sum(
        len(item.port_pairs) for entry in batch.entries for item in entry.occurrences)
    assert tuple(item.source_ref for item in placement.relations) == tuple(
        item.relation_id for _index, item in expected)
    assert placement.relations[-1].suppressed


def test_normal_candidate_pairs_ignore_later_route_and_port_obstacles(monkeypatch):
    batches = []
    prepare = surface_routes.prepare_normal_relation_routes

    def capture(context):
        batch = prepare(context)
        batches.append((context, batch))
        return batch

    monkeypatch.setattr(surface_routes, "prepare_normal_relation_routes", capture)
    compose_surface_layout(_surviving_relation_request())
    context, prepared = batches[-1]
    before = tuple(item.port_pairs for entry in prepared.entries for item in entry.occurrences)
    context.obstacles.add(SurfaceObstacle("later-route", "dependency-route", "timeline",
        ObstacleSegment((0, 0), (1, 0))))
    context.obstacles.add(SurfaceObstacle("later-port", "port", "timeline",
        ObstacleRect(0, 0, 1, 1)))
    after = prepare(context)
    assert tuple(item.port_pairs for entry in after.entries for item in entry.occurrences) == before
