"""One typed, renderer-neutral inventory of completed surface obstacles."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable


@dataclass(frozen=True)
class ObstacleRect:
    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        if (not all(isfinite(value) for value in (self.left, self.top, self.right, self.bottom))
                or self.right <= self.left or self.bottom <= self.top):
            raise ValueError("E_LAYOUT_OBSTACLE_GEOMETRY")


@dataclass(frozen=True)
class ObstacleSegment:
    """One axis-aligned stroked route/rule segment, not its enclosing route box."""

    start: tuple[float, float]
    end: tuple[float, float]
    stroke_width: float = 0.0

    def __post_init__(self) -> None:
        if (not all(isfinite(value) for value in (*self.start, *self.end, self.stroke_width))
                or self.start == self.end
                or (self.start[0] != self.end[0] and self.start[1] != self.end[1])
                or self.stroke_width < 0):
            raise ValueError("E_LAYOUT_OBSTACLE_GEOMETRY")


ObstacleGeometry = ObstacleRect | ObstacleSegment


def obstacle_envelope(geometry: ObstacleGeometry) -> tuple[float, float, float, float]:
    """Only seed a finite search grid; collision queries use exact geometry."""
    if isinstance(geometry, ObstacleRect):
        return geometry.left, geometry.top, geometry.right, geometry.bottom
    radius = geometry.stroke_width / 2
    return (min(geometry.start[0], geometry.end[0]) - radius,
            min(geometry.start[1], geometry.end[1]) - radius,
            max(geometry.start[0], geometry.end[0]) + radius,
            max(geometry.start[1], geometry.end[1]) + radius)


@dataclass(frozen=True)
class SurfaceObstacle:
    placement_id: str
    obstacle_class: str
    region_id: str
    geometry: ObstacleGeometry
    clearance: float = 0.0
    host_id: str | None = None

    def __post_init__(self) -> None:
        if (not self.placement_id or not self.obstacle_class or not self.region_id
                or not isfinite(self.clearance) or self.clearance < 0):
            raise ValueError("E_LAYOUT_OBSTACLE_INPUT")


def _intersects(left: ObstacleGeometry, right: ObstacleGeometry, clearance: float) -> bool:
    if isinstance(left, ObstacleRect) and isinstance(right, ObstacleRect):
        return (left.left < right.right + clearance and right.left - clearance < left.right
                and left.top < right.bottom + clearance and right.top - clearance < left.bottom)
    # Orthogonal segment envelopes are exact stroked-segment rectangles for
    # positive stroke/clearance. For a zero-width path, an interior crossing
    # still blocks, while a touch at an endpoint does not.
    if isinstance(left, ObstacleSegment) and isinstance(right, ObstacleSegment):
        return _segments_intersect(left, right, clearance)
    segment = left if isinstance(left, ObstacleSegment) else right
    rect = right if isinstance(left, ObstacleSegment) else left
    assert isinstance(segment, ObstacleSegment) and isinstance(rect, ObstacleRect)
    radius = segment.stroke_width / 2 + clearance
    x1, y1 = segment.start
    x2, y2 = segment.end
    if y1 == y2:
        return (rect.top - radius < y1 < rect.bottom + radius
                and min(x1, x2) < rect.right + radius and rect.left - radius < max(x1, x2))
    return (rect.left - radius < x1 < rect.right + radius
            and min(y1, y2) < rect.bottom + radius and rect.top - radius < max(y1, y2))


def _segments_intersect(left: ObstacleSegment, right: ObstacleSegment, clearance: float) -> bool:
    left_radius, right_radius = left.stroke_width / 2 + clearance / 2, right.stroke_width / 2 + clearance / 2
    lx1, ly1 = left.start
    lx2, ly2 = left.end
    rx1, ry1 = right.start
    rx2, ry2 = right.end
    if ly1 == ly2 and ry1 == ry2:
        return (abs(ly1 - ry1) <= left_radius + right_radius
                and min(lx1, lx2) - left_radius < max(rx1, rx2) + right_radius
                and min(rx1, rx2) - right_radius < max(lx1, lx2) + left_radius)
    if lx1 == lx2 and rx1 == rx2:
        return (abs(lx1 - rx1) <= left_radius + right_radius
                and min(ly1, ly2) - left_radius < max(ry1, ry2) + right_radius
                and min(ry1, ry2) - right_radius < max(ly1, ly2) + left_radius)
    horizontal, vertical = (left, right) if ly1 == ly2 else (right, left)
    hx1, hy = horizontal.start
    hx2, _ = horizontal.end
    vx, vy1 = vertical.start
    _, vy2 = vertical.end
    radius = horizontal.stroke_width / 2 + vertical.stroke_width / 2 + clearance
    return (min(hx1, hx2) - radius < vx < max(hx1, hx2) + radius
            and min(vy1, vy2) - radius < hy < max(vy1, vy2) + radius)


class SurfaceObstacleIndex:
    """A monotone surface-local closure; queries never mutate accepted geometry."""

    def __init__(self) -> None:
        self._by_id: dict[str, SurfaceObstacle] = {}

    def add(self, obstacle: SurfaceObstacle) -> None:
        if obstacle.placement_id in self._by_id:
            raise ValueError("E_LAYOUT_OBSTACLE_ID_DUPLICATE")
        self._by_id[obstacle.placement_id] = obstacle

    def extend(self, obstacles: Iterable[SurfaceObstacle]) -> None:
        for obstacle in obstacles:
            self.add(obstacle)

    def all(self) -> tuple[SurfaceObstacle, ...]:
        return tuple(self._by_id[key] for key in sorted(self._by_id))

    def collisions(self, geometry: ObstacleGeometry, *, classes: Iterable[str] | None = None,
                   regions: Iterable[str] | None = None, host_id: str | None = None,
                   port_ids: Iterable[str] = (),
                   clearance: float = 0.0) -> tuple[SurfaceObstacle, ...]:
        if not isfinite(clearance) or clearance < 0:
            raise ValueError("E_LAYOUT_OBSTACLE_INPUT")
        selected_classes = None if classes is None else frozenset(classes)
        selected_regions = None if regions is None else frozenset(regions)
        exemptions = frozenset(port_ids)
        if host_id is not None:
            host = self._by_id.get(host_id)
            if host is None or host.obstacle_class != "mark":
                raise ValueError("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID")
            exemptions |= {host_id}
        if any(port_id not in self._by_id or self._by_id[port_id].obstacle_class != "port"
               for port_id in exemptions.difference({host_id} if host_id is not None else set())):
            raise ValueError("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID")
        return tuple(item for item in self.all()
                     if item.placement_id not in exemptions
                     and (selected_classes is None or item.obstacle_class in selected_classes)
                     and (selected_regions is None or item.region_id in selected_regions)
                     and _intersects(geometry, item.geometry, clearance + item.clearance))
