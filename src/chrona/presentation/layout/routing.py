"""Deterministic renderer-neutral routing used while building a presentation Scene."""
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
import json
from math import isfinite

from chrona.presentation.layout.model import geometry_sum
from chrona.presentation.layout.obstacles import ObstacleSegment, SurfaceObstacleIndex, obstacle_envelope


class RouteSearchFailure(ValueError):
    """A bounded orthogonal search found no route; unrelated ValueErrors propagate."""


@dataclass(frozen=True)
class RouteAttemptEvidence:
    source_side: str
    target_side: str
    outcome: str
    blocker_ids: tuple[str, ...] = ()
    search_failure: str | None = None
    length: float | None = None
    direct_length: float | None = None
    bends: int | None = None
    max_bends: int | None = None
    max_detour_ratio: float | None = None

    def __post_init__(self) -> None:
        if (self.outcome not in {"egress-collision", "no-route-found", "quality-rejected", "accepted"}
                or not self.source_side or not self.target_side):
            raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID")
        if self.outcome == "egress-collision":
            if (not self.blocker_ids or self.search_failure is not None
                    or any(value is not None for value in self._quality_values())):
                raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID")
        elif self.outcome == "no-route-found":
            if (self.blocker_ids or self.search_failure not in {
                    "E_PRESENTATION_ROUTE_LIMIT", "E_CONNECTOR_UNROUTABLE"}
                    or any(value is not None for value in self._quality_values())):
                raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID")
        else:
            values = self._quality_values()
            if (self.blocker_ids or self.search_failure is not None
                    or any(value is None for value in values)
                    or not all(isfinite(value) for value in (self.length, self.direct_length, self.max_detour_ratio))
                    or self.length < 0 or self.direct_length < 0 or self.bends < 0
                    or self.max_bends < 0 or self.max_detour_ratio <= 0):
                raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID")
            within = self.bends <= self.max_bends and (
                self.direct_length == 0 or self.length <= self.direct_length * self.max_detour_ratio)
            if within != (self.outcome == "accepted"):
                raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID")

    def _quality_values(self) -> tuple[float | int | None, ...]:
        return (self.length, self.direct_length, self.bends, self.max_bends, self.max_detour_ratio)


@dataclass(frozen=True)
class RouteSuppressionEvidence:
    relation_id: str
    attempts: tuple[RouteAttemptEvidence, ...]

    def __post_init__(self) -> None:
        if not self.relation_id or not self.attempts or any(
                attempt.outcome == "accepted" for attempt in self.attempts):
            raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID")

    @property
    def primary_cause(self) -> str:
        outcomes = {attempt.outcome for attempt in self.attempts}
        if "quality-rejected" in outcomes:
            return "quality-rejected"
        if "no-route-found" in outcomes:
            return "no-route-found"
        return "egress-collision"

    @property
    def diagnostic(self) -> str:
        """Stable lane-only evidence, including each measured rejected port pair."""
        attempts = []
        for attempt in self.attempts:
            record = {"sourceSide": attempt.source_side, "targetSide": attempt.target_side,
                      "outcome": attempt.outcome}
            if attempt.blocker_ids:
                record["blockerIds"] = list(attempt.blocker_ids)
            if attempt.search_failure is not None:
                record["searchFailure"] = attempt.search_failure
            if attempt.length is not None:
                record.update(length=attempt.length, directLength=attempt.direct_length,
                              bends=attempt.bends, maxBends=attempt.max_bends,
                              maxDetourRatio=attempt.max_detour_ratio)
            attempts.append(record)
        payload = {"relationId": self.relation_id, "primaryCause": self.primary_cause,
                   "attempts": attempts}
        return "I_LAYOUT_LANE_ROUTE_CAUSE:" + json.dumps(payload, sort_keys=True, separators=(",", ":"))


def place_relation_route(*, source_port: tuple[float, float], target_port: tuple[float, float],
                         obstacles: tuple[tuple[float, float, float, float], ...] | SurfaceObstacleIndex,
                         bounds: tuple[float, float, float, float],
                         port_ids: tuple[str, ...] = (), regions: tuple[str, ...] | None = None,
                         classes: tuple[str, ...] | None = None) -> tuple[tuple[float, float], ...]:
    """Complete one dependency route before Scene projects a path primitive."""
    return route_orthogonal(source_port, target_port, obstacles, bounds=bounds,
                            port_ids=port_ids, regions=regions, classes=classes)


def relation_route_quality(points: tuple[tuple[float, float], ...], *,
                           max_bends: int, max_detour_ratio: float) -> bool:
    """Evaluate a completed route against the explicit Layout Profile limits."""
    if len(points) < 2:
        return False
    length, direct, bends = route_quality_metrics(points)
    return bends <= max_bends and (direct == 0 or length <= direct * max_detour_ratio)


def route_quality_metrics(points: tuple[tuple[float, float], ...]) -> tuple[float, float, int]:
    """Return the exact metrics used by the route-quality decision and evidence."""
    if len(points) < 2:
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID")
    bends = max(0, len(points) - 2)
    length = geometry_sum(abs(right[0] - left[0]) + abs(right[1] - left[1])
                          for left, right in zip(points, points[1:]))
    direct = abs(points[-1][0] - points[0][0]) + abs(points[-1][1] - points[0][1])
    return length, direct, bends


