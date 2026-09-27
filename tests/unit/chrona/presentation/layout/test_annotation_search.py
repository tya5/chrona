from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.annotation_search import lattice_positions, nearest_free_box, nearest_free_tail_box


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
