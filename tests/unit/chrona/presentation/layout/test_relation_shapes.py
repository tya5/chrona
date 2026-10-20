"""Shape-first routing must use the existing completed-route safety gates."""
from collections import Counter

import pytest

from chrona.presentation.layout import route_search as search
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.relation_shapes import (
    RelationShapeChannels, first_fit_port_pairs, outward_relation_shape_candidates,
    relation_shape_candidates, shape_channels,
)
from chrona.presentation.layout.routing import select_relation_route


def _port(side, point, *, stub=False):
    return ConnectorEgress(side, point, point, (), stub)


def _select(*, pairs=None, obstacles=None, **kwargs):
    return select_relation_route(pairs or ((_port("end", (0, 0)), _port("start", (10, 10))),),
        obstacles=obstacles or SurfaceObstacleIndex(), bounds=(-2, -2, 12, 12),
        source_host_id=None, target_host_id=None, relation_scene_id="relation:synthetic",
        max_bends=kwargs.pop("max_bends", 4), max_detour_ratio=kwargs.pop("max_detour_ratio", 2),
        search_policy="first-fit", **kwargs)


def test_port_order_is_physical_preference_with_stable_stub_ties():
    source = [_port(side, (0, 0)) for side in ("below", "above", "start", "end")]
    target = [_port(side, (10, 10)) for side in ("below", "above", "end", "start")]
    pairs = tuple((left, right) for left in source for right in target)
    stub = _port("start", (10, 10), stub=True)
    ordered = first_fit_port_pairs((*pairs, (source[-1], stub)))
    assert ordered[0] == (source[-1], stub)
    assert [(left.side, right.side) for left, right in ordered[1:]] == [
        (left, right) for left in ("end", "start", "above", "below")
        for right in ("start", "end", "above", "below")]
    assert pairs[0] == (source[0], target[0])  # inputs stay unchanged
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID"):
        first_fit_port_pairs(((_port("unknown", (0, 0)), target[0]),))


def test_channels_use_selected_clearance_contacts_and_completed_row_gaps():
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("mark", "mark", "timeline", ObstacleRect(4, 2, 6, 4), clearance=1))
    obstacles.add(SurfaceObstacle("excluded", "rule", "timeline", ObstacleRect(8, 2, 9, 4)))
    channels = shape_channels(obstacles, bounds=(0, 0, 10, 10), row_edges=((6, 8), (1, 4)))
    assert channels == RelationShapeChannels((0, 1, 9, 10), (0, 5, 10))


def test_shape_order_has_at_most_seven_raw_proposals_and_no_diagonal_or_outside_points():
    channels = RelationShapeChannels((0, 4, 6, 10), (0, 3, 7, 10))
    paths = relation_shape_candidates((1, 1), (9, 9), bounds=(0, 0, 10, 10), channels=channels)
    assert paths[:2] == (((1, 1), (9, 1), (9, 9)), ((1, 1), (1, 9), (9, 9)))
    assert paths[2:] == tuple(((1, 1), (x, 1), (x, 9), (9, 9)) for x in (4, 6)) + tuple(
        ((1, 1), (1, y), (9, y), (9, 9)) for y in (3, 7))
    assert len(paths) <= 7 and len(set(paths)) == len(paths)
    assert all(a[0] == b[0] or a[1] == b[1] for path in paths for a, b in zip(path, path[1:]))
    aligned = relation_shape_candidates((1, 1), (9, 1), bounds=(0, 0, 10, 10), channels=channels)
    assert aligned[0] == ((1, 1), (9, 1))
    assert aligned.count(aligned[0]) == 1
    outside = relation_shape_candidates((-1, 1), (9, 9), bounds=(0, 0, 10, 10), channels=channels)
    assert outside == ()


def test_outward_channel_proposal_reuses_finite_shape_grammar_for_four_bend_route():
    source = ConnectorEgress("above", (5., 8.), (5., 6.), ("source-mark",))
    target = ConnectorEgress("above", (15., 12.), (15., 10.), ("target-mark",))
    channels = RelationShapeChannels((0., 10., 20.), (0., 20.))
    proposals = outward_relation_shape_candidates((source, target), source_run=2., target_run=2.,
        bounds=(0., 0., 20., 20.), channels=channels)
    four_bend = ((5., 6.), (5., 4.), (10., 4.), (10., 8.), (15., 8.), (15., 10.))
    assert four_bend in proposals
    assert all(path[0] == source.exposed_port and path[-1] == target.exposed_port for path in proposals)
    assert all(all(a[0] == b[0] or a[1] == b[1] for a, b in zip(path, path[1:]))
               for path in proposals)
    assert all(all(0 <= x <= 20 and 0 <= y <= 20 for x, y in path) for path in proposals)