def route_quality_attempt(
    source_side: str, target_side: str, points: tuple[tuple[float, float], ...], *,
    max_bends: int, max_detour_ratio: float,
) -> RouteAttemptEvidence:
    """Close a measured attempt using the same metrics as the quality predicate."""
    length, direct, bends = route_quality_metrics(points)
    accepted = bends <= max_bends and (direct == 0 or length <= direct * max_detour_ratio)
    return RouteAttemptEvidence(source_side, target_side,
                                "accepted" if accepted else "quality-rejected",
                                length=length, direct_length=direct, bends=bends,
                                max_bends=max_bends, max_detour_ratio=max_detour_ratio)


def route_orthogonal(start: tuple[float, float], end: tuple[float, float],
                     obstacles: tuple[tuple[float, float, float, float], ...] | SurfaceObstacleIndex, *,
                     grid_offset: float = 2.0, bend_penalty: float = 12.0,
                     limit: int = 4096,
                     bounds: tuple[float, float, float, float] | None = None,
                     port_ids: tuple[str, ...] = (),
                     classes: tuple[str, ...] | None = None,
                     regions: tuple[str, ...] | None = None) -> tuple[tuple[float, float], ...]:
    """Return the stable shortest orthogonal route on a finite visibility grid."""
    index = obstacles if isinstance(obstacles, SurfaceObstacleIndex) else None
    boxes = (tuple(obstacle_envelope(item.geometry) for item in index.select(classes=classes, regions=regions))
             if index is not None else obstacles)
    xs_set = {start[0], end[0], *(value for box in boxes for value in (box[0] - grid_offset, box[2] + grid_offset))}
    ys_set = {start[1], end[1], *(value for box in boxes for value in (box[1] - grid_offset, box[3] + grid_offset))}
    if bounds is not None:
        left, top, right, bottom = bounds
        xs_set = {value for value in xs_set if left <= value <= right} | {left, right, start[0], end[0]}
        ys_set = {value for value in ys_set if top <= value <= bottom} | {top, bottom, start[1], end[1]}
    xs, ys = sorted(xs_set), sorted(ys_set)
    source = (xs.index(start[0]), ys.index(start[1]), -1)
    target = (xs.index(end[0]), ys.index(end[1]))

    def clear(a: tuple[float, float], b: tuple[float, float]) -> bool:
        if index is not None:
            return not index.collisions(ObstacleSegment(a, b), port_ids=port_ids,
                                        classes=classes, regions=regions)
        for left, top, right, bottom in boxes:
            if a[1] == b[1] and top < a[1] < bottom and max(a[0], b[0]) > left and min(a[0], b[0]) < right:
                return False
            if a[0] == b[0] and left < a[0] < right and max(a[1], b[1]) > top and min(a[1], b[1]) < bottom:
                return False
        return True

    if index is not None:
        # The two Manhattan shortest paths are the first finite candidates.
        # Most sparse relations need no visibility-grid expansion at all.
        simple = set()
        for via in ((end[0], start[1]), (start[0], end[1])):
            path = tuple(point for point in (start, via, end)
                         if not (point == start and point == via) and not (point == via and point == end))
            if start == end:
                continue
            if len(path) == 1:
                path = (start, end)
            elif path[0] != start:
                path = (start, *path)
            simple.add(path)
        for path in sorted(simple):
            if all(clear(a, b) for a, b in zip(path, path[1:])):
                return path

    def heuristic(state: tuple[int, int, int]) -> float:
        return abs(xs[state[0]] - end[0]) + abs(ys[state[1]] - end[1])

    costs, parents = {source: 0.0}, {}
    source_heuristic = heuristic(source)
    # Among equal f-costs, expand the state nearer the target. This preserves
    # A*'s shortest-path ordering while avoiding a source-side grid flood.
    queue = [(source_heuristic, source_heuristic, 0.0, source)]
    finish = None
    visited = 0
    limited = False
    while queue:
        _, _, cost, state = heappop(queue)
        if cost != costs[state]:
            continue
        visited += 1
        if visited > limit:
            limited = True
            break
        i, j, direction = state
        if (i, j) == target:
            finish = state
            break
        for ni, nj, next_direction in ((i - 1, j, 0), (i + 1, j, 0), (i, j - 1, 1), (i, j + 1, 1)):
            if not (0 <= ni < len(xs) and 0 <= nj < len(ys)):
                continue
            a, b = (xs[i], ys[j]), (xs[ni], ys[nj])
            if not clear(a, b):
                continue
            new_cost = cost + abs(a[0] - b[0]) + abs(a[1] - b[1]) + (bend_penalty if direction not in (-1, next_direction) else 0)
            new_state = (ni, nj, next_direction)
            if new_cost < costs.get(new_state, float("inf")):
                costs[new_state], parents[new_state] = new_cost, state
                next_heuristic = heuristic(new_state)
                heappush(queue, (new_cost + next_heuristic, next_heuristic, new_cost, new_state))
    if finish is None:
        raise RouteSearchFailure("E_PRESENTATION_ROUTE_LIMIT" if limited else "E_CONNECTOR_UNROUTABLE")
    path = []
    while True:
        path.append((xs[finish[0]], ys[finish[1]]))
        if finish == source:
            break
        finish = parents[finish]
    path.reverse()
    simplified: list[tuple[float, float]] = []
    for point in path:
        if len(simplified) >= 2:
            first, second = simplified[-2:]
            if first[0] == second[0] == point[0] or first[1] == second[1] == point[1]:
                simplified.pop()
        simplified.append(point)
    return tuple(simplified)
