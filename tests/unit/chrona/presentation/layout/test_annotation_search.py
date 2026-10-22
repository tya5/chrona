import chrona.presentation.layout.annotation_search as search
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.annotation_search import (
    coarse_lattice_positions, lattice_positions, nearest_free_box, nearest_free_tail_box,
)
from chrona.presentation.layout.annotation_search import nearest_free_routed_tail_box
from chrona.presentation.layout.annotation_search import _route_crosses_rule_once
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_quality import MarkPlacement
from chrona.presentation.layout.balloon_geometry import nearest_eligible_edge, tail_base_points


def test_lattice_positions_are_nearest_first_and_deterministic() -> None:
    region = LabelRect(0, 0, 400, 300)
    positions = lattice_positions(region, (80, 30), (200, 150), max_positions=8)
    assert positions[0] == LabelRect(160.0, 135.0, 80, 30)
    # Re-running with the same inputs reproduces the identical ordered tuple.
    assert positions == lattice_positions(region, (80, 30), (200, 150), max_positions=8)
    assert len(positions) <= 8


def test_lattice_positions_step_is_half_the_box_and_at_least_one_unit() -> None:
    region = LabelRect(0, 0, 10, 10)
    positions = lattice_positions(region, (0.001, 0.001), (5, 5), max_positions=1024)
    xs = sorted({box.x for box in positions})
    # The minimum step floor keeps the lattice finite even for a tiny box.
    assert xs[1] - xs[0] >= 1.0 - 1e-9


def test_lattice_positions_empty_when_box_cannot_fit_region() -> None:
    region = LabelRect(0, 0, 10, 10)
    assert lattice_positions(region, (20, 20), (5, 5), max_positions=16) == ()


def test_coarse_grid_spans_legal_region_with_existing_position_cap() -> None:
    region = LabelRect(10, 20, 300, 180)
    boxes = coarse_lattice_positions(region, (40, 20), (160, 110), max_positions=16)
    assert len(boxes) <= 16
    assert min(box.x for box in boxes) == region.x
    assert max(box.right for box in boxes) == region.right
    assert min(box.y for box in boxes) == region.y
    assert max(box.bottom for box in boxes) == region.bottom
    assert boxes == coarse_lattice_positions(region, (40, 20), (160, 110), max_positions=16)
    assert coarse_lattice_positions(region, (40, 20), (160, 110), max_positions=1) == (
        LabelRect(140, 100, 40, 20),)


def test_coarse_grid_small_budgets_are_bounded_deterministic_long_axis_samples() -> None:
    region = LabelRect(10, 20, 300, 100)
    for budget in (2, 3):
        boxes = coarse_lattice_positions(region, (40, 20), (160, 70), max_positions=budget)
        assert 0 < len(boxes) <= budget
        assert boxes == coarse_lattice_positions(region, (40, 20), (160, 70), max_positions=budget)
        expected_x = ({region.x, region.right - 40} if budget == 2 else
                      {region.x, (region.x + region.right - 40) / 2, region.right - 40})
        assert {box.x for box in boxes} == expected_x
        assert {box.y for box in boxes} == {60}


def test_coarse_grid_handles_degenerate_legal_origin_extents() -> None:
    vertical = coarse_lattice_positions(LabelRect(10, 20, 40, 120), (40, 20),
                                        (30, 80), max_positions=6)
    assert len(vertical) == 6
    assert {box.x for box in vertical} == {10}
    assert min(box.y for box in vertical) == 20
    assert max(box.bottom for box in vertical) == 140

    horizontal = coarse_lattice_positions(LabelRect(10, 20, 120, 20), (40, 20),
                                          (70, 30), max_positions=6)
    assert len(horizontal) == 6
    assert {box.y for box in horizontal} == {20}
    assert min(box.x for box in horizontal) == 10
    assert max(box.right for box in horizontal) == 130


def test_coarse_box_search_reaches_far_free_space_after_fine_neighborhood_misses() -> None:
    region = LabelRect(0, 0, 100, 100)
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("busy-neighborhood", "mark", "plot", ObstacleRect(0, 0, 90, 100)))
    fine, fine_trials = nearest_free_box(
        region=region, anchor_center=(50, 50), box_size=(10, 10), max_positions=16,
        obstacles=index, obstacle_classes=("mark",), search_pass="fine")
    coarse, coarse_trials = nearest_free_box(
        region=region, anchor_center=(50, 50), box_size=(10, 10), max_positions=16,
        obstacles=index, obstacle_classes=("mark",), search_pass="coarse")
    assert fine is None and fine_trials == 16
    assert coarse is not None and coarse.x == 90
    assert coarse.y in {0, 30, 60, 90}
    assert 0 < coarse_trials <= 16


