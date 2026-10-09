"""Deterministic renderer-neutral routing used while building a presentation Scene."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
import json
from math import hypot, isfinite

from chrona.presentation.layout.model import geometry_sum
from chrona.presentation.layout.obstacles import ObstacleSegment, SurfaceObstacleIndex
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.route_search import RouteSearchFailure


ROUTE_GRID_OFFSET = 2.0  # how far a route runs from the edge of an obstacle


def _route_attempt_error(owner: str, **operands: object) -> ValueError:
    fields = []
    for name, value in operands.items():
        shown = repr(value).replace("\n", " ").replace("\r", " ")[:96]
        fields.append(f"{name}={shown}")
    return ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: " + owner + " " + ", ".join(fields))


def remove_substroke_jogs(points: tuple[tuple[float, float], ...], minimum: float, *,
                         accept: Callable[[tuple[tuple[float, float], ...]], bool],
                         start_minimum: float = 0.0, end_minimum: float = 0.0,
                         ) -> tuple[tuple[float, float], ...]:
    """Collapse only sub-stroke jogs, never moving either boundary port.

    Try moving either adjoining run onto the other; obstacle and mark clearance
    are supplied by the route owner. Wider bend minimisation is a separate rule.
    """
    current = tuple(points)
    def limit(index, size):
        return max(minimum, start_minimum if index == 0 else 0.0,
                   end_minimum if index == size - 2 else 0.0)
    if not any(hypot(b[0] - a[0], b[1] - a[1]) + 1e-6 < limit(i, len(current))
               for i, (a, b) in enumerate(zip(current, current[1:]))):
        return current
    while True:
        clean = [current[0]]
        for point in current[1:]:
            if point == clean[-1]:
                continue
            if len(clean) > 1 and not _reverses(clean[-2], clean[-1], point) and (
                    clean[-2][0] == clean[-1][0] == point[0]
                    or clean[-2][1] == clean[-1][1] == point[1]):
                clean.pop()
            clean.append(point)
        current = tuple(clean)
        replacement = None
        for i, (a, b) in enumerate(zip(current, current[1:])):
            if hypot(b[0] - a[0], b[1] - a[1]) + 1e-6 >= limit(i, len(current)):
                continue
            axis = 0 if a[1] == b[1] else 1
            candidates = []
            if i + 2 < len(current):
                moved = list(current[i + 2]); moved[axis] = a[axis]
                candidates.append((*current[:i + 1], tuple(moved), *current[i + 3:]))
            if i > 0:
                moved = list(current[i - 1]); moved[axis] = b[axis]
                candidates.append((*current[:i - 1], tuple(moved), *current[i + 1:]))
            replacement = next((path for path in candidates
                if path[0] == current[0] and path[-1] == current[-1]
                and all(p[0] == q[0] or p[1] == q[1] for p, q in zip(path, path[1:]))
                and not route_self_overlaps(path) and accept(path)), None)
            if replacement is not None:
                break
        if replacement is None:
            return current
        current = replacement


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
    search_disposition: str | None = None

    def __post_init__(self) -> None:
        if (self.outcome not in {"egress-collision", "no-route-found", "quality-rejected", "accepted", "eligible-not-selected"}
                or not self.source_side or not self.target_side):
            raise _route_attempt_error("port-pair outcome", source_side=self.source_side,
                                       target_side=self.target_side, outcome=self.outcome)
        if self.search_disposition is not None and self.search_disposition not in {
                "bounded-candidates-exhausted", "expansion-limit"}:
            raise _route_attempt_error("search disposition", source_side=self.source_side,
                                       target_side=self.target_side,
                                       search_disposition=self.search_disposition,
                                       expected=("bounded-candidates-exhausted", "expansion-limit"))
        if self.search_disposition is not None and self.outcome != "quality-rejected":
            raise _route_attempt_error("search disposition outcome", source_side=self.source_side,
                                       target_side=self.target_side, outcome=self.outcome,
                                       search_disposition=self.search_disposition,
                                       expected_outcome="quality-rejected")
        if self.outcome == "egress-collision":
            if (not self.blocker_ids or self.search_failure is not None
                    or any(value is not None for value in self._quality_values())):
                raise _route_attempt_error("egress collision evidence",
                                           source_side=self.source_side, target_side=self.target_side,
                                           outcome=self.outcome, blocker_ids=self.blocker_ids,
                                           search_failure=self.search_failure,
                                           quality_values=self._quality_values())
        elif self.outcome == "no-route-found":
            if (self.blocker_ids or self.search_failure not in {
                    "E_PRESENTATION_ROUTE_LIMIT", "E_CONNECTOR_UNROUTABLE", "E_LAYOUT_ROUTE_SELF_OVERLAP",
                    "E_LAYOUT_ROUTE_THROUGH_MARK"}
                    or any(value is not None for value in self._quality_values())):
                raise _route_attempt_error("no-route evidence",
                                           source_side=self.source_side, target_side=self.target_side,
                                           outcome=self.outcome, search_failure=self.search_failure,
                                           blocker_ids=self.blocker_ids,
                                           quality_values=self._quality_values())
        else:
            values = self._quality_values()
            if (self.blocker_ids or self.search_failure is not None
                    or any(value is None for value in values)
                    or not all(isfinite(value) for value in (self.length, self.direct_length, self.max_detour_ratio))
                    or self.length < 0 or self.direct_length < 0 or self.bends < 0
                    or self.max_bends < 0 or self.max_detour_ratio <= 0):
                raise _route_attempt_error("route quality metrics",
                                           source_side=self.source_side, target_side=self.target_side,
                                           outcome=self.outcome, length=self.length,
                                           direct_length=self.direct_length, bends=self.bends,
                                           max_bends=self.max_bends,
                                           max_detour_ratio=self.max_detour_ratio)
            within = self.bends <= self.max_bends and (
                self.direct_length == 0 or self.length <= self.direct_length * self.max_detour_ratio)
            if within != (self.outcome in {"accepted", "eligible-not-selected"}):
                raise _route_attempt_error("route quality outcome", source_side=self.source_side,
                                           target_side=self.target_side, outcome=self.outcome,
                                           length=self.length, direct_length=self.direct_length,
                                           bends=self.bends, max_bends=self.max_bends,
                                           max_detour_ratio=self.max_detour_ratio)

    def _quality_values(self) -> tuple[float | int | None, ...]:
        return (self.length, self.direct_length, self.bends, self.max_bends, self.max_detour_ratio)


@dataclass(frozen=True)
class RouteSuppressionEvidence:
    relation_id: str
    attempts: tuple[RouteAttemptEvidence, ...]

    def __post_init__(self) -> None:
        if not self.relation_id or not self.attempts or any(
                attempt.outcome == "accepted" for attempt in self.attempts):
            raise _route_attempt_error("suppression evidence", relation_id=self.relation_id,
                                       attempt_outcomes=tuple(getattr(item, "outcome", None)
                                                              for item in self.attempts))

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
            if attempt.search_disposition is not None:
                record["searchDisposition"] = attempt.search_disposition
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


def route_self_overlaps(points: tuple[tuple[float, float], ...]) -> bool:
    """Whether two segments of one route overlap along a shared line (a reversal is the adjacent case, #1059)."""
    segments = [(a, b) for a, b in zip(points, points[1:]) if a != b]
    for index, (a, b) in enumerate(segments):
        for c, d in segments[index + 1:]:
            if a[1] == b[1] == c[1] == d[1]:
                low, high = max(min(a[0], b[0]), min(c[0], d[0])), min(max(a[0], b[0]), max(c[0], d[0]))
            elif a[0] == b[0] == c[0] == d[0]:
                low, high = max(min(a[1], b[1]), min(c[1], d[1])), min(max(a[1], b[1]), max(c[1], d[1]))
            else:
                continue
            if high - low > 1e-6:
                return True
    return False


def repair_self_reversal(points: tuple[tuple[float, float], ...], obstacles: SurfaceObstacleIndex, *,
                         classes: tuple[str, ...], regions: tuple[str, ...],
                         host_ids: tuple[str, ...] = (),
                         accept: Callable[[tuple[tuple[float, float], ...]], bool] | None = None,
                         ) -> tuple[tuple[float, float], ...] | None:
    """Replace each reversal by an honest extra bend, or None when the free corridor is not there (#1059).

    A route that drops along `x`, runs to a tip on the near side of `x` and turns back over the same line becomes:
    drop part of the way, jog sideways to the tip's coordinate, drop to the tip, then enter. The jog is tried nearest
    the tip first (the gap before the target row), then step by step back toward where the drop began. The two new
    segments must be free of the selected obstacles (the endpoints' own comparison marks, `host_ids`, excepted) and
    pass `accept` when supplied; any other overlap is not repaired.
    """
    current = tuple(points)
    for _ in range(len(current)):
        index = next((i for i in range(1, len(current) - 1)
                      if _reverses(current[i - 1], current[i], current[i + 1])), None)
        if index is None:
            return current if not route_self_overlaps(current) else None
        if index < 2:
            return None
        before, drop, tip = current[index - 2], current[index - 1], current[index]
        along = 0 if drop[1] == tip[1] else 1  # the axis of the reversing line; the drop runs along the other
        across = 1 - along
        if before[along] != drop[along]:
            return None
        direction = 1.0 if before[across] > drop[across] else -1.0
        span = abs(before[across] - drop[across])
        offsets = [min(step * JOG_STEP, span) for step in range(2, int(span // JOG_STEP) + 2)] + [span]
        repaired = None
        for offset in dict.fromkeys(offsets):
            level = drop[across] + direction * offset
            first = _point(drop[along], level, along)
            second = _point(tip[along], level, along)
            if not all(_free(obstacles, start, end, classes, regions, host_ids)
                       for start, end in ((first, second), (second, tip))):
                continue
            if accept is not None and not accept((first, second, tip)):
                continue
            path = [*current[:index - 1], first, second, *current[index:]]
            repaired = tuple(point for number, point in enumerate(path) if number == 0 or point != path[number - 1])
            break
        if repaired is None:
            return None
        current = repaired
    return None


JOG_STEP = 4.0  # candidate spacing for the repair jog, in surface units


def _point(along_value: float, across_value: float, along: int) -> tuple[float, float]:
    return (along_value, across_value) if along == 0 else (across_value, along_value)


def _free(obstacles: SurfaceObstacleIndex, start: tuple[float, float], end: tuple[float, float],
          classes: tuple[str, ...], regions: tuple[str, ...], host_ids: tuple[str, ...]) -> bool:
    if start == end:
        return True
    segment = ObstacleSegment(start, end)
    return not (obstacles.egress_collisions(segment, host_ids=host_ids, classes=classes, regions=regions)
                if host_ids else obstacles.collisions(segment, classes=classes, regions=regions))


def back_route_points(source_port: tuple[float, float], exit_dx: float, gap_y: float,
                      tip: tuple[float, float], target_port: tuple[float, float]) -> tuple[tuple[float, float], ...]:
    """The back-route of `relationRouting.entry: side` (#1060): out, to the row gap, back, drop, in.

    Leave the source port by `exit_dx` along the row, run to the gap line `gap_y`, travel to the entry tip (the
    stub's far end), drop to the target's mid height and enter. Equal and straight-through points collapse.
    """
    out = (source_port[0] + exit_dx, source_port[1])
    pieces = (source_port, out, (out[0], gap_y), (tip[0], gap_y), tip, target_port)
    points: list[tuple[float, float]] = []
    for point in pieces:
        if points and points[-1] == point:
            continue
        if len(points) >= 2 and ((points[-2][0] == points[-1][0] == point[0] and (points[-1][1] - points[-2][1]) * (point[1] - points[-1][1]) > 0)
                                 or (points[-2][1] == points[-1][1] == point[1] and (points[-1][0] - points[-2][0]) * (point[0] - points[-1][0]) > 0)):
            points[-1] = point
            continue
        points.append(point)
    return tuple(points)


def _reverses(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> bool:
    return ((a[1] == b[1] == c[1] and (b[0] - a[0]) * (c[0] - b[0]) < 0)
            or (a[0] == b[0] == c[0] and (b[1] - a[1]) * (c[1] - b[1]) < 0))


def relation_route_quality(points: tuple[tuple[float, float], ...], *,
                           max_bends: int, max_detour_ratio: float) -> bool:
    """Evaluate a completed route against the explicit Layout Profile limits."""
    if len(points) < 2 or route_self_overlaps(points):
        return False
    length, direct, bends = route_quality_metrics(points)
    return bends <= max_bends and (direct == 0 or length <= direct * max_detour_ratio)


def route_quality_metrics(points: tuple[tuple[float, float], ...]) -> tuple[float, float, int]:
    """Return the exact metrics used by the route-quality decision and evidence."""
    if len(points) < 2:
        raise _route_attempt_error("route point sequence", point_count=len(points))
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


@dataclass(frozen=True)
class RelationRouteSelection:
    """One deterministic port-pair search and its complete eligibility evidence."""

    selected_pair: tuple[ConnectorEgress, ConnectorEgress] | None
    points: tuple[tuple[float, float], ...]
    attempts: tuple[RouteAttemptEvidence, ...]

    def __post_init__(self) -> None:
        accepted = tuple(item for item in self.attempts if item.outcome == "accepted")
        if (not self.attempts or len(accepted) > 1
                or (self.selected_pair is None) != (not accepted)
                or (self.selected_pair is None and self.points)
                or (self.selected_pair is not None and len(self.points) < 2)):
            raise _route_attempt_error("route selection", point_count=len(self.points),
                                       attempt_outcomes=tuple(item.outcome for item in self.attempts),
                                       selected_pair=(tuple((item.side) for item in self.selected_pair)
                                                      if self.selected_pair is not None else None))


def select_relation_route(
    port_pairs: tuple[tuple[ConnectorEgress, ConnectorEgress], ...], *,
    obstacles: SurfaceObstacleIndex, bounds: tuple[float, float, float, float],
    source_host_id: str | None, target_host_id: str | None, relation_scene_id: str,
    max_bends: int, max_detour_ratio: float,
    classes: tuple[str, ...] = ("mark", "text", "label-visual"),
    regions: tuple[str, ...] = ("timeline", "group-header"),
    accept: Callable[[tuple[tuple[float, float], ...]], bool] | None = None,
    prepare: Callable[[tuple[tuple[float, float], ...], ConnectorEgress, ConnectorEgress],
                      tuple[tuple[float, float], ...] | None] | None = None,
    rank: Callable[[tuple[tuple[float, float], ...], ConnectorEgress, ConnectorEgress], tuple] | None = None,
) -> RelationRouteSelection:
    """Measure eligibility, then select by the caller's stable rank when supplied.

    The order is the caller's declared deterministic candidate order.
    Without a rank, the first accepted pair wins. With a rank, all eligible
    pairs are compared and exact ties keep the first. A search failure is
    distinguished from unrelated invalid input; endpoint
    labels are never exempted from either corridor or body collisions.
    """
    if not port_pairs or not relation_scene_id:
        raise _route_attempt_error("route candidate set", relation_scene_id=relation_scene_id,
                                   port_pair_count=len(port_pairs), bounds=bounds,
                                   max_bends=max_bends, max_detour_ratio=max_detour_ratio)
    attempts: list[RouteAttemptEvidence] = []
    best = None
    chosen = None
    chosen_points = ()
    chosen_attempt = -1
    for source, target in port_pairs:
        blockers = tuple(sorted({item.placement_id for egress in (source, target)
                                 if egress.corridor
                                 for item in obstacles.egress_collisions(
                                     ObstacleSegment(*egress.corridor), host_ids=egress.host_ids,
                                     classes=classes, regions=regions)}))
        if blockers:
            attempts.append(RouteAttemptEvidence(source.side, target.side, "egress-collision",
                                                 blocker_ids=blockers))
            continue
        port_ids = tuple(
            port_id for host_id, side in ((source_host_id, source.side), (target_host_id, target.side))
            for port_id in (f"port:{host_id or relation_scene_id}:{side}",)
            if obstacles.has(port_id)
        )
        measured, points = _select_pair_candidate(source, target, obstacles=obstacles, bounds=bounds,
            port_ids=port_ids, classes=classes, regions=regions, max_bends=max_bends,
            max_detour_ratio=max_detour_ratio, prepare=prepare, accept=accept)
        attempts.append(measured)
        if measured.outcome == "accepted":
            if rank is None:
                return RelationRouteSelection((source, target), tuple(points), tuple(attempts))
            score = rank(tuple(points), source, target)
            if best is None or score < best:
                if chosen_attempt >= 0:
                    attempts[chosen_attempt] = replace(attempts[chosen_attempt], outcome="eligible-not-selected")
                best, chosen, chosen_points, chosen_attempt = score, (source, target), tuple(points), len(attempts) - 1
            else:
                attempts[-1] = replace(measured, outcome="eligible-not-selected")
    return RelationRouteSelection(chosen, chosen_points, tuple(attempts))


def _select_pair_candidate(source, target, *, obstacles, bounds, port_ids, classes, regions,
                           max_bends, max_detour_ratio, prepare, accept):
    """Search alternatives for one pair; only completed, safe paths reach quality selection."""
    from chrona.presentation.layout.route_search import orthogonal_route_candidates

    rejected = None
    failure = "E_CONNECTOR_UNROUTABLE"
    disposition = "bounded-candidates-exhausted"
    try:
        for middle in orthogonal_route_candidates(source.exposed_port, target.exposed_port, obstacles,
                bounds=bounds, port_ids=port_ids, classes=classes, regions=regions):
            points = []
            for point in (*source.corridor, *middle, *reversed(target.corridor)):
                if not points or points[-1] != point:
                    points.append(point)
            if len(points) < 2:
                continue
            completed = tuple(points)
            repaired = repair_self_reversal(completed, obstacles, classes=classes, regions=regions,
                host_ids=(*source.host_ids, *target.host_ids), accept=accept)
            if repaired is not None:
                completed = repaired
            if prepare is not None:
                completed = prepare(completed, source, target)
            if completed is None or len(completed) < 2:
                continue
            if route_self_overlaps(completed):
                failure = "E_LAYOUT_ROUTE_SELF_OVERLAP"
                continue
            if accept is not None and not accept(completed):
                failure = "E_LAYOUT_ROUTE_THROUGH_MARK"
                continue
            measured = route_quality_attempt(source.side, target.side, completed,
                max_bends=max_bends, max_detour_ratio=max_detour_ratio)
            if measured.outcome == "accepted":
                return measured, completed
            if rejected is None or (measured.bends, measured.length) < (
                    rejected[0].bends, rejected[0].length):
                rejected = (measured, completed)
    except RouteSearchFailure as error:
        if str(error) == "E_PRESENTATION_ROUTE_LIMIT":
            disposition = "expansion-limit"
        failure = str(error)
    if rejected is not None:
        return replace(rejected[0], search_disposition=disposition), rejected[1]
    return RouteAttemptEvidence(source.side, target.side, "no-route-found",
        search_failure=failure), ()


def _route_memo_key(content_id: int, start: tuple[float, float], end: tuple[float, float],
                    grid_offset: float, bend_penalty: float, limit: int,
                    bounds: tuple[float, float, float, float] | None, port_ids: tuple[str, ...],
                    classes: tuple[str, ...] | None, regions: tuple[str, ...] | None) -> tuple:
    """Every input of an index-backed search; `repr` keeps -0.0 and 0.0 (and 1 and 1.0) apart."""
    return (content_id, repr((start, end, grid_offset, bend_penalty, limit, bounds)), port_ids,
            None if classes is None else frozenset(classes), None if regions is None else frozenset(regions))


def route_orthogonal(start: tuple[float, float], end: tuple[float, float],
                     obstacles: tuple[tuple[float, float, float, float], ...] | SurfaceObstacleIndex, *,
                     grid_offset: float = ROUTE_GRID_OFFSET, bend_penalty: float = 12.0,
                     limit: int = 4096,
                     bounds: tuple[float, float, float, float] | None = None,
                     port_ids: tuple[str, ...] = (),
                     classes: tuple[str, ...] | None = None,
                     regions: tuple[str, ...] | None = None) -> tuple[tuple[float, float], ...]:
    """Return the stable shortest orthogonal route on a finite visibility grid.

    Searches over an index are memoised on the index lineage by the exact content they read, so a
    repeated search (the planning rehearsals and the real phase) is answered without redoing it.
    """
    index = obstacles if isinstance(obstacles, SurfaceObstacleIndex) else None
    port_ids = tuple(port_ids)
    scope = None if index is None else index.route_memo_scope(classes, regions, port_ids)
    if scope is None:
        return _search_orthogonal(start, end, obstacles, grid_offset=grid_offset, bend_penalty=bend_penalty,
                                  limit=limit, bounds=bounds, port_ids=port_ids, classes=classes, regions=regions)
    memo, content_id = scope
    key = _route_memo_key(content_id, start, end, grid_offset, bend_penalty, limit, bounds,
                          port_ids, classes, regions)
    if key in memo.results:
        outcome = memo.results[key]
        if isinstance(outcome, str):  # a stored failure is its message; no traceback is retained
            raise RouteSearchFailure(outcome)
        return outcome
    try:
        outcome = _search_orthogonal(start, end, obstacles, grid_offset=grid_offset, bend_penalty=bend_penalty,
                                     limit=limit, bounds=bounds, port_ids=port_ids, classes=classes,
                                     regions=regions)
    except RouteSearchFailure as failure:
        memo.store(key, str(failure))
        raise
    memo.store(key, outcome)
    return outcome


def _search_orthogonal(start: tuple[float, float], end: tuple[float, float],
                       obstacles: tuple[tuple[float, float, float, float], ...] | SurfaceObstacleIndex, *,
                       grid_offset: float, bend_penalty: float, limit: int,
                       bounds: tuple[float, float, float, float] | None, port_ids: tuple[str, ...],
                       classes: tuple[str, ...] | None,
                       regions: tuple[str, ...] | None) -> tuple[tuple[float, float], ...]:
    from chrona.presentation.layout.route_search import orthogonal_route_candidates

    return next(orthogonal_route_candidates(start, end, obstacles,
        grid_offset=grid_offset, bend_penalty=bend_penalty, limit=limit,
        bounds=bounds, port_ids=port_ids, classes=classes, regions=regions))
