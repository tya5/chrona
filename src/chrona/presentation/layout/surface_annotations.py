"""Owns annotation boxes, text, visuals and connectors; reads completed marks, rows and slots and searches the one obstacle index."""

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from collections.abc import Mapping
from math import isfinite
from typing import Any, Callable

from chrona.presentation.layout.model import LayoutError, Rect, geometry_sum
from chrona.presentation.layout.surface_marks import (
    folded_instance_id as _folded_instance_id,
)
from chrona.presentation.layout.surface_visuals import (
    measure_candidate_visuals,
)
from chrona.presentation.model.semantic_registry import (
    semantic_binding)
from chrona.presentation.layout.text import measure_text_width, place_text, wrap_text
from chrona.presentation.layout.annotations import (
    AnnotationBox, annotation_rail_candidates, nearest_box_port, project_annotation_box,
    resolve_annotation_anchor,
)
from chrona.presentation.layout.annotation_search import (
    nearest_free_box, nearest_free_tail_box, nearest_free_routed_tail_box,
)
from chrona.presentation.layout.annotation_artwork import place_artwork
from chrona.presentation.layout.annotation_border import NO_BORDER, place_border, resolve_border
from chrona.presentation.layout.rounded_outline import (
    CORNER_CLEARANCE, clamp_radius, commands_points, resolve_corner_radius, rounded_rect_commands,
)
from chrona.presentation.layout.annotation_inline_size import fill_note, fill_target
from chrona.presentation.layout.viewer_fit import fit_text, require_followable_content
from chrona.presentation.model.theme_tokens import ViewerFitToken
from chrona.presentation.layout.annotation_kind_frame import EMPTY_FRAME, measure_kind_frame, place_kind_frame
from chrona.presentation.layout.annotation_tilt import (
    nearest_boundary_point, rotate_commands, polygon_commands, rotate_shape, rotate_text, rotated_corners, rotated_extent, tilt_for,
)
from chrona.presentation.layout.balloon_geometry import balloon_outline
from chrona.presentation.layout.labels import LabelPlacement
from chrona.presentation.layout.annotation_topology import (
    AnnotationRouteTrial, local_route_bounds, route_annotation_candidate, visible_segments,
)
from chrona.presentation.layout.comparison_marks import ComparisonMark
from chrona.presentation.layout.labels import (
    LabelRect, place_label,
)
from chrona.presentation.layout.obstacles import (
    ObstacleRect, ObstacleSegment, SurfaceObstacle, SurfaceObstacleIndex,
)
from chrona.presentation.layout.ports import ConnectorEgress, coincident_endpoint_port_ids, connector_egress_candidates
from chrona.presentation.model.placement_candidates import candidate_order
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.routing import (
    relation_route_quality,
)
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, MarkPlacement, PathCommand, PlacementDecision, RelationPlacement, RowPlacement, ScalePlacement,
    IconPlacement, LayoutImageFill, ShapePlacement, SurfaceLayoutRequest,
    SlotPlacement, TextPlacement, annotation_presentation,
)
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject
from chrona.presentation.layout.image_slice_geometry import image_slice_tiles
from chrona.presentation.layout.surface_geometry import (
    HOSTED_TEXT_PAINT_ORDER,
    bounds_from_rect as _bounds, coordinate_for_date as _coordinate,
)


ANNOTATION_PAINT_ORDER = 400


def _anchor_operand(value: object) -> str:
    """Keep one diagnostic operand bounded without shortening its source pointer."""
    return repr(value).replace("\n", " ").replace("\r", " ")[:96]


def _anchor_failure(annotation: Any, reason: str, *, code: str = "E_PRESENTATION_ANCHOR_MISSING",
                    **operands: object) -> LayoutError:
    """Attach a post-resolution anchor failure to its declared View source."""
    anchor = annotation.anchor
    values = {
        "annotation_id": annotation.annotation_id,
        "object_id": anchor.get("id"),
        "facet": anchor.get("facet"),
        "endpoint": anchor.get("endpoint"),
        **operands,
    }
    fields = []
    for name, value in values.items():
        fields.append(f"{name}={_anchor_operand(value)}")
    return LayoutError(code, annotation.anchor_source_ref, detail=f"{reason}: " + ", ".join(fields))


def _annotation_icon_subjects(annotation: Any) -> tuple[DiagnosticSubject, ...]:
    """Keep visual provenance tied to the normalized Project-object claim."""
    if not annotation.subject_id:
        return ()
    return (DiagnosticSubject.project_object(annotation.subject_id, annotation.subject or None),)


def _container_radius(value: Any, container: Any, text_size: float,
                      width: float, height: float) -> float:
    """Resolve a Theme role's physical radius, preserving the container's old em rule when absent."""
    legacy = (clamp_radius(float(container.corner_radius) * text_size, width, height)
              if container is not None else 0.0)
    return resolve_corner_radius(value, width=width, height=height, legacy_radius=legacy)


def _radius_aware_box_port(box: LabelRect, target: tuple[float, float], radius: float) -> tuple[float, float]:
    """Choose the nearest point on a straight edge run of a rounded rectangle."""
    if radius <= 0:
        return nearest_box_port(box, target)
    x, y = target
    r = min(radius, box.width / 2, box.height / 2)
    ports = ((min(max(x, box.x + r), box.right - r), box.y),
             (min(max(x, box.x + r), box.right - r), box.bottom),
             (box.right, min(max(y, box.y + r), box.bottom - r)),
             (box.x, min(max(y, box.y + r), box.bottom - r)))
    return min(ports, key=lambda port: (abs(port[0] - x) + abs(port[1] - y), ports.index(port)))


def _capsule_axis_radius(size: float, before: float, after: float) -> float:
    """Solve ``r = (content + max(before, kr) + max(after, kr)) / 2`` by its three linear regions."""
    k = CORNER_CLEARANCE
    content = max(0.0, size - before - after)
    low, high = sorted((before, after))
    candidates = (
        ((content + before + after) / 2, low / k),
        ((content + high) / (2 - k), high / k),
        (content / (2 - 2 * k), float("inf")),
    )
    lower = 0.0
    for radius, upper in candidates:
        if lower - 1e-9 <= radius <= upper + 1e-9:
            return max(0.0, radius)
        lower = upper
    return max(0.0, candidates[-1][0])


def _physical_radius_clearance(value: Any, width: float, height: float,
                               insets: tuple[float, float, float, float]) -> float:
    """A finite text inset that keeps content on paper for the completed physical radius."""
    if value == "capsule":
        top, right, bottom, left = insets
        radius = min(_capsule_axis_radius(width, left, right),
                     _capsule_axis_radius(height, top, bottom))
        return CORNER_CLEARANCE * radius
    # The actual radius can only be clamped below the declared px value, so this
    # requested-radius clearance is conservative for every eventual box size.
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)) or value < 0:
        raise ValueError("Corner radius requires finite nonnegative px or capsule")
    return CORNER_CLEARANCE * float(value)


def _is_annotation_list_candidate(candidate: Any) -> bool:
    """Whether this selected candidate places its text in the declared note list."""
    region = candidate.region
    if region.kind == "slot":
        return region.source == "annotations"
    if region.kind == "intersection":
        return any(
            _is_annotation_list_candidate(replace(candidate, region=member))
            for member in region.members
        )
    return False


@dataclass(frozen=True)
class SurfaceAnnotationContext:
    request: SurfaceLayoutRequest
    projection: Any
    layout_manifest: Any
    contract: Any
    review_rows: tuple[Any, ...]
    rows: tuple[RowPlacement, ...]
    by_source: Mapping[str, SlotPlacement]
    scale: ScalePlacement
    start: date
    end: date
    timeline: SlotPlacement
    timeline_bounds: tuple[float, float, float, float]
    mark_by_id: Mapping[str, MarkPlacement]
    comparison_clusters: Mapping[Any, Any]
    instance_rows: Mapping[str, str]
    metric_for: Callable[[str], Any]
    surface_obstacles: SurfaceObstacleIndex
    register_rect: Callable[[str, str, str, Rect], None]
    register_port: Callable[[str, tuple[float, float], str], None]


@dataclass(frozen=True)
class SurfaceAnnotationBatch:
    text: tuple[TextPlacement, ...]
    shapes: tuple[ShapePlacement, ...]
    relations: tuple[RelationPlacement, ...]
    icons: tuple[IconPlacement, ...]
    decisions: tuple[PlacementDecision, ...]
    diagnostics: tuple[str, ...]
    visible_label_overflows: tuple[Any, ...]
    visible_route_fallbacks: tuple[RelationPlacement, ...]
    handled_visual_sources: frozenset[str]
    suppressed_index_ids: frozenset[str]
    suppressed_callout_ids: frozenset[str]
    diagnostic_provenance: tuple[DiagnosticProvenance, ...] = ()


