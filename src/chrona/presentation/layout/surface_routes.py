"""Owns dependency ports, routes and relation labels; reads completed marks and the shared obstacle index."""
from __future__ import annotations

from dataclasses import dataclass, replace
from math import hypot
import json
import re
from collections.abc import Callable
from typing import Any, Mapping

from chrona.presentation.layout.labels import LabelRect, place_label
from chrona.presentation.layout.model import LayoutError, Rect, geometry_sum
from chrona.presentation.layout.surface_mark_visibility import MarkOccurrence, MarkOccurrenceKind
from chrona.presentation.layout.window_relation_admission import complete_window_relation_endpoint_absence
from chrona.presentation.layout.window_relation_geometry import relation_geometry_inside_plot
from chrona.presentation.layout.mark_facet_visibility import FacetDisposition
from chrona.presentation.model.projection import WindowMode
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex, obstacles_intersect,
    segment_length_inside_rect, segment_overlap_length,
)
from chrona.presentation.layout.ports import (
    ConnectorEgress, connector_egress_candidates, stub_pairs_first,
)
from chrona.presentation.layout.presentation import TrackPlacement
from chrona.presentation.layout.relation_terminals import (
    centred_on_route, complete_centred_terminals, marker_geometry, orient_terminal, terminal_length, terminal_run,
)
from chrona.presentation.layout.routing import (
    RouteSuppressionEvidence, back_route_points, route_self_overlaps,
    remove_substroke_jogs, route_quality_metrics, select_relation_route,
)
from chrona.presentation.layout.route_reduction import simplify_relation_route, terminal_runs_preserved
from chrona.presentation.layout.relation_fan_in import (
    NodeApproach, complete_fan_in, same_port_arrivals, target_port_identity, terminal_style,
)
from chrona.presentation.layout.path_geometry import flatten_path, rounded_orthogonal_path
from chrona.presentation.layout.surface_geometry import bounds_from_rect
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, MarkPlacement, PaintClip, PathCommand, RelationPlacement, RowPlacement, ShapePlacement,
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
    plot_bounds: tuple[float, float, float, float] | None = None


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
    explicit_window = getattr(projection, "window_mode", None) == WindowMode.EXPLICIT
    visibility_index = getattr(request, "mark_visibility_index", None)
    if explicit_window and visibility_index is None:
        raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window",
                          detail="stage=relation-admission; reason=missing-visibility-index")
    window_affected = explicit_window and any(
        facet.disposition != FacetDisposition.CONTAINED
        for visibility in visibility_index.entries.values() for facet in visibility.facets)
    plot_clip = PaintClip(context.plot_bounds) if window_affected and context.plot_bounds is not None else None
    timeline_bounds = context.timeline_bounds
    marks = context.marks
    rows, groups = context.rows, context.groups
    diagnostics: list[str] = []
    relations: list[RelationPlacement] = []
    route_fallbacks: list[RelationPlacement] = []
    declared_order: dict[str, int] = {}
    node_segments: dict[str, list[NodeApproach]] = {}
    instance_anchors: dict[str, list[tuple[str, tuple[float, float]]]] = {}
    comparison_instances: set[str] = set()
    instance_rows: dict[str, str] = {}
    instance_occurrences: dict[str, MarkOccurrence] = {}
    omitted_folded_instances: dict[str, list[tuple[str, None]]] = {}
    row_edges: dict[str, tuple[float, float]] = {}
    for review_row, row in zip(context.review_rows, rows, strict=True):
        row_edges[review_row.row_id] = (float(row.bounds.block), float(row.bounds.block + row.bounds.block_size))
        fallback = (float(row.bounds.inline + row.bounds.inline_size),
                    float(row.bounds.block + row.bounds.block_size / 2))
        for item in review_row.items:
            instance_id = (f"{review_row.row_id}:{item.item_id or item.object_id}"
                           if projection.rows else item.object_id)
            instance_anchors.setdefault(item.object_id, []).append((instance_id, fallback))
            instance_rows[instance_id] = review_row.row_id
            if explicit_window:
                kind = (MarkOccurrenceKind.LANE_FINAL if projection.lane_membership is not None
                        else MarkOccurrenceKind.ROW if projection.rows else MarkOccurrenceKind.AUTO)
                instance_occurrences[instance_id] = MarkOccurrence(
                    kind, review_row.row_id if projection.rows else item.object_id,
                    item.item_id or item.object_id, item.object_id,
                    item.source_kind if projection.rows else "combined")
            if item.source_kind in COMPARISON_SOURCE_KINDS:
                comparison_instances.add(instance_id)
    for folded in getattr(projection, "folded_points", ()):
        instance_id = f"group-header:{folded.group_id}:{folded.item.item_id or folded.item.object_id}"
        mark = next((item for item in marks if item.placement_id == f"planned:{instance_id}"), None)
        if explicit_window:
            occurrence = MarkOccurrence(MarkOccurrenceKind.FOLDED, folded.group_id,
                folded.item.item_id or folded.item.object_id, folded.item.object_id, folded.item.source_kind)
            instance_occurrences[instance_id] = occurrence
            if mark is None:
                proof = complete_window_relation_endpoint_absence(occurrence, "at",
                    projection=projection, as_of=request.surface_content.as_of,
                    visibility_index=visibility_index)
                if proof is None:
                    raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/foldedPoints",
                                      detail="stage=relation-admission; reason=missing-completed-mark")
                # Keep relation identity, not a fabricated coordinate or a generic label anchor.
                omitted_folded_instances.setdefault(folded.item.object_id, []).append((instance_id, None))
                instance_rows[instance_id] = f"group-header:{folded.group_id}"
        if mark is not None:
            instance_anchors.setdefault(folded.item.object_id, []).append((instance_id, mark.end_port))
            instance_rows[instance_id] = f"group-header:{folded.group_id}"
    # A baseline ghost is a comparison mark, not a relation endpoint (#1031): connect the current plan marks only.
    # An object that has no plan instance at all (a snapshot-only explicit row) keeps its comparison instances.
    relation_anchors = {object_id: [entry for entry in entries if entry[0] not in comparison_instances] or entries
                        for object_id, entries in instance_anchors.items()}
    for object_id, entries in omitted_folded_instances.items():
        relation_anchors.setdefault(object_id, []).extend(entries)
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
    primary_marks = tuple(mark for mark in marks if mark.placement_id.startswith("planned:")
                          and ":snapshot:" not in mark.placement_id and ":scenario:" not in mark.placement_id)
    primary_interiors: dict[float, tuple[ObstacleRect, ...]] = {}

    def clears_primary_marks(points: tuple[tuple[float, float], ...], width: float) -> bool:
        """Reject positive-length crossings of any planned mark's stroked interior."""
        if width not in primary_interiors:
            inset = width / 2
            primary_interiors[width] = tuple(ObstacleRect(
                float(mark.bounds.inline) + inset, float(mark.bounds.block) + inset,
                float(mark.bounds.inline + mark.bounds.inline_size) - inset,
                float(mark.bounds.block + mark.bounds.block_size) - inset)
                for mark in primary_marks if float(mark.bounds.inline_size) > width
                and float(mark.bounds.block_size) > width)
        return all(segment_length_inside_rect(ObstacleSegment(left, right), rect) <= 1e-9
                   for left, right in zip(points, points[1:]) if left != right
                   for rect in primary_interiors[width])

    def relation_stroke(relation) -> float:
        return float(request.theme_tokens.number(semantic_binding(relation.semantic_id).theme_role, "strokeWidth"))

    def entry_stub_length(semantic_id: str) -> float:
        """Arrowhead plus clearance: the straight run a horizontal entry needs beside the port (#1030)."""
        theme = request.theme_tokens
        clearance = max(float(context.metric_values.get("timeline.relation.cornerRadius", 0)),
                        float(theme.number(semantic_binding(semantic_id).theme_role, "strokeWidth")))
        return terminal_length(marker_geometry(theme.marker("relationTargetTerminal"), stroke_width=float(
            theme.number(semantic_binding(semantic_id).theme_role, "strokeWidth")))) + clearance

    def entry_minimum(semantic_id: str) -> float:
        """The head is mandatory; a completed turn may clip its configured radius."""
        theme = request.theme_tokens
        return (terminal_length(marker_geometry(theme.marker("relationTargetTerminal"), stroke_width=float(
                theme.number(semantic_binding(semantic_id).theme_role, "strokeWidth"))))
                + float(theme.number(semantic_binding(semantic_id).theme_role, "strokeWidth")))

    def entry_stub_free(egress: ConnectorEgress) -> bool:
        """The stub lies in the timeline and crosses no mark, text or label (host marks exempt)."""
        end = egress.exposed_port[0]
        if end < timeline_bounds[0] or end > timeline_bounds[0] + timeline_bounds[2]:
            return False
        return not obstacles.egress_collisions(ObstacleSegment(*egress.corridor), host_ids=egress.host_ids,
            classes=route_classes, regions=("timeline", "group-header"))

    def entry_candidates(mark, endpoint, toward, cluster, relation, *, entry):
        preferred = entry_stub_length(relation.semantic_id) if entry in {"side", "side-when-free"} else 0.0
        candidates = connector_egress_candidates(mark, endpoint, toward, cluster, entry=entry,
            stub_length=preferred, stub_free=entry_stub_free)
        minimum = entry_minimum(relation.semantic_id)
        if preferred > minimum and not any(item.stub for item in candidates):
            # Preserve full-radius geometry whenever free. A tighter corridor may
            # still retain the entire head; path completion clips only the turn.
            candidates = connector_egress_candidates(mark, endpoint, toward, cluster, entry=entry,
                stub_length=minimum, stub_free=entry_stub_free)
        return candidates

    def enters_along(relation, points) -> bool:
        """The horizontal semantic entry retains the head and mandatory clearance."""
        if len(points) < 2 or points[-1][1] != points[-2][1]:
            return False
        starts = relation.target_endpoint in {"start", "at"}
        run = points[-1][0] - points[-2][0]
        return (run if starts else -run) + 1e-6 >= entry_minimum(relation.semantic_id)

    marker_start = centred_on_route(marker_geometry(request.theme_tokens.marker("relationSourceTerminal")), "source")
    marker_end = centred_on_route(marker_geometry(request.theme_tokens.marker("relationTargetTerminal")), "target")
    window_rejected = [False]

    def prepare_route(points, width, hosts, source_side, target_side, *,
                      start_minimum=0.0, end_minimum=0.0):
        def clear(path):
            return terminal_runs_preserved(tuple(points), path,
                start_minimum=start_minimum or None, end_minimum=end_minimum or None
                ) and clears_primary_marks(path, width) and all(not obstacles.egress_collisions(
                ObstacleSegment(a, b), host_ids=hosts, classes=route_classes,
                regions=("timeline", "group-header")) for a, b in zip(path, path[1:]) if a != b)
        reduced = remove_substroke_jogs(tuple(points), width, accept=clear)
        def clear_reduction(path):
            if route_self_overlaps(path) or not clear(path):
                return False
            drawn, start, end = complete_centred_terminals(path, marker_start, marker_end, width)
            if any(hypot(b[0] - a[0], b[1] - a[1]) + 1e-6 < width
                   for a, b in zip(drawn, drawn[1:])):
                return False
            return not any(marker is not None and marker.centred and marker.angle_degrees is not None
                for marker in (orient_terminal(start, drawn, source_side, source=True),
                               orient_terminal(end, drawn, target_side, source=False)))

        # Retain declared corridors and enough free stroke beyond round-head
        # setbacks, not the arbitrary length of the search's original legs.
        reduced = simplify_relation_route(reduced, clears=clear_reduction,
            start_minimum=max(start_minimum, width + (marker_start.head_length / 2
                if marker_start is not None and marker_start.centred else 0.0)),
            end_minimum=max(end_minimum, width + (marker_end.head_length / 2
                if marker_end is not None and marker_end.centred else 0.0)))
        drawn, start, end = complete_centred_terminals(reduced, marker_start, marker_end, width)
        # A round head's reference offset makes its centre axis-sensitive too.
        # If a short tangent disagrees with its port normal, try removing just
        # that terminal jog, then try another port instead of detaching the head.
        first = orient_terminal(start, drawn, source_side, source=True)
        last = orient_terminal(end, drawn, target_side, source=False)
        start_limit = (start.head_length * 1.5 if start is not None and start.centred
                       and first.angle_degrees is not None else 0.0)
        end_limit = (end.head_length * 1.5 if end is not None and end.centred
                     and last.angle_degrees is not None else 0.0)
        if start_limit or end_limit:
            reduced = remove_substroke_jogs(reduced, width, accept=clear,
                start_minimum=start_limit, end_minimum=end_limit)
            drawn, start, end = complete_centred_terminals(reduced, marker_start, marker_end, width)
            first = orient_terminal(start, drawn, source_side, source=True)
            last = orient_terminal(end, drawn, target_side, source=False)
            if any(marker is not None and marker.centred and marker.angle_degrees is not None
                   for marker in (first, last)):
                return None
        if plot_clip is not None and not relation_geometry_inside_plot(plot_clip, drawn,
                marker_start=first, marker_end=last, stroke_width=width):
            window_rejected[0] = True
            return None
        return reduced

    def terminal_segments_fit(points, width):
        drawn, _, _ = complete_centred_terminals(tuple(points), marker_start, marker_end, width)
        return len(drawn) >= 2 and all(hypot(b[0] - a[0], b[1] - a[1]) + 1e-6 >= width
                                      for a, b in zip(drawn, drawn[1:]))

    def target_port(relation, target_id, mark, egress):
        return target_port_identity(target_id, relation.target_endpoint, egress.side,
                                    point=mark is not None and mark.mark_shape == "point")

    def shared_approach(source_id, target_id, points, *, port_id=None, paint_id="", terminal=None):
        return any(segment_overlap_length(candidate.segment, previous.segment) > 1e-9
                   and not same_port_arrivals(candidate, previous)
                   for node, candidate in (
                       (source_id, NodeApproach("", (points[0], points[1]))),
                       (target_id, NodeApproach("", (points[-2], points[-1]), port_id,
                                                paint_id, terminal_style(terminal))))
                   for previous in node_segments.get(node, ()))

    def routing_order(declared):
        """Stable arrivals-before-departures; cyclic remainder keeps declaration order."""
        indegree, followers = {}, {}
        for item in declared:
            source, target = str(item.source_object_id), str(item.target_object_id)
            indegree.setdefault(source, 0)
            indegree[target] = indegree.get(target, 0) + 1
            followers.setdefault(source, []).append(target)
        ready = [node for node in indegree if not indegree[node]]
        rank = {}
        for node in ready:
            rank[node] = len(rank)
            for target in followers.get(node, ()):
                indegree[target] -= 1
                if not indegree[target]:
                    ready.append(target)
        return sorted(enumerate(declared), key=lambda pair:
                      rank.get(str(pair[1].target_object_id), len(rank)))

    back_route_reason = [""]

    def back_route(relation, source_mark, target_mark, source_id, target_id, source_nominal):
        """`entry: side` (#1060): a target the source does not approach from the entry side is entered through the
        gap between the rows. Returns (egress pair, points) or None when it does not fit; the order then falls back,
        and `back_route_reason` names why (reported with the fallback diagnostic)."""
        def fail(reason: str):
            back_route_reason[0] = reason
            return None

        back_route_reason[0] = ""
        endpoint = relation.target_endpoint
        if (context.layout_manifest.relation_entry != "side" or source_mark is None or target_mark is None
                or endpoint not in {"start", "at", "finish", "end"}):
            return None
        starts = endpoint in {"start", "at"}
        bounds = target_mark.bounds
        source_edges, target_edges = row_edges.get(instance_rows.get(source_id, "")), row_edges.get(instance_rows.get(target_id, ""))
        if source_edges is None or target_edges is None or source_edges == target_edges:
            return fail("same-row")
        below = target_edges[0] > source_edges[0]
        gap_y = target_edges[0] if below else target_edges[1]
        far = (-1e9 if starts else 1e9, float(bounds.block))
        stub = next((item for item in entry_candidates(target_mark, endpoint, far,
            comparison_clusters.get((target_mark.source_ref, instance_rows[target_id]), ()), relation, entry="side")
            if item.exposed_port != item.semantic_port and item.side == ("start" if starts else "end")), None)
        if stub is None:
            return fail("entry-stub-blocked")
        width = relation_stroke(relation)
        source_run = terminal_length(marker_start) + max(width,
            float(context.metric_values.get("timeline.relation.cornerRadius", 0)))
        exits = connector_egress_candidates(source_mark, relation.source_endpoint, stub.semantic_port,
            comparison_clusters.get((source_mark.source_ref, instance_rows[source_id]), ()))
        best, chosen = None, None
        for source_exit in exits:
            dx, dy = {"start": (-1, 0), "end": (1, 0), "above": (0, -1), "below": (0, 1)}[source_exit.side]
            port = source_exit.semantic_port
            exposed = source_exit.exposed_port
            out = (exposed[0] + dx * source_run, exposed[1] + dy * source_run)
            raw = (port, exposed, *back_route_points(out, 0.0, gap_y, stub.exposed_port, stub.semantic_port))
            raw = tuple(point for index, point in enumerate(raw) if not index or point != raw[index - 1])
            hosts = (*stub.host_ids, *source_exit.host_ids)
            start_minimum = hypot(out[0] - port[0], out[1] - port[1])
            end_minimum = hypot(stub.exposed_port[0] - stub.semantic_port[0],
                                stub.exposed_port[1] - stub.semantic_port[1])
            points = prepare_route(raw, width, hosts, source_exit.side, stub.side,
                start_minimum=start_minimum, end_minimum=end_minimum)
            if points is None:
                fail("terminal-axis-blocked")
                continue
            if not terminal_segments_fit(points, width):
                fail("sub-stroke-segment")
                continue
            if len(points) < 3:
                fail("degenerate")
                continue
            # Shortest path retaining the two completed corridors (#1084).
            reference = (start_minimum + abs(out[0] - stub.exposed_port[0])
                         + abs(out[1] - stub.exposed_port[1]) + end_minimum)
            length, _, bends = route_quality_metrics(points)
            if (bends > context.layout_manifest.relation_max_bends or route_self_overlaps(points)
                    or length > reference * context.layout_manifest.relation_max_detour_ratio):
                fail("bends-or-detour")
                continue
            if any(not (timeline_bounds[0] <= p[0] <= timeline_bounds[0] + timeline_bounds[2]
                        and route_top <= p[1] <= route_bottom) for p in points):
                fail("entry-stub-blocked")
                continue
            blockers = tuple(hit for left_, right_ in zip(points, points[1:]) if left_ != right_
                for hit in obstacles.egress_collisions(ObstacleSegment(left_, right_), host_ids=hosts,
                    classes=route_classes, regions=("timeline", "group-header")))
            if blockers:
                fail("blocked:" + ",".join(sorted({item.obstacle_class + "=" + item.placement_id
                                                  for item in blockers}))[:200])
                continue
            if not clears_primary_marks(points, width):
                fail("primary-mark-blocked")
                continue
            completed, _, completed_end = complete_centred_terminals(points, marker_start, marker_end, width)
            score = (shared_approach(source_id, target_id, completed,
                port_id=target_port(relation, target_id, target_mark, stub),
                paint_id=relation.semantic_id, terminal=completed_end), bends, length)
            if best is None or score < best:
                best = score
                chosen = ((source_exit, stub), points)
        if chosen is not None:
            back_route_reason[0] = ""
        return chosen

    for declared_index, relation in routing_order(request.surface_content.relations):
        source, target, relation_id = relation.source_object_id, relation.target_object_id, relation.relation_id
        dependency_stroke = relation_stroke(relation)
        marker_start = centred_on_route(marker_geometry(
            request.theme_tokens.marker("relationSourceTerminal"), stroke_width=dependency_stroke), "source")
        marker_end = centred_on_route(marker_geometry(
            request.theme_tokens.marker("relationTargetTerminal"), stroke_width=dependency_stroke), "target")
        for source_id, source_anchor in relation_anchors.get(str(source), ()):
            for target_id, target_anchor in relation_anchors.get(str(target), ()):
                window_rejected[0] = False
                source_mark, target_mark = relation_marks.get(source_id), relation_marks.get(target_id)
                scene_id = (f"relation:{relation_id}:{source_id}:{target_id}"
                            if projection.rows else f"relation:{relation_id}")
                declared_order[scene_id] = declared_index
                if explicit_window:
                    proofs = tuple(proof for instance, endpoint in (
                        (source_id, relation.source_endpoint), (target_id, relation.target_endpoint))
                        if (proof := complete_window_relation_endpoint_absence(
                            instance_occurrences[instance], endpoint, projection=projection,
                            as_of=request.surface_content.as_of, visibility_index=visibility_index)) is not None)
                    if proofs:
                        relations.append(RelationPlacement(scene_id,
                            f"{source_id}:{relation.source_endpoint}", f"{target_id}:{relation.target_endpoint}",
                            suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED",
                            semantic_id=relation.semantic_id, source_ref=relation_id,
                            from_instance_id=source_id, to_instance_id=target_id,
                            window_endpoint_absences=proofs, window_suppression_reason="outside-window"))
                        diagnostics.append(f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}")
                        continue
                if window_affected and plot_clip is None:
                    raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window",
                                      detail="stage=routing; reason=missing-completed-plot")
                source_nominal = (source_mark.start_port if relation.source_endpoint in {"start", "at"}
                                  else source_mark.end_port) if source_mark else source_anchor
                target_nominal = (target_mark.start_port if relation.target_endpoint in {"start", "at"}
                                  else target_mark.end_port) if target_mark else target_anchor
                source_candidates = (connector_egress_candidates(source_mark, relation.source_endpoint,
                    target_nominal, comparison_clusters.get((source_mark.source_ref,
                        instance_rows[source_id]), ())) if source_mark else
                    (ConnectorEgress(relation.source_endpoint, source_nominal, source_nominal, ()),))
                target_candidates = (entry_candidates(target_mark, relation.target_endpoint,
                    source_nominal, comparison_clusters.get((target_mark.source_ref,
                        instance_rows[target_id]), ()), relation, entry=context.layout_manifest.relation_entry) if target_mark else
                    (ConnectorEgress(relation.target_endpoint, target_nominal, target_nominal, ()),))
                port_pairs = tuple((left, right) for left in source_candidates for right in target_candidates)
                if context.layout_manifest.relation_entry in {"side-when-free", "side"}:
                    # #1072: every exit of the source is tried with the horizontal entry before any other entry
                    port_pairs = stub_pairs_first(port_pairs)
                selected_pair: tuple[ConnectorEgress, ConnectorEgress] | None = None
                points: tuple[tuple[float, float], ...] = ()
                lane_selection = None
                def candidate_rank(candidate, source_exit, target_entry):
                    completed, _, completed_end = complete_centred_terminals(candidate, marker_start, marker_end, dependency_stroke)
                    policy = context.layout_manifest.relation_entry
                    entry_penalty = int((policy == "side-when-free" and not target_entry.stub)
                                        or (policy == "side" and not enters_along(relation, candidate)))
                    length, _, bends = route_quality_metrics(candidate)
                    return (shared_approach(source_id, target_id, completed,
                        port_id=target_port(relation, target_id, target_mark, target_entry),
                        paint_id=relation.semantic_id, terminal=completed_end), entry_penalty, bends, length)

                selection = select_relation_route(port_pairs, obstacles=obstacles,
                        bounds=((plot_clip.bounds[0], plot_clip.bounds[1],
                                 plot_clip.bounds[0] + plot_clip.bounds[2], plot_clip.bounds[1] + plot_clip.bounds[3])
                                if plot_clip is not None else
                                (timeline_bounds[0], route_top, timeline_bounds[0] + timeline_bounds[2], route_bottom)),
                        source_host_id=source_mark.placement_id if source_mark else None,
                        target_host_id=target_mark.placement_id if target_mark else None,
                        relation_scene_id=scene_id, max_bends=context.layout_manifest.relation_max_bends,
                        max_detour_ratio=context.layout_manifest.relation_max_detour_ratio, classes=route_classes,
                        prepare=lambda candidate, source_exit, target_entry: prepare_route(candidate, dependency_stroke,
                            (*source_exit.host_ids, *target_entry.host_ids), source_exit.side, target_entry.side,
                            start_minimum=hypot(source_exit.exposed_port[0] - source_exit.semantic_port[0],
                                                source_exit.exposed_port[1] - source_exit.semantic_port[1]),
                            end_minimum=hypot(target_entry.exposed_port[0] - target_entry.semantic_port[0],
                                              target_entry.exposed_port[1] - target_entry.semantic_port[1])),
                        accept=lambda candidate: clears_primary_marks(candidate, dependency_stroke)
                            and terminal_segments_fit(candidate, dependency_stroke), rank=candidate_rank)
                selected_pair, points = selection.selected_pair, selection.points
                if projection.lane_membership is not None:
                    lane_selection = selection
                if (context.layout_manifest.relation_entry == "side" and target_mark is not None
                        and not (selected_pair is not None and enters_along(relation, points))):
                    # #1060/#1084: the forward side entry did not give a horizontal entry; try the back-route
                    backed = back_route(relation, source_mark, target_mark, source_id, target_id, source_nominal)
                    if backed is not None:
                        back_rank = candidate_rank(backed[1], *backed[0])
                        forward_rank = (candidate_rank(points, *selected_pair)
                                        if selected_pair is not None else None)
                        if forward_rank is None or back_rank < forward_rank:
                            selected_pair, points = backed
                            lane_selection = None
                        elif back_rank[0] and not forward_rank[0]:
                            back_route_reason[0] = "node-approach-conflict"
                fallback = selected_pair is None
                if fallback:
                    if request.surface_content.relation_overflow == "suppress":
                        relations.append(RelationPlacement(scene_id,
                            f"{source_id}:{relation.source_endpoint}", f"{target_id}:{relation.target_endpoint}",
                            suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED",
                            semantic_id=relation.semantic_id if window_rejected[0] else "dependency",
                            source_ref=relation_id if window_rejected[0] else "",
                            from_instance_id=source_id if window_rejected[0] else None,
                            to_instance_id=target_id if window_rejected[0] else None,
                            window_suppression_reason="plot-containment" if window_rejected[0] else None))
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
                    if (not clears_primary_marks(points, dependency_stroke)
                            or not terminal_segments_fit(points, dependency_stroke)):
                        relations.append(RelationPlacement(scene_id,
                            f"{source_id}:{relation.source_endpoint}", f"{target_id}:{relation.target_endpoint}",
                            suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED"))
                        cause = ("I_LAYOUT_RELATION_MARK_BLOCKED" if not clears_primary_marks(points, dependency_stroke)
                                 else "I_LAYOUT_RELATION_SEGMENT_TOO_SHORT")
                        diagnostics.extend((f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}", f"{cause}:{scene_id}"))
                        if lane_selection is not None:
                            diagnostics.append(RouteSuppressionEvidence(scene_id, lane_selection.attempts).diagnostic)
                        continue
                    if lane_selection is not None and not _lane_fallback_clears_required_labels(points, context.text):
                        relations.append(RelationPlacement(scene_id,
                            f"{source_id}:{relation.source_endpoint}", f"{target_id}:{relation.target_endpoint}",
                            suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED"))
                        diagnostics.append(f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}")
                        diagnostics.append(RouteSuppressionEvidence(scene_id, lane_selection.attempts).diagnostic)
                        continue
                source_egress, target_egress = selected_pair
                source_port_id = f"{source_id}:{relation.source_endpoint}:{source_egress.side}"
                target_port_id = target_port(relation, target_id, target_mark, target_egress)
                radius = float(context.metric_values.get("timeline.relation.cornerRadius", 0))
                # Entry eligibility concerns the complete semantic corridor,
                # including the part subsequently occupied by a round head.
                side_entry_satisfied = enters_along(relation, points)
                points, completed_start, completed_end = complete_centred_terminals(
                    tuple(points), marker_start, marker_end, dependency_stroke)
                completed_start = orient_terminal(completed_start, points, source_egress.side, source=True)
                completed_end = orient_terminal(completed_end, points, target_egress.side, source=False)
                arc_blocked = corner_arc_blocker(obstacles, frozenset((*source_egress.host_ids, *target_egress.host_ids)),
                                                 dependency_stroke, route_classes)

                placed = RelationPlacement(scene_id, source_port_id, target_port_id, tuple(points),
                    semantic_id=relation.semantic_id, corner_radius=radius,
                    path_commands=(rounded_orthogonal_path(tuple(points), radius,
                        start_run=terminal_run(marker_start),
                        end_run=terminal_run(marker_end),
                        blocked=lambda arc: arc_blocked(arc) or not clears_primary_marks(arc, dependency_stroke))
                        if radius > 0 and not fallback else ()),
                    marker_start=completed_start, marker_end=completed_end,
                    label_content=relation_label_content(relation), source_ref=relation_id,
                    from_instance_id=source_id, to_instance_id=target_id, paint_clip=plot_clip)
                if plot_clip is not None and not relation_geometry_inside_plot(plot_clip, placed.points,
                        path_commands=placed.path_commands, marker_start=placed.marker_start,
                        marker_end=placed.marker_end, stroke_width=dependency_stroke):
                    relations.append(RelationPlacement(scene_id, source_port_id, target_port_id,
                        suppressed=True, diagnostic="W_LAYOUT_RELATION_SUPPRESSED",
                        semantic_id=relation.semantic_id, source_ref=relation_id,
                        from_instance_id=source_id, to_instance_id=target_id,
                        window_suppression_reason="plot-containment"))
                    diagnostics.append(f"W_LAYOUT_RELATION_SUPPRESSED:{scene_id}")
                    continue
                for mark, side, port in ((source_mark, source_egress.side, source_egress.exposed_port),
                                        (target_mark, target_egress.side, target_egress.exposed_port)):
                    obstacle_id = f"port:{mark.placement_id if mark else scene_id}:{side}"
                    if not obstacles.has(obstacle_id):
                        register_port(obstacle_id, port)
                relations.append(placed)
                node_segments.setdefault(source_id, []).append(NodeApproach(scene_id, (points[0], points[1])))
                node_segments.setdefault(target_id, []).append(NodeApproach(scene_id, (points[-2], points[-1]),
                    target_port_id, relation.semantic_id, terminal_style(completed_end)))
                if (context.layout_manifest.relation_entry == "side" and target_mark is not None
                        and relation.target_endpoint in {"start", "at", "finish", "end"} and len(points) >= 2
                        and not side_entry_satisfied):
                    # #1060: with `entry: side` a relation that still does not enter along the bar is reported
                    diagnostics.append(f"I_LAYOUT_RELATION_ENTRY_FALLBACK:{scene_id};reason={back_route_reason[0] or 'forward-entry-failed'}")
                dependency_role = semantic_binding(placed.semantic_id).theme_role
                register_path(scene_id, placed.points,
                    float(request.theme_tokens.number(dependency_role, "strokeWidth")), placed.path_commands)
                if fallback:
                    route_fallbacks.append(placed)

    for node, segments in node_segments.items():
        explained = set()
        for index, first in enumerate(segments):
            for second in segments[index + 1:]:
                first_id, second_id = first.relation_id, second.relation_id
                pair = tuple(sorted((first_id, second_id)))
                if (first_id != second_id and pair not in explained
                        and not same_port_arrivals(first, second)
                        and segment_overlap_length(first.segment, second.segment) > 1e-9):
                    diagnostics.append("I_LAYOUT_RELATION_NODE_APPROACH_SHARED:" + json.dumps({
                        "nodeInstanceId": node, "relationIds": pair, "reason": "terminal-corridor-shared"},
                        sort_keys=True, separators=(",", ":")))
                    explained.add(pair)
    relations.sort(key=lambda item: declared_order[item.relation_id])
    completed_relations = complete_fan_in(tuple(relations))
    fallback_ids = {item.relation_id for item in route_fallbacks}
    return SurfaceRoutesBatch(completed_relations,
        tuple(item for item in completed_relations if item.relation_id in fallback_ids),
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
            search_side_neighborhood=True,
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
