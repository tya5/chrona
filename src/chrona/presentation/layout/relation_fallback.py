"""Finite fixed connector geometry; no graph search or safety/completeness claim."""
from collections.abc import Callable
from dataclasses import dataclass
from math import isfinite

from chrona.presentation.layout.ports import ConnectorEgress
from chrona.presentation.layout.relation_shapes import first_fit_port_pairs

Point = tuple[float, float]
Path = tuple[Point, ...]
Pair = tuple[ConnectorEgress, ConnectorEgress]
_DIRECTIONS = {"end": (1., 0.), "start": (-1., 0.), "above": (0., -1.), "below": (0., 1.)}


def _corridor_ends(pair: Pair, source_run: float, target_run: float) -> tuple[Point, Point]:
    source, target = pair
    coordinates = (*source.semantic_port, *source.exposed_port,
                   *target.semantic_port, *target.exposed_port)
    if (source.side not in _DIRECTIONS or target.side not in _DIRECTIONS
            or any(not isinstance(value, (int, float)) or isinstance(value, bool)
                   or not isfinite(value) for value in (*coordinates, source_run, target_run))
            or min(source_run, target_run) < 0):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: fixed connector corridors")
    if any(egress.semantic_port[0] != egress.exposed_port[0]
           and egress.semantic_port[1] != egress.exposed_port[1] for egress in pair):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: non-orthogonal endpoint corridor")
    sx, sy = source.exposed_port
    tx, ty = target.exposed_port
    sd, td = _DIRECTIONS[source.side], _DIRECTIONS[target.side]
    a = (sx + sd[0] * source_run, sy + sd[1] * source_run)
    b = (tx + td[0] * target_run, ty + td[1] * target_run)
    if not all(isfinite(value) for value in (*a, *b)):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: overflowing endpoint corridor")
    return a, b


def _without_duplicate_neighbours(points: Path) -> Path:
    return tuple(point for number, point in enumerate(points) if not number or point != points[number - 1])


def fixed_connector_candidates(pair: Pair, *, source_run: float, target_run: float) -> tuple[Path, ...]:
    """Preferred L/Z proposals retain independent outward endpoint corridors."""
    source, target = pair
    a, b = _corridor_ends(pair, source_run, target_run)
    middle_x, middle_y = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    clearance = max(source_run, target_run, 1.)
    centres = (
        (a, (b[0], a[1]), b), (a, (a[0], b[1]), b),
        (a, (middle_x, a[1]), (middle_x, b[1]), b),
        (a, (a[0], middle_y), (b[0], middle_y), b),
        (a, (a[0], max(a[1], b[1]) + clearance),
         (b[0], max(a[1], b[1]) + clearance), b),
        (a, (a[0], min(a[1], b[1]) - clearance),
         (b[0], min(a[1], b[1]) - clearance), b),
    )
    paths = []
    for centre in centres:
        raw = (source.semantic_port, source.exposed_port, *centre,
               target.exposed_port, target.semantic_port)
        path = _without_duplicate_neighbours(raw)
        if len(path) >= 2 and path not in paths:
            paths.append(path)
    return tuple(paths)


@dataclass(frozen=True)
class FixedConnectorSelection:
    selected_pair: Pair
    points: Path


@dataclass(frozen=True)
class PairedStubGeometry:
    """Two independent fragments; never an accepted connected-route receipt."""

    source: Path
    target: Path


def paired_stub_geometry(pair: Pair, *, source_run: float, target_run: float) -> PairedStubGeometry:
    source, target = pair
    a, b = _corridor_ends(pair, source_run, target_run)
    outgoing = _without_duplicate_neighbours((source.semantic_port, source.exposed_port, a))
    incoming = _without_duplicate_neighbours((b, target.exposed_port, target.semantic_port))
    if len(outgoing) < 2 or len(incoming) < 2:
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: paired stubs require visible endpoint runs")
    return PairedStubGeometry(outgoing, incoming)


def complete_fixed_connector(pairs: tuple[Pair, ...], *, source_run: float, target_run: float,
                             prepare: Callable[[Path, ConnectorEgress, ConnectorEgress], Path | None],
                             accept: Callable[[Path], bool]) -> FixedConnectorSelection | None:
    """Complete the first admissible fixed corridor; caller owns host/terminal checks."""
    for pair in first_fit_port_pairs(pairs):
        for path in fixed_connector_candidates(pair, source_run=source_run, target_run=target_run):
            completed = prepare(path, *pair)
            if completed is not None and accept(completed):
                return FixedConnectorSelection(pair, completed)
    return None
