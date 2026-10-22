"""Timeline relations do not ride along primary mark boundaries (#1841)."""
import pytest

from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, segment_closed_rect_contact_interval,
)
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.surface_routes import _primary_egress_blockers, _primary_mark_contact_is_clear


def _bounds(placement_id="planned:source", *, left=0, top=0, right=100, bottom=10):
    return ((placement_id, ObstacleRect(left, top, right, bottom)),)


def _parts(points, *, physical_ids=()):
    return tuple((start, end, tuple(physical_ids)) for start, end in zip(points, points[1:]))


def test_closed_contact_interval_distinguishes_boundary_run_from_isolated_touch():
    rect = ObstacleRect(0, 0, 100, 10)
    assert segment_closed_rect_contact_interval(ObstacleSegment((-5, 0), (5, 0)), rect) == (0.5, 1.0)
    assert segment_closed_rect_contact_interval(ObstacleSegment((-5, 5), (0, 5)), rect) == (1.0, 1.0)
    assert segment_closed_rect_contact_interval(ObstacleSegment((-5, -5), (-1, -1)), rect) is None


def test_temporal_tip_touch_and_outward_detour_are_allowed():
    source = ConnectorEgress("end", (100, 5), (100, 5), ("planned:source",))
    target = ConnectorEgress("start", (200, 5), (200, 5), ("planned:target",))
    bounds = (*_bounds(), *_bounds("planned:target", left=200, right=300))

    direct = ((100, 5), (200, 5))
    outward_detour = ((100, 5), (110, 5), (110, -15), (190, -15), (190, 5), (200, 5))
    assert _primary_mark_contact_is_clear(_parts(direct), bounds,
        route_start=direct[0], route_end=direct[-1], source_egress=source, target_egress=target)
    assert _primary_mark_contact_is_clear(_parts(outward_detour), bounds,
        route_start=outward_detour[0], route_end=outward_detour[-1],
        source_egress=source, target_egress=target)


def test_mandatory_end_face_corridor_is_rejected_before_middle_path_search():
    invalid = ConnectorEgress("above", (100, 5), (100, 0), ("planned:source",))
    outward = ConnectorEgress("end", (100, 5), (110, 5), ("planned:source",))
    assert _primary_egress_blockers(invalid, _bounds()) == ("planned:source",)
    assert _primary_egress_blockers(outward, _bounds()) == ()
    assert _primary_egress_blockers(
        ConnectorEgress("end", (100, 5), (100, 5), ("planned:source",)), _bounds()) == ()


def test_egress_preflight_keeps_named_physical_scope_and_selected_stage_bounds():
    hosted = ConnectorEgress("end", (50, 5), (100, 5), ("point",),
                             corridor_host_ids=("planned:source",))
    assert _primary_egress_blockers(hosted, _bounds()) == ()
    foreign = _bounds("foreign", left=70, right=80)
    assert _primary_egress_blockers(hosted, (*_bounds(), *foreign)) == ("foreign",)
    assert _primary_egress_blockers(hosted, _bounds()) == ()


def test_positive_length_source_top_edge_and_end_face_slides_are_blocked():
    source = ConnectorEgress("end", (100, 5), (100, 5), ("planned:source",))
    target = ConnectorEgress("start", (200, 5), (200, 5), ("planned:target",))
    bounds = (*_bounds(), *_bounds("planned:target", left=200, right=300))
    top_edge = ((100, 5), (105, 5), (105, 0), (50, 0), (50, -15), (190, -15), (190, 5), (200, 5))
    end_face = ((100, 5), (100, 0), (115, 0), (115, -15), (190, -15), (190, 5), (200, 5))

    assert not _primary_mark_contact_is_clear(_parts(top_edge), bounds,
        route_start=top_edge[0], route_end=top_edge[-1], source_egress=source, target_egress=target)
    assert not _primary_mark_contact_is_clear(_parts(end_face), bounds,
        route_start=end_face[0], route_end=end_face[-1], source_egress=source, target_egress=target)


