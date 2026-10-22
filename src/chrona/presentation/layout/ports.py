"""Finite Layout-owned boundary ports for visible connector geometry."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from math import isfinite

from chrona.presentation.layout.model import LayoutError, geometry_sum
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacleIndex
from chrona.presentation.layout.surface_quality import MarkPlacement, PathCommand


@dataclass(frozen=True)
class ConnectorEgress:
    side: str
    semantic_port: tuple[float, float]
    exposed_port: tuple[float, float]
    host_ids: tuple[str, ...]
    stub: bool = False  # the horizontal-entry stub candidate of `relationRouting.entry` (#1030)
    through_body: bool = False  # a span exit on the far side of its own mark: the corridor crosses the bar (#1072)
    corridor_host_ids: tuple[str, ...] = ()

    @property
    def corridor(self) -> tuple[tuple[float, float], ...]:
        return (() if self.semantic_port == self.exposed_port
                else (self.semantic_port, self.exposed_port))


_EGRESS_DIRECTIONS = {"end": (1., 0.), "start": (-1., 0.),
                      "above": (0., -1.), "below": (0., 1.)}


def outward_corridor_ends(pair: tuple[ConnectorEgress, ConnectorEgress], *,
                          source_run: float, target_run: float) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return points beyond each exposed port by its existing terminal/stroke reserve."""
    source, target = pair
    coordinates = (*source.semantic_port, *source.exposed_port,
                   *target.semantic_port, *target.exposed_port)
    if (source.side not in _EGRESS_DIRECTIONS or target.side not in _EGRESS_DIRECTIONS
            or any(not isinstance(value, (int, float)) or isinstance(value, bool)
                   or not isfinite(value) for value in (*coordinates, source_run, target_run))
            or min(source_run, target_run) < 0):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: fixed connector corridors")
    if any(egress.semantic_port[0] != egress.exposed_port[0]
           and egress.semantic_port[1] != egress.exposed_port[1] for egress in pair):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: non-orthogonal endpoint corridor")
    sx, sy = source.exposed_port
    tx, ty = target.exposed_port
    sd, td = _EGRESS_DIRECTIONS[source.side], _EGRESS_DIRECTIONS[target.side]
    a = (sx + sd[0] * source_run, sy + sd[1] * source_run)
    b = (tx + td[0] * target_run, ty + td[1] * target_run)
    if not all(isfinite(value) for value in (*a, *b)):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: overflowing endpoint corridor")
    return a, b


def coincident_endpoint_port_ids(index: SurfaceObstacleIndex,
                                 endpoint: tuple[float, float],
                                 host_ids: tuple[str, ...]) -> tuple[str, ...]:
    """Authorize only registered ports of the endpoint's connected hosts."""
    prefixes = tuple(f"port:{host_id}:" for host_id in host_ids)
    result = []
    for item in index.select(classes=("port",)):
        if not item.placement_id.startswith(prefixes) or not isinstance(item.geometry, ObstacleRect):
            continue
        point = ((item.geometry.left + item.geometry.right) / 2,
                 (item.geometry.top + item.geometry.bottom) / 2)
        if abs(point[0] - endpoint[0]) <= 1e-6 and abs(point[1] - endpoint[1]) <= 1e-6:
            result.append(item.placement_id)
    return tuple(result)


def _viewport_extent(mark: MarkPlacement) -> tuple[float, float, float, float]:
    bounds = mark.bounds
    left, top = float(bounds.inline), float(bounds.block)
    return left, top, left + float(bounds.inline_size), top + float(bounds.block_size)


