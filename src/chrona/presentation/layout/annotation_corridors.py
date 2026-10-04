"""Finite strict corridor descriptors; geometry and validation stay in Layout.

Input preparation is bounded by obstacle/axis counts, not the connector trial
budget. A completed path is materialized only on pop, and charged once there.
Rectangular interior pruning never replaces the full collision validator.
"""
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from math import inf

from chrona.presentation.layout.model import geometry_sum
from chrona.presentation.layout.obstacles import (
    BOUNDARY_CONTACT_TOLERANCE as EPS, ObstacleRect, ObstacleSegment,
    SurfaceObstacleIndex, obstacle_envelope,
)
from chrona.presentation.layout.routing import relation_route_quality

Point = tuple[float, float]
Bounds = tuple[float, float, float, float]


@dataclass(frozen=True)
class StrictCorridorRequest:
    start: Point
    end: Point
    index: SurfaceObstacleIndex
    bounds: Bounds
    port_ids: tuple[str, ...] = ()
    tie_break: tuple[float, ...] = ()


def _horizontal_forbidden(rect: Bounds, anchor: float, y: float) -> tuple[tuple[float, float], ...]:
    left, top, right, bottom = rect
    if not top + EPS < y < bottom - EPS:
        return ()
    intervals = []
    if right - max(anchor, left) > EPS:
        intervals.append((max(anchor, left) + EPS, inf))
    if min(anchor, right) - left > EPS:
        intervals.append((-inf, min(anchor, right) - EPS))
    return tuple(intervals)


def _vertical_crosses(rect: Bounds, x: float, start: float, end: float) -> bool:
    left, top, right, bottom = rect
    return (left + EPS < x < right - EPS
            and min(max(start, end), bottom) - max(min(start, end), top) > EPS)


def _allowed(values: tuple[float, ...], forbidden: list[tuple[float, float]]) -> tuple[float, ...]:
    merged: list[tuple[float, float]] = []
    for low, high in sorted(forbidden):
        if low >= high:
            continue
        if merged and low < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(high, merged[-1][1]))
        else:
            merged.append((low, high))
    # Open interval endpoints remain eligible exact boundary contacts.
    return tuple(value for value in values if not any(low < value < high for low, high in merged))


@dataclass
class _Row:
    request_id: int
    start: Point
    end: Point
    swapped: bool
    family: str
    y: float
    values: tuple[float, ...]
    position: int = 0

    def coordinates(self, value: float) -> tuple[float, ...]:
        """Analytic comparison key, not a completed path or collision query."""
        sx, sy = self.start
        ex, ey = self.end
        if self.family == "direct":
            flat = (sx, sy, ex, ey)
        elif self.family == "elbow":
            flat = (sx, sy, ex, sy, ex, ey)
        elif self.family == "hvh":
            flat = (sx, sy, value, sy, value, ey, ex, ey)
        else:
            flat = (sx, sy, sx, self.y, value, self.y, value, ey, ex, ey)
        if self.swapped:
            return tuple(coordinate for i in range(0, len(flat), 2) for coordinate in (flat[i+1], flat[i]))
        return flat

    def rank(self, request: StrictCorridorRequest, value: float) -> tuple[float, ...]:
        sx, sy = self.start
        ex, ey = self.end
        bends = {"direct": 0, "elbow": 1, "hvh": 2, "vhvh": 3}[self.family]
        if self.family in {"direct", "elbow"}:
            length = abs(ex-sx) + abs(ey-sy)
        else:
            vertical = ((abs(ey-sy),) if self.family == "hvh"
                        else (abs(self.y-sy), abs(ey-self.y)))
            length = geometry_sum((abs(value-sx), abs(ex-value), *vertical))
        return (bends, length, *request.tie_break, *self.coordinates(value))


