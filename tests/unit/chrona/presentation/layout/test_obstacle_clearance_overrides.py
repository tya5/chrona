"""A query snapshot may widen named obstacles by a clearance without touching the accepted inventory (#1848)."""
from __future__ import annotations

from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)


def _index() -> SurfaceObstacleIndex:
    index = SurfaceObstacleIndex()
    index.extend((
        SurfaceObstacle("name", "text", "timeline", ObstacleRect(100, 10, 160, 30)),
        SurfaceObstacle("bar", "mark", "timeline", ObstacleRect(10, 10, 90, 30)),
    ))
    return index


def test_clearance_override_widens_only_the_snapshot_and_only_the_named_obstacle() -> None:
    index = _index()
    snapshot = index.copy(clearance_overrides={"name": 8.0, "missing": 3.0})  # an unknown identity is harmless

    probe = ObstacleSegment((95, 0), (95, 40), stroke_width=1)  # 5 px from the name, 5 px from the bar
    assert [item.placement_id for item in index.collisions(probe)] == []
    assert [item.placement_id for item in snapshot.collisions(probe)] == ["name"]
    assert snapshot.get("bar").clearance == 0.0 and snapshot.get("name").clearance == 8.0
    assert index.get("name").clearance == 0.0
    assert not snapshot.has("missing")


def test_clearance_equal_to_the_current_value_keeps_the_snapshot_shared_and_relaxation_restores_it() -> None:
    index = _index()
    unchanged = index.copy(clearance_overrides={"name": 0.0})
    assert [item.placement_id for item in unchanged.all()] == [item.placement_id for item in index.all()]
    widened = index.copy(clearance_overrides={"name": 8.0})
    relaxed = widened.copy(clearance_overrides={"name": 0.0})
    probe = ObstacleSegment((95, 0), (95, 40), stroke_width=1)
    assert relaxed.collisions(probe) == ()
    assert widened.collisions(probe)


def test_clearance_override_composes_with_geometry_overrides_and_exclusions() -> None:
    index = _index()
    moved = ObstacleRect(120, 10, 180, 30)
    snapshot = index.copy(geometry_overrides={"name": moved}, excluded_ids=("bar",),
                          clearance_overrides={"name": 4.0, "bar": 9.0})
    assert [item.placement_id for item in snapshot.all()] == ["name"]
    assert snapshot.get("name").geometry == moved and snapshot.get("name").clearance == 4.0
