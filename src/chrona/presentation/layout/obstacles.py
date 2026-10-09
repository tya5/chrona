"""One typed, renderer-neutral inventory of completed surface obstacles."""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import ceil, floor, hypot, isfinite, sqrt
from typing import Iterable, Mapping


@dataclass(frozen=True)
class ObstacleRect:
    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        if (not all(isfinite(value) for value in (self.left, self.top, self.right, self.bottom))
                or self.right <= self.left or self.bottom <= self.top):
            raise _obstacle_error("E_LAYOUT_OBSTACLE_GEOMETRY", "ObstacleRect",
                                  left=self.left, top=self.top, right=self.right, bottom=self.bottom)


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
            raise _obstacle_error("E_LAYOUT_OBSTACLE_GEOMETRY", "ObstacleSegment",
                                  start=self.start, end=self.end, stroke_width=self.stroke_width)


ObstacleGeometry = ObstacleRect | ObstacleSegment
# A corridor that a lane route needs but has not been placed in yet: member names avoid it, routes ignore it.
ROUTE_RESERVE_CLASS = "route-reserve"
BOUNDARY_CONTACT_TOLERANCE = 1e-9


def _obstacle_error(code: str, owner: str, **operands: object) -> ValueError:
    fields = []
    for name, value in operands.items():
        shown = repr(value).replace("\n", " ").replace("\r", " ")[:96]
        fields.append(f"{name}={shown}")
    return ValueError(f"{code}: {owner} " + ", ".join(fields))


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
            raise _obstacle_error("E_LAYOUT_OBSTACLE_INPUT", "SurfaceObstacle",
                                  placement_id=self.placement_id, obstacle_class=self.obstacle_class,
                                  region_id=self.region_id, clearance=self.clearance)


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


def obstacles_intersect(left: ObstacleGeometry, right: ObstacleGeometry, clearance: float = 0.0) -> bool:
    """Apply Layout's canonical visible-obstacle collision predicate read-only."""
    if not isfinite(clearance) or clearance < 0:
        raise _obstacle_error("E_LAYOUT_OBSTACLE_INPUT", "collision clearance", clearance=clearance)
    return _intersects(left, right, clearance)


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


def segment_length_inside_rect(segment: ObstacleSegment, rect: ObstacleRect) -> float:
    """Length of a straight segment inside a rectangle; boundary contact is zero."""
    x1, y1 = segment.start
    x2, y2 = segment.end
    low, high = 0.0, 1.0
    for value, delta, start, end in ((x1, x2 - x1, rect.left, rect.right),
                                     (y1, y2 - y1, rect.top, rect.bottom)):
        if delta == 0:
            if not start + BOUNDARY_CONTACT_TOLERANCE < value < end - BOUNDARY_CONTACT_TOLERANCE:
                return 0.0
            continue
        a, b = sorted(((start - value) / delta, (end - value) / delta))
        low, high = max(low, a), min(high, b)
    return max(0.0, high - low) * hypot(x2 - x1, y2 - y1)


def segment_overlap_length(first: tuple[tuple[float, float], tuple[float, float]],
                           second: tuple[tuple[float, float], tuple[float, float]]) -> float:
    """Shared orthogonal collinear length, excluding crossings and point contacts."""
    (a, b), (c, d) = first, second
    if a[1] == b[1] == c[1] == d[1]:
        axis = 0
    elif a[0] == b[0] == c[0] == d[0]:
        axis = 1
    else:
        return 0.0
    return max(0.0, min(max(a[axis], b[axis]), max(c[axis], d[axis]))
               - max(min(a[axis], b[axis]), min(c[axis], d[axis])))


def _segment_crosses_rect_interior(segment: ObstacleSegment, rect: ObstacleRect) -> bool:
    return segment_length_inside_rect(segment, rect) > BOUNDARY_CONTACT_TOLERANCE


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


# A selection is scanned linearly for its first queries and gets a grid only when it is
# queried again and again (a route search), so a short-lived index pays no build cost.
_GRID_AFTER_QUERIES = 2
_GRID_MIN_ITEMS = 16
_GRID_WIDE_CELLS = 64


# Memoised route searches (#760 item 2). The memo is a value-keyed cache of pure results,
# private to one index lineage (`copy()` shares it); see the design document for the key.
ROUTE_MEMO_LIMIT = 4096
_ROUTE_MEMO_CONTENT_LIMIT = 256
_UNSET = object()


class _RouteMemo:
    """Search results keyed by the exact content a search read; bounded, never evicting."""

    __slots__ = ("results", "contents")

    def __init__(self) -> None:
        self.results: dict[tuple, object] = {}
        self.contents: dict[tuple[str, ...], int] = {}

    def content_id(self, content: tuple[str, ...]) -> int | None:
        """A small id equal exactly when the contents are equal; None once the bound is reached."""
        known = self.contents.get(content)
        if known is None and len(self.contents) < _ROUTE_MEMO_CONTENT_LIMIT:
            known = self.contents[content] = len(self.contents)
        return known

    def store(self, key: tuple, value: object) -> None:
        if len(self.results) < ROUTE_MEMO_LIMIT:
            self.results[key] = value