def test_default_box_search_remains_the_fine_search() -> None:
    args = dict(region=LabelRect(0, 0, 400, 300), anchor_center=(200, 150),
                box_size=(80, 30), max_positions=8, obstacles=SurfaceObstacleIndex(),
                obstacle_classes=("mark",))
    assert nearest_free_box(**args) == nearest_free_box(**args, search_pass="fine")


def test_nearest_free_box_finds_first_collision_free_lattice_position() -> None:
    region = LabelRect(0, 0, 400, 300)
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:anchor", "mark", "plot", ObstacleRect(190, 140, 210, 160)))
    box, trials = nearest_free_box(region=region, anchor_center=(200, 150), box_size=(80, 30),
                                   max_positions=256, obstacles=index, obstacle_classes=("mark",),
                                   host_id="mark:anchor")
    assert box is not None and trials == 1
    assert not index.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom), classes=("mark",),
                                host_id="mark:anchor")


def test_nearest_free_box_avoids_a_dependency_route_and_reports_bounded_trials() -> None:
    region = LabelRect(0, 0, 400, 300)
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:anchor", "mark", "plot", ObstacleRect(190, 140, 210, 160)))
    index.add(SurfaceObstacle("dep:1", "dependency-route", "plot", ObstacleSegment((0, 150), (400, 150), 2.0)))
    box, trials = nearest_free_box(region=region, anchor_center=(200, 150), box_size=(80, 30),
                                   max_positions=256, obstacles=index,
                                   obstacle_classes=("mark", "dependency-route"), host_id="mark:anchor")
    assert box is not None
    assert not index.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom),
                                classes=("dependency-route",))
    assert trials >= 1


def test_nearest_free_box_honours_the_as_of_side_constraint() -> None:
    region = LabelRect(0, 0, 400, 300)
    index = SurfaceObstacleIndex()
    box, _ = nearest_free_box(region=region, anchor_center=(350, 150), box_size=(60, 20),
                              max_positions=512, obstacles=index, obstacle_classes=("mark",),
                              side_of_as_of=(300.0, "end"))
    assert box is not None and box.x >= 300.0


def test_nearest_free_box_returns_none_when_every_position_collides() -> None:
    region = LabelRect(0, 0, 20, 20)
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:blocker", "mark", "plot", ObstacleRect(0, 0, 20, 20)))
    box, trials = nearest_free_box(region=region, anchor_center=(10, 10), box_size=(20, 20),
                                   max_positions=4, obstacles=index, obstacle_classes=("mark",))
    assert box is None and trials >= 1


def test_nearest_free_tail_box_finds_a_box_whose_tail_also_avoids_obstacles() -> None:
    region = LabelRect(0, 0, 400, 300)
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:anchor", "mark", "plot", ObstacleRect(190, 140, 210, 160)))
    index.add(SurfaceObstacle("dep:1", "dependency-route", "plot", ObstacleSegment((0, 50), (400, 50), 2.0)))
    anchor = LabelRect(190, 140, 20, 20)
    box, tip, trials = nearest_free_tail_box(
        region=region, anchor=anchor, box_size=(80, 30), max_positions=256, obstacles=index,
        obstacle_classes=("mark", "dependency-route"), corner_radius=4, tail_base=10, host_id="mark:anchor")
    assert box is not None and tip is not None and trials >= 1
    assert not index.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom),
                                classes=("mark", "dependency-route"), host_id="mark:anchor")