def place_annotations(context: SurfaceAnnotationContext) -> SurfaceAnnotationBatch:
    """Place annotations, reflowing a declared note list after monotone suppressions."""
    annotations = context.request.surface_content.annotations
    if context.by_source.get("annotations") is None or not annotations:
        return _place_annotations_once(context, frozenset(), frozenset())

    suppressed_indexes: frozenset[str] = frozenset()
    suppressed_callouts: frozenset[str] = frozenset()
    limit = 2 * len(annotations) + 1
    original_index = context.surface_obstacles
    original_ids = {item.placement_id for item in original_index.all()}
    final_index: SurfaceObstacleIndex | None = None
    batch: SurfaceAnnotationBatch | None = None

    for _ in range(limit):
        working_index = original_index.copy()

        def register_rect(placement_id: str, obstacle_class: str, region_id: str, bounds: Rect) -> None:
            inline, block, inline_size, block_size = _bounds(bounds)
            if inline_size > 0 and block_size > 0:
                working_index.add(SurfaceObstacle(
                    placement_id, obstacle_class, region_id,
                    ObstacleRect(inline, block, inline + inline_size, block + block_size)))

        def register_port(placement_id: str, point: tuple[float, float], region_id: str) -> None:
            working_index.add(SurfaceObstacle(
                placement_id, "port", region_id,
                ObstacleRect(point[0] - 0.01, point[1] - 0.01,
                             point[0] + 0.01, point[1] + 0.01)))

        working_context = replace(context, surface_obstacles=working_index,
                                   register_rect=register_rect, register_port=register_port)
        batch = _place_annotations_once(working_context, suppressed_indexes, suppressed_callouts)
        discovered_indexes = suppressed_indexes | batch.suppressed_index_ids
        discovered_callouts = suppressed_callouts | batch.suppressed_callout_ids
        if discovered_indexes == suppressed_indexes and discovered_callouts == suppressed_callouts:
            final_index = working_index
            break
        # Union with the current sets makes every retry a strict, finite growth
        # step; each identity can be added only once per suppression class.
        assert (len(discovered_indexes) + len(discovered_callouts)
                > len(suppressed_indexes) + len(suppressed_callouts))
        suppressed_indexes, suppressed_callouts = discovered_indexes, discovered_callouts
    else:
        raise AssertionError("annotation list reflow exceeded its finite suppression bound")

    assert batch is not None and final_index is not None
    for obstacle in final_index.all():
        if obstacle.placement_id not in original_ids:
            original_index.add(obstacle)
    return batch