def test_outward_channel_proposals_reject_leads_outside_bounds_and_keep_physical_port_identity():
    source = ConnectorEgress("end", (0., 5.), (2., 5.), ("source",), corridor_host_ids=("physical",))
    target = ConnectorEgress("start", (20., 15.), (18., 15.), ("target",))
    paths = outward_relation_shape_candidates((source, target), source_run=3., target_run=3.,
        bounds=(0., 0., 20., 20.), channels=RelationShapeChannels((0., 10., 20.), (0., 10., 20.)))
    assert paths
    assert all(path[0] == source.exposed_port and path[-1] == target.exposed_port for path in paths)
    assert all(path[0] != source.semantic_port and path[-1] != target.semantic_port for path in paths)
    assert outward_relation_shape_candidates((source, target), source_run=19., target_run=3.,
        bounds=(0., 0., 20., 20.), channels=RelationShapeChannels((0., 10., 20.), (0., 10., 20.))) == ()


def test_shape_settled_relation_never_builds_a_graph_or_invokes_search(monkeypatch):
    counts = Counter()
    def forbidden(*args, **kwargs):
        counts["graph_or_search"] += 1
        raise AssertionError("shape-settled route must not search")
    monkeypatch.setattr(search, "_build_sparse_graph", forbidden)
    monkeypatch.setattr(search, "orthogonal_route_candidates", forbidden)
    result = _select(rank=lambda *args: (_ for _ in ()).throw(AssertionError("first-fit must not rank")))
    assert result.settled_by_shape
    assert result.points == ((0, 0), (10, 0), (10, 10))
    assert not counts


def test_raw_shape_collision_rejects_the_first_elbow_without_search():
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("block", "mark", "timeline", ObstacleRect(4, -1, 6, 1)))
    result = _select(obstacles=obstacles)
    assert result.settled_by_shape
    assert result.points == ((0, 0), (0, 10), (10, 10))


def test_completed_terminal_preparation_can_reject_a_raw_shape_and_choose_the_next():
    seen = []
    def prepare(points, source, target):
        seen.append(points)
        return None if points[1] == (10, 0) else points
    result = _select(prepare=prepare)
    assert result.settled_by_shape
    assert seen[:2] == [((0, 0), (10, 0), (10, 10)), ((0, 0), (0, 10), (10, 10))]
    assert result.points == seen[1]


def test_shapes_do_not_waive_bend_quality_or_full_route_acceptance(monkeypatch):
    counts = Counter()
    original = search._build_sparse_graph
    reverse = search._reverse_bounds
    def build(*args, **kwargs):
        counts["graph"] += 1
        return original(*args, **kwargs)
    monkeypatch.setattr(search, "_build_sparse_graph", build)
    def exact_reverse(*args):
        counts["reverse"] += 1
        return reverse(*args)
    monkeypatch.setattr(search, "_reverse_bounds", exact_reverse)
    result = _select(max_bends=0)
    assert result.selected_pair is None and not result.settled_by_shape
    assert result.attempts[0].outcome == "quality-rejected"
    assert counts["graph"] == 1  # exact rescue reuses the cheap fallback's geometry
    assert counts["reverse"] == 1  # only the rescue prepares the exact bound
    result = _select(accept=lambda points: False)
    assert result.selected_pair is None and not result.settled_by_shape
    assert result.attempts[0].search_failure == "E_LAYOUT_ROUTE_THROUGH_MARK"


def test_blocked_host_corridor_is_not_waived_by_shapes():
    source = ConnectorEgress("end", (0, 0), (3, 0), ("host",))
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("host", "mark", "timeline", ObstacleRect(-1, -1, 3, 1)))
    obstacles.add(SurfaceObstacle("other", "text", "timeline", ObstacleRect(1, -1, 2, 1)))
    result = _select(pairs=((source, _port("start", (10, 10))),), obstacles=obstacles)
    assert result.selected_pair is None and not result.settled_by_shape
    assert result.attempts[0].outcome == "egress-collision"
    assert result.attempts[0].blocker_ids == ("other",)


def test_prepared_self_overlapping_shape_is_not_admitted():
    result = _select(prepare=lambda points, source, target: ((0, 0), (8, 0), (3, 0), (10, 10)))
    assert result.selected_pair is None and not result.settled_by_shape
    assert result.attempts[0].search_failure == "E_LAYOUT_ROUTE_SELF_OVERLAP"


def test_later_shape_winner_retains_evidence_of_earlier_search(monkeypatch):
    searches = []
    def candidate(start, end, *args, **kwargs):
        searches.append((start, end))
        yield (start, (end[0], start[1]), end)
    monkeypatch.setattr(search, "orthogonal_route_candidates", candidate)
    source = _port("end", (0, 0))
    result = _select(pairs=((source, _port("start", (5, 5))), (source, _port("end", (10, 10)))),
                     accept=lambda points: points[-1] == (10, 10))
    assert searches == [((0, 0), (5, 5))]
    assert result.settled_by_shape and result.search_used


@pytest.mark.parametrize("channels", [((True,), ()), ((float("nan"),), ()), ((2, 1), ()), ((1, 1), ())])
def test_channel_invariants_reject_nonfinite_duplicate_unsorted_and_boolean_coordinates(channels):
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID"):
        RelationShapeChannels(*channels)
