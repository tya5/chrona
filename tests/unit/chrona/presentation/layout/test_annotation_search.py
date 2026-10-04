from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.annotation_search import lattice_positions, nearest_free_box, nearest_free_tail_box
from chrona.presentation.layout.annotation_search import nearest_free_routed_tail_box
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
    last_fit = nearest_free_routed_tail_box(region=LabelRect(0, 0, 120, 100),
                                           route_state_limit=1, **common)
    assert last_fit.box is not None and not last_fit.exhausted and last_fit.route_states == 1
    # The canonical first route fits at the last permitted state. Force
    # that route to collide with a stroke, which interval setup cannot prune.
    index.add(SurfaceObstacle("stroke:below", "dependency-route", "plot",
                              ObstacleSegment((0, 51), (120, 51))))
    capped = nearest_free_routed_tail_box(region=LabelRect(0, 0, 120, 100),
                                          route_state_limit=1, **common)
    assert capped.box is None and capped.exhausted and capped.route_states == 1


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
