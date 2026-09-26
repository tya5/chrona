"""One typed, renderer-neutral inventory of completed surface obstacles."""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isfinite
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
    """One stroked route/rule segment, not its enclosing route box."""

    start: tuple[float, float]
    end: tuple[float, float]
    stroke_width: float = 0.0

    def __post_init__(self) -> None:
        if (not all(isfinite(value) for value in (*self.start, *self.end, self.stroke_width))
                or self.start == self.end
                or self.stroke_width < 0):
            raise ValueError("E_LAYOUT_OBSTACLE_GEOMETRY")


ObstacleGeometry = ObstacleRect | ObstacleSegment
BOUNDARY_CONTACT_TOLERANCE = 1e-9


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
    if isinstance(left, ObstacleSegment) and isinstance(right, ObstacleSegment):
        return _segments_intersect(left, right, clearance)
    segment = left if isinstance(left, ObstacleSegment) else right
    rect = right if isinstance(left, ObstacleSegment) else left
    assert isinstance(segment, ObstacleSegment) and isinstance(rect, ObstacleRect)
    radius = segment.stroke_width / 2 + clearance
    if _segment_crosses_rect_interior(segment, rect):
        return True
    if radius == 0:
        return False
    corners = ((rect.left, rect.top), (rect.right, rect.top),
               (rect.right, rect.bottom), (rect.left, rect.bottom))
    return any(_segment_distance(segment.start, segment.end, corners[index], corners[(index + 1) % 4]) < radius
               for index in range(4))


def _segments_intersect(left: ObstacleSegment, right: ObstacleSegment, clearance: float) -> bool:
    radius = left.stroke_width / 2 + right.stroke_width / 2 + clearance
    distance = _segment_distance(left.start, left.end, right.start, right.end)
    if radius > 0:
        return distance < radius
    if distance > 1e-9:
        return False
    # A shared endpoint is a legal touch only when the interiors do not
    # overlap. Any crossing or collinear overlap blocks.
    shared = set((left.start, left.end)).intersection((right.start, right.end))
    if not shared:
        return True
    if len(shared) == 2:
        return True
    point = next(iter(shared))
    other_left = left.end if left.start == point else left.start
    other_right = right.end if right.start == point else right.start
    cross = _cross(point, other_left, other_right)
    return abs(cross) < 1e-9 and ((other_left[0] - point[0]) * (other_right[0] - point[0])
                                  + (other_left[1] - point[1]) * (other_right[1] - point[1])) > 0


def _segment_crosses_rect_interior(segment: ObstacleSegment, rect: ObstacleRect) -> bool:
    x1, y1 = segment.start
    x2, y2 = segment.end
    low, high = 0.0, 1.0
    for value, delta, start, end in ((x1, x2 - x1, rect.left, rect.right),
                                     (y1, y2 - y1, rect.top, rect.bottom)):
        if delta == 0:
            if not start + BOUNDARY_CONTACT_TOLERANCE < value < end - BOUNDARY_CONTACT_TOLERANCE:
                return False
            continue
        a, b = sorted(((start - value) / delta, (end - value) / delta))
        low, high = max(low, a), min(high, b)
    return low < high and hypot(x2 - x1, y2 - y1) * (high - low) > BOUNDARY_CONTACT_TOLERANCE


def _cross(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_segment_distance(point: tuple[float, float], start: tuple[float, float],
                            end: tuple[float, float]) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    position = max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy)
                            / (dx * dx + dy * dy)))
    return hypot(point[0] - start[0] - position * dx, point[1] - start[1] - position * dy)


def _segment_distance(a: tuple[float, float], b: tuple[float, float],
                      c: tuple[float, float], d: tuple[float, float]) -> float:
    cross1, cross2 = _cross(a, b, c), _cross(a, b, d)
    cross3, cross4 = _cross(c, d, a), _cross(c, d, b)
    if cross1 * cross2 <= 0 and cross3 * cross4 <= 0:
        # Collinear disjoint segments fail the bounding-box overlap test.
        if (max(min(a[0], b[0]), min(c[0], d[0])) <= min(max(a[0], b[0]), max(c[0], d[0]))
                and max(min(a[1], b[1]), min(c[1], d[1])) <= min(max(a[1], b[1]), max(c[1], d[1]))):
            return 0.0
    return min(_point_segment_distance(a, c, d), _point_segment_distance(b, c, d),
               _point_segment_distance(c, a, b), _point_segment_distance(d, a, b))