def test_nearest_free_tail_box_rejects_positions_whose_tail_crosses_a_route_the_body_clears() -> None:
    # A short dependency route hugging the anchor's edge does not overlap the
    # box body at the two nearest lattice positions, but a direct tail from
    # either position back to the anchor must cross it: only the joint
    # box-plus-tail trial (#466) can see that, so the search takes more than
    # one trial and lands on a position whose tail is genuinely clear.
    region = LabelRect(0, 0, 400, 300)
    anchor = LabelRect(190, 140, 20, 20)
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:anchor", "mark", "plot", ObstacleRect(190, 140, 210, 160)))
    index.add(SurfaceObstacle("dep:1", "dependency-route", "plot", ObstacleSegment((150, 138), (250, 138), 1.0)))
    box, tip, trials = nearest_free_tail_box(
        region=region, anchor=anchor, box_size=(80, 30), max_positions=64, obstacles=index,
        obstacle_classes=("mark", "dependency-route"), corner_radius=4, tail_base=10, host_id="mark:anchor")
    assert box is not None and tip is not None
    assert trials > 1  # at least one earlier candidate was rejected on tail collision
    assert not index.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom),
                                classes=("mark", "dependency-route"), host_id="mark:anchor")


def test_routed_tail_search_returns_bounded_strict_route_and_keeps_box_out_of_index() -> None:
    region = LabelRect(0, 0, 120, 100)
    index = SurfaceObstacleIndex()
    mark = MarkPlacement("mark:anchor", "anchor", Rect(40, 40, 10, 10),
                         (40, 45), (50, 45), mark_shape="point")
    index.add(SurfaceObstacle("mark:anchor", "mark", "plot", ObstacleRect(40, 40, 50, 50)))
    result = nearest_free_routed_tail_box(
        region=region, anchor=mark, endpoint="at", siblings=(mark,), box_size=(30, 20),
        max_positions=128, obstacles=index, obstacle_classes=("mark", "text", "dependency-route"),
        corner_radius=3, tail_base=8, content_bounds=(0, 0, 120, 100), host_id="mark:anchor",
        route_state_limit=1024)
    assert result.box is not None and result.tip is not None
    assert result.egress is not None and result.route is not None
    assert result.route.topology == "strict"
    assert result.full_points[0] == result.egress.semantic_port
    assert result.full_points[-1] == result.tip
    assert 0 < result.route_states <= 1024
    assert not result.exhausted
    assert not index.has("candidate:balloon-box")
    candidate_index = SurfaceObstacleIndex()
    candidate_index.extend(index.all())
    candidate_index.add(SurfaceObstacle("candidate:box", "annotation-box", "plot",
                                        ObstacleRect(result.box.x, result.box.y,
                                                     result.box.right, result.box.bottom)))
    assert not any(candidate_index.collisions(ObstacleSegment(a, b))
                   for a, b in zip(result.route.points, result.route.points[1:]))
    edge = nearest_eligible_edge(result.box, result.tip)
    base_a, base_b = tail_base_points(
        result.box, result.tip, edge=edge, tail_base=8,
        corner_radius=min(3, result.box.width / 2, result.box.height / 2))
    assert not any(candidate_index.collisions(ObstacleSegment(a, b),
                                               classes=("mark", "text", "dependency-route"))
                   for a, b in ((base_a, result.tip), (result.tip, base_b)))


def test_coarse_routed_tail_search_finds_a_complete_collision_free_pair() -> None:
    region = LabelRect(0, 0, 120, 100)
    index = SurfaceObstacleIndex()
    mark = MarkPlacement("mark:anchor", "anchor", Rect(40, 40, 10, 10),
                         (40, 45), (50, 45), mark_shape="point")
    index.add(SurfaceObstacle("mark:anchor", "mark", "plot", ObstacleRect(40, 40, 50, 50)))
    result = nearest_free_routed_tail_box(
        region=region, anchor=mark, endpoint="at", siblings=(mark,), box_size=(30, 20),
        max_positions=16, obstacles=index, obstacle_classes=("mark", "text", "dependency-route"),
        corner_radius=3, tail_base=8, content_bounds=(0, 0, 120, 100), host_id="mark:anchor",
        route_state_limit=1024, search_pass="coarse")
    assert result.box is not None and result.tip is not None
    assert result.egress is not None and result.route is not None
    assert result.route.topology == "strict"
    assert result.full_points[0] == result.egress.semantic_port
    assert result.full_points[-1] == result.tip
    assert 0 < result.box_trials <= 16
    assert 0 < result.route_states <= 1024
    assert not result.exhausted

    completed = SurfaceObstacleIndex()
    completed.extend(index.all())
    completed.add(SurfaceObstacle("candidate:balloon-box", "annotation-box", "plot",
                                  ObstacleRect(result.box.x, result.box.y,
                                               result.box.right, result.box.bottom)))
    assert not completed.collisions(ObstacleRect(result.box.x, result.box.y,
                                                  result.box.right, result.box.bottom),
                                    classes=("mark", "text", "dependency-route"),
                                    host_id="mark:anchor")
    assert not any(completed.collisions(ObstacleSegment(a, b),
                                        classes=("mark", "text", "dependency-route", "annotation-box"),
                                        host_id="mark:anchor")
                   for a, b in zip(result.full_points, result.full_points[1:]))
    edge = nearest_eligible_edge(result.box, result.tip)
    base_a, base_b = tail_base_points(
        result.box, result.tip, edge=edge, tail_base=8,
        corner_radius=min(3, result.box.width / 2, result.box.height / 2))
    assert not any(completed.collisions(ObstacleSegment(a, b),
                                        classes=("mark", "text", "dependency-route", "annotation-box"),
                                        host_id="mark:anchor")
                   for a, b in ((base_a, result.tip), (result.tip, base_b)))


