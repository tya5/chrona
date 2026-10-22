"""Owns measured member-label candidates and text projection; reads the closed request, Theme treatments and Layout slot geometry."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from chrona.presentation.layout.label_chip_measurement import MeasuredLabelChip
from chrona.presentation.layout.label_footprint_measurement import (
    LabelFootprintMeasurement,
    measure_label_footprint,
)
from chrona.presentation.layout.labels import (
    LabelCandidateGeometry,
    LabelRect,
    LabelRequest,
    MemberNameAssociation,
)
from chrona.presentation.layout.surface_geometry import bounds_from_rect
from chrona.presentation.layout.surface_quality import (
    MarkPlacement,
    SlotPlacement,
    SurfaceLayoutRequest,
    TextPlacement,
)
from chrona.presentation.layout.text import measured_text_bounds, place_text


DEFAULT_MEMBER_END_GAP_EM = 2.0


@dataclass(frozen=True)
class PreparedMemberLabelCandidate:
    """One role-specific, measured candidate without a selected placement rung."""

    measurement: LabelFootprintMeasurement
    provisional: TextPlacement
    geometry: LabelCandidateGeometry
    slot_bounds: LabelRect


def project_prepared_member_text(
    prepared: PreparedMemberLabelCandidate,
    *,
    inline: float,
    baseline_block: float,
    overflow: str,
) -> TextPlacement:
    """Translate the measured run without consulting fonts a second time.

    Use the text owner's baseline-pivot arithmetic rather than adding an
    origin to a rounded rectangle. Allocation may change the selected pose;
    the measured typography, runs and font identity remain immutable.
    """
    provisional = prepared.provisional
    return replace(provisional,
        bounds=measured_text_bounds(
            inline=inline, baseline_block=baseline_block,
            width=float(provisional.bounds.inline_size),
            height=float(provisional.bounds.block_size),
            font_size=float(prepared.measurement.treatment.font_size), rotation=0),
        baseline=(inline, baseline_block), overflow=overflow)


def _member_reach(font_size: float, member_names: Mapping[str, Any]) -> float:
    """Reach bound of a member name: declared em (default 2) times label font size."""
    return float(member_names.get("maxEndGapEm", DEFAULT_MEMBER_END_GAP_EM)) * font_size


def prepare_member_label_candidate(
    label_request: LabelRequest,
    *,
    role: str,
    measured_lane_label: Any,
    request: SurfaceLayoutRequest,
    timeline_rect: LabelRect,
    slot: SlotPlacement | None,
    host: MarkPlacement | None,
    associated_member: bool,
    own_marks: tuple[MarkPlacement, ...],
    member_names: Mapping[str, Any],
    as_of_chip_measurement: MeasuredLabelChip | None,
) -> PreparedMemberLabelCandidate:
    """Prepare exactly the measurement and candidate geometry used by Layout.

    This function deliberately does not select a final position, register
    obstacles, or emit Scene content. Callers may prepare multiple
    typography-role variants and then pass their geometry to the existing
    placement solver.
    """
    measured = measure_label_footprint(
        label_request.placement_id, label_request.content, role,
        label_request.semantic_id, request, wrap=label_request.wrap,
        available_inline=timeline_rect.width * 0.4, lane_measure=measured_lane_label,
        chip_measurement_override=(as_of_chip_measurement
            if label_request.semantic_id == "asOfLabel" else None))
    size, padding, chip_measure = measured.size, measured.chip_padding, measured.chip_measurement
    font_size = float(measured.treatment.font_size)
    provisional = place_text(placement_id=label_request.placement_id, source_ref=label_request.source_ref,
        content=label_request.content, inline=0, baseline_block=font_size,
        typography_role=role, theme_tokens=request.theme_tokens,
        font_metrics=request.font_metrics, collision_region=label_request.collision_region,
        collision_domain=label_request.collision_domain, semantic_id=label_request.semantic_id,
        lane_row_id=label_request.lane_row_id, lane_member_id=label_request.lane_member_id,
        lane_source_kind=label_request.lane_source_kind, lines=measured.lines,
        estimated_delta=label_request.estimated_delta)
    bounds = label_request.bounds or timeline_rect
    if label_request.bounds is not None and measured.chip is not None:
        if chip_measure is None:
            bounds = LabelRect(bounds.x - padding[0], bounds.y - padding[1],
                bounds.width + 2 * padding[0], bounds.height + 2 * padding[1])
        else:
            safe = chip_measure.geometry.text_bounds
            bounds = LabelRect(bounds.x - measured.text_insets[0], bounds.y - measured.text_insets[1],
                bounds.width + size[0] - float(safe.inline_size),
                bounds.height + size[1] - float(safe.block_size))
    slot_bounds = LabelRect(*bounds_from_rect(slot.bounds)) if slot is not None else bounds
    reach = _member_reach(font_size, member_names)
    association = (MemberNameAssociation(LabelRect(*bounds_from_rect(host.bounds)),
        measured.leading + measured.text_insets[0], measured.text_insets[1],
        float(provisional.bounds.inline_size), float(provisional.bounds.block_size), reach)
        if associated_member else None)
    final_association = (replace(association, also_marks=tuple(
        LabelRect(*bounds_from_rect(mark.bounds)) for mark in own_marks[1:]))
        if association is not None and len(own_marks) > 1 else None)
    geometry = LabelCandidateGeometry(size=size, gap=measured.gap,
        text_inline_inset=measured.leading + measured.text_insets[0], maximum_end_gap=reach,
        association=association, final_association=final_association,
        maximum_stagger=size[1] + measured.gap if label_request.lane_row_id is not None else None,
        bounds=bounds)
    return PreparedMemberLabelCandidate(measured, provisional, geometry, slot_bounds)
