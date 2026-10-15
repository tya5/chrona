"""Finite Layout-owned boundary ports for visible connector geometry."""
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from chrona.presentation.layout.model import LayoutError, geometry_sum
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacleIndex
from chrona.presentation.layout.surface_quality import MarkPlacement


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


def connector_boundary_ports(mark: MarkPlacement, endpoint: str,
                             toward: tuple[float, float]) -> tuple[tuple[str, tuple[float, float]], ...]:
    """Enumerate finite outline ports in deterministic distance/side order."""
    if endpoint == "start" and mark.mark_shape != "point":
        return () if mark.start_port is None else (("start", mark.start_port),)
    if endpoint in {"finish", "end"} and mark.mark_shape != "point":
        return () if mark.end_port is None else (("end", mark.end_port),)
    if endpoint not in {"at", "body", "start", "finish", "end"}:
        raise ValueError(f"E_PRESENTATION_ANCHOR_MISSING: connector endpoint={endpoint!r}; expected at, body, start, finish, or end")
    bounds = mark.bounds
    left, top = float(bounds.inline), float(bounds.block)
    right, bottom = left + float(bounds.inline_size), top + float(bounds.block_size)
    center_x, center_y = (left + right) / 2, (top + bottom) / 2
    # Cardinal tips are on a diamond point glyph's outline. For a span body,
    # these are its four boundary midpoints. Stable tie order: end/start/above/below.
    ports = (("end", (right, center_y)), ("start", (left, center_y)),
             ("above", (center_x, top)), ("below", (center_x, bottom)))
    return tuple(sorted(ports, key=lambda item: (abs(item[1][0] - toward[0]) + abs(item[1][1] - toward[1]),
                                                 ports.index(item))))


def connector_boundary_port(mark: MarkPlacement, endpoint: str,
                            toward: tuple[float, float]) -> tuple[float, float]:
    """Return the preferred boundary port for callers without route search."""
    ports = connector_boundary_ports(mark, endpoint, toward)
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
            if egress is not None and _point_on_segment(egress.exposed_port, start, end):
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
                                explicit_neighbors: tuple[MarkPlacement, ...] = ()) -> tuple[ConnectorEgress, ...]:
    """Keep the temporal port while leaving only its connected comparison host.

    ``entry="side-when-free"`` (``relationRouting.entry``, #1030) puts a stub candidate first for a span ``start``
    whose ``toward`` lies left of the cluster (the mirrored ``end``: right of it): the route must end ``stub_length``
    beside the port and run straight into it. It is offered only when ``stub_free`` accepts the stub; the distance
    order follows it unchanged, so a stub that cannot be routed falls back to today's order.
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
        semantic_ports = connector_boundary_ports(mark, endpoint, toward)
    else:
        semantic = mark.start_port if endpoint == "start" else mark.end_port
        semantic_ports = tuple((side, semantic) for side in ("end", "start", "above", "below"))
    for side, semantic in semantic_ports:
        exposed = {"end": (right, semantic[1]), "start": (left, semantic[1]),
                   "above": (semantic[0], top), "below": (semantic[0], bottom)}[side]
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
