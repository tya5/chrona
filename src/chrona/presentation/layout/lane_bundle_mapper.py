"""Map Review projection items to closed, zero-origin lane candidate bundles."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from math import isfinite
from typing import Any, Mapping, Sequence
from urllib.parse import quote

from chrona.presentation.layout.icon_geometry import complete_icon_paths
from chrona.presentation.layout.label_visual_measurement import measure_label_visual_run
from chrona.presentation.layout.lane_allocation import (
    LaneCandidate, LaneFacetPort, LaneGlyphPartProjection, LaneIconProjection,
    LaneMark, LaneMarkFacet, LaneMember, LanePlainMarkProjection,
    LaneProgressProjection, LaneRequiredLabelProjection, LaneLabelVisualProjection,
)
from chrona.presentation.layout.lane_preflight import (
    LaneMeasurementIdentity, SurfaceLanePlan, preflight_surface_lanes,
)
from chrona.presentation.layout.lane_projection import (
    ExpectedLaneMark, LaneProjectionClosure, LaneProjectionInstance,
    close_lane_projection,
)
from chrona.presentation.layout.mark_geometry import compose_item_marks
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.obstacles import ObstacleGeometry, ObstacleRect, ObstacleSegment, obstacle_envelope
from chrona.presentation.layout.presentation import MarkBandFrame
from chrona.presentation.layout.surface_quality import IconPlacement, MarkPlacement, ScalePlacement, ShapePlacement, VisualRequest
from chrona.presentation.layout.text import measure_text_width, metric_for_role
from chrona.presentation.model.projection import ReviewProjection


@dataclass(frozen=True)
class LaneExpectedFacet:
    """One completed required primitive/path in the pre-allocation inventory."""

    instance: LaneProjectionInstance
    facet_id: str
    primitive_id: str
    purpose: str
    part_index: int | None = None


@dataclass(frozen=True)
class LaneFacetAbsence:
    """One selected visual intent that has an approved intentional absence."""

    instance: LaneProjectionInstance
    purpose: str
    reason: str


@dataclass(frozen=True)
class LaneCandidateMapping:
    """Exact mapping closure retained beside candidates for diagnostics/tests."""

    projection_closure: LaneProjectionClosure
    candidates: tuple[LaneCandidate, ...]
    expected_facets: tuple[LaneExpectedFacet, ...]
    intentional_absences: tuple[LaneFacetAbsence, ...]


def map_lane_candidates(
    projection: ReviewProjection,
    *,
    frame: MarkBandFrame,
    as_of: date | None,
    theme_tokens: Any,
    slot_id: str,
    measurement_identity: LaneMeasurementIdentity,
    font_metrics: Any,
    label_visual_requests: Mapping[LaneProjectionInstance, tuple[VisualRequest, ...]],
    icon_assets: Mapping[str, Any],
    include_finish_delta: bool,
    label_typography_role: str,
    progress_fill_source: str | None = None,
    mark_visual_requests: Mapping[tuple[LaneProjectionInstance, str], VisualRequest] | None = None,
    predecessor_relations: Mapping[str, tuple[tuple[str, str], ...]] | None = None,
) -> LaneCandidateMapping:
    """Compose marks in a zero-origin frame and close every candidate payload.

    Text comes from Review semantics; fonts and label visuals are measured by
    the shared Layout service. Icon requests are keyed by typed projection
    instance and mark role so repeated source objects cannot alias.
    """
    if (frame.block_origin != 0 or not isinstance(frame.inline_scale, ScalePlacement)
            or frame.inline_scale.scale_id != measurement_identity.scale_identity
            or getattr(font_metrics, "content_identity", None) != measurement_identity.font_asset_identity):
        raise LayoutError("E_LAYOUT_LANE_FRAME_INVALID", "/layout/markBandFrame")
    if not slot_id or progress_fill_source not in {None, "actual", "planned"}:
        raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", "/body/progressFill")
    closure = close_lane_projection(projection, as_of=as_of)
    items = _item_by_instance(projection, closure)
    group_order: dict[str, int] = {}
    for row in projection.rows:
        if row.group_id and row.group_id not in group_order:
            group_order[row.group_id] = len(group_order)

    marks_by_instance: dict[LaneProjectionInstance, tuple[MarkPlacement, ...]] = {}
    expected_by_instance: dict[LaneProjectionInstance, tuple[ExpectedLaneMark, ...]] = {}
    for expected in closure.expected_marks:
        expected_by_instance.setdefault(expected.instance, ())
        expected_by_instance[expected.instance] += (expected,)
    for instance in closure.instances:
        item = items[instance]
        composition = compose_item_marks(
            item=item, instance_id=instance.placement_key, source_kind=instance.source_kind,
            frame=frame, as_of=as_of, theme_tokens=theme_tokens, slot_id=slot_id,
            emit_missing_actual=True, emit_diagnostics=False,
        )
        expected_ids = {entry.placement_id for entry in expected_by_instance.get(instance, ())}
        marks = composition.marks
        emitted_ids = [mark.placement_id for mark in marks]
        if len(set(emitted_ids)) != len(emitted_ids) or set(emitted_ids) != expected_ids:
            raise LayoutError("E_LAYOUT_LANE_EXPECTED_MARK_SET_MISMATCH",
                              f"/projection/rows/{instance.row_id}/items/{instance.item_id}",
                              detail=f"expected={sorted(expected_ids)} emitted={sorted(emitted_ids)}")
        if any(mark.source_ref != instance.object_id for mark in marks):
            raise LayoutError("E_LAYOUT_LANE_EXPECTED_MARK_SET_MISMATCH",
                              f"/projection/rows/{instance.row_id}/items/{instance.item_id}")
        marks_by_instance[instance] = marks

    all_marks = tuple(mark for instance in closure.instances for mark in marks_by_instance[instance])
    if len({mark.placement_id for mark in all_marks}) != len(all_marks):
        raise LayoutError("E_LAYOUT_LANE_EXPECTED_MARK_SET_MISMATCH", "/layout/marks")
    visual_by_host = _compose_mark_icons(all_marks, mark_visual_requests or {}, icon_assets, theme_tokens)
    progress_by_host, progress_absences = _compose_progress(
        closure, items, marks_by_instance, progress_fill_source, theme_tokens,
    )

    roots_by_row: dict[str, list[tuple[Any, tuple[LaneProjectionInstance, ...]]]] = {}
    attached_by_host: dict[LaneProjectionInstance, list[tuple[Any, tuple[LaneProjectionInstance, ...]]]] = {}
    for row in projection.rows:
        row_instances = [instance for instance in closure.instances if instance.row_id == row.row_id]
        item_groups: dict[str, list[LaneProjectionInstance]] = {}
        for instance in row_instances:
            item_groups.setdefault(instance.object_id, []).append(instance)
        for object_id, group in item_groups.items():
            selected = _representative(group, row.table_subject_id, items)
            attached_to = {items[instance].attached_to for instance in group}
            if len(attached_to) != 1:
                raise LayoutError("E_LAYOUT_LANE_ATTACHED_HOST_INVALID",
                                  f"/projection/rows/{row.row_id}/items/{object_id}/attached_to")
            if selected.attached_to is None:
                roots_by_row.setdefault(row.row_id, []).append((selected, tuple(group)))
            else:
                host_instances = {host for child, host in closure.attached_hosts
                                  if child in group}
                if len(host_instances) != 1:
                    raise LayoutError("E_LAYOUT_LANE_ATTACHED_HOST_INVALID",
                                      f"/projection/rows/{row.row_id}/items/{object_id}/attached_to")
                host = next(iter(host_instances))
                attached_by_host.setdefault(host, []).append((selected, tuple(group)))

    candidates: list[LaneCandidate] = []
    expected_facets: list[LaneExpectedFacet] = []
    absences = [LaneFacetAbsence(item.instance, item.role, item.reason)
                for item in closure.intentional_absences]
    absences.extend(progress_absences)
    predecessor_relations = predecessor_relations or {}
    representative_instances: set[LaneProjectionInstance] = set()
    for row_index, row in enumerate(projection.rows):
        row_roots = roots_by_row.get(row.row_id, ())
        for root_item, root_variants in row_roots:
            root_instance = _instance_for_item(root_item, root_variants, items)
            child_groups = tuple(attached_by_host.get(root_instance, ()))
            member_specs = ((root_item, root_variants), *child_groups)
            members: list[LaneMember] = []
            facets_by_instance: dict[LaneProjectionInstance, tuple[LaneMarkFacet, ...]] = {}
            track_by_instance: dict[LaneProjectionInstance, str] = {}
            for representative, variants in member_specs:
                representative_instance = _instance_for_item(representative, variants, items)
                representative_instances.add(representative_instance)
                label = _measure_required_label(
                    representative, representative_instance,
                    label_visual_requests.get(representative_instance, ()),
                    icon_assets=icon_assets, theme_tokens=theme_tokens,
                    font_metrics=font_metrics, measurement_identity=measurement_identity,
                    include_finish_delta=include_finish_delta,
                    typography_role=label_typography_role,
                )
                semantic_facets: list[LaneMarkFacet] = []
                local_facets_by_instance: dict[LaneProjectionInstance, tuple[LaneMarkFacet, ...]] = {}
                for source_instance in variants:
                    source_item = items[source_instance]
                    source_facets: list[LaneMarkFacet] = []
                    for mark in marks_by_instance[source_instance]:
                        facets = _mark_facets(source_item, source_instance, mark, theme_tokens)
                        facets = _overlay_compound_facets(facets)
                        facets = _with_mark_visuals(
                            source_item, source_instance, mark, facets,
                            visual_by_host.get(mark.placement_id, ()),
                            progress_by_host.get(mark.placement_id, ()), theme_tokens,
                        )
                        for facet in facets:
                            expected_facets.append(LaneExpectedFacet(
                                source_instance, facet.facet_id, facet.primitive_id, facet.purpose,
                                (facet.icon_projection.path_index if facet.icon_projection else None)))
                        source_facets.extend(facets)
                    local_facets_by_instance[source_instance] = tuple(source_facets)
                    track_by_instance[source_instance] = source_item.track
                # Same-object source variants are exempt only when their View
                # track explicitly declares shared composition.
                for index, left_instance in enumerate(variants):
                    for right_instance in variants[index + 1:]:
                        if (items[left_instance].track == "shared"
                                and items[right_instance].track == "shared"):
                            local_facets_by_instance[left_instance] = _with_overlay_targets(
                                local_facets_by_instance[left_instance],
                                tuple(facet.facet_id for facet in local_facets_by_instance[right_instance]))
                            local_facets_by_instance[right_instance] = _with_overlay_targets(
                                local_facets_by_instance[right_instance],
                                tuple(facet.facet_id for facet in local_facets_by_instance[left_instance]))
                facets = tuple(facet for source_instance in variants
                               for facet in local_facets_by_instance[source_instance])
                representative_marks = marks_by_instance[representative_instance]
                interval_mark = next((mark for mark in representative_marks
                                      if mark.placement_id.startswith(("planned:", "actual:"))), None)
                if interval_mark is None:
                    raise LayoutError("E_LAYOUT_LANE_EXPECTED_MARK_SET_MISMATCH",
                                      f"/projection/rows/{row.row_id}/items/{representative_instance.item_id}")
                members.append(LaneMember(
                    _member_id(representative_instance),
                    LaneMark(float(interval_mark.bounds.inline),
                             float(interval_mark.bounds.inline + interval_mark.bounds.inline_size), facets),
                    label.required_inline_size, None, label,
                ))
                facets_by_instance[representative_instance] = facets

            # Attached host relations are explicit pairwise exemptions. They
            # do not create a transitive exemption to other attached children.
            root_facets = facets_by_instance[root_instance]
            rebuilt: list[LaneMember] = [members[0]]
            for member, (child_item, child_variants) in zip(members[1:], child_groups, strict=True):
                child_instance = _instance_for_item(child_item, child_variants, items)
                child_facets = facets_by_instance[child_instance]
                root_facets = _with_overlay_targets(root_facets,
                                                    tuple(facet.facet_id for facet in child_facets))
                child_facets = _with_overlay_targets(child_facets,
                                                     tuple(facet.facet_id for facet in root_facets))
                facets_by_instance[root_instance] = root_facets
                facets_by_instance[child_instance] = child_facets
                rebuilt[0] = _member_with_facets(rebuilt[0], root_facets)
                rebuilt.append(_member_with_facets(member, child_facets))
            members = rebuilt
            root_member = members[0]
            group_rank = group_order.get(row.group_id, -1)
            member_ids = tuple(member.member_id for member in members)
            candidates.append(LaneCandidate(
                root_member.member_id, row.group_id,
                (row_index, row.items.index(root_item), root_member.member_id),
                root_member.mark, root_member.title_width, root_member.delta_width,
                predecessors=predecessor_relations.get(root_member.member_id, ()),
                group_order=(group_rank, row.group_id) if group_rank >= 0 else (),
                bundle=tuple(members),
            ))
    if any(instance not in representative_instances for instance in label_visual_requests):
        raise LayoutError("E_LAYOUT_LANE_LABEL_VISUAL_UNAVAILABLE", "/body/visuals")
    if len({candidate.candidate_id for candidate in candidates}) != len(candidates):
        raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", "/projection/rows")
    return LaneCandidateMapping(closure, tuple(candidates), tuple(expected_facets), tuple(absences))


def preflight_review_lanes(
    projection: ReviewProjection,
    *, frame: MarkBandFrame, as_of: date | None, theme_tokens: Any,
    slot_id: str, measurement_identity: LaneMeasurementIdentity,
    font_metrics: Any, label_visual_requests: Mapping[LaneProjectionInstance, tuple[VisualRequest, ...]],
    icon_assets: Mapping[str, Any], include_finish_delta: bool, label_typography_role: str,
    seed_inline_frame: Any, group_titles: Mapping[str, str], lane_label: str,
    include_count: bool, group_header_block_size: Any = None,
    mark_row_height: float, label_row_height: float,
    progress_fill_source: str | None = None,
    mark_visual_requests: Mapping[tuple[LaneProjectionInstance, str], VisualRequest] | None = None,
    candidate_titles: Mapping[str, str] | None = None,
    predecessor_relations: Mapping[str, tuple[tuple[str, str], ...]] | None = None,
    clearance: float = 0.0, canvas_left: float | None = None, canvas_right: float | None = None,
) -> tuple[LaneCandidateMapping, SurfaceLanePlan]:
    """Map the exact Review closure, then allocate once into immutable preflight."""
    from decimal import Decimal

    mapped = map_lane_candidates(
        projection, frame=frame, as_of=as_of, theme_tokens=theme_tokens, slot_id=slot_id,
        measurement_identity=measurement_identity, font_metrics=font_metrics,
        label_visual_requests=label_visual_requests, icon_assets=icon_assets,
        include_finish_delta=include_finish_delta, label_typography_role=label_typography_role,
        progress_fill_source=progress_fill_source, mark_visual_requests=mark_visual_requests,
        predecessor_relations=predecessor_relations,
    )
    group_header = group_header_block_size if group_header_block_size is not None else Decimal(0)
    title_map = dict(candidate_titles or {
        candidate.candidate_id: candidate.members_for_placement[0].required_label.title
        for candidate in mapped.candidates
    })
    plan = preflight_surface_lanes(
        mapped.candidates, seed_inline_frame=seed_inline_frame,
        measurement_identity=measurement_identity, as_of=as_of,
        group_titles=group_titles, candidate_titles=title_map,
        lane_label=lane_label, include_count=include_count,
        mark_row_height=mark_row_height, label_row_height=label_row_height,
        group_header_block_size=group_header, clearance=clearance,
        canvas_left=canvas_left, canvas_right=canvas_right,
    )
    return mapped, plan


def _item_by_instance(projection: ReviewProjection, closure: LaneProjectionClosure) -> dict[LaneProjectionInstance, Any]:
    result: dict[LaneProjectionInstance, Any] = {}
    for row in projection.rows:
        for item in row.items:
            instance = next((value for value in closure.instances
                             if value.row_id == row.row_id
                             and value.item_id == (item.item_id or item.object_id)), None)
            if instance is None:
                raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", f"/projection/rows/{row.row_id}")
            result[instance] = item
    return result


def _representative(instances: Sequence[LaneProjectionInstance], table_subject_id: str,
                    items: Mapping[LaneProjectionInstance, Any]) -> Any:
    ordered = [items[instance] for instance in instances]
    subject = next((item for item in ordered if item.item_id == table_subject_id), None)
    if subject is not None:
        return subject
    primary = [item for item in ordered if item.source_kind in {"primary", "combined"}]
    return primary[0] if primary else ordered[0]


def _instance_for_item(item: Any, variants: Sequence[LaneProjectionInstance],
                       items: Mapping[LaneProjectionInstance, Any]) -> LaneProjectionInstance:
    return next(instance for instance in variants if items[instance] is item)


def _member_id(instance: LaneProjectionInstance) -> str:
    return f"member:{instance.placement_key}"


def _measure_required_label(item: Any, instance: LaneProjectionInstance,
                            visual_requests: tuple[VisualRequest, ...], *, icon_assets: Mapping[str, Any],
                            theme_tokens: Any, font_metrics: Any,
                            measurement_identity: LaneMeasurementIdentity,
                            include_finish_delta: bool, typography_role: str) -> LaneRequiredLabelProjection:
    if not item.title:
        raise LayoutError("E_LAYOUT_LANE_LABEL_VISUAL_UNAVAILABLE", f"/projection/items/{instance.item_id}/title")
    delta = f"{item.finish_delta:+d}d" if include_finish_delta and item.finish_delta is not None else None
    content = " ".join(value for value in (item.title, delta) if value)
    placement_id = f"member-label:{instance.placement_key}"
    normalized_requests = tuple(
        replace(request, target_kind="plot-label", selector=(("id", instance.placement_key),))
        for request in visual_requests
    )
    measured = measure_label_visual_run(
        placement_id, content, typography_role, visual_requests=normalized_requests,
        icon_assets=dict(icon_assets), theme_tokens=theme_tokens, font_metrics=font_metrics,
    )
    leading: list[LaneLabelVisualProjection] = []
    trailing: list[LaneLabelVisualProjection] = []
    treatment = theme_tokens.text_treatment(typography_role)
    leading_cursor = 0.0
    for visual, icon, width, gap in measured.visuals:
        if visual.side == "trailing":
            continue
        top = (measured.text_block_size - width * icon.viewport[1] / icon.viewport[0]) / 2
        value = LaneLabelVisualProjection(
            visual.side, icon.icon_id, icon.content_identity, tuple(icon.viewport),
            float(width), float(measured.text_block_size), float(gap),
            Rect(Decimal(str(leading_cursor)), Decimal(str(top)), Decimal(str(width)),
                 Decimal(str(width * icon.viewport[1] / icon.viewport[0]))),
            icon.alternative, bool(visual.decorative),
        )
        leading.append(value)
        leading_cursor += width + gap
    trailing_cursor = leading_cursor + measured.text_width
    for visual, icon, width, gap in measured.visuals:
        if visual.side != "trailing":
            continue
        height = width * icon.viewport[1] / icon.viewport[0]
        top = (measured.text_block_size - height) / 2
        value = LaneLabelVisualProjection(
            visual.side, icon.icon_id, icon.content_identity, tuple(icon.viewport),
            float(width), float(measured.text_block_size), float(gap),
            Rect(Decimal(str(trailing_cursor)), Decimal(str(top)), Decimal(str(width)),
                 Decimal(str(height))),
            icon.alternative, bool(visual.decorative),
        )
        trailing.append(value)
        trailing_cursor += width + gap
    metric = metric_for_role(theme_tokens, typography_role, font_metrics)
    delta_width = (measure_text_width(
        delta, font_size=float(treatment.font_size), font_metrics=metric,
        letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
        numeric_spacing=treatment.numeric_spacing,
    ) if delta is not None else None)
    return LaneRequiredLabelProjection(
        item.title, delta, content, typography_role, treatment.paint_content(content),
        treatment.family, treatment.weight, float(treatment.font_size),
        float(treatment.line_height), float(treatment.letter_spacing),
        treatment.transform, treatment.numeric_spacing,
        measurement_identity.theme_identity, measurement_identity.font_asset_identity,
        measurement_identity.scale_identity, measured.text_width, delta_width,
        measured.text_block_size,
        tuple(leading), tuple(trailing),
    )


def _compose_mark_icons(marks: Sequence[MarkPlacement],
                        requests: Mapping[tuple[LaneProjectionInstance, str], VisualRequest],
                        icon_assets: Mapping[str, Any], theme_tokens: Any) -> dict[str, tuple[IconPlacement, ...]]:
    result: dict[str, list[IconPlacement]] = {}
    for (instance, role), visual in requests.items():
        hosts = [mark for mark in marks if mark.placement_id == f"{role}:{instance.placement_key}"]
        icon = icon_assets.get(visual.ref or "")
        if len(hosts) != 1 or icon is None:
            raise LayoutError("E_LAYOUT_LANE_ICON_UNAVAILABLE", visual.source_ref)
        host = hosts[0]
        try:
            scale, _ = theme_tokens.icon_ratios("icon-mark")
        except Exception as error:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref) from error
        height = float(host.bounds.block_size) * float(scale)
        if height <= 0 or icon.viewport[1] <= 0:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref)
        width = min(float(host.bounds.inline_size), height * icon.viewport[0] / icon.viewport[1])
        bounds = Rect(host.bounds.inline + (host.bounds.inline_size - Decimal(str(width))) / 2,
                      host.bounds.block + (host.bounds.block_size - Decimal(str(height))) / 2,
                      Decimal(str(width)), Decimal(str(height)))
        placement = IconPlacement(
            f"visual:{host.placement_id}", host.source_ref, visual.source_ref, icon.icon_id,
            icon.kind, icon.content_identity, icon.viewport, icon.payload, icon.alternative,
            visual.decorative, bounds, "iconMark", width / icon.viewport[0], host.slot_id,
            paint_order=host.paint_order + 1,
            completed_paths=complete_icon_paths(icon.payload,
                                                (float(bounds.inline), float(bounds.block),
                                                 float(bounds.inline_size), float(bounds.block_size)),
                                                width / icon.viewport[0]) if icon.kind == "vector" else (),
        )
        result.setdefault(host.placement_id, []).append(placement)
    return {key: tuple(values) for key, values in result.items()}


def _compose_progress(closure: LaneProjectionClosure, items: Mapping[LaneProjectionInstance, Any],
                      marks: Mapping[LaneProjectionInstance, tuple[MarkPlacement, ...]],
                      source: str | None, theme: Any,
                      ) -> tuple[dict[str, tuple[Any, ...]], list[LaneFacetAbsence]]:
    if source is None:
        return {}, []
    from chrona.presentation.layout.surface_composer import progress_fill_bounds

    try:
        inset, radius = theme.progress_track("progress-fill")
    except Exception as error:
        raise LayoutError("E_LAYOUT_LANE_PROGRESS_UNAVAILABLE", "/body/progressFill") from error
    result: dict[str, list[Any]] = {}
    absences: list[LaneFacetAbsence] = []
    for instance in closure.instances:
        item = items[instance]
        fraction = ((item.actual or {}).get("progress") if source == "actual"
                    else item.planned_progress)
        prefix = "actual" if source == "actual" else "planned"
        host = next((mark for mark in marks[instance]
                     if mark.placement_id.startswith(prefix + ":")), None)
        if not isinstance(fraction, (int, float)) or isinstance(fraction, bool):
            absences.append(LaneFacetAbsence(instance, "progress", "fraction-unavailable"))
            continue
        if not isfinite(float(fraction)) or not 0 <= fraction <= 1:
            raise LayoutError("E_LAYOUT_LANE_PROGRESS_INVALID",
                              f"/projection/rows/{instance.row_id}/items/{instance.item_id}/progress")
        if fraction == 0:
            absences.append(LaneFacetAbsence(instance, "progress", "zero-fraction"))
            continue
        if host is None:
            absences.append(LaneFacetAbsence(instance, "progress", "host-mark-unavailable"))
            continue
        bounds = progress_fill_bounds(host.bounds, float(fraction), inset)
        if bounds is None:
            absences.append(LaneFacetAbsence(instance, "progress", "empty-fill"))
            continue
        shape = ShapePlacement(
            f"progress-fill:{host.placement_id}", item.object_id, "Rect", bounds,
            clip_host_id=host.placement_id, paint_order=host.paint_order + 1,
            semantic_id="progressFill", corner_radius=float(radius),
        )
        if not _rect_contains(host.bounds, shape.bounds):
            raise LayoutError("E_LAYOUT_LANE_PROGRESS_INVALID", shape.placement_id)
        result.setdefault(host.placement_id, []).append(shape)
    return {key: tuple(values) for key, values in result.items()}, absences


def _mark_facets(item: Any, instance: LaneProjectionInstance, mark: MarkPlacement,
                 theme: Any) -> tuple[LaneMarkFacet, ...]:
    if mark.mark_shape == "span":
        bounds = _bounds(mark.bounds)
        width = _stroke_width(theme, mark.semantic_id)
        footprint = _expanded_rect(bounds, width / 2 if width is not None else 0.0, mark.placement_id)
        payload = LanePlainMarkProjection(mark.mark_shape, mark.semantic_id, mark.paint_order,
                                          mark.corner_radius, mark.end_treatment)
        return (_facet(instance, item, mark, mark.placement_id, "Rect",
                       (("rect", _rect_points(bounds)),), bounds, footprint,
                       mark, plain=payload),)
    if not mark.symbol_parts:
        raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", mark.placement_id)
    result: list[LaneMarkFacet] = []
    for index, part in enumerate(mark.symbol_parts):
        commands = _commands(part.commands)
        points = tuple(point for _, pairs in commands for point in pairs)
        if not points:
            raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", mark.placement_id)
        bounds = _point_bounds(points)
        stroke_width = _stroke_width(theme, mark.semantic_id) if part.paint_mode == "stroke" else None
        if part.paint_mode == "stroke" and (stroke_width is None or stroke_width <= 0):
            raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", mark.placement_id,
                              detail="stroke glyph has no finite positive Theme width")
        footprint = _path_footprint(points, stroke_width, mark.placement_id)
        part_payload = LaneGlyphPartProjection(
            index, mark.semantic_id, mark.paint_order + index,
            part.paint_mode, part.paint_color,
            mark.mark_shape, mark.corner_radius, mark.end_treatment,
        )
        primitive_id = mark.placement_id if len(mark.symbol_parts) == 1 else f"{mark.placement_id}:part:{index}"
        result.append(_facet(instance, item, mark, primitive_id, "Symbol", commands,
                             bounds, footprint, mark if index == 0 else None,
                             glyph=part_payload))
    return tuple(result)


def _with_mark_visuals(item: Any, instance: LaneProjectionInstance, mark: MarkPlacement,
                       facets: tuple[LaneMarkFacet, ...], icons: Sequence[IconPlacement],
                       progress: Sequence[Any], theme: Any) -> tuple[LaneMarkFacet, ...]:
    result = list(facets)
    for icon in icons:
        icon_facets = _overlay_all(_icon_facets(item, instance, icon))
        result.extend(_with_overlay_targets(icon_facets,
                                            tuple(facet.facet_id for facet in facets)))
        result[:len(facets)] = list(_with_overlay_targets(tuple(result[:len(facets)]),
                                                         tuple(facet.facet_id for facet in icon_facets)))
    for shape in progress:
        bounds = _bounds(shape.bounds)
        width = _stroke_width(theme, "progress-fill")
        footprint = _expanded_rect(bounds, width / 2 if width is not None else 0.0, shape.placement_id)
        host = mark
        payload = LaneProgressProjection(host.placement_id, host.bounds, shape.bounds,
                                         shape.semantic_id, shape.paint_order,
                                         shape.corner_radius)
        result.append(_facet(instance, item, mark, shape.placement_id, "Rect",
                             (("rect", _rect_points(bounds)),), bounds, footprint, None,
                             progress=payload))
        result[-1] = _with_overlay_targets((result[-1],),
                                           tuple(facet.facet_id for facet in facets))[0]
        # The host relation is symmetric and restricted to this exact mark.
        result[:len(facets)] = list(_with_overlay_targets(tuple(result[:len(facets)]),
                                                         (result[-1].facet_id,)))
    return tuple(result)


def _icon_facets(item: Any, instance: LaneProjectionInstance,
                 icon: IconPlacement) -> tuple[LaneMarkFacet, ...]:
    if icon.kind == "raster":
        if not isinstance(icon.payload, bytes) or not icon.payload:
            raise LayoutError("E_LAYOUT_LANE_ICON_UNAVAILABLE", icon.placement_id)
        bounds = _bounds(icon.bounds)
        projection = LaneIconProjection(
            icon.placement_id, icon.icon_id, "raster", icon.asset_identity,
            icon.viewport, icon.bounds, icon.visual_capability_source_ref,
            icon.alternative, icon.decorative, icon.slot_id, icon.paint_order,
            icon.stroke_scale, raster_payload=icon.payload,
        )
        return (_facet(instance, item, None, icon.placement_id, "Icon",
                       (("viewport", _rect_points(bounds)),), bounds,
                       _expanded_rect(bounds, 0, icon.placement_id), None,
                       icon=projection),)
    if icon.kind != "vector" or not icon.completed_paths:
        raise LayoutError("E_LAYOUT_LANE_ICON_UNAVAILABLE", icon.placement_id)
    result: list[LaneMarkFacet] = []
    count = len(icon.completed_paths)
    for index, path in enumerate(icon.completed_paths):
        commands = _commands(path.commands)
        points = tuple(point for _, pairs in commands for point in pairs)
        if not points:
            raise LayoutError("E_LAYOUT_LANE_ICON_UNAVAILABLE", icon.placement_id)
        bounds = _point_bounds(points)
        width = path.stroke_width
        if path.paint == "stroke" and (width is None or not isfinite(width) or width <= 0):
            raise LayoutError("E_LAYOUT_LANE_ICON_UNAVAILABLE", icon.placement_id,
                              detail="stroke icon path has no finite positive width")
        projection = LaneIconProjection(
            icon.placement_id, icon.icon_id, "vector", icon.asset_identity,
            icon.viewport, icon.bounds, icon.visual_capability_source_ref,
            icon.alternative, icon.decorative, icon.slot_id, icon.paint_order,
            icon.stroke_scale, path_index=index, path_count=count,
            paint=path.paint, stroke_width=width, line_cap=path.line_cap,
            line_join=path.line_join,
        )
        result.append(_facet(instance, item, None, icon.placement_id, "Icon",
                             commands, bounds, _path_footprint(points, width, icon.placement_id),
                             None, icon=projection, facet_suffix=f"path:{index}"))
    return tuple(result)


def _facet(instance: LaneProjectionInstance, item: Any, mark: MarkPlacement | None,
           primitive_id: str, primitive_type: str, commands: tuple,
           bounds: tuple[float, float, float, float], footprint: ObstacleGeometry,
           port_mark: MarkPlacement | None, *, plain=None, glyph=None,
           progress=None, icon=None, facet_suffix: str | None = None) -> LaneMarkFacet:
    source_item = item.item_id or item.object_id
    purpose = ("progress" if progress is not None else "icon" if icon is not None else
               mark.semantic_id if mark is not None else "mark")
    id_value = facet_suffix or primitive_id
    facet_id = f"{instance.placement_key}:{quote(purpose, safe='-._~')}:{quote(id_value, safe='-._~')}"
    ports: tuple[LaneFacetPort, ...] = ()
    host_bounds = None
    if port_mark is not None:
        ports = (
            LaneFacetPort(f"{instance.placement_key}:{quote(primitive_id, safe='-._~')}:start",
                          "start", port_mark.start_port),
            LaneFacetPort(f"{instance.placement_key}:{quote(primitive_id, safe='-._~')}:end",
                          "end", port_mark.end_port),
        )
        host_bounds = _bounds(port_mark.bounds)
    return LaneMarkFacet(
        facet_id, instance.placement_key, source_item, item.object_id,
        "primary" if item.source_kind == "combined" else item.source_kind,
        purpose, primitive_id, primitive_type, commands, bounds, footprint,
        ports, port_host_bounds=host_bounds, icon_projection=icon,
        plain_mark_projection=plain, glyph_part_projection=glyph,
        progress_projection=progress,
    )


def _source_kind(item: Any, purpose: str) -> str:
    if purpose == "actual":
        return "actual"
    if purpose in {"snapshot", "scenario"}:
        return purpose
    return "primary" if item.source_kind == "combined" else item.source_kind


def _stroke_width(theme: Any, role: str) -> float | None:
    value = theme.optional_number(role, "strokeWidth")
    if value is None:
        return None
    width = float(value)
    if not isfinite(width) or width < 0:
        raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", f"/body/roles/{role}/strokeWidth")
    return width


def _path_footprint(points: tuple[tuple[float, float], ...], stroke_width: float | None,
                    path: str) -> ObstacleGeometry:
    if stroke_width is not None and len(points) == 2 and points[0] != points[1]:
        return ObstacleSegment(points[0], points[1], stroke_width=stroke_width)
    bounds = _point_bounds(points)
    if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
        if len(points) >= 2 and points[0] != points[-1]:
            return ObstacleSegment(points[0], points[-1], stroke_width=stroke_width or 0.0)
        raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", path)
    return _expanded_rect(bounds, 10 * stroke_width if stroke_width is not None else 0.0, path)


def _expanded_rect(bounds: tuple[float, float, float, float], expansion: float,
                   path: str) -> ObstacleRect:
    left, top, right, bottom = bounds
    result = ObstacleRect(left - expansion, top - expansion,
                          right + expansion, bottom + expansion)
    if not all(isfinite(value) for value in (result.left, result.top, result.right, result.bottom)):
        raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", path)
    return result


def _bounds(rect: Rect) -> tuple[float, float, float, float]:
    left, top = float(rect.inline), float(rect.block)
    return left, top, left + float(rect.inline_size), top + float(rect.block_size)


def _rect_points(bounds: tuple[float, float, float, float]) -> tuple[tuple[float, float], ...]:
    left, top, right, bottom = bounds
    return ((left, top), (right, top), (right, bottom), (left, bottom))


def _commands(commands: Sequence[Any]) -> tuple[tuple[str, tuple[tuple[float, float], ...]], ...]:
    result = tuple((command.kind, tuple(tuple(point) for point in command.points))
                   if hasattr(command, "kind") else
                   (command[0], tuple(tuple(point) for point in command[1]))
                   for command in commands)
    if (not result or any(not all(isinstance(value, (int, float)) and isfinite(value)
                                  for point in points for value in point)
                          for _, points in result)):
        raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", "/layout/geometry")
    return result


def _point_bounds(points: Sequence[tuple[float, float]]) -> tuple[float, float, float, float]:
    if not points:
        raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", "/layout/geometry")
    return (min(point[0] for point in points), min(point[1] for point in points),
            max(point[0] for point in points), max(point[1] for point in points))


def _rect_contains(host: Rect, child: Rect) -> bool:
    return (host.inline <= child.inline and host.block <= child.block
            and host.inline + host.inline_size >= child.inline + child.inline_size
            and host.block + host.block_size >= child.block + child.block_size)


def _overlay_compound_facets(facets: tuple[LaneMarkFacet, ...]) -> tuple[LaneMarkFacet, ...]:
    return _with_overlay_targets(
        facets, tuple(other.facet_id for other in facets)) if len(facets) > 1 else facets


def _overlay_all(facets: tuple[LaneMarkFacet, ...]) -> tuple[LaneMarkFacet, ...]:
    return tuple(_with_overlay_targets((facet,),
                                       tuple(other.facet_id for other in facets if other is not facet))[0]
                 for facet in facets)


def _with_overlay_targets(facets: tuple[LaneMarkFacet, ...], targets: tuple[str, ...]
                          ) -> tuple[LaneMarkFacet, ...]:
    return tuple(replace(facet, overlay_with=tuple(dict.fromkeys((*facet.overlay_with,
                                                                  *(target for target in targets
                                                                    if target != facet.facet_id)))))
                 for facet in facets)


def _member_with_facets(member: LaneMember, facets: tuple[LaneMarkFacet, ...]) -> LaneMember:
    mark = LaneMark(member.mark.left, member.mark.right, facets)
    return LaneMember(member.member_id, mark, member.title_width, member.delta_width,
                      member.required_label)
