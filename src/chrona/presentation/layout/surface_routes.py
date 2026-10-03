"""Owns dependency ports, routes and relation labels; reads completed marks and the shared obstacle index."""
from __future__ import annotations

from dataclasses import dataclass, replace
import re
from collections.abc import Callable
from typing import Any, Mapping

from chrona.presentation.layout.labels import LabelRect, place_label
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex, obstacles_intersect,
)
from chrona.presentation.layout.ports import (
    ConnectorEgress, connector_egress_candidates,
)
from chrona.presentation.layout.presentation import TrackPlacement
from chrona.presentation.layout.relation_terminals import centred_on_route, marker_geometry, trim_for_centred_terminals
from chrona.presentation.layout.routing import (
    RouteSearchFailure, RouteSuppressionEvidence, place_relation_route,
    relation_route_quality, select_lane_relation_route,
)
from chrona.presentation.layout.path_geometry import flatten_path, rounded_orthogonal_path
from chrona.presentation.layout.surface_geometry import bounds_from_rect
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, MarkPlacement, PathCommand, RelationPlacement, RowPlacement, ShapePlacement,
    SurfaceLayoutRequest, TextPlacement,
)
from chrona.presentation.layout.text import metric_for_role, measure_text_width, place_text
from chrona.presentation.model.semantic_registry import semantic_binding


@dataclass(frozen=True)
class SurfaceRoutesContext:
    request: SurfaceLayoutRequest
    projection: Any
    review_rows: tuple[Any, ...]
    rows: tuple[RowPlacement, ...]
    groups: tuple[Any, ...]
    marks: tuple[MarkPlacement, ...]
    timeline_bounds: tuple[float, float, float, float]
    layout_manifest: Any
    metric_values: Mapping[str, Any]
    text: tuple[TextPlacement, ...]
    obstacles: SurfaceObstacleIndex


@dataclass(frozen=True)
class SurfaceRoutesBatch:
    relations: tuple[RelationPlacement, ...]
    visible_route_fallbacks: tuple[RelationPlacement, ...]
    instance_anchors: Mapping[str, tuple[tuple[str, tuple[float, float]], ...]]
    instance_rows: Mapping[str, str]
    comparison_clusters: Mapping[tuple[str, str], tuple[MarkPlacement, ...]]
    diagnostics: tuple[str, ...]


@dataclass(frozen=True)
class SurfaceRelationLabelsBatch:
    text: tuple[TextPlacement, ...]
    diagnostics: tuple[str, ...]
    visible_label_overflows: tuple[tuple[TextPlacement, LabelRect], ...]


def relation_label_content(relation: Any) -> str:
    """Format selected non-zero relation facts without changing their provenance."""
    parts: list[str] = []
    if "endpointPair" in relation.label_content:
        parts.append(f"{relation.source_endpoint}->{relation.target_endpoint}")
    if "lag" in relation.label_content:
        raw = relation.lag.get("value") if isinstance(relation.lag, Mapping) else relation.lag
        value = str(raw)
        if all(int(component) == 0 for component in re.findall(r"-?\d+", value)):
            value = ""
        elif value and value[0] not in "+-":
            value = "+" + value
        if value:
            parts.append(value + (f" [{relation.lag_calendar}]" if relation.lag_calendar else ""))
    return " ".join(parts)


def relation_label_anchor(points: tuple[tuple[float, float], ...]) -> LabelRect:
    left, right = max(zip(points, points[1:]),
        key=lambda pair: abs(pair[1][0] - pair[0][0]) + abs(pair[1][1] - pair[0][1]))
    x1, y1 = left
    x2, y2 = right
    return LabelRect(min(x1, x2), min(y1, y2), max(1.0, abs(x2 - x1)), max(1.0, abs(y2 - y1)))


def _lane_fallback_clears_required_labels(points: tuple[tuple[float, float], ...],
                                          text: tuple[TextPlacement, ...]) -> bool:
    labels = tuple(ObstacleRect(float(item.bounds.inline), float(item.bounds.block),
        float(item.bounds.inline + item.bounds.inline_size),
        float(item.bounds.block + item.bounds.block_size)) for item in text
        if item.semantic_id in {"memberLabel", "finishDelta"} and item.required
        and item.overflow != "suppressed")
    return all(not obstacles_intersect(ObstacleSegment(start, end), label)
        for start, end in zip(points, points[1:]) for label in labels)