def test_only_named_endpoint_touch_and_segment_local_physical_corridors_are_exempt():
    source = ConnectorEgress("end", (100, 5), (100, 5), ("planned:source",))
    unrelated_touch = ((0, 5), (100, 5))
    assert not _primary_mark_contact_is_clear(_parts(unrelated_touch), _bounds(),
        route_start=unrelated_touch[0], route_end=unrelated_touch[-1], source_egress=source)

    corridor = ((0, 5), (100, 5))
    assert _primary_mark_contact_is_clear(_parts(corridor, physical_ids=("planned:source",)),
        _bounds(), route_start=corridor[0], route_end=corridor[-1], source_egress=source)


def test_tiny_positive_primary_bounds_are_not_dropped():
    tiny = (("planned:tiny", ObstacleRect(0, 0, 1e-12, 1e-12)),)
    crossing = ((-1e-12, 0.5e-12), (2e-12, 0.5e-12))
    assert not _primary_mark_contact_is_clear(_parts(crossing), tiny,
        route_start=crossing[0], route_end=crossing[-1])


@pytest.mark.parametrize("policy", ["first-fit", "best"])
def test_padded_window_outward_candidate_passes_normal_pair_validators(monkeypatch, policy):
    """Endpoint padding admits a safe route independently of sparse graph search."""
    from dataclasses import replace
    from datetime import date

    from chrona.presentation.layout import surface_routes
    from tests.unit.chrona.presentation.scene import test_relation_rounded_corners as fixture

    original_projection = fixture.ReviewProjection
    original_manifest = fixture._manifest
    original_select = surface_routes.select_relation_route
    captured = []

    def padded_projection(*args, **kwargs):
        projection = original_projection(*args, **kwargs)
        return replace(projection, window=(date(2026, 1, 15), date(2026, 3, 1)))

    def capture_pair_validators(pairs, **kwargs):
        result = original_select(pairs, **kwargs)
        pair = next((pair for pair in pairs if pair[0].side == "start" and pair[1].side == "end"), None)
        if pair is not None:
            source, target = pair
            x0, y0 = source.semantic_port
            x1, y1 = target.semantic_port
            middle_y = (y0 + y1) / 2
            source_run, target_run = kwargs["outward_runs"]
            candidate = ((x0, y0), (x0 - source_run, y0),
                         (x0 - source_run, middle_y), (x1 + target_run, middle_y),
                         (x1 + target_run, y1), (x1, y1))
            short_candidate = ((x0, y0), (x0 - 2, y0), (x0 - 2, middle_y),
                               (x1 + 2, middle_y), (x1 + 2, y1), (x1, y1))
            captured.append((kwargs["bounds"], source, target, candidate,
                             kwargs["prepare"](candidate, source, target),
                             kwargs["accept"](candidate), result.selected_pair,
                             result.settled_by_shape, result.points,
                             kwargs["prepare"](short_candidate, source, target),
                             kwargs["accept"](short_candidate)))
        return result

    monkeypatch.setattr(fixture, "ReviewProjection", padded_projection)
    monkeypatch.setattr(fixture, "_manifest", lambda *args, **kwargs: replace(
        original_manifest(*args, **kwargs), relation_search=policy))
    monkeypatch.setattr(surface_routes, "select_relation_route", capture_pair_validators)

    relation = {"id": "dep", "from": {"object": "a", "endpoint": "start"},
                "to": {"object": "b", "endpoint": "end"}}
    _, drawn = fixture._drawn(0, relation=relation)

    (bounds, source, target, candidate, prepared, accepted, selected_pair,
     settled_by_shape, points, short_prepared, short_accepted) = captured[0]
    assert bounds == (504.0, 48.0, 996.0, 1000.0)
    assert source.semantic_port == source.exposed_port == (688.8888888888889, 286.0)
    assert target.semantic_port == target.exposed_port == (900.0, 762.0)
    assert bounds[0] < source.semantic_port[0] < bounds[2]
    assert bounds[0] < target.semantic_port[0] < bounds[2]
    assert len(candidate) == 6
    assert prepared == candidate
    assert accepted is True
    assert short_prepared is None or not short_accepted
    assert selected_pair == (source, target)
    # First-fit retains its finite proposal; best can now find the same legal
    # endpoint domain through the minimum-lead-aware ordinary graph.
    assert settled_by_shape is (policy == "first-fit")
    assert drawn.points == points
    assert len(points) == 6
