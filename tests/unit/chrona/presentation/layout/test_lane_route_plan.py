"""Obstacle-index isolation and route geometry controls retained after corridor retirement."""
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.routing import route_orthogonal


def test_index_copies_are_independent_for_private_layout_trials():
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:a", "mark", "timeline", ObstacleRect(40, 40, 60, 60)))
    clone = index.copy()
    clone.add(SurfaceObstacle("text:probe", "text", "timeline", ObstacleRect(10, 10, 20, 20)))
    index.add(SurfaceObstacle("text:final", "text", "timeline", ObstacleRect(20, 20, 30, 30)))

    assert [item.placement_id for item in clone.all()] == ["mark:a", "text:probe"]
    assert [item.placement_id for item in index.all()] == ["mark:a", "text:final"]


def test_router_uses_real_mark_geometry_and_keeps_a_clear_orthogonal_route():
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("mark:block", "mark", "timeline", ObstacleRect(40, 30, 60, 70)))
    path = route_orthogonal((0, 50), (100, 50), index, bounds=(0, 0, 100, 100),
                            classes=("mark",), regions=("timeline",))

    assert path[0] == (0, 50) and path[-1] == (100, 50)
    assert all(not (start[0] == end[0] and 40 < start[0] < 60
                    and max(start[1], end[1]) > 30 and min(start[1], end[1]) < 70)
               for start, end in zip(path, path[1:]))
