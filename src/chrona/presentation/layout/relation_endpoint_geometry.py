"""Shared geometry for mandatory relation endpoint leads and span endpoint ink."""
from __future__ import annotations

from math import hypot
from math import isfinite

from chrona.presentation.layout.obstacles import ObstacleGeometry, ObstacleRect, ObstacleSegment
from chrona.presentation.layout.relation_terminals import (
    complete_centred_terminals, marker_ink_bounds, terminal_run,
)
from chrona.presentation.layout.ports import ConnectorEgress, outward_corridor_ends
from chrona.presentation.layout.surface_quality import MarkerGeometry


def endpoint_tangent_minimum(width: float, marker: MarkerGeometry | None) -> float:
    """Minimum straight lead required before a completed route may turn."""
    reserve = marker.head_length / 2 if marker is not None and marker.centred else terminal_run(marker)
    return width + reserve


def endpoint_lead_run(exposed_port: tuple[float, float], semantic_port: tuple[float, float],
                      width: float, marker: MarkerGeometry | None) -> float:
    """Mandatory free lead remaining after an already completed host corridor."""
    corridor = hypot(exposed_port[0] - semantic_port[0], exposed_port[1] - semantic_port[1])
    return max(0.0, endpoint_tangent_minimum(width, marker) - corridor)


def temporal_route_inline_hull(pair: tuple[ConnectorEgress, ConnectorEgress], width: float,
                               source_marker: MarkerGeometry | None,
                               target_marker: MarkerGeometry | None,
                               temporal_anchors: tuple[tuple[float, float], tuple[float, float]]
                               ) -> tuple[float, float]:
    """Smallest inline interval containing temporal anchors, corridors and mandatory outward leads."""
    if (len(pair) != 2 or isinstance(width, bool) or not isinstance(width, (int, float))
            or not isfinite(width) or width < 0):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: temporal endpoint hull inputs")
    source, target = pair
    source_run = endpoint_lead_run(source.exposed_port, source.semantic_port, width, source_marker)
    target_run = endpoint_lead_run(target.exposed_port, target.semantic_port, width, target_marker)
    source_out, target_out = outward_corridor_ends(pair, source_run=source_run, target_run=target_run)
    if not isinstance(temporal_anchors, tuple) or len(temporal_anchors) != 2 or any(
            not isinstance(anchor, tuple) or len(anchor) != 2
            or any(isinstance(value, bool) or not isinstance(value, (int, float))
                   or not isfinite(value) for value in anchor)
            for anchor in temporal_anchors):
        raise ValueError("E_LAYOUT_ROUTE_ATTEMPT_INVALID: temporal endpoint anchors")
    xs = [source.semantic_port[0], source.exposed_port[0], source_out[0],
          target.semantic_port[0], target.exposed_port[0], target_out[0]]
    xs.extend(anchor[0] for anchor in temporal_anchors)
    return min(xs), max(xs)


def intrinsic_span_endpoint_ink(port: tuple[float, float], endpoint: str, width: float,
                                marker: MarkerGeometry | None, *, terminal_side: str
                                ) -> tuple[ObstacleGeometry, ...]:
    """Return the mandatory outward stroke footprint of a temporal span endpoint.

    A span has a known outward normal at its start/end; point and body hosts do
    not. The returned lead and marker bounds reuse route-lead and marker-projection
    geometry, including a marker outline's stroke extent.
    """
    if endpoint not in {"start", "end", "finish"}:
        raise ValueError("span endpoint must be start, end, or finish")
    if terminal_side not in {"source", "target"}:
        raise ValueError("terminal side must be source or target")
    run = endpoint_tangent_minimum(width, marker)
    sign = -1.0 if endpoint == "start" else 1.0
    far = (port[0] + sign * run, port[1])
    lead = ObstacleSegment(port, far, width)
    if marker is None:
        return (lead,)
    path = (port, far) if terminal_side == "source" else (far, port)
    side = "start" if terminal_side == "source" else "end"
    path, start, end = complete_centred_terminals(path,
        marker if terminal_side == "source" else None,
        marker if terminal_side == "target" else None, width)
    completed_marker = start if terminal_side == "source" else end
    marker_bounds = ObstacleRect(*marker_ink_bounds(completed_marker, side=side,
        points=path, path_commands=(), stroke_width=width))
    return lead, marker_bounds