def test_routed_tail_distinguishes_no_box_from_connector_budget_exhaustion() -> None:
    index = SurfaceObstacleIndex()
    mark = MarkPlacement("mark:anchor", "anchor", Rect(40, 40, 10, 10),
                         (40, 45), (50, 45), mark_shape="point")
    index.add(SurfaceObstacle("mark:anchor", "mark", "plot", ObstacleRect(40, 40, 50, 50)))
    common = dict(anchor=mark, endpoint="at", siblings=(mark,), box_size=(30, 20),
                  max_positions=128, obstacles=index,
                  obstacle_classes=("mark", "text", "dependency-route", "port"),
                  corner_radius=3, tail_base=8, content_bounds=(0, 0, 120, 100),
                  host_id="mark:anchor")
    no_box = nearest_free_routed_tail_box(region=LabelRect(0, 0, 20, 20),
                                          route_state_limit=1, **common)
    assert no_box.box is None and no_box.box_trials == 0 and not no_box.exhausted
    capped = nearest_free_routed_tail_box(region=LabelRect(0, 0, 120, 100),
                                          route_state_limit=1, **common)
    assert capped.box is None and capped.exhausted and capped.route_states == 1


def test_coarse_routed_search_rejects_free_boxes_behind_a_blocked_connector():
    anchor = MarkPlacement("mark:anchor", "anchor", Rect(10, 45, 10, 10),
                           (10, 50), (20, 50), mark_shape="span")
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:anchor", "mark", "plot", ObstacleRect(10, 45, 20, 55)))
    index.add(SurfaceObstacle("barrier", "dependency-route", "plot",
                              ObstacleSegment((45, 0), (45, 100), 2.0)))
    result = nearest_free_routed_tail_box(
        region=LabelRect(60, 0, 40, 100), anchor=anchor, endpoint="finish",
        siblings=(anchor,), box_size=(20, 10), max_positions=16, obstacles=index,
        obstacle_classes=("dependency-route",), corner_radius=3, tail_base=8,
        content_bounds=(0, 0, 100, 100), max_detour_ratio=2.0,
        host_id="mark:anchor",
        search_pass="coarse")
    assert result.box is None
    assert result.box_trials > 0
    assert 0 < result.route_states <= 1024


def test_coarse_tail_search_rejects_boxes_larger_than_the_anchor_as_of_side() -> None:
    # The whole plot has ample empty space on the far side, but no complete
    # 210-unit box can fit before the as-of rule at x=200. Coarse search must
    # preserve the same body-side contract as fine search, before checking a
    # direct tail or trying routed egress.
    region = LabelRect(0, 0, 600, 100)
    anchor_box = LabelRect(145, 45, 10, 10)
    index = SurfaceObstacleIndex()
    side = (200.0, "start")
    common = dict(region=region, box_size=(210, 20), max_positions=32,
                  obstacles=index, obstacle_classes=("mark",),
                  side_of_as_of=side, search_pass="coarse")

    direct, tip, direct_trials = nearest_free_tail_box(
        anchor=anchor_box, corner_radius=0, tail_base=0, **common)
    mark = MarkPlacement("mark:anchor", "anchor", Rect(145, 45, 10, 10),
                         (145, 50), (155, 50), mark_shape="span")
    routed = nearest_free_routed_tail_box(
        anchor=mark, endpoint="start", siblings=(mark,), corner_radius=0,
        tail_base=0, content_bounds=(0, 0, 600, 100), **common)

    assert direct is None and tip is None and direct_trials > 0
    assert routed.box is None and not routed.exhausted
    assert routed.box_trials > 0
    assert routed.route_states == 0