class SurfaceObstacleIndex:
    """A monotone surface-local closure; queries never mutate accepted geometry."""

    def __init__(self) -> None:
        self._by_id: dict[str, SurfaceObstacle] = {}
        self._ordered: tuple[SurfaceObstacle, ...] | None = None

    def add(self, obstacle: SurfaceObstacle) -> None:
        if obstacle.placement_id in self._by_id:
            raise ValueError("E_LAYOUT_OBSTACLE_ID_DUPLICATE")
        self._by_id[obstacle.placement_id] = obstacle
        self._ordered = None

    def extend(self, obstacles: Iterable[SurfaceObstacle]) -> None:
        for obstacle in obstacles:
            self.add(obstacle)

    def all(self) -> tuple[SurfaceObstacle, ...]:
        if self._ordered is None:
            self._ordered = tuple(self._by_id[key] for key in sorted(self._by_id))
        return self._ordered

    def has(self, placement_id: str) -> bool:
        return placement_id in self._by_id

    def select(self, *, classes: Iterable[str] | None = None,
               regions: Iterable[str] | None = None) -> tuple[SurfaceObstacle, ...]:
        selected_classes = None if classes is None else frozenset(classes)
        selected_regions = None if regions is None else frozenset(regions)
        return tuple(item for item in self.all()
                     if (selected_classes is None or item.obstacle_class in selected_classes)
                     and (selected_regions is None or item.region_id in selected_regions))

    def collisions(self, geometry: ObstacleGeometry, *, classes: Iterable[str] | None = None,
                   regions: Iterable[str] | None = None, host_id: str | None = None,
                   rule_host_id: str | None = None,
                   port_ids: Iterable[str] = (),
                   clearance: float = 0.0) -> tuple[SurfaceObstacle, ...]:
        if not isfinite(clearance) or clearance < 0:
            raise ValueError("E_LAYOUT_OBSTACLE_INPUT")
        exemptions = frozenset(port_ids)
        if host_id is not None:
            host = self._by_id.get(host_id)
            if host is None or host.obstacle_class != "mark":
                raise ValueError("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID")
            exemptions |= {host_id}
        if rule_host_id is not None:
            rule = self._by_id.get(rule_host_id)
            if rule is None or rule.obstacle_class != "rule":
                raise ValueError("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID")
            exemptions |= {rule_host_id}
        if any(port_id not in self._by_id or self._by_id[port_id].obstacle_class != "port"
               for port_id in exemptions.difference({item for item in (host_id, rule_host_id) if item is not None})):
            raise ValueError("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID")
        candidate_box = obstacle_envelope(geometry)
        return tuple(item for item in self.select(classes=classes, regions=regions)
                     if item.placement_id not in exemptions
                     and _envelopes_overlap(candidate_box, obstacle_envelope(item.geometry),
                                            clearance + item.clearance)
                     and _intersects(geometry, item.geometry, clearance + item.clearance))

    def egress_collisions(self, segment: ObstacleSegment, *, host_ids: Iterable[str],
                          classes: Iterable[str] | None = None,
                          regions: Iterable[str] | None = None,
                          port_ids: Iterable[str] = ()) -> tuple[SurfaceObstacle, ...]:
        """Exempt named comparison marks on one endpoint corridor only."""
        hosts = frozenset(host_ids)
        if not hosts or any(host not in self._by_id or self._by_id[host].obstacle_class != "mark"
                            for host in hosts):
            raise ValueError("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID")
        def shared_endpoint_branch(item: SurfaceObstacle) -> bool:
            other = item.geometry
            if (item.obstacle_class not in {"dependency-route", "leader-route"}
                    or not isinstance(other, ObstacleSegment)
                    or segment.start not in (other.start, other.end)):
                return False
            far = other.end if segment.start == other.start else other.start
            cross = _cross(segment.start, segment.end, far)
            dot = ((segment.end[0] - segment.start[0]) * (far[0] - segment.start[0])
                   + (segment.end[1] - segment.start[1]) * (far[1] - segment.start[1]))
            return abs(cross) > BOUNDARY_CONTACT_TOLERANCE or dot < 0

        return tuple(item for item in self.collisions(segment, classes=classes, regions=regions,
                                                       port_ids=port_ids)
                     if item.placement_id not in hosts and not shared_endpoint_branch(item))


def _envelopes_overlap(left: tuple[float, float, float, float],
                       right: tuple[float, float, float, float], clearance: float) -> bool:
    return (left[0] <= right[2] + clearance and right[0] - clearance <= left[2]
            and left[1] <= right[3] + clearance and right[1] - clearance <= left[3])
