"""Finite Layout-owned boundary ports for visible connector geometry."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

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
    return connector_boundary_ports(mark, endpoint, toward)[0][1]


def connector_egress_candidates(mark: MarkPlacement, endpoint: str,
                                toward: tuple[float, float],
                                siblings: tuple[MarkPlacement, ...], *, entry: str = "any", stub_length: float = 0.0,
                                stub_free: Callable[[ConnectorEgress], bool] | None = None) -> tuple[ConnectorEgress, ...]:
    """Keep the temporal port while leaving only its connected comparison host.

    ``entry="side-when-free"`` (``relationRouting.entry``, #1030) puts a stub candidate first for a span ``start``
    whose ``toward`` lies left of the cluster (the mirrored ``end``: right of it): the route must end ``stub_length``
    beside the port and run straight into it. It is offered only when ``stub_free`` accepts the stub; the distance
    order follows it unchanged, so a stub that cannot be routed falls back to today's order.
    """
    if endpoint not in {"start", "finish", "end", "at", "body"}:
        raise ValueError(f"E_PRESENTATION_ANCHOR_MISSING: connector endpoint={endpoint!r}; expected start, finish, end, at, or body")
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
        natural = "start" if endpoint == "start" else "end"
        through_body = (mark.mark_shape != "point" and endpoint not in {"at", "body"}
                        and side in {"start", "end"} and side != natural)
        if through_body:
            # A temporal endpoint cannot egress through the opposite side of its own bar.
            continue
        candidates.append(ConnectorEgress(side, semantic, exposed, tuple(sorted(connected)), False,
            through_body))
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
                           (plain.exposed_port[0] + direction * stub_length, plain.exposed_port[1]), plain.host_ids, True)
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