def test_routed_tail_exempts_only_the_named_source_port_on_egress() -> None:
    index = SurfaceObstacleIndex()
    mark = MarkPlacement("mark:anchor", "anchor", Rect(40, 40, 10, 10),
                         (40, 45), (50, 45), mark_shape="span")
    index.add(SurfaceObstacle("mark:anchor", "mark", "plot", ObstacleRect(40, 40, 50, 50)))
    index.add(SurfaceObstacle("port:mark:anchor:end", "port", "plot",
                              ObstacleRect(49.5, 44.5, 50.5, 45.5)))
    result = nearest_free_routed_tail_box(
        region=LabelRect(0, 0, 120, 100), anchor=mark, endpoint="finish",
        siblings=(mark,), box_size=(30, 20), max_positions=128,
        obstacles=index, obstacle_classes=("mark", "text", "dependency-route", "port"),
        corner_radius=3, tail_base=8, content_bounds=(0, 0, 120, 100),
        host_id="mark:anchor")
    assert result.box is not None and result.egress is not None
    assert result.egress.semantic_port == (50, 45)


def test_as_of_fallback_routes_once_transversely_and_keeps_other_obstacles_authoritative() -> None:
    mark = MarkPlacement("mark:anchor", "anchor", Rect(20, 40, 10, 10),
                         (20, 45), (30, 45), mark_shape="point")
    as_of = SurfaceObstacle("as-of", "rule", "timeline", ObstacleSegment((50, 0), (50, 100)))
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:anchor", "mark", "plot", ObstacleRect(20, 40, 30, 50)))
    index.add(as_of)
    args = dict(
        region=LabelRect(0, 0, 160, 100), anchor=mark, endpoint="at", siblings=(mark,),
        box_size=(30, 20), max_positions=1, obstacles=index,
        obstacle_classes=("mark", "text", "dependency-route", "rule"),
        corner_radius=3, tail_base=8, content_bounds=(0, 0, 160, 100),
        host_id="mark:anchor", side_of_as_of=(50.0, "start"), search_pass="coarse",
        route_state_limit=1024, crossing_rule_id="as-of")

    result = nearest_free_routed_tail_box(**args)
    assert result.box is not None and result.tip is not None and result.egress is not None
    assert result.route is not None and result.route.topology == "strict"
    assert result.box.x > 50
    assert all(point[0] < 50 for point in (result.egress.semantic_port,
                                            result.egress.exposed_port,
                                            *result.egress.corridor))
    assert _route_crosses_rule_once(result.route.points, as_of.geometry)
    assert all(point[0] > 50 for point in (result.tip,))
    edge = nearest_eligible_edge(result.box, result.tip)
    base_a, base_b = tail_base_points(result.box, result.tip, edge=edge, tail_base=8,
                                      corner_radius=3)
    assert all(point[0] > 50 for point in (base_a, base_b))
    assert 0 < result.route_states <= 1024

    # The typed route exemption is only for the exact as-of rule. A text
    # obstacle covering the crossing remains authoritative.
    blocked = SurfaceObstacleIndex()
    blocked.extend(index.all())
    blocked.add(SurfaceObstacle("blocking-text", "text", "timeline",
                                ObstacleRect(49, 0, 51, 100)))
    assert nearest_free_routed_tail_box(**{**args, "obstacles": blocked}).box is None
    other_rule = SurfaceObstacleIndex()
    other_rule.extend(index.all())
    other_rule.add(SurfaceObstacle("another-rule", "rule", "timeline",
                                   ObstacleSegment((50, 0), (50, 100))))
    assert nearest_free_routed_tail_box(**{**args, "obstacles": other_rule}).box is None


def test_as_of_fallback_requires_exactly_one_interior_transverse_crossing() -> None:
    rule = ObstacleSegment((50, 0), (50, 100))
    assert _route_crosses_rule_once(((30, 40), (70, 40)), rule)
    assert not _route_crosses_rule_once(((30, 40), (50, 40), (70, 40)), rule)
    assert not _route_crosses_rule_once(((30, 40), (70, 40), (30, 50), (70, 50)), rule)
    assert not _route_crosses_rule_once(((50, -10), (50, 110)), rule)
    assert not _route_crosses_rule_once(((30, 0), (70, 0)), rule)