def _flatten(commands: tuple[PathCommand, ...], *, close: bool) -> tuple[tuple[tuple[float, float], tuple[float, float]], ...]:
    segments: list[tuple[tuple[float, float], tuple[float, float]]] = []
    start = current = None
    for command in commands:
        if command.kind == "move":
            if close and start is not None and current != start:
                segments.append((current, start))
            start = current = (float(command.points[0][0]), float(command.points[0][1]))
        elif current is None:
            continue
        elif command.kind == "line":
            point = (float(command.points[0][0]), float(command.points[0][1]))
            segments.append((current, point))
            current = point
        elif command.kind == "quadratic":
            (cx, cy), (ex, ey) = command.points
            previous = current
            for step in range(1, 17):
                t = step / 16
                point = ((1 - t) ** 2 * current[0] + 2 * (1 - t) * t * cx + t * t * ex,
                         (1 - t) ** 2 * current[1] + 2 * (1 - t) * t * cy + t * t * ey)
                segments.append((previous, point))
                previous = point
            current = (float(ex), float(ey))
    if close and start is not None and current != start:
        segments.append((current, start))
    return tuple(segments)


def painted_cardinal_ports(mark: MarkPlacement) -> dict[str, tuple[float, float]]:
    """Outermost painted points on the viewport's cardinal axes of a compound point glyph.

    Only a point mark that carries completed painted glyph parts qualifies; a
    built-in diamond or ordinary point has no painted parts and keeps its
    viewport tips. Stroke parts extend the fill edge by half their width.
    A side whose axis never meets paint is omitted so the caller falls back.
    """
    if mark.mark_shape != "point":
        return {}
    left, top, right, bottom = _viewport_extent(mark)
    center_x, center_y = (left + right) / 2, (top + bottom) / 2
    best: dict[str, float] = {}
    for part in mark.symbol_parts:
        if part.paint_mode not in {"fill", "stroke"}:
            continue
        half = float(part.stroke_width or 0.0) / 2 if part.paint_mode == "stroke" else 0.0
        for (x1, y1), (x2, y2) in _flatten(part.commands, close=part.paint_mode == "fill"):
            if y1 != y2 and min(y1, y2) <= center_y <= max(y1, y2):
                x = x1 + (center_y - y1) * (x2 - x1) / (y2 - y1)
                best["end"] = max(best.get("end", float("-inf")), x + half)
                best["start"] = min(best.get("start", float("inf")), x - half)
            if x1 != x2 and min(x1, x2) <= center_x <= max(x1, x2):
                y = y1 + (center_x - x1) * (y2 - y1) / (x2 - x1)
                best["below"] = max(best.get("below", float("-inf")), y + half)
                best["above"] = min(best.get("above", float("inf")), y - half)
    result = {}
    if "end" in best:
        result["end"], result["start"] = (best["end"], center_y), (best["start"], center_y)
    if "below" in best:
        result["below"], result["above"] = (center_x, best["below"]), (center_x, best["above"])
    return result


def connector_boundary_ports(mark: MarkPlacement, endpoint: str,
                             toward: tuple[float, float], *, painted: bool = False) -> tuple[tuple[str, tuple[float, float]], ...]:
    """Enumerate finite outline ports in deterministic distance/side order."""
    if endpoint == "start" and mark.mark_shape != "point":
        return () if mark.start_port is None else (("start", mark.start_port),)
    if endpoint in {"finish", "end"} and mark.mark_shape != "point":
        return () if mark.end_port is None else (("end", mark.end_port),)
    if endpoint not in {"at", "body", "start", "finish", "end"}:
        raise ValueError(f"E_PRESENTATION_ANCHOR_MISSING: connector endpoint={endpoint!r}; expected at, body, start, finish, or end")
    left, top, right, bottom = _viewport_extent(mark)
    center_x, center_y = (left + right) / 2, (top + bottom) / 2
    # Cardinal tips are on a diamond point glyph's outline. For a span body,
    # these are its four boundary midpoints. Stable tie order: end/start/above/below.
    # A compound point glyph may be inset in its viewport: its tips are where the
    # cardinal axes leave the completed painted outline (#1913).
    ink = painted_cardinal_ports(mark) if painted else {}
    ports = (("end", ink.get("end", (right, center_y))), ("start", ink.get("start", (left, center_y))),
             ("above", ink.get("above", (center_x, top))), ("below", ink.get("below", (center_x, bottom))))
    return tuple(sorted(ports, key=lambda item: (abs(item[1][0] - toward[0]) + abs(item[1][1] - toward[1]),
                                                 ports.index(item))))


