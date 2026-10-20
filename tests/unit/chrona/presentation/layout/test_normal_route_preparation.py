"""The normal port-pair domains are prepared once, in route-selection order."""
from dataclasses import replace

from chrona.presentation.layout import surface_routes
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle
from chrona.presentation.layout.relation_routing_order import dependency_routing_order
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.model.surface_content import RelationPresentationFact
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
    relations = (_relation("active", "object-4", "object-6"),
                 _relation("outside", "object-1", "object-4"))
    # Use a real, routable span-to-span active relation. A self-loop used to
    # trigger recovery here and reached unrelated, invalid halo fixture data.
    request = _surviving_relation_request()
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
    # The prepared search batch is reordered for routing; completed placements
    # retain the authored relation order and the out-of-window entry is still
    # present as a typed suppression.
    assert tuple(item.source_ref for item in placement.relations) == tuple(
        relation.relation_id for relation in relations)
    assert next(item for item in placement.relations if item.source_ref == "outside").suppressed


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


def test_intrinsic_endpoint_footprints_use_admitted_spans_without_building_route_ports(monkeypatch):
    contexts = []
    prepare = surface_routes.prepare_normal_relation_routes

    def capture(context, **kwargs):
        contexts.append(context)
        return prepare(context, **kwargs)

    monkeypatch.setattr(surface_routes, "prepare_normal_relation_routes", capture)
    compose_surface_layout(_surviving_relation_request())
    context = contexts[-1]

    def unexpected(*_args, **_kwargs):
        raise AssertionError("intrinsic footprints must not build finite route candidates")

    monkeypatch.setattr(surface_routes, "connector_egress_candidates", unexpected)
    monkeypatch.setattr(surface_routes, "_entry_candidates", unexpected)
    footprints = surface_routes.intrinsic_relation_endpoint_footprints(context)
    assert footprints
    assert all(item.obstacle_class == "mark" and item.placement_id.startswith("intrinsic-endpoint:")
               and isinstance(item.geometry, (ObstacleRect, ObstacleSegment)) for item in footprints)
    assert len({item.placement_id for item in footprints}) == len(footprints)

    point_context = replace(context, marks=tuple(replace(mark, mark_shape="point")
                                                 for mark in context.marks))
    assert surface_routes.intrinsic_relation_endpoint_footprints(point_context) == ()
    open_span_context = replace(context, marks=tuple(replace(mark, mark_shape="open-span")
                                                      for mark in context.marks))
    assert surface_routes.intrinsic_relation_endpoint_footprints(open_span_context)
    body_context = replace(context, marks=tuple(replace(mark, mark_shape="body")
                                                for mark in context.marks))
    assert surface_routes.intrinsic_relation_endpoint_footprints(body_context) == ()


def test_intrinsic_endpoint_footprints_omit_window_absent_relation_occurrences(monkeypatch):
    contexts = []
    prepare = surface_routes.prepare_normal_relation_routes

    def capture(context, **kwargs):
        contexts.append(context)
        return prepare(context, **kwargs)

    monkeypatch.setattr(surface_routes, "prepare_normal_relation_routes", capture)
    request = _surviving_relation_request()
    outside = _relation("outside", "object-1", "object-4")
    request = replace(request, surface_content=replace(request.surface_content, relations=(outside,)))
    compose_surface_layout(request)
    footprints = surface_routes.intrinsic_relation_endpoint_footprints(contexts[-1])
    assert footprints == ()