def test_as_of_fallback_continues_after_body_free_box_has_no_route(monkeypatch) -> None:
    mark = MarkPlacement("mark:anchor", "anchor", Rect(20, 40, 10, 10),
                         (20, 45), (30, 45), mark_shape="point")
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:anchor", "mark", "plot", ObstacleRect(20, 40, 30, 50)))
    index.add(SurfaceObstacle("as-of", "rule", "timeline", ObstacleSegment((50, 0), (50, 100))))
    first = LabelRect(130, 0, 30, 20)
    later = LabelRect(65, 40, 30, 20)
    monkeypatch.setattr(search, "_candidate_positions",
                        lambda *args, **kwargs: iter((first, later)))
    original_egresses = search.connector_egress_candidates

    def egresses(anchor, endpoint, target, siblings, **kwargs):
        # The first box is body-free but has no legal source egress; the next
        # coarse box has a complete strict route in the same bounded search.
        if target == (first.x + first.width / 2, first.y + first.height / 2):
            return ()
        return original_egresses(anchor, endpoint, target, siblings, **kwargs)

    monkeypatch.setattr(search, "connector_egress_candidates", egresses)
    result = nearest_free_routed_tail_box(
        region=LabelRect(0, 0, 160, 100), anchor=mark, endpoint="at", siblings=(mark,),
        box_size=(30, 20), max_positions=2, obstacles=index,
        obstacle_classes=("mark", "text", "dependency-route", "rule"),
        corner_radius=3, tail_base=8, content_bounds=(0, 0, 160, 100),
        host_id="mark:anchor", side_of_as_of=(50.0, "start"), search_pass="coarse",
        route_state_limit=1024, crossing_rule_id="as-of")

    assert result.box == later
    assert result.route is not None and result.egress is not None
    assert result.box_trials == 2
    assert 0 < result.route_states <= 1024


def _marks(*items):
    index = SurfaceObstacleIndex()
    for placement_id, rect in items:
        index.add(SurfaceObstacle(placement_id, "mark", "plot", ObstacleRect(*rect)))
    return index


def test_least_covering_box_takes_a_position_that_covers_no_other_object() -> None:
    region = LabelRect(0, 0, 400, 100)
    index = _marks(("planned:a", (0, 0, 150, 100)), ("planned:b", (150, 0, 250, 100)))
    owner = {"planned:a": "a", "planned:b": "b"}.__getitem__
    choice = search.least_covering_box(
        region=region, anchor_center=(75, 50), box_size=(100, 30), max_positions=1024, obstacles=index,
        obstacle_classes=("mark",), mark_owner=owner, own_owner="a")
    assert choice is not None and choice.covered_owners == ()
    # The anchor's own mark may stay under the box; the other object's may not.
    assert choice.box.x < 150 and choice.box.right <= 150 + 1e-9 or choice.box.x >= 250 - 1e-9


def test_least_covering_box_names_the_fewest_covered_objects_when_none_is_free() -> None:
    region = LabelRect(0, 0, 200, 40)
    index = _marks(("planned:a", (0, 0, 40, 40)), ("planned:b", (40, 0, 120, 40)), ("planned:c", (120, 0, 200, 40)))
    owner = {"planned:a": "a", "planned:b": "b", "planned:c": "c"}.__getitem__
    choice = search.least_covering_box(
        region=region, anchor_center=(20, 20), box_size=(60, 20), max_positions=1024, obstacles=index,
        obstacle_classes=("mark",), mark_owner=owner, own_owner="a")
    assert choice is not None
    assert len(choice.covered_owners) == 1 and choice.covered_owners[0] in {"b", "c"}


def test_largest_free_extent_is_smaller_than_the_box_that_failed() -> None:
    region = LabelRect(0, 0, 300, 100)
    index = _marks(("planned:a", (100, 0, 110, 100)), ("planned:b", (200, 0, 210, 100)))
    width, height = search.largest_free_extent(
        region=region, box_size=(120, 30), obstacles=index, obstacle_classes=("mark",))
    assert (width < 120 or height < 30) and width > 0 and height > 0