# Row members that are comparison marks (baseline ghosts, scenario ghosts); relations never end on them.
COMPARISON_SOURCE_KINDS = frozenset({"snapshot", "scenario"})


def _combined_connector_points(source: ConnectorEgress, middle: tuple[tuple[float, float], ...],
                               target: ConnectorEgress) -> tuple[tuple[float, float], ...]:
    pieces = (*source.corridor, *middle, *reversed(target.corridor))
    completed: list[tuple[float, float]] = []
    for point in pieces:
        if not completed or completed[-1] != point:
            completed.append(point)
    return tuple(completed)


def corner_arc_blocker(obstacles: SurfaceObstacleIndex, hosts: frozenset[str], width: float,
                       classes: tuple[str, ...]) -> Callable[[tuple[tuple[float, float], ...]], bool]:
    """A corner arc must clear what the polyline cleared; the route's own host marks are exempt (#1046)."""
    def blocked(chords: tuple[tuple[float, float], ...]) -> bool:
        return any(item.placement_id not in hosts for left, right in zip(chords, chords[1:])
                   for item in obstacles.collisions(ObstacleSegment(left, right, width), classes=classes,
                                                    regions=("timeline", "group-header")))
    return blocked


def compose_surface_routes(context: SurfaceRoutesContext) -> SurfaceRoutesBatch:
    """Complete semantic relation routes and labels against the pre-route index."""
    request, projection, obstacles = context.request, context.projection, context.obstacles
    timeline_bounds = context.timeline_bounds
    marks = context.marks
    rows, groups = context.rows, context.groups
    diagnostics: list[str] = []
    relations: list[RelationPlacement] = []
    route_fallbacks: list[RelationPlacement] = []
    instance_anchors: dict[str, list[tuple[str, tuple[float, float]]]] = {}
    comparison_instances: set[str] = set()
    instance_rows: dict[str, str] = {}
    for review_row, row in zip(context.review_rows, rows, strict=True):
        fallback = (float(row.bounds.inline + row.bounds.inline_size),
                    float(row.bounds.block + row.bounds.block_size / 2))
        for item in review_row.items:
            instance_id = (f"{review_row.row_id}:{item.item_id or item.object_id}"
                           if projection.rows else item.object_id)
            instance_anchors.setdefault(item.object_id, []).append((instance_id, fallback))
            instance_rows[instance_id] = review_row.row_id
            if item.source_kind in COMPARISON_SOURCE_KINDS:
                comparison_instances.add(instance_id)
    for folded in getattr(projection, "folded_points", ()):
        instance_id = f"group-header:{folded.group_id}:{folded.item.item_id or folded.item.object_id}"
        mark = next((item for item in marks if item.placement_id == f"planned:{instance_id}"), None)
        if mark is not None:
            instance_anchors.setdefault(folded.item.object_id, []).append((instance_id, mark.end_port))
            instance_rows[instance_id] = f"group-header:{folded.group_id}"
    # A baseline ghost is a comparison mark, not a relation endpoint (#1031): connect the current plan marks only.
    # An object that has no plan instance at all (a snapshot-only explicit row) keeps its comparison instances.
    relation_anchors = {object_id: [entry for entry in entries if entry[0] not in comparison_instances] or entries
                        for object_id, entries in instance_anchors.items()}
    relation_marks = {mark.placement_id.removeprefix("planned:"): mark
                      for mark in marks if mark.placement_id.startswith("planned:")}
    comparison_clusters: dict[tuple[str, str], tuple[MarkPlacement, ...]] = {}
    for mark in marks:
        instance_id = mark.placement_id.split(":", 1)[1]
        row_id = instance_rows.get(instance_id)
        if row_id is not None:
            key = (mark.source_ref, row_id)
            comparison_clusters[key] = (*comparison_clusters.get(key, ()), mark)

    def register_path(placement_id: str, points: tuple[tuple[float, float], ...], stroke_width: float,
                      commands: tuple[PathCommand, ...] = ()) -> None:
        for index, (source, target) in enumerate(zip(points, points[1:])):
            if source != target:
                obstacles.add(SurfaceObstacle(f"{placement_id}:segment:{index}", "dependency-route",
                    "timeline", ObstacleSegment(source, target, stroke_width)))
        # The drawn arcs lie inside each turn: register their chords too so a label or later route
        # in the elbow keeps its distance from the ink, not only from the polyline (#1046).
        if any(command.kind == "quadratic" for command in commands):
            drawn = flatten_path(commands)
            for index, (source, target) in enumerate(zip(drawn, drawn[1:])):
                if source != target:
                    obstacles.add(SurfaceObstacle(f"{placement_id}:arc:{index}", "dependency-route",
                        "timeline", ObstacleSegment(source, target, stroke_width)))

    def register_port(placement_id: str, point: tuple[float, float]) -> None:
        obstacles.add(SurfaceObstacle(placement_id, "port", "timeline",
            ObstacleRect(point[0] - 0.01, point[1] - 0.01, point[0] + 0.01, point[1] + 0.01)))

    route_top = min((float(group.header_bounds.block) for group in groups if group.header_bounds is not None),
                    default=timeline_bounds[1])
    route_bottom = max((timeline_bounds[1] + timeline_bounds[3],
        *(float(group.header_bounds.block + group.header_bounds.block_size)
          for group in groups if group.header_bounds is not None)))
    route_classes = ("mark", "text", "label-visual")

    def entry_stub_length(semantic_id: str) -> float:
        """Arrowhead plus clearance: the straight run a horizontal entry needs beside the port (#1030)."""
        theme = request.theme_tokens
        clearance = max(float(context.metric_values.get("timeline.relation.cornerRadius", 0)),
                        float(theme.number(semantic_binding(semantic_id).theme_role, "strokeWidth")))
        return marker_geometry(theme.marker("relationTargetTerminal")).head_length + clearance

    def entry_stub_free(egress: ConnectorEgress) -> bool:
        """The stub lies in the timeline and crosses no mark, text or label (host marks exempt)."""
        end = egress.exposed_port[0]
        if end < timeline_bounds[0] or end > timeline_bounds[0] + timeline_bounds[2]:
            return False
        return not obstacles.egress_collisions(ObstacleSegment(*egress.corridor), host_ids=egress.host_ids,
            classes=route_classes, regions=("timeline", "group-header"))

    for relation in request.surface_content.relations:
        source, target, relation_id = relation.source_object_id, relation.target_object_id, relation.relation_id
        for source_id, source_anchor in relation_anchors.get(str(source), ()):
            for target_id, target_anchor in relation_anchors.get(str(target), ()):
                source_mark, target_mark = relation_marks.get(source_id), relation_marks.get(target_id)
                source_nominal = (source_mark.start_port if relation.source_endpoint in {"start", "at"}
                                  else source_mark.end_port) if source_mark else source_anchor
                target_nominal = (target_mark.start_port if relation.target_endpoint in {"start", "at"}
                                  else target_mark.end_port) if target_mark else target_anchor
                scene_id = (f"relation:{relation_id}:{source_id}:{target_id}"
                            if projection.rows else f"relation:{relation_id}")
                source_candidates = (connector_egress_candidates(source_mark, relation.source_endpoint,
                    target_nominal, comparison_clusters.get((source_mark.source_ref,
                        instance_rows[source_id]), ())) if source_mark else
                    (ConnectorEgress(relation.source_endpoint, source_nominal, source_nominal, ()),))
                target_candidates = (connector_egress_candidates(target_mark, relation.target_endpoint,
                    source_nominal, comparison_clusters.get((target_mark.source_ref,
                        instance_rows[target_id]), ()), entry=context.layout_manifest.relation_entry,
                    stub_length=(entry_stub_length(relation.semantic_id)
                                 if context.layout_manifest.relation_entry == "side-when-free" else 0.0),
                    stub_free=entry_stub_free) if target_mark else
                    (ConnectorEgress(relation.target_endpoint, target_nominal, target_nominal, ()),))
                port_pairs = tuple((left, right) for left in source_candidates for right in target_candidates)
                selected_pair: tuple[ConnectorEgress, ConnectorEgress] | None = None
                points: tuple[tuple[float, float], ...] = ()
                lane_selection = None
                if projection.lane_membership is not None:
                    lane_selection = select_lane_relation_route(port_pairs, obstacles=obstacles,
                        bounds=(timeline_bounds[0], route_top, timeline_bounds[0] + timeline_bounds[2], route_bottom),
                        source_host_id=source_mark.placement_id if source_mark else None,
                        target_host_id=target_mark.placement_id if target_mark else None,
                        relation_scene_id=scene_id, max_bends=context.layout_manifest.relation_max_bends,
                        max_detour_ratio=context.layout_manifest.relation_max_detour_ratio, classes=route_classes)
                    selected_pair, points = lane_selection.selected_pair, lane_selection.points
                else:
                    for source_egress, target_egress in port_pairs:
                        if any(obstacles.egress_collisions(ObstacleSegment(*egress.corridor),
                            host_ids=egress.host_ids, classes=route_classes,
                            regions=("timeline", "group-header")) for egress in
                            (source_egress, target_egress) if egress.corridor):
                            continue
                        source_port, target_port = source_egress.exposed_port, target_egress.exposed_port
                        source_obstacle_id = f"port:{source_mark.placement_id if source_mark else scene_id}:{source_egress.side}"
                        target_obstacle_id = f"port:{target_mark.placement_id if target_mark else scene_id}:{target_egress.side}"
                        existing_ports = tuple(port_id for port_id in
                            (source_obstacle_id, target_obstacle_id) if obstacles.has(port_id))
                        try:
                            middle = ((source_port,) if source_port == target_port else place_relation_route(
                                source_port=source_port, target_port=target_port, obstacles=obstacles,
                                regions=("timeline", "group-header"), classes=route_classes,
                                port_ids=existing_ports, bounds=(timeline_bounds[0], route_top,
                                    timeline_bounds[0] + timeline_bounds[2], route_bottom)))
                        except RouteSearchFailure:
                            continue
                        candidate_points = _combined_connector_points(source_egress, middle, target_egress)
                        if len(candidate_points) >= 2 and relation_route_quality(candidate_points,
                            max_bends=context.layout_manifest.relation_max_bends,
                            max_detour_ratio=context.layout_manifest.relation_max_detour_ratio):
                            selected_pair, points = (source_egress, target_egress), candidate_points
                            break
                fallback = selected_pair is None
                if fallback:
                    if request.surface_content.relation_overflow == "suppress":
                        relations.append(RelationPlacement(scene_id,
                            f"{source_id}:{relation.source_endpoint}", f"{target_id}:{relation.target_endpoint}",
                            suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED"))
                        diagnostics.append(f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}")
                        if lane_selection is not None:
                            diagnostics.append(RouteSuppressionEvidence(scene_id, lane_selection.attempts).diagnostic)
                        continue
                    selected_pair = port_pairs[0]
                    first_source, first_target = selected_pair
                    points = ((first_source.semantic_port, first_target.semantic_port)
                        if first_source.semantic_port != first_target.semantic_port else
                        (first_source.semantic_port, (first_source.semantic_port[0] + 1.0,
                                                       first_source.semantic_port[1])))
                    if lane_selection is not None and not _lane_fallback_clears_required_labels(points, context.text):
                        relations.append(RelationPlacement(scene_id,
                            f"{source_id}:{relation.source_endpoint}", f"{target_id}:{relation.target_endpoint}",
                            suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED"))
                        diagnostics.append(f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}")
                        diagnostics.append(RouteSuppressionEvidence(scene_id, lane_selection.attempts).diagnostic)
                        continue
                source_egress, target_egress = selected_pair
                source_port_id = f"{source_id}:{relation.source_endpoint}:{source_egress.side}"
                target_port_id = f"{target_id}:{relation.target_endpoint}:{target_egress.side}"
                for mark, side, port in ((source_mark, source_egress.side, source_egress.exposed_port),
                                          (target_mark, target_egress.side, target_egress.exposed_port)):
                    obstacle_id = f"port:{mark.placement_id if mark else scene_id}:{side}"
                    if not obstacles.has(obstacle_id):
                        register_port(obstacle_id, port)
                radius = float(context.metric_values.get("timeline.relation.cornerRadius", 0))
                marker_start = centred_on_route(marker_geometry(request.theme_tokens.marker("relationSourceTerminal")), "source")
                marker_end = centred_on_route(marker_geometry(request.theme_tokens.marker("relationTargetTerminal")), "target")
                points = trim_for_centred_terminals(tuple(points), marker_start, marker_end)
                dependency_stroke = float(request.theme_tokens.number(
                    semantic_binding(relation.semantic_id).theme_role, "strokeWidth"))
                arc_blocked = corner_arc_blocker(obstacles, frozenset((*source_egress.host_ids, *target_egress.host_ids)),
                                                 dependency_stroke, route_classes)

                placed = RelationPlacement(scene_id, source_port_id, target_port_id, tuple(points),
                    semantic_id=relation.semantic_id, corner_radius=radius,
                    path_commands=(rounded_orthogonal_path(tuple(points), radius,
                        start_run=0.0 if marker_start.centred else marker_start.head_length,
                        end_run=0.0 if marker_end.centred else marker_end.head_length, blocked=arc_blocked)
                        if radius > 0 and not fallback else ()),
                    marker_start=marker_start, marker_end=marker_end,
                    label_content=relation_label_content(relation), source_ref=relation_id)
                relations.append(placed)
                dependency_role = semantic_binding(placed.semantic_id).theme_role
                register_path(scene_id, placed.points,
                    float(request.theme_tokens.number(dependency_role, "strokeWidth")), placed.path_commands)
                if fallback:
                    route_fallbacks.append(placed)

    return SurfaceRoutesBatch(tuple(relations), tuple(route_fallbacks),
        {key: tuple(values) for key, values in instance_anchors.items()}, instance_rows,
        comparison_clusters, tuple(diagnostics))


def place_relation_labels(context: SurfaceRoutesContext,
                          routes: SurfaceRoutesBatch) -> SurfaceRelationLabelsBatch:
    """Place relation labels only after post-route optional labels have joined the index."""
    request, obstacles = context.request, context.obstacles
    timeline_rect = LabelRect(*context.timeline_bounds)
    relation_text: list[TextPlacement] = []
    diagnostics: list[str] = []
    visible_overflows: list[tuple[TextPlacement, LabelRect]] = []
    for placed_relation in routes.relations:
        if placed_relation.suppressed:
            continue
        content = placed_relation.label_content
        if not content:
            continue
        treatment = request.theme_tokens.text_treatment("annotation")
        metrics = metric_for_role(request.theme_tokens, "annotation", request.font_metrics)
        font_size, line_height = treatment.font_size, treatment.line_height
        size = (measure_text_width(content, font_size=float(font_size), font_metrics=metrics,
            letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform),
            float(font_size) * float(line_height))
        text_id = f"relation-label:{placed_relation.relation_id.removeprefix('relation:')}"
        candidate = place_label(relation_label_anchor(placed_relation.points), size,
            ("above", "below", "start", "end"), bounds=timeline_rect, obstacles=obstacles,
            gap=max(1.0, float(font_size) * 0.25), required=False,
            overflow=request.surface_content.relation_overflow,
            classes=("mark", "text", "label-visual", "dependency-route"))
        if candidate is None:
            diagnostics.append(f"W_LAYOUT_RELATION_LABEL_SUPPRESSED:{placed_relation.relation_id}")
            continue
        placed_text = replace(place_text(placement_id=text_id, source_ref=placed_relation.source_ref,
            content=content, inline=candidate.bounds.x, baseline_block=candidate.bounds.y + float(font_size),
            typography_role="annotation", theme_tokens=request.theme_tokens,
            font_metrics=request.font_metrics, collision_region="relation-label",
            collision_domain=CollisionDomain("timeline", "overlay")),
            fallback_ladder=("above", "below", "start", "end"), selected_rung=candidate.side)
        relation_text.append(placed_text)
        inline, block, width, height = bounds_from_rect(placed_text.bounds)
        obstacles.add(SurfaceObstacle(placed_text.placement_id, "text", "timeline",
            ObstacleRect(inline, block, inline + width, block + height)))
        if candidate.visible_overflow:
            visible_overflows.append((placed_text, timeline_rect))
    return SurfaceRelationLabelsBatch(tuple(relation_text), tuple(diagnostics), tuple(visible_overflows))
