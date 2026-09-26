"""Finite Layout-owned boundary ports for visible connector geometry."""
from __future__ import annotations

from dataclasses import dataclass

from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacleIndex
from chrona.presentation.layout.surface_quality import MarkPlacement


@dataclass(frozen=True)
class ConnectorEgress:
    side: str
    semantic_port: tuple[float, float]
    exposed_port: tuple[float, float]
    host_ids: tuple[str, ...]

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
        return (("start", mark.start_port),)
    if endpoint in {"finish", "end"} and mark.mark_shape != "point":
        return (("end", mark.end_port),)
    if endpoint not in {"at", "body", "start", "finish", "end"}:
        raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
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
    return connector_boundary_ports(mark, endpoint, toward)[0][1]


def connector_egress_candidates(mark: MarkPlacement, endpoint: str,
                                toward: tuple[float, float],
                                siblings: tuple[MarkPlacement, ...]) -> tuple[ConnectorEgress, ...]:
    """Keep the temporal port while leaving only its connected comparison host."""
    if endpoint not in {"start", "finish", "end", "at", "body"}:
        raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
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
    cluster = tuple(connected[key] for key in sorted(connected))
    left = min(float(item.bounds.inline) for item in cluster)
    top = min(float(item.bounds.block) for item in cluster)
    right = max(float(item.bounds.inline + item.bounds.inline_size) for item in cluster)
    bottom = max(float(item.bounds.block + item.bounds.block_size) for item in cluster)
    candidates = []
    if mark.mark_shape == "point" or endpoint in {"at", "body"}:
        semantic_ports = connector_boundary_ports(mark, endpoint, toward)
    else:
        semantic = mark.start_port if endpoint == "start" else mark.end_port
        semantic_ports = tuple((side, semantic) for side in ("end", "start", "above", "below"))
    for side, semantic in semantic_ports:
        exposed = {"end": (right, semantic[1]), "start": (left, semantic[1]),
                   "above": (semantic[0], top), "below": (semantic[0], bottom)}[side]
        candidates.append(ConnectorEgress(side, semantic, exposed, tuple(sorted(connected))))
    order = {"end": 0, "start": 1, "above": 2, "below": 3}
    return tuple(sorted(candidates, key=lambda item: (
        abs(item.exposed_port[0] - toward[0]) + abs(item.exposed_port[1] - toward[1]),
        order[item.side])))


def _overlaps(left: MarkPlacement, right: MarkPlacement) -> bool:
    a, b = left.bounds, right.bounds
    return (a.inline < b.inline + b.inline_size and b.inline < a.inline + a.inline_size
            and a.block < b.block + b.block_size and b.block < a.block + a.block_size)