class StrictCorridorSearch:
    """Merge all finite pair streams without materializing paths during setup."""

    def __init__(self, requests: tuple[StrictCorridorRequest, ...]):
        self.requests = requests
        self.prepared_rows = 0
        self.generated = 0
        self._heap: list[tuple[tuple[float, ...], int, _Row]] = []
        for request_id, request in enumerate(requests):
            self._prepare(request_id, request)

    @property
    def has_candidates(self) -> bool:
        return bool(self._heap)

    def _include(self, row: _Row) -> None:
        self.prepared_rows += 1
        if not row.values:
            return
        request = self.requests[row.request_id]
        row.values = tuple(sorted(row.values, key=lambda value: row.rank(request, value)))
        heappush(self._heap, (row.rank(request, row.values[0]), self.prepared_rows, row))

    def _prepare(self, request_id: int, request: StrictCorridorRequest) -> None:
        if request.start == request.end:
            return
        left, top, right, bottom = request.bounds
        xs, ys = {request.start[0], request.end[0]}, {request.start[1], request.end[1]}
        rectangles = []
        for item in request.index.all():
            envelope = obstacle_envelope(item.geometry)
            if isinstance(item.geometry, ObstacleRect) and item.placement_id not in request.port_ids:
                rectangles.append(envelope)
            x1, y1, x2, y2 = envelope
            padding = item.clearance + 2.0
            if x2+padding < left or x1-padding > right or y2+padding < top or y1-padding > bottom:
                continue
            xs.update((x1-2.0, x2+2.0))
            ys.update((y1-2.0, y2+2.0))
        xx = tuple(sorted(x for x in xs if left <= x <= right))
        yy = tuple(sorted(y for y in ys if top <= y <= bottom))
        if request.start[0] == request.end[0] or request.start[1] == request.end[1]:
            self._include(_Row(request_id, request.start, request.end, False, "direct", 0., (0.,)))
        for swapped in (False, True):
            flip = (lambda point: (point[1], point[0])) if swapped else (lambda point: point)
            start, end = flip(request.start), flip(request.end)
            axes, rows = (yy, xx) if swapped else (xx, yy)
            rects = [(t,l,b,r) for l,t,r,b in rectangles] if swapped else rectangles
            if start[0] != end[0] and start[1] != end[1]:
                self._include(_Row(request_id, start, end, swapped, "elbow", 0., (0.,)))
            # Partition degeneracies into direct/elbow families, avoiding both
            # zero legs and uncharged duplicate canonical paths.
            values = tuple(x for x in axes if x not in (start[0], end[0]))
            if start[1] != end[1]:
                forbidden = []
                for rect in rects:
                    forbidden.extend(_horizontal_forbidden(rect, start[0], start[1]))
                    forbidden.extend(_horizontal_forbidden(rect, end[0], end[1]))
                    if min(max(start[1],end[1]),rect[3])-max(min(start[1],end[1]),rect[1]) > EPS:
                        forbidden.append((rect[0]+EPS,rect[2]-EPS))
                self._include(_Row(request_id,start,end,swapped,"hvh",0.,_allowed(values,forbidden)))
            for y in rows:
                if y in (start[1],end[1]) or any(_vertical_crosses(rect,start[0],start[1],y) for rect in rects):
                    continue
                forbidden = []
                for rect in rects:
                    forbidden.extend(_horizontal_forbidden(rect,start[0],y))
                    forbidden.extend(_horizontal_forbidden(rect,end[0],end[1]))
                    if min(max(y,end[1]),rect[3])-max(min(y,end[1]),rect[1]) > EPS:
                        forbidden.append((rect[0]+EPS,rect[2]-EPS))
                self._include(_Row(request_id,start,end,swapped,"vhvh",y,_allowed(values,forbidden)))

    def pop(self) -> tuple[int, tuple[Point, ...]]:
        rank, serial, row = heappop(self._heap)
        self.generated += 1
        coordinates = row.coordinates(row.values[row.position])
        points = tuple((coordinates[i],coordinates[i+1]) for i in range(0,len(coordinates),2))
        row.position += 1
        if row.position < len(row.values):
            request = self.requests[row.request_id]
            heappush(self._heap, (row.rank(request,row.values[row.position]),serial,row))
        return row.request_id, points


def strict_route_is_valid(points: tuple[Point, ...], request: StrictCorridorRequest, *,
                          max_bends: int, max_detour_ratio: float) -> bool:
    return (len(points) >= 2 and all(a != b and (a[0] == b[0] or a[1] == b[1])
                                   for a,b in zip(points,points[1:]))
            and relation_route_quality(points,max_bends=max_bends,max_detour_ratio=max_detour_ratio)
            and not any(request.index.collisions(ObstacleSegment(a,b),port_ids=request.port_ids)
                        for a,b in zip(points,points[1:])))
