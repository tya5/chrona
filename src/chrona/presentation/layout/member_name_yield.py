"""Typed Layout boundary for the required-endpoint member-name exception."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.relation_terminals import marker_ink_bounds
from chrona.presentation.layout.surface_quality import MarkerGeometry, PathCommand, TextPlacement


@dataclass(frozen=True)
class MemberNameYieldRequest:
    """Exact name-only blockers and completed candidate ink, not a route verdict."""

    blocker_ids: tuple[str, ...]
    protected_ink: tuple[SurfaceObstacle, ...]
    # A connected route (#1908) may also displace the one other name that solely holds an earlier
    # pose of a blocker with none left; a required stub endpoint never does.
    displace: bool = False


@dataclass(frozen=True)
class MemberNameYieldResult:
    """One atomic content snapshot; already-completed routes remain untouched."""

    obstacles: SurfaceObstacleIndex
    text: tuple[TextPlacement, ...]
    required_obstacle_ids: frozenset[str]


MemberNameYield = Callable[
    [MemberNameYieldRequest, SurfaceObstacleIndex], MemberNameYieldResult | None,
]


def endpoint_candidate_ink(
    relation_id: str,
    source: tuple[tuple[float, float], ...],
    target: tuple[tuple[float, float], ...],
    source_marker: MarkerGeometry | None,
    target_marker: MarkerGeometry | None,
    stroke_width: float,
) -> tuple[SurfaceObstacle, ...]:
    """Protect an already-admissible candidate's actual stroke and terminal ink."""
    result = []
    for endpoint, points, marker, side in (
        ("source", source, source_marker, "start"),
        ("target", target, target_marker, "end"),
    ):
        for index, (start, end) in enumerate(zip(points, points[1:])):
            if start != end:
                result.append(SurfaceObstacle(
                    f"endpoint-candidate:{relation_id}:{endpoint}:segment:{index}",
                    "dependency-route", "timeline", ObstacleSegment(start, end, stroke_width),
                    route_owner_id=relation_id))
        if marker is not None:
            result.append(SurfaceObstacle(
                f"endpoint-candidate:{relation_id}:{endpoint}:terminal",
                "dependency-route", "timeline", ObstacleRect(*marker_ink_bounds(
                    marker, side=side, points=points, path_commands=(), stroke_width=stroke_width)),
                route_owner_id=relation_id))
    return tuple(result)


def route_candidate_ink(
    relation_id: str,
    points: tuple[tuple[float, float], ...],
    source_marker: MarkerGeometry | None,
    target_marker: MarkerGeometry | None,
    stroke_width: float,
    *,
    path_commands: tuple[PathCommand, ...] = (),
) -> tuple[SurfaceObstacle, ...]:
    """Protect a connected candidate's completed stroke and both terminals."""
    result = [SurfaceObstacle(f"route-candidate:{relation_id}:segment:{index}", "dependency-route",
                "timeline", ObstacleSegment(start, end, stroke_width), route_owner_id=relation_id)
              for index, (start, end) in enumerate(zip(points, points[1:])) if start != end]
    for endpoint, marker, side in (("source", source_marker, "start"), ("target", target_marker, "end")):
        if marker is not None:
            result.append(SurfaceObstacle(f"route-candidate:{relation_id}:{endpoint}:terminal",
                "dependency-route", "timeline", ObstacleRect(*marker_ink_bounds(
                    marker, side=side, points=points, path_commands=path_commands, stroke_width=stroke_width)),
                route_owner_id=relation_id))
    return tuple(result)


def endpoint_candidate_blocker_ids(
    ink: tuple[SurfaceObstacle, ...], required_content: SurfaceObstacleIndex,
) -> tuple[str, ...]:
    """Check the very same stroke/head ink protected during name placement."""
    return tuple(sorted({blocker.placement_id for item in ink
        for blocker in required_content.collisions(item.geometry,
            classes=("text", "label-visual", "relation-label"), regions=("timeline", "group-header"))}))