def connector_boundary_port(mark: MarkPlacement, endpoint: str,
                            toward: tuple[float, float], *, painted: bool = False) -> tuple[float, float]:
    """Return the preferred boundary port for callers without route search."""
    ports = connector_boundary_ports(mark, endpoint, toward, painted=painted)
    if not ports:
        raise LayoutError("E_PRESENTATION_ANCHOR_MISSING", "/layout/connectorPort",
                          node_id=mark.placement_id[:120],
                          detail=f"endpoint={endpoint!r}; reason=temporal-endpoint-unavailable")
    return ports[0][1]


def physical_host_neighbors(mark: MarkPlacement, marks: Iterable[MarkPlacement],
                            endpoint: str) -> tuple[MarkPlacement, ...]:
    """Return the exact resolved host, or hosted points covering a span endpoint."""
    by_id = {item.placement_id: item for item in marks}
    if mark.mark_shape == "point":
        host = by_id.get(mark.physical_host.placement_id) if mark.physical_host is not None else None
        return (host,) if host is not None and host.mark_shape != "point" else ()
    if endpoint not in {"start", "at", "finish", "end"}:
        return ()
    semantic = mark.start_port if endpoint in {"start", "at"} else mark.end_port
    if semantic is None:
        return ()
    x, y = semantic
    result = []
    for child in by_id.values():
        host = child.physical_host
        if child.mark_shape != "point" or host is None or host.placement_id != mark.placement_id:
            continue
        bounds = child.bounds
        left, top = float(bounds.inline), float(bounds.block)
        right, bottom = left + float(bounds.inline_size), top + float(bounds.block_size)
        if left - 1e-9 <= x <= right + 1e-9 and top - 1e-9 <= y <= bottom + 1e-9:
            result.append(child)
    return tuple(sorted(result, key=lambda item: item.placement_id))


def split_route_at_physical_corridors(
        points: tuple[tuple[float, float], ...],
        source: ConnectorEgress | None,
        target: ConnectorEgress | None,
) -> tuple[tuple[tuple[float, float], tuple[float, float], tuple[str, ...]], ...]:
    """Split route segments at each recorded exposed boundary.

    The final tuple on each segment contains only physical host IDs authorized
    for that endpoint corridor. Legacy comparison hosts are supplied separately
    by callers and therefore keep their established whole-route semantics.
    """
    if len(points) < 2:
        return ()
    if not any(egress is not None and egress.corridor_host_ids for egress in (source, target)):
        return tuple((start, end, ()) for start, end in zip(points, points[1:]) if start != end)

    def corridor_limit(egress: ConnectorEgress | None, *, reverse: bool) -> float:
        if egress is None or not egress.corridor_host_ids:
            return 0.0
        path = tuple(reversed(points)) if reverse else points
        semantic, exposed = egress.semantic_port, egress.exposed_port
        if not path or not _point_on_segment(path[0], semantic, exposed):
            return 0.0
        def progress(point: tuple[float, float]) -> float:
            if semantic[0] != exposed[0]:
                direction = 1.0 if exposed[0] > semantic[0] else -1.0
                return (point[0] - semantic[0]) * direction
            if semantic[1] != exposed[1]:
                direction = 1.0 if exposed[1] > semantic[1] else -1.0
                return (point[1] - semantic[1]) * direction
            return 0.0

        previous_progress = progress(path[0])
        distance = 0.0
        for start, end in zip(path, path[1:]):
            if not _point_on_segment(start, semantic, exposed):
                return 0.0
            current_progress = progress(end)
            if current_progress < previous_progress - 1e-9:
                return 0.0
            length = abs(end[0] - start[0]) + abs(end[1] - start[1])
            if _point_on_segment(exposed, start, end):
                if (previous_progress > progress(exposed) + 1e-9
                        or current_progress < progress(exposed) - 1e-9):
                    return 0.0
                return distance + abs(exposed[0] - start[0]) + abs(exposed[1] - start[1])
            if not _point_on_segment(end, semantic, exposed):
                return 0.0
            distance += length
            previous_progress = current_progress
        return 0.0

    source_limit = corridor_limit(source, reverse=False)
    target_limit = corridor_limit(target, reverse=True)
    total = geometry_sum(abs(b[0] - a[0]) + abs(b[1] - a[1])
                         for a, b in zip(points, points[1:]))
    result = []
    distance = 0.0
    for start, end in zip(points, points[1:]):
        length = abs(end[0] - start[0]) + abs(end[1] - start[1])
        cuts = [start, end]
        for egress in (source, target):
            if (egress is not None and egress.corridor_host_ids
                    and _point_on_segment(egress.exposed_port, start, end)):
                cuts.append(egress.exposed_port)
        cuts = sorted(set(cuts), key=lambda point: abs(point[0] - start[0]) + abs(point[1] - start[1]))
        traversed = 0.0
        for left, right in zip(cuts, cuts[1:]):
            part_length = abs(right[0] - left[0]) + abs(right[1] - left[1])
            midpoint = distance + traversed + part_length / 2
            midpoint_point = ((left[0] + right[0]) / 2, (left[1] + right[1]) / 2)
            hosts = set()
            if (source is not None and midpoint <= source_limit + 1e-9
                    and _point_on_segment(midpoint_point, source.semantic_port, source.exposed_port)):
                hosts.update(source.corridor_host_ids)
            if (target is not None and total - midpoint <= target_limit + 1e-9
                    and _point_on_segment(midpoint_point, target.semantic_port, target.exposed_port)):
                hosts.update(target.corridor_host_ids)
            result.append((left, right, tuple(sorted(hosts))))
            traversed += part_length
        distance += length
    return tuple(result)