class _PreparedSelection:
    """One `select()` result with its envelopes, and a conservative grid over them.

    The grid only narrows which positions the unchanged collision predicates are
    asked about: every pair the exact envelope test accepts shares a grid cell,
    and candidates are always visited in ascending (sorted `placement_id`) position.
    """

    __slots__ = ("items", "envelopes", "clearances", "max_clearance", "queries", "_grid", "content_id")

    def __init__(self, items: tuple[SurfaceObstacle, ...]) -> None:
        self.items = items
        self.envelopes = tuple(obstacle_envelope(item.geometry) for item in items)
        self.clearances = tuple(item.clearance for item in items)
        self.max_clearance = max(self.clearances, default=0.0)
        self.queries = 0
        self._grid: tuple | None = None
        self.content_id: int | None | object = _UNSET  # computed on first route-memo use

    def candidates(self, box: tuple[float, float, float, float], clearance: float) -> Iterable[int]:
        """Ascending positions that may overlap `box` widened by `clearance`; a superset."""
        self.queries += 1
        count = len(self.items)
        if count < _GRID_MIN_ITEMS or self.queries <= _GRID_AFTER_QUERIES:
            return range(count)
        if self._grid is None:
            self._grid = self._build_grid()
        origin_x, origin_y, size, cells, slack, table, wide = self._grid
        reach = clearance + self.max_clearance + slack
        low_x = max(0, floor((box[0] - reach - origin_x) / size))
        high_x = min(cells - 1, floor((box[2] + reach - origin_x) / size))
        low_y = max(0, floor((box[1] - reach - origin_y) / size))
        high_y = min(cells - 1, floor((box[3] + reach - origin_y) / size))
        if low_x > high_x or low_y > high_y:
            return wide
        found = set(wide)
        for cell_x in range(low_x, high_x + 1):
            for cell_y in range(low_y, high_y + 1):
                found.update(table.get((cell_x, cell_y), ()))
        return sorted(found)

    def _build_grid(self) -> tuple:
        envelopes = self.envelopes
        origin_x = min(box[0] for box in envelopes)
        origin_y = min(box[1] for box in envelopes)
        extent_x = max(box[2] for box in envelopes) - origin_x
        extent_y = max(box[3] for box in envelopes) - origin_y
        magnitude = max(max(abs(value) for box in envelopes for value in box), 1.0)
        slack = 1e-6 + 1e-9 * magnitude
        per_axis = max(1, ceil(sqrt(len(envelopes))))
        size = max(extent_x, extent_y) / per_axis or 1.0
        cells = per_axis + 1
        table: dict[tuple[int, int], list[int]] = {}
        wide: list[int] = []
        for position, (left, top, right, bottom) in enumerate(envelopes):
            low_x = max(0, floor((left - slack - origin_x) / size))
            high_x = min(cells - 1, floor((right + slack - origin_x) / size))
            low_y = max(0, floor((top - slack - origin_y) / size))
            high_y = min(cells - 1, floor((bottom + slack - origin_y) / size))
            if (high_x - low_x + 1) * (high_y - low_y + 1) > _GRID_WIDE_CELLS:
                wide.append(position)
                continue
            for cell_x in range(low_x, high_x + 1):
                for cell_y in range(low_y, high_y + 1):
                    table.setdefault((cell_x, cell_y), []).append(position)
        return origin_x, origin_y, size, cells, slack, table, tuple(wide)


