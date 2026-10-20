"""Outward channel proposals stay inside ordinary route selection and validation."""

import pytest

from chrona.presentation.layout import route_search, routing
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
    segment_closed_rect_contact_interval,
)
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.relation_shapes import RelationShapeChannels
from chrona.presentation.layout.route_search import RouteSearchFailure
from chrona.presentation.layout.routing import route_quality_metrics, select_relation_route


BOUNDS = (0., 0., 20., 20.)
CHANNELS = RelationShapeChannels((0., 10., 20.), (0., 20.))
EXPECTED = ((5., 6.), (5., 4.), (10., 4.), (10., 8.), (15., 8.), (15., 10.))


def _pair(*, semantic=True):
    source = ConnectorEgress("above", (5., 6.) if semantic else (5., 8.), (5., 6.), ("source",))
    target = ConnectorEgress("above", (15., 10.) if semantic else (15., 12.), (15., 10.), ("target",))
    return source, target


def _select(pair, **kwargs):
    return select_relation_route((pair,), obstacles=kwargs.pop("obstacles", SurfaceObstacleIndex()),
        bounds=kwargs.pop("bounds", BOUNDS), source_host_id=None, target_host_id=None,
        relation_scene_id="relation:outward", max_bends=kwargs.pop("max_bends", 4),
        max_detour_ratio=kwargs.pop("max_detour_ratio", 2), channels=kwargs.pop("channels", CHANNELS),
        outward_runs=kwargs.pop("outward_runs", (2., 2.)), **kwargs)


def _bounded_miss(*args, **kwargs):
    raise RouteSearchFailure("E_PRESENTATION_ROUTE_LIMIT")


@pytest.mark.parametrize("policy", ["first-fit", "best"])
def test_outward_proposal_uses_normal_preparation_acceptance_and_quality(policy, monkeypatch):
    pair = _pair()
    prepared, accepted = [], []

    def prepare(points, source, target):
        prepared.append((points, source, target))
        return points

    def accept(points):
        accepted.append(points)
        return points == EXPECTED

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", _bounded_miss)
    selected = _select(pair, search_policy=policy, prepare=prepare, accept=accept)

    assert selected.selected_pair == pair
    assert selected.points == EXPECTED
    assert selected.settled_by_shape and not selected.settled_by_hint
    assert selected.search_used is (policy == "best")
    assert prepared and accepted
    assert prepared[-1] == (EXPECTED, *pair)
    length, _, bends = route_quality_metrics(selected.points)
    assert bends == 4 and length <= 14. * 2


def test_outward_candidate_with_four_bends_is_rejected_by_three_bend_limit(monkeypatch):
    pair = _pair()
    monkeypatch.setattr(route_search, "orthogonal_route_candidates", _bounded_miss)
    selected = _select(pair, search_policy="best", max_bends=3,
                       accept=lambda points: points == EXPECTED)
    assert selected.selected_pair is None
    assert any(item.outcome == "quality-rejected" for item in selected.attempts)


def test_obstacle_blocks_every_outward_bridge_without_relaxing_safety(monkeypatch):
    pair = _pair()
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("wall", "mark", "timeline", ObstacleRect(9., 0., 11., 20.)))
    monkeypatch.setattr(route_search, "orthogonal_route_candidates", _bounded_miss)
    blocked = []
    def accept(points):
        hit = any(segment_closed_rect_contact_interval(ObstacleSegment(a, b),
            obstacles.get("wall").geometry) is not None for a, b in zip(points, points[1:]))
        if hit:
            blocked.append(points)
        return not hit
    selected = _select(pair, search_policy="best", obstacles=obstacles,
        accept=accept)
    assert selected.selected_pair is None
    assert blocked and all(any(segment_closed_rect_contact_interval(ObstacleSegment(a, b),
        obstacles.get("wall").geometry) is not None for a, b in zip(points, points[1:]))
        for points in blocked)


def test_outside_leads_are_not_clamped_into_bounds(monkeypatch):
    pair = (ConnectorEgress("above", (5., 2.), (5., 2.), ("source",)),
            ConnectorEgress("above", (15., 12.), (15., 12.), ("target",)))
    generated = []
    original = routing.outward_relation_shape_candidates
    def capture(*args, **kwargs):
        proposals = original(*args, **kwargs)
        generated.append(proposals)
        return proposals
    monkeypatch.setattr(routing, "outward_relation_shape_candidates", capture)
    monkeypatch.setattr(route_search, "orthogonal_route_candidates", _bounded_miss)
    selected = _select(pair, search_policy="best", accept=lambda points: False,
        outward_runs=(3., 2.), bounds=BOUNDS)
    assert selected.selected_pair is None
    assert generated == [()]


def test_best_keeps_an_accepted_graph_route_without_trying_outward_proposals(monkeypatch):
    pair = (ConnectorEgress("end", (0., 0.), (0., 0.), ("source",)),
            ConnectorEgress("start", (10., 10.), (10., 10.), ("target",)))
    graph_path = ((0., 0.), (10., 0.), (10., 10.))
    monkeypatch.setattr(route_search, "orthogonal_route_candidates",
                        lambda *args, **kwargs: iter((graph_path,)))
    monkeypatch.setattr(routing, "outward_relation_shape_candidates",
                        lambda *args, **kwargs: pytest.fail("accepted graph path must win"))
    selected = _select(pair, search_policy="best", channels=CHANNELS, outward_runs=(2., 2.))
    assert selected.selected_pair == pair and selected.points == graph_path
    assert selected.search_used and not selected.settled_by_shape


def test_validated_hint_keeps_priority_over_outward_proposals(monkeypatch):
    pair = (ConnectorEgress("end", (0., 0.), (0., 0.), ("source",)),
            ConnectorEgress("start", (10., 10.), (10., 10.), ("target",)))
    hint = ((0., 0.), (10., 0.), (10., 10.))
    monkeypatch.setattr(routing, "outward_relation_shape_candidates",
                        lambda *args, **kwargs: pytest.fail("hint must be checked first"))
    selected = _select(pair, search_policy="best", preferred_routes=((pair, hint),))
    assert selected.points == hint and selected.settled_by_hint
    assert not selected.settled_by_shape and not selected.search_used


def test_best_still_ranks_accepted_candidates_across_port_pairs(monkeypatch):
    source_first = ConnectorEgress("end", (0., 0.), (0., 0.), ("source:first",))
    source_second = ConnectorEgress("start", (0., 2.), (0., 2.), ("source:second",))
    target = ConnectorEgress("start", (10., 10.), (10., 10.), ("target",))

    def graph(start, end, *args, **kwargs):
        return iter(((start, (end[0], start[1]), end),))

    monkeypatch.setattr(route_search, "orthogonal_route_candidates", graph)
    selected = select_relation_route(((source_first, target), (source_second, target)),
        obstacles=SurfaceObstacleIndex(), bounds=(-5., -5., 20., 20.), source_host_id=None,
        target_host_id=None, relation_scene_id="relation:pair-rank", max_bends=4,
        max_detour_ratio=4, search_policy="best", outward_runs=(2., 2.),
        rank=lambda points, source, target: (0 if source.host_ids == ("source:second",) else 1,))
    assert selected.selected_pair == (source_second, target)
    assert selected.points[0] == source_second.semantic_port
    assert not selected.settled_by_shape