def _point_on_segment(point: tuple[float, float], start: tuple[float, float],
                      end: tuple[float, float]) -> bool:
    if start[0] == end[0]:
        return abs(point[0] - start[0]) <= 1e-9 and min(start[1], end[1]) - 1e-9 <= point[1] <= max(start[1], end[1]) + 1e-9
    if start[1] == end[1]:
        return abs(point[1] - start[1]) <= 1e-9 and min(start[0], end[0]) - 1e-9 <= point[0] <= max(start[0], end[0]) + 1e-9
    return False


def connector_egress_candidates(mark: MarkPlacement, endpoint: str,
                                toward: tuple[float, float],
                                siblings: tuple[MarkPlacement, ...], *, entry: str = "any", stub_length: float = 0.0,
                                stub_free: Callable[[ConnectorEgress], bool] | None = None,
                                explicit_neighbors: tuple[MarkPlacement, ...] = (), painted: bool = False) -> tuple[ConnectorEgress, ...]:
    """Keep the temporal port while leaving only its connected comparison host.

    ``entry="side-when-free"`` (``relationRouting.entry``, #1030) puts a stub candidate first for a span ``start``
    whose ``toward`` lies left of the cluster (the mirrored ``end``: right of it): the route must end ``stub_length``
    beside the port and run straight into it. It is offered only when ``stub_free`` accepts the stub; the distance
    order follows it unchanged, so a stub that cannot be routed falls back to today's order.

    ``painted=True`` (annotation leaders, #1913) takes a compound point glyph's semantic tips from its completed
    painted outline instead of its viewport box. The exposed port stays at the viewport edge, so the leader starts on
    the paint and crosses the inset inside its own host through the existing corridor; diamond and ordinary points
    have no painted parts and are unchanged.
    """
    if endpoint not in {"start", "finish", "end", "at", "body"}:
        raise ValueError(f"E_PRESENTATION_ANCHOR_MISSING: connector endpoint={endpoint!r}; expected start, finish, end, at, or body")
    if ((endpoint == "start" and mark.mark_shape != "point" and mark.start_port is None)
            or (endpoint in {"finish", "end"} and mark.mark_shape != "point"
                and mark.end_port is None)):
        return ()
    connected = {mark.placement_id: mark}
    pending = [mark]
    while pending:
        current = pending.pop()
        for sibling in siblings:
            if (sibling.source_ref != mark.source_ref or sibling.placement_id in connected
                    or not _overlaps(current, sibling)):
                continue
            connected[sibling.placement_id] = sibling
            pending.append(sibling)
    physical_neighbors = {item.placement_id: item for item in (
        *physical_host_neighbors(mark, (mark, *siblings, *explicit_neighbors), endpoint),
        *explicit_neighbors)}
    cluster = tuple(connected[key] for key in sorted(connected))
    extent_marks = (*cluster, *(physical_neighbors[key] for key in sorted(physical_neighbors)))
    left = min(float(item.bounds.inline) for item in extent_marks)
    top = min(float(item.bounds.block) for item in extent_marks)
    right = max(float(item.bounds.inline + item.bounds.inline_size) for item in extent_marks)
    bottom = max(float(item.bounds.block + item.bounds.block_size) for item in extent_marks)
    candidates = []
    if mark.mark_shape == "point" or endpoint in {"at", "body"}:
        semantic_ports = connector_boundary_ports(mark, endpoint, toward, painted=painted)
    else:
        semantic = mark.start_port if endpoint == "start" else mark.end_port
        semantic_ports = tuple((side, semantic) for side in ("end", "start", "above", "below"))
    for side, semantic in semantic_ports:
        # Paint (outline stroke) may overshoot the viewport: never pull the exposed port back inside it.
        exposed = {"end": (max(right, semantic[0]) if painted else right, semantic[1]),
                   "start": (min(left, semantic[0]) if painted else left, semantic[1]),
                   "above": (semantic[0], min(top, semantic[1]) if painted else top),
                   "below": (semantic[0], max(bottom, semantic[1]) if painted else bottom)}[side]
        natural = "start" if endpoint == "start" else "end"
        through_body = (mark.mark_shape != "point" and endpoint not in {"at", "body"}
                        and side in {"start", "end"} and side != natural)
        if through_body:
            # A temporal endpoint cannot egress through the opposite side of its own bar.
            continue
        candidates.append(ConnectorEgress(side, semantic, exposed, tuple(sorted(connected)), False,
            through_body, tuple(sorted(physical_neighbors))))
    order = {"end": 0, "start": 1, "above": 2, "below": 3}
    ranked = tuple(sorted(candidates, key=lambda item: (
        abs(item.exposed_port[0] - toward[0]) + abs(item.exposed_port[1] - toward[1]),
        order[item.side])))
    point = mark.mark_shape == "point"
    if (entry not in {"side-when-free", "side"} or stub_free is None
            or (point and entry != "side") or (endpoint in {"at", "body"} and not (point and endpoint == "at"))):
        return ranked
    horizontal = ("start" if endpoint in {"start", "at"} and toward[0] < left
                  else "end" if endpoint in {"finish", "end"} and toward[0] > right else None)
    plain = next((item for item in ranked if item.side == horizontal), None)
    if plain is None or stub_length <= 0:
        return ranked
    direction = -1.0 if horizontal == "start" else 1.0
    stub = ConnectorEgress(plain.side, plain.semantic_port,
                           (plain.exposed_port[0] + direction * stub_length, plain.exposed_port[1]), plain.host_ids,
                           True, plain.through_body, plain.corridor_host_ids)
    return (stub, *ranked) if stub_free(stub) else ranked


def stub_pairs_first(pairs: tuple[tuple[ConnectorEgress, ConnectorEgress], ...]
                     ) -> tuple[tuple[ConnectorEgress, ConnectorEgress], ...]:
    """Try every source exit with the horizontal entry stub before any other pair (#1072); order inside each group kept.

    An exit through the source's own bar (the far side of a span) is not promoted: its corridor crosses the mark.
    """
    def first(pair: tuple[ConnectorEgress, ConnectorEgress]) -> bool:
        return pair[1].stub and not pair[0].through_body

    return (*(pair for pair in pairs if first(pair)), *(pair for pair in pairs if not first(pair)))


def _overlaps(left: MarkPlacement, right: MarkPlacement) -> bool:
    a, b = left.bounds, right.bounds
    return (a.inline < b.inline + b.inline_size and b.inline < a.inline + a.inline_size
            and a.block < b.block + b.block_size and b.block < a.block + a.block_size)