def _place_annotations_once(context: SurfaceAnnotationContext,
                            suppressed_index_ids: frozenset[str],
                            suppressed_callout_ids: frozenset[str]) -> SurfaceAnnotationBatch:
    """Place every annotation box, its text, visuals and connector; the obstacle index is the only shared state."""
    request, projection, layout_manifest, contract = context.request, context.projection, context.layout_manifest, context.contract
    review_rows, rows, by_source, scale = context.review_rows, context.rows, context.by_source, context.scale
    start, end, timeline, timeline_bounds = context.start, context.end, context.timeline, context.timeline_bounds
    mark_by_id, comparison_clusters, instance_rows = context.mark_by_id, context.comparison_clusters, context.instance_rows
    metric_for, surface_obstacles = context.metric_for, context.surface_obstacles
    register_rect, register_port = context.register_rect, context.register_port
    text: list[TextPlacement] = []
    shapes: list[ShapePlacement] = []
    relations: list[RelationPlacement] = []
    candidate_icons: list[IconPlacement] = []
    placement_decisions: list[PlacementDecision] = []
    diagnostics: list[str] = []
    diagnostic_provenance: list[DiagnosticProvenance] = []
    visible_label_overflows: list[Any] = []
    visible_route_fallbacks: list[RelationPlacement] = []
    handled_candidate_visuals: set[str] = set()
    discovered_index_suppressions = set(suppressed_index_ids)
    discovered_callout_suppressions = set(suppressed_callout_ids)
    annotation_slot = by_source.get("annotations")
    annotation_slot_id = annotation_slot.slot_id if annotation_slot is not None else ""
    rail_records: list[TextPlacement] = []
    # Full callout footprints govern exhausted-rail completion, independently
    # of the numbered list's ordering and its body-only text records.
    rail_boxes: list[LabelRect] = []

    def add_diagnostic(value: str, annotation: Any) -> None:
        diagnostics.append(value)
        # `subject_id` is set only when normalized View annotation ingress
        # resolved its explicit Project-object anchor.
        if annotation.subject_id:
            diagnostic_provenance.append(DiagnosticProvenance(value, (
                DiagnosticSubject.project_object(annotation.subject_id, annotation.subject or None),)))

    def ordered_rail_candidates(annotation: Any, resolved: Any, *, anchor_y: float,
                                text_size: tuple[float, float], rail: LabelRect,
                                allow_inline_overflow: bool = False) -> tuple[AnnotationBox, ...]:
        """Enumerate free rail boxes at or below the preceding completed list entry."""
        previous_bottom = max(
            (float(item.bounds.block + item.bounds.block_size) for item in rail_records),
            default=rail.y)
        height = text_size[1]
        candidates = annotation_rail_candidates(
            annotation, resolved, anchor_y=max(anchor_y, previous_bottom + height / 2),
            text_size=text_size, rail=rail, obstacles=surface_obstacles,
            allow_inline_overflow=allow_inline_overflow)
        return tuple(candidate for candidate in candidates
                     if candidate.placement.bounds.y >= previous_bottom)

    def complete_list_record(*, annotation: Any, resolved: Any, placement_id: str,
                             content: str, lines: tuple[str, ...], text_size: tuple[float, float],
                             font_size: float, typography_role: str,
                             presentation: Any, anchor_y: float) -> tuple[TextPlacement, bool]:
        """Place a finalized list record, stacking explicitly when the slot cannot fit it."""
        assert annotation_slot is not None
        rail = LabelRect(*_bounds(annotation_slot.bounds))
        previous_bottom = max(
            (float(item.bounds.block + item.bounds.block_size) for item in rail_records),
            default=rail.y)
        candidates = ordered_rail_candidates(
            annotation, resolved, anchor_y=anchor_y, text_size=text_size,
            rail=rail)
        placed: TextPlacement | None = None
        for candidate_box in candidates:
            bounds = candidate_box.placement.bounds
            trial = place_text(
                placement_id=placement_id, source_ref=annotation.annotation_id,
                content=content, inline=bounds.x, baseline_block=bounds.y + font_size,
                typography_role=typography_role, theme_tokens=request.theme_tokens,
                font_metrics=request.font_metrics, collision_region="annotations",
                collision_domain=CollisionDomain(annotation_slot_id, "content"),
                lines=lines, semantic_id="annotationListText", annotation=presentation)
            fits_slot = (
                rail.x <= float(trial.bounds.inline)
                and float(trial.bounds.inline + trial.bounds.inline_size) <= rail.right
                and rail.y <= float(trial.bounds.block)
                and float(trial.bounds.block + trial.bounds.block_size) <= rail.bottom
            )
            if fits_slot and not surface_obstacles.collisions(ObstacleRect(
                    float(trial.bounds.inline), float(trial.bounds.block),
                    float(trial.bounds.inline + trial.bounds.inline_size),
                    float(trial.bounds.block + trial.bounds.block_size))):
                placed = trial
                break
        overflow = placed is None
        if placed is None:
            bounds = LabelRect(rail.x, previous_bottom, text_size[0], text_size[1])
            placed = place_text(
                placement_id=placement_id, source_ref=annotation.annotation_id,
                content=content, inline=bounds.x, baseline_block=bounds.y + font_size,
                typography_role=typography_role, theme_tokens=request.theme_tokens,
                font_metrics=request.font_metrics, collision_region="annotations",
                collision_domain=CollisionDomain(annotation_slot_id, "content"),
                lines=lines, semantic_id="annotationListText", annotation=presentation)
            placed = replace(placed, overflow="visible-overflow")
        placed = replace(placed, paint_order=ANNOTATION_PAINT_ORDER + 1)
        text.append(placed)
        register_rect(placed.placement_id, "text", "annotations", placed.bounds)
        rail_records.append(placed)
        if overflow:
            visible_label_overflows.append((placed, rail))
        return placed, overflow

    if annotation_slot or request.surface_content.annotations:
        annotation_marks = comparison_marks(projection)
        kind_theme = None  # the Theme's kind roles, read once and only when an annotation's kind is dressed (#584)
        for index, annotation in enumerate(request.surface_content.annotations):
            presentation = annotation_presentation(annotation.purpose)
            annotation_id, body_content = annotation.annotation_id, annotation.content
            body_content = f"{annotation.number}. {body_content}" if annotation.number is not None else body_content
            content = body_content
            has_index_suppression = annotation_id in suppressed_index_ids
            list_content = (f"{body_content} (index not shown on plot)"
                            if has_index_suppression else body_content)
            annotation_visuals = measure_candidate_visuals(
                f"annotation-text:{annotation_id}", "annotation", request).visuals
            handled_candidate_visuals.update(visual.source_ref for visual, _, _, _ in annotation_visuals)
            annotation_leading = geometry_sum(width + gap for visual, icon, width, gap in annotation_visuals if visual.side == "leading")
            annotation_trailing = geometry_sum(width + gap for visual, icon, width, gap in annotation_visuals if visual.side == "trailing")
            resolved = resolve_annotation_anchor(annotation, annotation_marks)
            matching = [(review_row, row) for review_row, row in zip(review_rows, rows, strict=True)
                        if any(item.object_id == resolved.object_id for item in review_row.items)]
            anchor = annotation.anchor
            row_id, item_id = anchor.get("rowId"), anchor.get("itemId")
            if row_id is not None or item_id is not None:
                matching = [(review_row, row) for review_row, row in matching
                            if (row_id is None or review_row.row_id == row_id)
                            and (item_id is None or any(item.item_id == item_id and item.object_id == resolved.object_id for item in review_row.items))]
            folded_matches = [(folded, mark_by_id.get(f"{resolved.facet}:{_folded_instance_id(folded, folded.item)}"))
                              for folded in getattr(projection, "folded_points", ())
                              if folded.item.object_id == resolved.object_id]
            if row_id is not None or item_id is not None:
                folded_matches = [(folded, mark) for folded, mark in folded_matches
                                  if (row_id is None or row_id == f"group-header:{folded.group_id}:{folded.item.object_id}")
                                  and (item_id is None or item_id == folded.item.item_id)]
            if len(matching) + len(folded_matches) > 1:
                raise _anchor_failure(annotation, "anchor matches multiple rows or folded points",
                                      code="E_PRESENTATION_ROW_ANCHOR_AMBIGUOUS",
                                      row_id=row_id, item_id=item_id,
                                      match_count=len(matching) + len(folded_matches))
            if matching:
                anchor_bounds = annotation_anchor_bounds(
                    resolved.mark, resolved.endpoint, matching[0][1], scale,
                    source_ref=annotation.anchor_source_ref,
                    annotation_id=annotation.annotation_id)
                selected_items = tuple(item for item in matching[0][0].items
                                       if item.object_id == resolved.object_id and (item_id is None or item.item_id == item_id))
                anchor_item = selected_items[0] if selected_items else None
                anchor_instance_id = ((f"{matching[0][0].row_id}:{anchor_item.item_id or anchor_item.object_id}"
                                       if projection.rows else anchor_item.object_id)
                                      if anchor_item is not None else "")
                anchor_host = mark_by_id.get(f"{resolved.facet}:{anchor_instance_id}")
            elif folded_matches and folded_matches[0][1] is not None:
                folded, mark = folded_matches[0]
                anchor_bounds = LabelRect(*_bounds(mark.bounds))
                selected_items = (folded.item,)
                anchor_host = mark
            else:
                raise _anchor_failure(annotation, "selected mark has no matching rendered row or folded point")
            as_of_side_constraint: tuple[float, str] | None = None
            if contract.time.as_of is not None and start <= contract.time.as_of < end:
                as_of_x = _coordinate(contract.time.as_of, scale)
                as_of_side_constraint = (as_of_x, "start" if anchor_bounds.x < as_of_x else "end")
            annotation_text_role = semantic_binding(presentation.text_semantic_id).theme_role
            annotation_treatment = request.theme_tokens.text_treatment(annotation_text_role)
            annotation_metrics = metric_for(annotation_text_role)
            size, line_height = float(annotation_treatment.font_size), float(annotation_treatment.line_height)
            if annotation_slot is not None:
                text_available = max(1.0, float(annotation_slot.bounds.inline_size) - annotation_leading - annotation_trailing)
            else:
                # A plot/content-only candidate list declares its own text
                # width bound (#466); an annotation with no annotations slot
                # must declare at least one bounded nearest-free/adjacent
                # candidate.
                declared_max_em = max((candidate.search.max_inline_em for candidate in annotation.candidates
                                       if candidate.search.max_inline_em is not None), default=None)
                if declared_max_em is None:
                    raise LayoutError("E_LAYOUT_ANNOTATION_WIDTH_UNBOUNDED", f"/annotations/{index}")
                text_available = max(1.0, declared_max_em * size - annotation_leading - annotation_trailing)
            text_width = min(text_available, max(size * 4, measure_text_width(
                content, font_size=size, font_metrics=annotation_metrics,
                letter_spacing=float(annotation_treatment.letter_spacing), text_transform=annotation_treatment.transform)))
            width = annotation_leading + text_width + annotation_trailing
            annotation_lines = (content,)
            annotation_search_count = 0
            tail_box_position_limit = tail_box_positions_examined = 0
            tail_route_state_limit = tail_route_states_examined = 0
            tail_route_search_exhausted = False
            tail_topology: str | None = None
            kind_measure = EMPTY_FRAME
            tilt_angle = 0.0  # the Theme's deterministic tilt for this annotation's position (#584)
            frame_width = frame_height = 0.0
            routed_tail_tip: tuple[float, float] | None = None
            # Numbered text-only/legacy rail notes keep their index status in
            # the same measured list entry. Candidate-backed callouts update
            # this from the region that actually wins the search.
            status_in_list = True
            selected_leader: tuple[ConnectorEgress, AnnotationRouteTrial,
                                   tuple[tuple[float, float], ...],
                                   tuple[tuple[float, float], ...]] | None = None

            def trial_leader(candidate_box: Any, rung: str
                             ) -> tuple[ConnectorEgress, AnnotationRouteTrial,
                                        tuple[tuple[float, float], ...],
                                        tuple[tuple[float, float], ...]] | None:
                nonlocal annotation_search_count
                if not candidate_box.leader_required or presentation.leader_semantic_id is None:
                    return None
                if anchor_host is None:
                    raise _anchor_failure(annotation, "selected mark has no placed leader host")
                candidate_bounds = candidate_box.placement.bounds
                anchor_center = (anchor_bounds.x + anchor_bounds.width / 2,
                                 anchor_bounds.y + anchor_bounds.height / 2)
                candidate_radius = (_container_radius(
                    role_corner_radius, container, size, candidate_bounds.width, candidate_bounds.height)
                    if role_corner_radius is not None
                    and (container is None or container.outline == "rectangle") and not tilt_angle else 0.0)
                target = _radius_aware_box_port(candidate_bounds, anchor_center, candidate_radius)
                anchor_instance = anchor_host.placement_id.split(":", 1)[1]
                anchor_row = instance_rows.get(anchor_instance)
                source_candidates = connector_egress_candidates(
                    anchor_host, resolved.endpoint, target,
                    comparison_clusters.get((anchor_host.source_ref, anchor_row), (anchor_host,)))
                viewport = request.layout_manifest.viewport
                content_extent = (float(viewport.inline), float(viewport.block),
                                  max(float(viewport.inline + viewport.inline_size), candidate_bounds.right),
                                  max(float(viewport.block + viewport.block_size), candidate_bounds.bottom))
                route_bounds = local_route_bounds(
                    _bounds(anchor_host.bounds),
                    (candidate_bounds.x, candidate_bounds.y, candidate_bounds.width, candidate_bounds.height),
                    target, content_extent)
                connector_stroke_width = float(request.theme_tokens.number(
                    semantic_binding(presentation.leader_semantic_id).theme_role, "strokeWidth"))
                route_specs: list[tuple[ConnectorEgress, tuple[tuple[float, float], ...], tuple[str, ...]]] = []
                for source_egress in source_candidates:
                    source_port_id = f"port:{anchor_host.placement_id}:{source_egress.side}"
                    known_ports = coincident_endpoint_port_ids(
                        surface_obstacles, source_egress.exposed_port, source_egress.host_ids)
                    known_ports = tuple(dict.fromkeys((*known_ports, *coincident_endpoint_port_ids(
                        surface_obstacles, source_egress.semantic_port, source_egress.host_ids))))
                    if surface_obstacles.has(source_port_id) and source_port_id not in known_ports:
                        known_ports = (*known_ports, source_port_id)
                    if source_egress.corridor and surface_obstacles.egress_collisions(
                            ObstacleSegment(*source_egress.corridor), host_ids=source_egress.host_ids,
                            port_ids=known_ports):
                        continue
                    base_prefix = (source_egress.corridor if source_egress.corridor
                                   else (source_egress.semantic_port,))
                    # Clear the entire possible bridge gap before turning
                    # back across a dependency from the same endpoint.
                    fanout_deltas = ((6.0, 0.0), (-6.0, 0.0), (0.0, 6.0), (0.0, -6.0))
                    prefixes = (base_prefix, *(tuple((*base_prefix,
                                                      (source_egress.exposed_port[0] + dx,
                                                       source_egress.exposed_port[1] + dy)))
                                                for dx, dy in fanout_deltas))
                    for prefix in prefixes:
                        if len(prefix) > len(base_prefix):
                            stub = ObstacleSegment(source_egress.exposed_port, prefix[-1])
                            if (surface_obstacles.egress_collisions(
                                    stub, host_ids=source_egress.host_ids, port_ids=known_ports)
                                    or any(item.placement_id in source_egress.host_ids
                                           for item in surface_obstacles.collisions(stub, classes=("mark",)))):
                                continue
                        route_specs.append((source_egress, tuple(prefix), known_ports))
                # Probe every finite sparse endpoint before spending the
                # dense-grid budget on any one poor endpoint.
                for dense_search, candidates in ((False, route_specs), (True, route_specs[:2])):
                    for source_egress, prefix, known_ports in candidates:
                        annotation_search_count += 1
                        trial = route_annotation_candidate(
                            prefix[-1], target, surface_obstacles,
                            bounds=route_bounds, port_ids=known_ports,
                            max_bends=layout_manifest.annotation_max_bends,
                            max_detour_ratio=layout_manifest.annotation_max_detour_ratio,
                            allow_bridge=rung == "rail", dense=dense_search,
                            connector_stroke_width=connector_stroke_width)
                        if trial is None:
                            continue
                        full_points = (*prefix[:-1], *trial.points)
                        if relation_route_quality(full_points, max_bends=layout_manifest.annotation_max_bends,
                                                  max_detour_ratio=layout_manifest.annotation_max_detour_ratio):
                            return source_egress, trial, tuple(full_points), tuple(prefix)
                return None

            tail_tip: tuple[float, float] | None = None
            container = None
            role_corner_radius = None
            box_border = NO_BORDER
            # The box role's viewer-fit mode (#1050) is read outside the search below, whose handler reports a Layout
            # pointer: a refused declaration keeps its own Theme pointer.
            viewer_fit = (request.theme_tokens.viewer_fit(semantic_binding(presentation.box_semantic_id).theme_role)
                          if annotation.purpose in {"callout", "highlight", "note", "explanatory-arrow"}
                          else ViewerFitToken())
            fill_declared = used_fill = False
            filled = fill_size = None
            content_top = content_right = content_bottom = content_left = 0.0
            try:
                if annotation.purpose in {"callout", "highlight", "note", "explanatory-arrow"}:
                    intent = selected_items[0].presentation if selected_items else None
                    preferred = ((intent or {}).get("callout") or {}).get("placement") if isinstance(intent, dict) else None
                    wrap_declared = ((intent or {}).get("text") or {}).get("wrap") if isinstance(intent, dict) else None
                    wrap = wrap_declared or "forbid"
                    # A declared candidate's maxInlineEm is a text-width bound
                    # for a plot/content search (#466): it forces wrapping so
                    # a long note becomes a narrow, tall box rather than one
                    # too wide to fit any free lattice position.
                    plot_wrap_em = max((candidate.search.max_inline_em for candidate in annotation.candidates
                                        if candidate.search.max_inline_em is not None), default=None)
                    wrap_available = float(plot_wrap_em) * size if plot_wrap_em is not None else text_available
                    annotation_box_role = semantic_binding(presentation.box_semantic_id).theme_role
                    container = request.theme_tokens.annotation_container(annotation_box_role)
                    role_corner_radius = request.theme_tokens.optional_token(
                        annotation_box_role, "cornerRadius", "radius")
                    # A Theme-dressed Project kind adds a header and optional stamp column.
                    # Content sizing keeps a text-width bound; fill sizing subtracts all chrome below.
                    kind_token = request.theme_tokens.annotation_kind(annotation.kind)
                    if kind_token is not None and kind_theme is None:
                        kind_theme = request.theme_tokens.annotation_kind_frame()
                    kind_measure = measure_kind_frame(
                        kind=kind_token, subject=annotation.subject, subject_id=annotation.subject_id,
                        frame=kind_theme, theme_tokens=request.theme_tokens, metric_for=metric_for,
                        outline=container.outline if container is not None else None,
                        pointer=f"/annotations/{index}", text_size=size,
                        header_texts=annotation.kind_header_lines, heading_content=annotation.kind_heading_text)
                    require_followable_content(viewer_fit, has_kind_frame=not kind_measure.empty,
                                               has_visual=bool(annotation_visuals), pointer=f"/annotations/{index}")
                    wrap_available = max(1.0, wrap_available - kind_measure.inline_insets)
                    if plot_wrap_em is not None:
                        wrap = "allow"
                    # A container with a content inset (always an image-backed one, #465; optionally a
                    # rectangle or balloon, #991) measures text into that smaller box, then
                    # expands it by the inset to the paint box the search and
                    # collision below actually use -- the box a rectangle or
                    # balloon container already uses today, unchanged.
                    content_top = content_right = content_bottom = content_left = 0.0
                    if container is not None and container.content_insets_em is not None:
                        content_top, content_right, content_bottom, content_left = (
                            float(value) * size for value in container.content_insets_em)
                    # A box border (#1049) lies on the box edge and the inset is measured from inside it: the
                    # effective insets are border + content inset, read by the text origin, the kind frame's content
                    # box, the wrap chrome and the box size alike.
                    box_border = resolve_border(container.border) if container is not None else NO_BORDER
                    border_top, border_right, border_bottom, border_left = box_border.insets
                    content_top += border_top
                    content_right += border_right
                    content_bottom += border_bottom
                    content_left += border_left
                    if (container is not None and container.outline == "rectangle"
                            and role_corner_radius is None and container.corner_radius > 0):
                        # A rounded corner removes paper (#1087): every inset keeps the text and the kind frame on it.
                        clearance = float(container.corner_radius) * size * CORNER_CLEARANCE
                        content_top, content_right, content_bottom, content_left = (
                            max(value, clearance) for value in (content_top, content_right, content_bottom, content_left))

                    def measure_note(measured_content: str, wrap_bound: float, may_wrap: bool
                                     ) -> tuple[tuple[str, ...], float, tuple[float, float]]:
                        lines = (wrap_text(measured_content, available_inline=wrap_bound, font_size=size, font_metrics=annotation_metrics,
                                           letter_spacing=float(annotation_treatment.letter_spacing),
                                           text_transform=annotation_treatment.transform)
                                 if may_wrap else (measured_content,))
                        widest = max(measure_text_width(line, font_size=size, font_metrics=annotation_metrics,
                                                        letter_spacing=float(annotation_treatment.letter_spacing),
                                                        text_transform=annotation_treatment.transform)
                                     for line in lines)
                        body_inline = annotation_leading + widest + annotation_trailing
                        return lines, widest, (
                            max(body_inline, kind_measure.header_inline) + kind_measure.inline_insets
                            + content_left + content_right,
                            max(size * line_height * len(lines) + kind_measure.header_block, kind_measure.stamp_block)
                            + content_top + content_bottom)

                    # A tilted note is searched and registered through the axis-aligned bounds of its rotated
                    # frame; once a position is chosen the whole frame is rotated about their centre (#584).
                    tilt_angle = tilt_for(container.tilt_degrees if container is not None else None, index)
                    if tilt_angle:
                        if annotation_visuals:
                            raise LayoutError("E_LAYOUT_ANNOTATION_TILT_VISUAL", f"/annotations/{index}")
                    # `inlineSize: fill` (#1051): on a row-aligned rung of an annotations slot the note takes the slot's
                    # inline size and wraps in what its chrome leaves; any other rung keeps the content size above.
                    fill_declared = container is not None and container.inline_size == "fill"
                    def measure_variant(measured_content: str, *, list_entry: bool):
                        may_wrap = (wrap == "allow" or (list_entry and has_index_suppression))
                        lines, measured_width, frame_size = measure_note(
                            measured_content, wrap_available, may_wrap)
                        search_size = (rotated_extent(*frame_size, tilt_angle) if tilt_angle else frame_size)
                        filled_variant = None
                        if fill_declared and annotation_slot is not None:
                            fill_may_wrap = (wrap_declared != "forbid" or plot_wrap_em is not None or list_entry)
                            filled_variant = fill_note(
                                lambda bound: measure_note(measured_content, bound, fill_may_wrap),
                                target=fill_target(float(annotation_slot.bounds.inline_size),
                                                   max_inline_em=(float(container.max_inline_em)
                                                                  if container.max_inline_em is not None else None),
                                                   text_size=size),
                                chrome=(annotation_leading + annotation_trailing + kind_measure.inline_insets
                                        + content_left + content_right),
                                tilt_degrees=tilt_angle)
                        measured_fill_size = (
                            rotated_extent(filled_variant.frame_inline, filled_variant.frame_block, tilt_angle)
                            if filled_variant is not None and tilt_angle else
                            (filled_variant.frame_inline, filled_variant.frame_block)
                            if filled_variant is not None else None)
                        return (measured_content, lines, measured_width, frame_size, search_size,
                                filled_variant, measured_fill_size)

                    plot_variant = measure_variant(body_content, list_entry=False)
                    list_variant = (measure_variant(list_content, list_entry=True)
                                    if has_index_suppression else plot_variant)
                    if (role_corner_radius is not None
                            and (container is None or container.outline in {"rectangle", "balloon"})):
                        # Insets enlarge content-sized boxes, so avoid a radius/inset loop: a physical px value
                        # uses its requested radius as a finite conservative bound; capsule computes its exact
                        # shorter-side radius from the three piecewise-linear inset regions. Re-measure once.
                        variants = (plot_variant,) if list_variant is plot_variant else (plot_variant, list_variant)
                        base_insets = (content_top, content_right, content_bottom, content_left)
                        required = 0.0
                        for variant in variants:
                            dimensions = [(*variant[3], False)]
                            if variant[5] is not None:
                                dimensions.append((variant[5].frame_inline, variant[5].frame_block, True))
                            for dimension in dimensions:
                                measured_width, measured_height = dimension[:2]
                                filled_width = len(dimension) == 3 and dimension[2]
                                if role_corner_radius == "capsule" and filled_width:
                                    # Fill width can exceed its slot when wrapping leaves an unbreakable word.
                                    # Re-insetting can add at most 2c to that measured width; solve c >= k(W+2c)/2.
                                    clearance = (CORNER_CLEARANCE * measured_width
                                                / (2 * (1 - CORNER_CLEARANCE)))
                                else:
                                    clearance = _physical_radius_clearance(
                                        role_corner_radius, measured_width, measured_height, base_insets)
                                required = max(required, clearance)
                        content_top, content_right, content_bottom, content_left = (
                            max(value, required) for value in base_insets)
                        if base_insets != (content_top, content_right, content_bottom, content_left):
                            plot_variant = measure_variant(body_content, list_entry=False)
                            list_variant = (measure_variant(list_content, list_entry=True)
                                            if has_index_suppression else plot_variant)
                    (content, annotation_lines, text_width, frame_size, annotation_size,
                     filled, fill_size) = plot_variant

                    def use_variant(candidate: Any | None) -> None:
                        nonlocal content, annotation_lines, text_width, frame_width, frame_height
                        nonlocal annotation_size, filled, fill_size
                        variant = (list_variant if has_index_suppression and candidate is not None
                                   and _is_annotation_list_candidate(candidate) else plot_variant)
                        (content, annotation_lines, text_width, frame_size, annotation_size,
                         filled, fill_size) = variant
                        frame_width, frame_height = frame_size

                    used_fill = False
                    candidates, ladder = candidate_order(annotation.candidates, annotation.purpose,
                                                          annotation.fallback_ladder, preferred)
                    box, selected_rung, tail_tip = None, None, None
                    for candidate in (() if annotation_id in suppressed_callout_ids else candidates):
                        use_variant(candidate)
                        used_fill = False
                        rung = candidate.candidate_id
                        if candidate.search.kind == "row-aligned":
                            candidate_boxes = ordered_rail_candidates(
                                annotation, resolved, anchor_y=anchor_bounds.y + anchor_bounds.height / 2,
                                text_size=fill_size or annotation_size,
                                rail=LabelRect(*_bounds(annotation_slot.bounds)))
                            for candidate_box in candidate_boxes:
                                annotation_search_count += 1
                                leader_trial = trial_leader(candidate_box, rung)
                                if candidate_box.leader_required and presentation.leader_semantic_id is not None and leader_trial is None:
                                    continue
                                box, selected_rung, selected_leader = candidate_box, rung, leader_trial
                                used_fill = filled is not None
                                break
                        elif candidate.search.kind == "nearest-free":
                            region_bounds = LabelRect(*_bounds(timeline.bounds))
                            host_id = anchor_host.placement_id if anchor_host is not None else None
                            if candidate.connector.kind == "tail":
                                if container is None or container.outline != "balloon":
                                    raise LayoutError("E_LAYOUT_ANNOTATION_TAIL_REQUIRES_BALLOON", f"/annotations/{index}")
                                corner_radius = (_container_radius(
                                    role_corner_radius, container, size, annotation_size[0], annotation_size[1])
                                    if role_corner_radius is not None else float(container.corner_radius) * size)
                                tail_base = float(container.tail_base) * size
                                free_box, trial_tip, trials = nearest_free_tail_box(
                                    region=region_bounds, anchor=anchor_bounds, box_size=annotation_size,
                                    max_positions=candidate.search.max_positions, obstacles=surface_obstacles,
                                    obstacle_classes=candidate.obstacles.classes, corner_radius=corner_radius,
                                    tail_base=tail_base, host_id=host_id, side_of_as_of=as_of_side_constraint)
                                annotation_search_count += trials
                                tail_box_position_limit = candidate.search.max_positions
                                tail_box_positions_examined = trials
                                if free_box is not None:
                                    box = AnnotationBox(resolved, LabelPlacement(rung, free_box, False), False)
                                    selected_rung, tail_tip = rung, trial_tip
                                    tail_topology = "direct-tail"
                                elif anchor_host is not None:
                                    anchor_instance = anchor_host.placement_id.split(":", 1)[1]
                                    anchor_row = instance_rows.get(anchor_instance)
                                    viewport = request.layout_manifest.viewport
                                    routed = nearest_free_routed_tail_box(
                                        region=region_bounds, anchor=anchor_host,
                                        endpoint=resolved.endpoint,
                                        siblings=comparison_clusters.get(
                                            (anchor_host.source_ref, anchor_row), (anchor_host,)),
                                        box_size=annotation_size,
                                        max_positions=candidate.search.max_positions,
                                        obstacles=surface_obstacles,
                                        obstacle_classes=candidate.obstacles.classes,
                                        corner_radius=corner_radius, tail_base=tail_base,
                                        content_bounds=(
                                            float(viewport.inline), float(viewport.block),
                                            float(viewport.inline + viewport.inline_size),
                                            float(viewport.block + viewport.block_size)),
                                        host_id=host_id, side_of_as_of=as_of_side_constraint,
                                        max_bends=layout_manifest.annotation_max_bends,
                                        max_detour_ratio=layout_manifest.annotation_max_detour_ratio)
                                    annotation_search_count += routed.box_trials + routed.route_states
                                    tail_box_positions_examined = max(trials, routed.box_trials)
                                    tail_route_state_limit = 1024
                                    tail_route_states_examined = routed.route_states
                                    tail_route_search_exhausted = routed.exhausted and routed.box is None
                                    if routed.exhausted and routed.box is None:
                                        add_diagnostic(
                                            f"W_LAYOUT_ANNOTATION_ROUTE_SEARCH_EXHAUSTED:{annotation_id}:{rung}", annotation)
                                    if routed.box is not None and routed.egress is not None and routed.route is not None:
                                        box = AnnotationBox(resolved, LabelPlacement(rung, routed.box, False), False)
                                        selected_rung, tail_tip = rung, routed.tip
                                        routed_tail_tip = routed.tip
                                        tail_topology = "routed-tail"
                                        prefix = (routed.egress.corridor if routed.egress.corridor
                                                  else (routed.egress.exposed_port,))
                                        selected_leader = (routed.egress, routed.route,
                                                           routed.full_points, prefix)
                            else:
                                anchor_center = (anchor_bounds.x + anchor_bounds.width / 2,
                                                 anchor_bounds.y + anchor_bounds.height / 2)
                                free_box, trials = nearest_free_box(
                                    region=region_bounds, anchor_center=anchor_center, box_size=annotation_size,
                                    max_positions=candidate.search.max_positions, obstacles=surface_obstacles,
                                    obstacle_classes=candidate.obstacles.classes, host_id=host_id,
                                    side_of_as_of=as_of_side_constraint)
                                annotation_search_count += trials
                                if free_box is not None:
                                    leader_required = candidate.connector.kind == "leader"
                                    candidate_box = AnnotationBox(resolved, LabelPlacement(rung, free_box, False), leader_required)
                                    leader_trial = trial_leader(candidate_box, rung) if leader_required else None
                                    if not (leader_required and presentation.leader_semantic_id is not None and leader_trial is None):
                                        box, selected_rung, selected_leader = candidate_box, rung, leader_trial
                        else:
                            candidate_box = project_annotation_box(
                                annotation, resolved, anchor_bounds=anchor_bounds, text_size=annotation_size,
                                candidate_sides=(rung,), viewport=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=surface_obstacles, overflow="clip-optional", required=False)
                            candidate_boxes = (candidate_box,) if candidate_box is not None else ()
                            for candidate_box in candidate_boxes:
                                annotation_search_count += 1
                                leader_trial = trial_leader(candidate_box, rung)
                                if candidate_box.leader_required and presentation.leader_semantic_id is not None and leader_trial is None:
                                    continue
                                box, selected_rung, selected_leader = candidate_box, rung, leader_trial
                                break
                        if box is not None:
                            status_in_list = _is_annotation_list_candidate(candidate)
                            break
                    if (box is not None and annotation.candidates
                            and selected_rung != candidates[0].candidate_id):
                        add_diagnostic(
                            f"W_LAYOUT_ANNOTATION_CANDIDATE_FALLBACK:{annotation_id}:{selected_rung}", annotation)
                    if box is None:
                        if annotation_id in suppressed_callout_ids:
                            placement_decisions.append(PlacementDecision(
                                f"annotation:{annotation_id}", annotation_id, tuple(ladder),
                                "suppress", "suppressed", search_count=annotation_search_count))
                            add_diagnostic(f"W_LAYOUT_ANNOTATION_SUPPRESSED:annotation:{annotation_id}", annotation)
                            discovered_callout_suppressions.add(annotation_id)
                            if annotation_slot is not None and annotation.number is not None:
                                summary_content = (f"{annotation.number}. {annotation.content} "
                                                   "(callout not shown on plot)")
                                summary_lines = wrap_text(
                                    summary_content, available_inline=max(1.0, text_available),
                                    font_size=size, font_metrics=annotation_metrics,
                                    letter_spacing=float(annotation_treatment.letter_spacing),
                                    text_transform=annotation_treatment.transform)
                                summary_width = max(
                                    measure_text_width(
                                        line, font_size=size, font_metrics=annotation_metrics,
                                        letter_spacing=float(annotation_treatment.letter_spacing),
                                        text_transform=annotation_treatment.transform)
                                    for line in summary_lines)
                                summary_height = size * line_height * len(summary_lines)
                                complete_list_record(
                                    annotation=annotation, resolved=resolved,
                                    placement_id=f"annotation-summary:{annotation_id}",
                                    content=summary_content, lines=summary_lines,
                                    text_size=(summary_width, summary_height), font_size=size,
                                    typography_role=annotation_text_role,
                                    presentation=presentation,
                                    anchor_y=anchor_bounds.y + anchor_bounds.height / 2)
                            continue
                        if "suppress" in ladder:
                            placement_decisions.append(PlacementDecision(f"annotation:{annotation_id}", annotation_id,
                                                                         tuple(ladder), "suppress", "suppressed",
                                                                         search_count=annotation_search_count))
                            add_diagnostic(f"W_LAYOUT_ANNOTATION_SUPPRESSED:annotation:{annotation_id}", annotation)
                            discovered_callout_suppressions.add(annotation_id)
                            continue
                        # A normal annotation is never silently suppressed or
                        # rejected.  Complete its first declared placement in
                        # visible-overflow mode after the explicit fit ladder
                        # has been exhausted.
                        selected_rung = next(rung for rung in ladder if rung != "suppress")
                        first_candidate = next((item for item in candidates if item.candidate_id == selected_rung), None)
                        status_in_list = (first_candidate is None
                                          or _is_annotation_list_candidate(first_candidate))
                        use_variant(first_candidate)
                        if selected_rung == "rail":
                            used_fill = filled is not None
                            rail = LabelRect(*_bounds(annotation_slot.bounds))
                            text_size = fill_size or annotation_size
                            rail_candidates = ordered_rail_candidates(
                                annotation, resolved,
                                anchor_y=anchor_bounds.y + anchor_bounds.height / 2,
                                text_size=text_size, rail=rail, allow_inline_overflow=True)
                            previous_bottom = max((
                                rail.y,
                                *(item.bottom for item in rail_boxes),
                                *(float(item.bounds.block + item.bounds.block_size)
                                  for item in rail_records)))
                            fallback_bounds = LabelRect(
                                rail.x, max(rail.y, previous_bottom), text_size[0], text_size[1])
                            box = rail_candidates[0] if rail_candidates else AnnotationBox(
                                resolved, LabelPlacement("rail", fallback_bounds, True), True)
                        elif first_candidate is not None and first_candidate.search.kind == "nearest-free":
                            # #449 never refuses: complete the first declared
                            # candidate's own region at its nearest lattice
                            # position, visibly overflowing any obstacle.
                            region_bounds = LabelRect(*_bounds(timeline.bounds))
                            anchor_center = (anchor_bounds.x + anchor_bounds.width / 2,
                                             anchor_bounds.y + anchor_bounds.height / 2)
                            width, height = annotation_size
                            forced = LabelRect(min(max(anchor_center[0] - width / 2, region_bounds.x),
                                                   region_bounds.right - width),
                                               min(max(anchor_center[1] - height / 2, region_bounds.y),
                                                   region_bounds.bottom - height), width, height)
                            box = AnnotationBox(resolved, LabelPlacement(selected_rung, forced, True), False)
                        else:
                            box = project_annotation_box(
                                annotation, resolved, anchor_bounds=anchor_bounds, text_size=annotation_size,
                                candidate_sides=(selected_rung,), viewport=LabelRect(*_bounds(annotation_slot.bounds)),
                                obstacles=surface_obstacles, overflow="visible-overflow", required=True)
                        if box is None:  # Defensive: visible-overflow is a total Layout policy.
                            raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", f"/annotations/{index}")
                    placement_decisions.append(PlacementDecision(f"annotation:{annotation_id}", annotation_id,
                                                                 tuple(ladder), selected_rung, "placed",
                                                                 search_count=annotation_search_count,
                                                                 selected_topology=(tail_topology or
                                                                                    (selected_leader[1].topology
                                                                                     if selected_leader else None)),
                                                                 crossing_ids=(selected_leader[1].crossing_ids
                                                                               if selected_leader else ()),
                                                                 box_position_limit=tail_box_position_limit,
                                                                 box_positions_examined=tail_box_positions_examined,
                                                                 route_state_limit=tail_route_state_limit,
                                                                 route_states_examined=tail_route_states_examined,
                                                                 route_search_exhausted=tail_route_search_exhausted))
                    if used_fill:
                        # The note sits in its slot at the slot's width (#1051): the wrapped lines and frame are the
                        # filled ones, and a trailing visual stands at the box's end edge.
                        annotation_lines, frame_width, frame_height = filled.lines, filled.frame_inline, filled.frame_block
                        text_width = (frame_width - annotation_leading - annotation_trailing - kind_measure.inline_insets
                                      - content_left - content_right)
                    elif fill_declared:
                        add_diagnostic(f"W_LAYOUT_ANNOTATION_FILL_NOT_SLOT:{annotation_id}:{selected_rung or 'none'}", annotation)
                else:
                    if has_index_suppression and annotation.number is not None:
                        content = list_content
                        annotation_lines = wrap_text(
                            content, available_inline=text_available, font_size=size,
                            font_metrics=annotation_metrics,
                            letter_spacing=float(annotation_treatment.letter_spacing),
                            text_transform=annotation_treatment.transform)
                        text_width = max(measure_text_width(
                            line, font_size=size, font_metrics=annotation_metrics,
                            letter_spacing=float(annotation_treatment.letter_spacing),
                            text_transform=annotation_treatment.transform) for line in annotation_lines)
                        width = min(text_available, text_width)
                        annotation_size = (width, size * line_height * len(annotation_lines))
                    else:
                        annotation_size = (width, size * line_height)
                    status_in_list = True
                    box = project_annotation_box(annotation, resolved, anchor_bounds=anchor_bounds, text_size=annotation_size,
                                                 candidate_sides=(annotation.side,),
                                                 viewport=LabelRect(*_bounds(annotation_slot.bounds)), obstacles=surface_obstacles,
                                                 overflow=annotation_slot.overflow, required=annotation_slot.priority == "required")
            except LayoutError:
                raise
            except ValueError as error:
                raise LayoutError(str(error), f"/annotations/{index}") from error
            if box is None:
                continue
            bounds = box.placement.bounds
            rail_overflow = box.placement.visible_overflow and status_in_list
            overflow_viewport = (LabelRect(*_bounds(annotation_slot.bounds)) if annotation_slot is not None
                                 else LabelRect(*_bounds(timeline.bounds)))
            annotation_bounds = Rect(Decimal(str(bounds.x)), Decimal(str(bounds.y)),
                                     Decimal(str(bounds.width)), Decimal(str(bounds.height)))
            if tilt_angle:
                frame_x = bounds.x + (bounds.width - frame_width) / 2
                frame_y = bounds.y + (bounds.height - frame_height) / 2
                tilt_center = (bounds.x + bounds.width / 2, bounds.y + bounds.height / 2)
                tilt_polygon = rotated_corners(frame_x, frame_y, frame_width, frame_height, tilt_center, tilt_angle)
            else:
                frame_x, frame_y, frame_width, frame_height = bounds.x, bounds.y, bounds.width, bounds.height
            # The radius a rectangle container draws (#1087): its declared em, clamped to what the paint box can carry.
            box_radius = (_container_radius(role_corner_radius, container, size, frame_width, frame_height)
                          if (container is None or container.outline == "rectangle") and tail_tip is None else 0.0)
            tilt_commands = None
            if tilt_angle and box_radius > 0:
                tilt_commands = rotate_commands(rounded_rect_commands(
                    (frame_x, frame_y, frame_width, frame_height), box_radius), tilt_center, tilt_angle)
                tilt_polygon = tuple(commands_points(tilt_commands))
            if tail_tip is not None:
                container = request.theme_tokens.annotation_container(
                    semantic_binding(presentation.box_semantic_id).theme_role)
                corner_radius = (_container_radius(role_corner_radius, container, size, bounds.width, bounds.height)
                                 if role_corner_radius is not None else float(container.corner_radius) * size)
                tail_base = float(container.tail_base) * size
                outline = balloon_outline(bounds, tail_tip, corner_radius=corner_radius, tail_base=tail_base)
                shapes.append(ShapePlacement(f"annotation-box:{annotation_id}", annotation_id, "Balloon",
                                             annotation_bounds, path_commands=outline,
                                             semantic_id=presentation.box_semantic_id, annotation=presentation,
                                             paint_order=ANNOTATION_PAINT_ORDER))
            elif tilt_angle:
                shapes.append(ShapePlacement(f"annotation-box:{annotation_id}", annotation_id, "Tilt",
                                             annotation_bounds,
                                             path_commands=tilt_commands or polygon_commands(tilt_polygon),
                                             semantic_id=presentation.box_semantic_id, annotation=presentation,
                                             paint_order=ANNOTATION_PAINT_ORDER))
            elif container is not None and container.outline == "image":
                icon = request.icon_assets.get(container.image_ref)
                if icon is None or icon.kind != "raster":
                    raise LayoutError("E_LAYOUT_ANNOTATION_IMAGE_UNRESOLVED", f"/annotations/{index}")
                slice_insets_px = tuple(float(value) * size for value in container.slice_insets_em)
                tiles = image_slice_tiles((bounds.x, bounds.y, bounds.width, bounds.height),
                                          viewport=icon.viewport, slice_insets=slice_insets_px)
                shapes.append(ShapePlacement(f"annotation-box:{annotation_id}", annotation_id, "Rect",
                                             annotation_bounds,
                                             semantic_id=presentation.box_semantic_id, annotation=presentation,
                                             paint_order=ANNOTATION_PAINT_ORDER,
                                             image_fill=LayoutImageFill(icon.content_identity, icon.viewport,
                                                                        icon.payload, tiles)))
            else:
                shapes.append(ShapePlacement(f"annotation-box:{annotation_id}", annotation_id, "Rect",
                                             annotation_bounds,
                                             semantic_id=presentation.box_semantic_id, annotation=presentation,
                                             paint_order=ANNOTATION_PAINT_ORDER, corner_radius=box_radius))
            if viewer_fit.mode != "raw":
                shapes[-1] = replace(shapes[-1], viewer_fit=viewer_fit.mode)
            register_rect(f"annotation-box:{annotation_id}", "annotation-box", "annotations", annotation_bounds)
            if annotation_slot is not None and status_in_list:
                rail_boxes.append(bounds)
            # Vector artwork (#848) is ink over the paper the box just painted, under the kind frame and the text.
            artwork_shapes = place_artwork(
                container.artwork if container is not None else (), annotation_id=annotation_id,
                presentation=presentation, box=(frame_x, frame_y, frame_width, frame_height), text_size=size,
                theme_tokens=request.theme_tokens, paint_order=ANNOTATION_PAINT_ORDER, pointer=f"/annotations/{index}")
            shapes.extend(rotate_shape(item, tilt_center, tilt_angle) if tilt_angle else item
                          for item in artwork_shapes)
            annotation_text_slot = "annotations" if annotation_slot is not None else timeline.slot_id
            if not box_border.empty:
                # Box border strips (#1049): over the artwork's rim, under the kind frame and the text.
                border_shapes = place_border(
                    box_border, annotation_id=annotation_id, presentation=presentation,
                    box=(frame_x, frame_y, frame_width, frame_height), theme_tokens=request.theme_tokens,
                    paint_order=ANNOTATION_PAINT_ORDER, radius=box_radius)
                shapes.extend(rotate_shape(item, tilt_center, tilt_angle) if tilt_angle else item
                              for item in border_shapes)
            if not kind_measure.empty:
                kind_shapes, kind_text = place_kind_frame(
                    kind_measure, annotation_id=annotation_id, presentation=presentation,
                    content_box=(frame_x + content_left, frame_y + content_top,
                                 frame_width - content_left - content_right,
                                 frame_height - content_top - content_bottom),
                    inner_border_box=(frame_x + box_border.start, frame_y + box_border.top,
                                      frame_width - box_border.start - box_border.end,
                                      frame_height - box_border.top - box_border.bottom),
                    theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                    annotation_slot=annotation_text_slot, paint_order=ANNOTATION_PAINT_ORDER)
                kind_text = tuple(fit_text(item, viewer_fit, request.font_metrics, box_id=f"annotation-box:{annotation_id}")
                                  for item in kind_text)
                if rail_overflow:
                    kind_text = tuple(replace(item, overflow="visible-overflow") for item in kind_text)
                if tilt_angle:
                    kind_shapes = tuple(rotate_shape(item, tilt_center, tilt_angle) for item in kind_shapes)
                    kind_text = tuple(rotate_text(item, tilt_center, tilt_angle) for item in kind_text)
                shapes.extend(kind_shapes)
                for kind_line in kind_text:
                    text.append(kind_line)
                    register_rect(kind_line.placement_id, "text", "annotations", kind_line.bounds)
                    if rail_overflow:
                        visible_label_overflows.append((kind_line, overflow_viewport))
            placed_annotation = place_text(placement_id=f"annotation-text:{annotation_id}", source_ref=annotation_id, content=content,
                                           inline=frame_x + annotation_leading + content_left + kind_measure.body_inset_left,
                                           baseline_block=(frame_y + content_top
                                                           + kind_measure.header_block + size),
                                           typography_role=annotation_text_role,
                                           theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                           collision_region="annotations", collision_domain=CollisionDomain(annotation_text_slot, "content"),
                                           lines=annotation_lines, semantic_id=presentation.text_semantic_id,
                                           annotation=presentation)
            placed_annotation = replace(placed_annotation, paint_order=ANNOTATION_PAINT_ORDER + 1)
            placed_annotation = fit_text(placed_annotation, viewer_fit, request.font_metrics,
                                         box_id=f"annotation-box:{annotation_id}", end_inset=content_right)
            if rail_overflow:
                placed_annotation = replace(placed_annotation, overflow="visible-overflow")
            if tilt_angle:
                placed_annotation = rotate_text(placed_annotation, tilt_center, tilt_angle)
            text.append(placed_annotation)
            register_rect(placed_annotation.placement_id, "text", "annotations", placed_annotation.bounds)
            if annotation_slot is not None and annotation.number is not None and status_in_list:
                rail_records.append(placed_annotation)
            if box.placement.visible_overflow:
                visible_label_overflows.append((placed_annotation, overflow_viewport))
            if annotation_visuals:
                if not hasattr(annotation_metrics, "cap_height_at"):
                    raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(visual.source_ref for visual, _, _, _ in annotation_visuals))
                cap_height = float(annotation_metrics.cap_height_at(size))
                for visual, icon, icon_width, gap in annotation_visuals:
                    inline = ((bounds.x if visual.side == "leading"
                               else bounds.x + annotation_leading + text_width + annotation_trailing - gap - icon_width)
                              + kind_measure.body_inset_left + box_border.start)
                    icon_bounds = Rect(Decimal(str(inline)), Decimal(str(placed_annotation.baseline[1] - cap_height
                                                                          + (cap_height - size) / 2)),
                                       Decimal(str(icon_width)), Decimal(str(size)))
                    candidate_icons.append(IconPlacement(f"visual:{placed_annotation.placement_id}:{visual.side}",
                                                         annotation_id, visual.source_ref, icon.icon_id, icon.kind,
                                                         icon.content_identity, icon.viewport, icon.payload, icon.alternative,
                                                         visual.decorative, icon_bounds, "labelVisual",
                                                         icon_width / icon.viewport[0], annotation_slot_id,
                                                         paint_order=placed_annotation.paint_order,
                                                         subjects=_annotation_icon_subjects(annotation)))
            if annotation.number is not None:
                note_index_visuals = measure_candidate_visuals(
                    f"note-index:{annotation_id}", "annotation", request).visuals
                handled_candidate_visuals.update(visual.source_ref for visual, _, _, _ in note_index_visuals)
                note_index_leading = geometry_sum(width + gap for visual, _, width, gap in note_index_visuals
                                                  if visual.side == "leading")
                note_index_trailing = geometry_sum(width + gap for visual, _, width, gap in note_index_visuals
                                                   if visual.side == "trailing")
                note_index_content = str(annotation.number)
                note_index_width = measure_text_width(note_index_content, font_size=size, font_metrics=annotation_metrics,
                                                      letter_spacing=float(annotation_treatment.letter_spacing),
                                                      text_transform=annotation_treatment.transform)
                note_index_size = (note_index_leading + note_index_width + note_index_trailing, size * line_height)
                note_index = (None if annotation_id in suppressed_index_ids else place_label(
                    anchor_bounds, note_index_size, ("end", "start", "above", "below"),
                    bounds=LabelRect(*timeline_bounds), obstacles=surface_obstacles,
                    gap=max(1.0, size * 0.25), required=False, overflow="suppress",
                ))
                if note_index is None:
                    add_diagnostic(f"W_LAYOUT_NOTE_INDEX_SUPPRESSED:{annotation_id}", annotation)
                    discovered_index_suppressions.add(annotation_id)
                else:
                    note_index_inline = note_index.bounds.x
                    note_index_text = place_text(placement_id=f"note-index:{annotation_id}", source_ref=annotation_id,
                                                 content=note_index_content, inline=note_index_inline + note_index_leading,
                                                 baseline_block=note_index.bounds.y + size, typography_role="annotation",
                                                 theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                                                 collision_region="annotations",
                                                 collision_domain=CollisionDomain("timeline", "overlay"),
                                                 semantic_id="noteIndex")
                    if anchor_host is not None:
                        note_index_text = replace(note_index_text, host_placement_id=anchor_host.placement_id,
                                                  paint_order=max(HOSTED_TEXT_PAINT_ORDER, anchor_host.paint_order + 1))
                    text.append(note_index_text)
                    register_rect(note_index_text.placement_id, "text", "timeline", note_index_text.bounds)
                    if note_index_visuals:
                        if not hasattr(annotation_metrics, "cap_height_at"):
                            raise LayoutError("E_FONT_METRICS_CAP_HEIGHT", next(visual.source_ref for visual, _, _, _ in note_index_visuals))
                        cap_height = float(annotation_metrics.cap_height_at(size))
                        for visual, icon, icon_width, gap in note_index_visuals:
                            inline = (note_index.bounds.x if visual.side == "leading"
                                      else note_index.bounds.x + note_index_leading + note_index_width + note_index_trailing - gap - icon_width)
                            icon_bounds = Rect(Decimal(str(inline)), Decimal(str(note_index_text.baseline[1] - cap_height
                                                                                  + (cap_height - size) / 2)),
                                               Decimal(str(icon_width)), Decimal(str(size)))
                            candidate_icons.append(IconPlacement(f"visual:note-index:{annotation_id}:{visual.side}",
                                                                 annotation_id, visual.source_ref, icon.icon_id, icon.kind,
                                                                 icon.content_identity, icon.viewport, icon.payload, icon.alternative,
                                                                 visual.decorative, icon_bounds, "labelVisual",
                                                                 icon_width / icon.viewport[0], annotation_slot_id,
                                                                 paint_order=note_index_text.paint_order,
                                                                 subjects=_annotation_icon_subjects(annotation)))
                if (has_index_suppression and annotation_slot is not None and annotation.number is not None
                        and not status_in_list):
                    status_content = f"{annotation.number}. index not shown on plot"
                    rail = LabelRect(*_bounds(annotation_slot.bounds))
                    status_lines = wrap_text(
                        status_content, available_inline=max(1.0, rail.width), font_size=size,
                        font_metrics=annotation_metrics,
                        letter_spacing=float(annotation_treatment.letter_spacing),
                        text_transform=annotation_treatment.transform)
                    status_width = max(measure_text_width(
                        line, font_size=size, font_metrics=annotation_metrics,
                        letter_spacing=float(annotation_treatment.letter_spacing),
                        text_transform=annotation_treatment.transform) for line in status_lines)
                    status_height = size * line_height * len(status_lines)
                    complete_list_record(
                        annotation=annotation, resolved=resolved,
                        placement_id=f"annotation-status:{annotation_id}",
                        content=status_content, lines=status_lines,
                        text_size=(status_width, status_height), font_size=size,
                        typography_role=annotation_text_role,
                        presentation=presentation,
                        anchor_y=anchor_bounds.y + anchor_bounds.height / 2)
            if (box.leader_required or routed_tail_tip is not None) and presentation.leader_semantic_id is not None:
                anchor_center = (anchor_bounds.x + anchor_bounds.width / 2,
                                 anchor_bounds.y + anchor_bounds.height / 2)
                leader_radius = (box_radius if role_corner_radius is not None
                                 and (container is None or container.outline == "rectangle")
                                 and not tilt_angle else 0.0)
                target = (routed_tail_tip if routed_tail_tip is not None else
                          _radius_aware_box_port(bounds, anchor_center, leader_radius))
                if anchor_host is None:
                    raise _anchor_failure(annotation, "selected mark has no placed leader host")
                target_port_obstacle_id = f"port:annotation:{annotation_id}:target"
                leader_fallback = selected_leader is None
                if leader_fallback:
                    anchor_instance_id = anchor_host.placement_id.split(":", 1)[1]
                    anchor_row_id = instance_rows.get(anchor_instance_id)
                    selected_source = connector_egress_candidates(
                        anchor_host, resolved.endpoint, target,
                        comparison_clusters.get((anchor_host.source_ref, anchor_row_id), (anchor_host,)))[0]
                    points = (selected_source.semantic_port, target)
                    path_commands = ()
                    visible_route_segments = tuple(zip(points, points[1:]))
                else:
                    selected_source, route_trial, points, prefix = selected_leader
                    path_commands = ((PathCommand("move", (prefix[0],)),
                                      *(PathCommand("line", (point,)) for point in prefix[1:]),
                                      *route_trial.commands[1:])
                                     if route_trial.commands else ())
                    visible_route_segments = tuple(zip(prefix, prefix[1:])) + visible_segments(route_trial)
                if tilt_angle:
                    # The route ends at the bounds of the rotated frame; the leader goes on to the paper's edge.
                    tip = nearest_boundary_point(tilt_polygon, target)
                    if tip != target:
                        points = (*points, tip)
                        if path_commands:
                            path_commands = (*path_commands, PathCommand("line", (tip,)))
                source_side = selected_source.side
                source_port_obstacle_id = f"port:{anchor_host.placement_id}:{source_side}"
                if not surface_obstacles.has(source_port_obstacle_id):
                    register_port(source_port_obstacle_id, selected_source.exposed_port, "timeline")
                if not surface_obstacles.has(target_port_obstacle_id):
                    register_port(target_port_obstacle_id, target, "annotations")
                leader_semantic_id = presentation.leader_semantic_id
                leader_stroke_width = float(request.theme_tokens.number(
                    semantic_binding(leader_semantic_id).theme_role, "strokeWidth"))
                marker_end = (marker_geometry(
                    request.theme_tokens.marker(semantic_binding(leader_semantic_id).theme_role),
                    stroke_width=leader_stroke_width)
                              if presentation.purpose == "explanatory-arrow" else None)
                placed_leader = RelationPlacement(f"annotation-leader:{annotation_id}",
                                                  f"{resolved.object_id}:{resolved.facet}:{resolved.endpoint}:{source_side}",
                                                  f"annotation-box:{annotation_id}", tuple(points),
                                                  semantic_id=leader_semantic_id, marker_end=marker_end,
                                                  path_commands=path_commands,
                                                  annotation=presentation, source_ref=annotation_id)
                relations.append(placed_leader)
                for segment_index, (segment_start, segment_end) in enumerate(visible_route_segments):
                    if segment_start != segment_end:
                        surface_obstacles.add(SurfaceObstacle(
                            f"{placed_leader.relation_id}:segment:{segment_index}", "leader-route", "annotations",
                            ObstacleSegment(segment_start, segment_end, leader_stroke_width)))
                if leader_fallback:
                    visible_route_fallbacks.append(placed_leader)
    return SurfaceAnnotationBatch(
        tuple(text), tuple(shapes), tuple(relations), tuple(candidate_icons), tuple(placement_decisions),
        tuple(diagnostics), tuple(visible_label_overflows), tuple(visible_route_fallbacks),
        frozenset(handled_candidate_visuals), frozenset(discovered_index_suppressions),
        frozenset(discovered_callout_suppressions), tuple(diagnostic_provenance))


