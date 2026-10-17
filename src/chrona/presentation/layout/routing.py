"""Deterministic renderer-neutral routing used while building a presentation Scene."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from itertools import chain as _chain
import json
from math import hypot, isfinite

from chrona.presentation.layout.model import geometry_sum
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, SurfaceObstacleIndex
from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.route_search import RelationExpansionBudget, RouteSearchFailure
from chrona.presentation.layout.route_quality_bounds import rectangular_detour_lower_bound
from chrona.presentation.layout.relation_shapes import (
    RelationShapeChannels, first_fit_port_pairs, relation_shape_candidates, shape_channels,
    supplemental_relation_channel_candidates,
)


ROUTE_GRID_OFFSET = 2.0  # how far a route runs from the edge of an obstacle
RELATION_SEARCH_EXPANSIONS = 4096  # shared by all pairs of one resolved relation instance


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
                "bounded-candidates-exhausted", "finite-domain-exhausted", "quality-infeasible", "expansion-limit"}:
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
class CriticalRouteEvidence:
    """Protected finite-domain work, separate from ordinary quota receipts."""

    expansions: int
    exhausted: bool
    quality_fallback: RouteAttemptEvidence | None = None
    attempts: tuple[RouteAttemptEvidence, ...] = ()

    def __post_init__(self) -> None:
        if (isinstance(self.expansions, bool) or not isinstance(self.expansions, int)
                or self.expansions < 0 or not isinstance(self.exhausted, bool)
                or (self.quality_fallback is not None
                    and self.quality_fallback.outcome != "quality-rejected")):
            raise _route_attempt_error("critical finite-domain evidence")

    def diagnostic(self, relation_id: str) -> str:
        payload = {"relationId": relation_id, "searchDomain": "finite-port-event",
                   "expansions": self.expansions}
        if self.quality_fallback is not None:
            measured = self.quality_fallback
            payload.update(bends=measured.bends, maxBends=measured.max_bends,
                           length=measured.length, directLength=measured.direct_length,
                           maxDetourRatio=measured.max_detour_ratio)
            code = "I_LAYOUT_CRITICAL_RELATION_QUALITY_FALLBACK"
        elif self.exhausted:
            code = "W_LAYOUT_CRITICAL_RELATION_SEARCH_DOMAIN_EXHAUSTED"
            payload["failureEvidence"] = [{"sourceSide": item.source_side,
                "targetSide": item.target_side, "outcome": item.outcome,
                "blockerIds": item.blocker_ids, "searchFailure": item.search_failure}
                for item in self.attempts]
        else:
            code = "I_LAYOUT_CRITICAL_RELATION_SEARCH"
        return code + ":" + json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class RelationRouteSelection:
    """One deterministic port-pair search and its complete eligibility evidence."""

    selected_pair: tuple[ConnectorEgress, ConnectorEgress] | None
    points: tuple[tuple[float, float], ...]
    attempts: tuple[RouteAttemptEvidence, ...]
    settled_by_shape: bool = False
    search_used: bool = False
    search_budget: int | None = None
    search_expansions: int = 0
    settled_by_hint: bool = False
    hint_rejection: str | None = None
    critical_evidence: CriticalRouteEvidence | None = None

    @property
    def budget_hit(self) -> bool:
        return self.search_budget is not None and self.search_expansions == self.search_budget

    def __post_init__(self) -> None:
        accepted = tuple(item for item in self.attempts if item.outcome == "accepted")
        fallback = self.critical_evidence.quality_fallback if self.critical_evidence is not None else None
        if (self.critical_evidence is not None and self.critical_evidence.exhausted
                and fallback is None and self.selected_pair is not None):
            raise _route_attempt_error("critical domain exhaustion with selected route")
        if (self.critical_evidence is not None and not self.critical_evidence.exhausted
                and self.selected_pair is None):
            raise _route_attempt_error("incomplete critical domain without selected route")
        if fallback is not None:
            if accepted or fallback not in self.attempts:
                raise _route_attempt_error("critical quality fallback receipt")
            accepted = (fallback,)
        if (isinstance(self.search_expansions, bool) or not isinstance(self.search_expansions, int)
                or self.search_expansions < 0
                or (self.search_budget is None and self.search_expansions != 0)
                or (self.search_budget is not None and (
                    isinstance(self.search_budget, bool) or not isinstance(self.search_budget, int)
                    or self.search_budget < 1 or self.search_expansions > self.search_budget))):
            raise _route_attempt_error("search budget receipt", budget=self.search_budget,
                                       expansions=self.search_expansions)
        if (not isinstance(self.settled_by_shape, bool) or not isinstance(self.search_used, bool)
                or not isinstance(self.settled_by_hint, bool)
                or (self.settled_by_hint and (self.selected_pair is None or self.search_used or self.settled_by_shape))
                or (self.settled_by_shape and self.selected_pair is None)
                or not self.attempts or len(accepted) > 1
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
    search_policy: str = "best",
    channels: RelationShapeChannels | None = None,
    search_budget: int | None = None,
    preferred_routes: tuple[tuple[tuple[ConnectorEgress, ConnectorEgress], tuple[tuple[float, float], ...]], ...] = (),
    protected: bool = False,
    endpoint_preserving_prepare: bool = False,
    protected_quality_barriers: Callable[[ConnectorEgress, ConnectorEgress], tuple[ObstacleRect, ...]] | None = None,
    label_repair_obstacle_ids: frozenset[str] = frozenset(),
    route_stroke_width: float = 0.0,
) -> RelationRouteSelection:
    """Measure eligibility, then select by the caller's stable rank when supplied.

    The order is the caller's declared deterministic candidate order.
    Without a rank, the first accepted pair wins. With a rank, eligible
    candidates found within deterministic per-pair quotas are compared and
    exact ties keep the first. A search failure is
    distinguished from unrelated invalid input; endpoint
    labels are never exempted from either corridor or body collisions.
    Explicit first-fit sorts admitted ports and tries finite shapes before
    that pair's cheap search, ignoring rank after full acceptance. Only if
    that whole phase fails, the original ranked best phase rescues the relation
    within the same explicit budget. The internal default preserves callers.
    """
    if not port_pairs or not relation_scene_id:
        raise _route_attempt_error("route candidate set", relation_scene_id=relation_scene_id,
                                   port_pair_count=len(port_pairs), bounds=bounds,
                                   max_bends=max_bends, max_detour_ratio=max_detour_ratio)
    if search_policy not in {"best", "first-fit"}:
        raise _route_attempt_error("search policy", search_policy=search_policy)
    repair_active = (search_policy == "first-fit" and bool(label_repair_obstacle_ids)
                     and any(obstacles.has(identifier) for identifier in label_repair_obstacle_ids))
    if repair_active and (isinstance(route_stroke_width, bool)
            or not isinstance(route_stroke_width, (int, float))
            or not isfinite(route_stroke_width) or route_stroke_width < 0):
        raise _route_attempt_error("route stroke width", route_stroke_width=route_stroke_width)
    phases = (("best", port_pairs),)
    if search_policy == "first-fit":
        phases = (("first-fit", first_fit_port_pairs(port_pairs)), ("best", port_pairs))
        if channels is None:
            channels = shape_channels(obstacles, bounds=bounds, classes=classes, regions=regions,
                                      grid_offset=ROUTE_GRID_OFFSET)
    attempts: list[RouteAttemptEvidence] = []
    best = None
    chosen = None
    chosen_points = ()
    chosen_attempt = -1
    search_used = False
    hint_rejection = None
    budget = RelationExpansionBudget(search_budget) if search_budget is not None else None

    def result(pair, points, evidence, *, shaped=False, hinted=False):
        return RelationRouteSelection(pair, tuple(points), tuple(evidence),
            settled_by_shape=shaped, search_used=search_used,
            search_budget=search_budget, search_expansions=budget.expansions if budget is not None else 0,
            settled_by_hint=hinted, hint_rejection=hint_rejection)

    def pair_domain(source, target):
        blockers = tuple(sorted({item.placement_id for egress in (source, target)
            if egress.corridor for item in obstacles.egress_collisions(
                ObstacleSegment(*egress.corridor), host_ids=egress.host_ids,
                classes=classes, regions=regions)}))
        port_ids = tuple(port_id
            for host_id, side in ((source_host_id, source.side), (target_host_id, target.side))
            for port_id in (f"port:{host_id or relation_scene_id}:{side}",) if obstacles.has(port_id))
        return blockers, port_ids

    for pair, middle in (preferred_routes if search_policy == "first-fit" else ()):
        blockers, port_ids = pair_domain(*pair)
        if pair not in port_pairs or blockers:
            hint_rejection = "egress-collision" if blockers else "unadmitted-port-pair"
        else:
            measured, points = _select_pair_candidate(*pair, obstacles=obstacles, bounds=bounds,
                port_ids=port_ids, classes=classes, regions=regions, max_bends=max_bends,
                max_detour_ratio=max_detour_ratio, prepare=prepare, accept=accept,
                limit=0, candidate_paths=(middle,))
            if measured.outcome == "accepted":
                return result(pair, points, (measured,), hinted=True)
            hint_rejection = measured.search_failure or measured.outcome

    for phase, phase_pairs in phases:
        if budget is not None and budget.hit:
            break
        quota, remainder = divmod(RELATION_SEARCH_EXPANSIONS, len(phase_pairs))
        for pair_index, (source, target) in enumerate(phase_pairs):
            blockers, port_ids = pair_domain(source, target)
            if blockers:
                attempts.append(RouteAttemptEvidence(source.side, target.side, "egress-collision",
                                                     blocker_ids=blockers))
                continue
            pair_limit = quota + int(pair_index < remainder)
            if phase == "first-fit":
                shapes = relation_shape_candidates(source.exposed_port, target.exposed_port,
                                                   bounds=bounds, channels=channels)
                if repair_active:
                    shapes = _chain(shapes, supplemental_relation_channel_candidates(
                        source.exposed_port, target.exposed_port, bounds=bounds, channels=channels,
                        obstacles=obstacles, route_stroke_width=float(route_stroke_width),
                        grid_offset=ROUTE_GRID_OFFSET, classes=classes, regions=regions))
                shaped, shaped_points = _select_pair_candidate(source, target, obstacles=obstacles, bounds=bounds,
                    port_ids=port_ids, classes=classes, regions=regions, max_bends=max_bends,
                    max_detour_ratio=max_detour_ratio, prepare=prepare, accept=accept,
                    limit=pair_limit, candidate_paths=shapes)
                if shaped.outcome == "accepted":
                    return result((source, target), shaped_points, (*attempts, shaped), shaped=True)
            if pair_limit == 0:
                attempts.append(RouteAttemptEvidence(source.side, target.side, "no-route-found",
                                                     search_failure="E_PRESENTATION_ROUTE_LIMIT"))
                continue
            search_used = True
            measured, points = _select_pair_candidate(source, target, obstacles=obstacles, bounds=bounds,
                port_ids=port_ids, classes=classes, regions=regions, max_bends=max_bends,
                max_detour_ratio=max_detour_ratio, prepare=prepare, accept=accept,
                limit=pair_limit, exact_bound=phase == "best",
                **({"budget": budget} if budget is not None else {}))
            attempts.append(measured)
            if measured.outcome == "accepted":
                if rank is None or phase == "first-fit":
                    return result((source, target), points, attempts)
                score = rank(tuple(points), source, target)
                if best is None or score < best:
                    if chosen_attempt >= 0:
                        attempts[chosen_attempt] = replace(attempts[chosen_attempt], outcome="eligible-not-selected")
                    best, chosen, chosen_points, chosen_attempt = score, (source, target), tuple(points), len(attempts) - 1
                else:
                    attempts[-1] = replace(measured, outcome="eligible-not-selected")
            if budget is not None and budget.hit:
                break
    if chosen is not None or not protected:
        return result(chosen, chosen_points, attempts)

    # Exhaust only the declared finite domain; reuse all completed validators.
    protected_expansions = 0
    protected_search_used = False
    def charge_protected():
        nonlocal protected_expansions
        protected_expansions += 1

    def protected_candidates(source, target, port_ids):
        from chrona.presentation.layout.route_search import orthogonal_route_candidates
        nonlocal protected_search_used
        protected_search_used = True
        yield from orthogonal_route_candidates(source.exposed_port, target.exposed_port,
            obstacles, bounds=bounds, port_ids=port_ids, classes=classes, regions=regions,
            limit=None, on_expansion=charge_protected)

    fallback = None
    protected_start = len(attempts)
    naturally_exhausted = True
    protected_best = None
    protected_chosen = None
    protected_pairs = first_fit_port_pairs(port_pairs) if search_policy == "first-fit" else port_pairs
    protected_channels = channels or shape_channels(obstacles, bounds=bounds, classes=classes,
                                                    regions=regions, grid_offset=ROUTE_GRID_OFFSET)
    for source, target in protected_pairs:
        blockers, port_ids = pair_domain(source, target)
        if blockers:
            attempts.append(RouteAttemptEvidence(source.side, target.side, "egress-collision", blocker_ids=blockers))
            continue
        shapes = relation_shape_candidates(source.exposed_port, target.exposed_port,
                                           bounds=bounds, channels=protected_channels)
        candidates = _chain(shapes, protected_candidates(source, target, port_ids))
        quality_impossible = False
        if prepare is None or endpoint_preserving_prepare:
            quality_impossible = max_bends < int(source.semantic_port[0] != target.semantic_port[0]
                                                 and source.semantic_port[1] != target.semantic_port[1])
            if protected_quality_barriers is not None:
                direct = sum(abs(a - b) for a, b in zip(source.semantic_port, target.semantic_port))
                lower = rectangular_detour_lower_bound(source.semantic_port, target.semantic_port,
                    protected_quality_barriers(source, target))
                quality_impossible |= direct > 0 and lower > direct * max_detour_ratio
        measured, points = _select_pair_candidate(source, target, obstacles=obstacles, bounds=bounds,
            port_ids=port_ids, classes=classes, regions=regions, max_bends=max_bends,
            max_detour_ratio=max_detour_ratio, prepare=prepare, accept=accept,
            limit=None, candidate_paths=candidates, stop_on_safe=quality_impossible)
        attempts.append(measured)
        if measured.outcome == "accepted":
            naturally_exhausted = False
            if search_policy == "first-fit" or rank is None:
                protected_chosen = ((source, target), points)
                break
            score = rank(points, source, target)
            if protected_best is None or score < protected_best:
                if protected_chosen is not None:
                    attempts[protected_chosen[2]] = replace(attempts[protected_chosen[2]], outcome="eligible-not-selected")
                protected_best = score
                protected_chosen = ((source, target), points, len(attempts) - 1)
            else:
                attempts[-1] = replace(measured, outcome="eligible-not-selected")
        if measured.outcome == "quality-rejected":
            naturally_exhausted &= measured.search_disposition != "quality-infeasible"
            score = (rank(points, source, target) if search_policy == "best" and rank is not None
                     else (measured.bends, measured.length))
            if fallback is None or (search_policy == "best" and score < fallback[0]):
                fallback = (score, (source, target), points, measured)
    if protected_chosen is not None:
        return RelationRouteSelection(protected_chosen[0], protected_chosen[1], tuple(attempts),
            search_used=search_used or protected_search_used,
            search_budget=search_budget, search_expansions=budget.expansions if budget is not None else 0,
            hint_rejection=hint_rejection, critical_evidence=CriticalRouteEvidence(
                protected_expansions, False, attempts=tuple(attempts[protected_start:])))
    evidence = CriticalRouteEvidence(protected_expansions, naturally_exhausted,
        fallback[3] if fallback else None, tuple(attempts[protected_start:]))
    return RelationRouteSelection(fallback[1] if fallback else None, fallback[2] if fallback else (),
        tuple(attempts), search_used=search_used or protected_search_used, search_budget=search_budget,
        search_expansions=budget.expansions if budget is not None else 0,
        hint_rejection=hint_rejection, critical_evidence=evidence)


def _select_pair_candidate(source, target, *, obstacles, bounds, port_ids, classes, regions,
                           max_bends, max_detour_ratio, prepare, accept, limit, candidate_paths=None,
                           budget=None, exact_bound=True, stop_on_safe=False):
    """Search alternatives for one pair; only completed, safe paths reach quality selection."""
    from chrona.presentation.layout.route_search import orthogonal_route_candidates

    rejected = None
    failure = "E_CONNECTOR_UNROUTABLE"
    disposition = "finite-domain-exhausted" if limit is None else "bounded-candidates-exhausted"
    try:
        candidates = (orthogonal_route_candidates(source.exposed_port, target.exposed_port, obstacles,
            bounds=bounds, port_ids=port_ids, classes=classes, regions=regions, limit=limit,
            **({"budget": budget} if budget is not None else {}),
            **({"exact_bound": False} if not exact_bound else {}))
            if candidate_paths is None else candidate_paths)
        for middle in candidates:
            # Both generators and explicit prior proposals obey the same domain.
            if (any(not (bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]) for x, y in middle)
                    or any(a[0] != b[0] and a[1] != b[1] for a, b in zip(middle, middle[1:]))):
                failure = "E_CONNECTOR_UNROUTABLE"
                continue
            if candidate_paths is not None and any(obstacles.collisions(ObstacleSegment(a, b),
                    port_ids=port_ids, classes=classes, regions=regions)
                    for a, b in zip(middle, middle[1:])):
                failure = "E_LAYOUT_ROUTE_THROUGH_MARK"
                continue
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
            if stop_on_safe:
                if (completed[0] != source.semantic_port or completed[-1] != target.semantic_port):
                    raise _route_attempt_error("quality lower bound requires preserved endpoints")
                return replace(measured, search_disposition="quality-infeasible"), completed
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
    memo.store(key, outcome, record_count=1 + len(outcome))
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