class SurfaceObstacleIndex:
    """A monotone surface-local closure; queries never mutate accepted geometry."""

    def __init__(self) -> None:
        self._by_id: dict[str, SurfaceObstacle] = {}
        self._ordered: tuple[SurfaceObstacle, ...] | None = None
        self._prepared: dict[tuple[frozenset[str] | None, frozenset[str] | None], _PreparedSelection] = {}
        self._route_memo = _RouteMemo()

    def add(self, obstacle: SurfaceObstacle) -> None:
        if obstacle.placement_id in self._by_id:
            raise _obstacle_error("E_LAYOUT_OBSTACLE_ID_DUPLICATE", "obstacle inventory",
                                  placement_id=obstacle.placement_id)
        self._by_id[obstacle.placement_id] = obstacle
        self._ordered = None
        self._prepared = {}

    def copy(self, *, geometry_overrides: Mapping[str, ObstacleGeometry] | None = None) -> "SurfaceObstacleIndex":
        """An independent query snapshot, optionally using completed paint footprints.

        Accepted placements remain in the original inventory. Memoization reads
        exact obstacle content, including any substituted geometry.
        """
        if geometry_overrides is not None and any(key not in self._by_id for key in geometry_overrides):
            raise _obstacle_error("E_LAYOUT_OBSTACLE_INPUT", "geometry override",
                                  unknown_placement_ids=tuple(key for key in geometry_overrides
                                                              if key not in self._by_id))
        clone = SurfaceObstacleIndex()
        clone._by_id = (dict(self._by_id) if not geometry_overrides else
                        {key: replace(item, geometry=geometry_overrides[key])
                         if key in geometry_overrides else item for key, item in self._by_id.items()})
        clone._route_memo = self._route_memo  # value-keyed results of pure searches, valid for any lineage member
        return clone

    def route_memo_scope(self, classes: Iterable[str] | None, regions: Iterable[str] | None,
                         port_ids: Iterable[str]) -> tuple[_RouteMemo, int] | None:
        """The memo and the id of the selection's exact content, or None when a search must run fresh.

        A search reads only the selected obstacles and the named port exemptions, so equal content
        and equal exemptions give an equal result. An exemption that is not an existing port makes
        `collisions` raise, so such a call is never memoised.
        """
        if any(port_id not in self._by_id or self._by_id[port_id].obstacle_class != "port"
               for port_id in port_ids):
            return None
        prepared = self._selection(classes, regions)
        if prepared.content_id is _UNSET:
            # `repr` round-trips floats, so it tells 0.0 from -0.0 and one ulp from the next.
            prepared.content_id = self._route_memo.content_id(tuple(repr(item) for item in prepared.items))
        content_id = prepared.content_id
        return None if content_id is None else (self._route_memo, content_id)

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
        return self._selection(classes, regions).items

    def _selection(self, classes: Iterable[str] | None,
                   regions: Iterable[str] | None) -> _PreparedSelection:
        selected_classes = None if classes is None else frozenset(classes)
        selected_regions = None if regions is None else frozenset(regions)
        key = (selected_classes, selected_regions)
        prepared = self._prepared.get(key)
        if prepared is None:
            prepared = self._prepared[key] = _PreparedSelection(tuple(
                item for item in self.all()
                if (selected_classes is None or item.obstacle_class in selected_classes)
                and (selected_regions is None or item.region_id in selected_regions)))
        return prepared

    def collisions(self, geometry: ObstacleGeometry, *, classes: Iterable[str] | None = None,
                   regions: Iterable[str] | None = None, host_id: str | None = None,
                   rule_host_id: str | None = None,
                   port_ids: Iterable[str] = (),
                   clearance: float = 0.0) -> tuple[SurfaceObstacle, ...]:
        if not isfinite(clearance) or clearance < 0:
            raise _obstacle_error("E_LAYOUT_OBSTACLE_INPUT", "collision clearance", clearance=clearance)
        exemptions = frozenset(port_ids)
        if host_id is not None:
            host = self._by_id.get(host_id)
            if host is None or host.obstacle_class != "mark":
                raise _obstacle_error("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID", "host exemption",
                                      host_id=host_id,
                                      actual_class=host.obstacle_class if host is not None else None,
                                      expected_class="mark")
            exemptions |= {host_id}
        if rule_host_id is not None:
            rule = self._by_id.get(rule_host_id)
            if rule is None or rule.obstacle_class != "rule":
                raise _obstacle_error("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID", "rule host exemption",
                                      rule_host_id=rule_host_id,
                                      actual_class=rule.obstacle_class if rule is not None else None,
                                      expected_class="rule")
            exemptions |= {rule_host_id}
        if any(port_id not in self._by_id or self._by_id[port_id].obstacle_class != "port"
               for port_id in exemptions.difference({item for item in (host_id, rule_host_id) if item is not None})):
            raise _obstacle_error("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID", "port exemptions",
                                  invalid_port_ids=tuple(port_id for port_id in exemptions
                                                         if port_id not in self._by_id
                                                         or self._by_id[port_id].obstacle_class != "port"))
        candidate_box = obstacle_envelope(geometry)
        prepared = self._selection(classes, regions)
        items, envelopes, clearances = prepared.items, prepared.envelopes, prepared.clearances
        found = []
        # Candidates arrive in ascending position, i.e. the sorted `placement_id`
        # order `select()` always returned; the tests below are the original ones.
        for position in prepared.candidates(candidate_box, clearance):
            item = items[position]
            reach = clearance + clearances[position]
            if (item.placement_id not in exemptions
                    and _envelopes_overlap(candidate_box, envelopes[position], reach)
                    and _intersects(geometry, item.geometry, reach)):
                found.append(item)
        return tuple(found)

    def egress_collisions(self, segment: ObstacleSegment, *, host_ids: Iterable[str],
                          classes: Iterable[str] | None = None,
                          regions: Iterable[str] | None = None,
                          port_ids: Iterable[str] = ()) -> tuple[SurfaceObstacle, ...]:
        """Exempt named comparison marks on one endpoint corridor only."""
        hosts = frozenset(host_ids)
        if not hosts or any(host not in self._by_id or self._by_id[host].obstacle_class != "mark"
                            for host in hosts):
            raise _obstacle_error("E_LAYOUT_OBSTACLE_EXEMPTION_INVALID", "egress host exemptions",
                                  host_ids=tuple(hosts), expected_class="mark",
                                  actual_classes=tuple((host, self._by_id[host].obstacle_class
                                                        if host in self._by_id else None)
                                                       for host in hosts))
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