def comparison_marks(projection: Any) -> tuple[ComparisonMark, ...]:
    marks: list[ComparisonMark] = []
    for item in projection.items:
        for facet, value in (("planned", item.planned), ("actual", item.actual)):
            if not value:
                continue
            if item.source_type == "point" and isinstance(value.get("at"), date):
                marks.append(ComparisonMark(item.object_id, facet, "point", at=value["at"]))
            elif item.source_type == "span" and isinstance(value.get("start"), date) and isinstance(value.get("end", value.get("finish")), date):
                marks.append(ComparisonMark(item.object_id, facet, "span", start=value["start"], end=value.get("end", value.get("finish"))))
    return tuple(marks)


def annotation_anchor_bounds(mark: ComparisonMark, endpoint: str, row: RowPlacement,
                              scale: ScalePlacement, *, source_ref: str = "/",
                              annotation_id: str = "") -> LabelRect:
    if endpoint == "start":
        at = mark.start
    elif endpoint in {"finish", "end"}:
        at = mark.end
    elif endpoint == "at":
        at = mark.at
    elif endpoint == "body":
        at = mark.at or (mark.start + (mark.end - mark.start) / 2 if mark.start and mark.end else None)
    else:
        at = None
    if not isinstance(at, date):
        raise LayoutError("E_PRESENTATION_ANCHOR_MISSING", source_ref,
                          detail=f"annotation_id={_anchor_operand(annotation_id)}, "
                                 f"object_id={_anchor_operand(mark.source_id)}, "
                                 f"facet={_anchor_operand(mark.facet)}, "
                                 f"endpoint={_anchor_operand(endpoint)}, "
                                 "reason=selected mark has no resolved endpoint date")
    return LabelRect(_coordinate(at, scale), float(row.bounds.block + row.bounds.block_size * Decimal("0.35")),
                     1.0, max(2.0, float(row.bounds.block_size) * 0.2))
