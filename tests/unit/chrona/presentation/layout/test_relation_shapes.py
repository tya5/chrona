"""Shape-first routing must use the existing completed-route safety gates."""
from collections import Counter

import pytest

from chrona.presentation.layout import route_search as search
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.relation_shapes import (
    RelationShapeChannels, first_fit_port_pairs, relation_shape_candidates, shape_channels,
    supplemental_relation_channel_candidates,
)
from chrona.presentation.layout import routing
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


def test_repair_supplement_is_bounded_and_keeps_basic_candidates_first(monkeypatch):
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("source-label", "text", "timeline", ObstacleRect(0.5, 1, 9, 2)))
    obstacles.add(SurfaceObstacle("target-label", "label-visual", "timeline", ObstacleRect(0.5, 8, 9, 9)))
    obstacles.add(SurfaceObstacle("middle-mark", "mark", "timeline", ObstacleRect(-2, 4.5, 2, 5.5)))
    bounds = (-10, -2, 10, 12)
    channels = shape_channels(obstacles, bounds=bounds)
    base = relation_shape_candidates((0, 0), (0, 10), bounds=bounds, channels=channels)
    extra = tuple(supplemental_relation_channel_candidates((0, 0), (0, 10), bounds=bounds,
        channels=channels, obstacles=obstacles, route_stroke_width=1.0))
    assert 0 < len(extra) <= 8

    def accept(points):
        return not any(obstacles.collisions(ObstacleSegment(a, b, 1.0),
            classes=("text", "label-visual"), regions=("timeline", "group-header"))
            for a, b in zip(points, points[1:]))

    generated = []
    original_supplement = routing.supplemental_relation_channel_candidates
    def watched_supplement(*args, **kwargs):
        generated.append(True)
        yield from original_supplement(*args, **kwargs)
    monkeypatch.setattr(routing, "supplemental_relation_channel_candidates", watched_supplement)

    result = select_relation_route(((_port("end", (0, 0)), _port("start", (0, 10))),),
        obstacles=obstacles, bounds=bounds, source_host_id=None, target_host_id=None,
        relation_scene_id="relation:repair-supplement", max_bends=4, max_detour_ratio=2,
        search_policy="first-fit", channels=channels,
        label_repair_obstacle_ids=frozenset({"source-label", "target-label"}),
        route_stroke_width=1.0, prepare=lambda points, source, target: points, accept=accept)
    assert result.selected_pair is not None and result.settled_by_shape
    assert result.points in extra
    assert result.points not in base
    assert result.points == ((0, 0), (0, 2.5), (-4, 2.5), (-4, 7.5), (0, 7.5), (0, 10))
    assert generated == [True]
    assert not result.search_used
    assert all(not obstacles.collisions(ObstacleSegment(a, b, 1.0),
        classes=("text", "label-visual"), regions=("timeline", "group-header"))
        for a, b in zip(result.points, result.points[1:]))


def test_supplement_is_not_invoked_without_a_matching_repair_obstacle(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("normal first-fit must keep the existing basic shape grammar")
    monkeypatch.setattr(routing, "supplemental_relation_channel_candidates", forbidden)
    result = _select(label_repair_obstacle_ids=frozenset({"not-in-domain"}), route_stroke_width=float("nan"))
    assert result.settled_by_shape


def test_repair_supplement_has_no_degenerate_vertical_span_with_one_contact_row():
    proposals = tuple(supplemental_relation_channel_candidates((0, 0), (0, 10),
        bounds=(-5, -5, 5, 15), channels=RelationShapeChannels((-5, 5), (0, 5, 10)),
        obstacles=SurfaceObstacleIndex(), route_stroke_width=1.0))
    assert proposals == ()


def test_outward_channel_clearance_is_scoped_to_each_row_pair():
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("source-label", "text", "timeline",
        ObstacleRect(947, 265, 1089, 284.6)))
    obstacles.add(SurfaceObstacle("target-label", "label-visual", "timeline",
        ObstacleRect(1044, 585, 1154, 604.6)))
    channels = RelationShapeChannels((1070,), (274.8, 284.8, 583.0, 584.8, 594.8))
    proposals = tuple(supplemental_relation_channel_candidates((944, 274.8), (944, 594.8),
        bounds=(900, 200, 1200, 700), channels=channels, obstacles=obstacles,
        route_stroke_width=1.0))
    assert ((944, 274.8), (944, 286.6), (1070, 286.6), (1070, 583.0),
            (944, 583.0), (944, 594.8)) in proposals
    assert len(proposals) <= 8


@pytest.mark.parametrize("width", [True, -1.0, float("nan"), float("inf")])
def test_route_rejects_invalid_stroke_width_only_for_matching_repair_domain(width):
    obstacles = SurfaceObstacleIndex()
    obstacles.add(SurfaceObstacle("label", "text", "timeline", ObstacleRect(4, 4, 6, 6)))
    with pytest.raises(ValueError, match="E_LAYOUT_ROUTE_ATTEMPT_INVALID"):
        _select(obstacles=obstacles, label_repair_obstacle_ids=frozenset({"label"}),
                route_stroke_width=width)


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
    assert counts["graph"] == 2  # cheap fallback, then exact rescue
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
