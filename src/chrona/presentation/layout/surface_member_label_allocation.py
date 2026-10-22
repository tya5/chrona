"""Owns measured member-name group allocation and the bounded exchange; reads candidate cursors and completed obstacles."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, TYPE_CHECKING

from chrona.presentation.layout.labels import LabelPlacement, LabelRect, LabelRequest
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacle, SurfaceObstacleIndex
from chrona.presentation.layout.surface_geometry import bounds_from_rect
from chrona.presentation.layout.surface_member_label_measurement import (
    PreparedMemberLabelCandidate, project_prepared_member_text,
)
from chrona.presentation.layout.surface_quality import MarkPlacement

if TYPE_CHECKING:
    from chrona.presentation.layout.labels import MemberNameSearchCursor


@dataclass
class MemberLabelAllocation:
    request: LabelRequest
    prepared: PreparedMemberLabelCandidate
    variants: Mapping[str, PreparedMemberLabelCandidate]
    styles: Mapping[str, Any]
    host: MarkPlacement | None
    own_marks: tuple[MarkPlacement, ...]
    associated_member: bool
    delta_extra: float
    candidate: LabelPlacement | None
    search: MemberNameSearchCursor | None = None
    exchanged: bool = False
    forced_suppression: bool = False

    def selected_preparation(self) -> PreparedMemberLabelCandidate:
        return (self.variants[self.candidate.side]
                if self.candidate is not None and self.variants else self.prepared)

    @property
    def movable(self) -> bool:
        return (self.associated_member and not self.request.is_required_before_routes
                and self.search is not None and not self.exchanged
                and self.candidate is not None and not self.candidate.visible_overflow)


def member_text_candidate(prepared: PreparedMemberLabelCandidate,
                          candidate: LabelPlacement) -> LabelPlacement:
    """Inset a full visual footprint to its measured text ground."""
    measurement = prepared.measurement
    if measurement.chip is None:
        return candidate
    box = candidate.bounds
    if measurement.chip_measurement is None:
        horizontal, vertical = measurement.chip_padding
        bounds = LabelRect(box.x + horizontal, box.y + vertical,
            box.width - 2 * horizontal, box.height - 2 * vertical)
    else:
        safe = measurement.chip_measurement.geometry.text_bounds
        bounds = LabelRect(box.x + measurement.text_insets[0], box.y + measurement.text_insets[1],
            float(safe.inline_size), float(safe.block_size))
    return replace(candidate, bounds=bounds)


def member_group_obstacles(allocation: MemberLabelAllocation) -> tuple[SurfaceObstacle, ...]:
    """Explicit full-group ownership, without emitting Scene primitives."""
    candidate = allocation.candidate
    if candidate is None:
        return ()
    prepared = allocation.selected_preparation()
    text_candidate = member_text_candidate(prepared, candidate)
    measured_text = project_prepared_member_text(prepared,
        inline=text_candidate.bounds.x + prepared.measurement.leading,
        baseline_block=text_candidate.bounds.y + float(prepared.measurement.treatment.font_size), overflow="fit")
    inline, block, width, height = bounds_from_rect(measured_text.bounds)
    placement_id, slot = allocation.request.placement_id, allocation.request.collision_domain.slot
    text = ((SurfaceObstacle(placement_id, "text", slot,
                ObstacleRect(inline, block, inline + width, block + height)),)
            if width > 0 and height > 0 else ())
    box = candidate.bounds
    return (*text, SurfaceObstacle(f"label-footprint:{placement_id}", "label-visual", slot,
        ObstacleRect(box.x, box.y, box.right, box.bottom)))


def exchange_member_name(later: MemberLabelAllocation, earlier: tuple[MemberLabelAllocation, ...],
                         obstacles: SurfaceObstacleIndex
                         ) -> tuple[MemberLabelAllocation, tuple[str, ...]] | None:
    """Try one atomic exchange using only the two requests' existing domains.

    Failed probes consume the earlier cursor, never its accepted placement.
    Group IDs come from explicit Layout registration, not identity parsing.
    Previously exchanged groups are fixed, so a later request cannot cascade.
    The returned IDs are the old earlier group to replace in the owner's index.
    """
    if (later.search is None or later.candidate is not None or not later.associated_member
            or later.request.is_required_before_routes):
        return None
    owners = {obstacle.placement_id: allocation for allocation in earlier if allocation.movable
              for obstacle in member_group_obstacles(allocation)}
    for evidence in later.search.evaluated_normal_candidates:
        current = later.search.revalidate(evidence, obstacles)
        if current is None:
            continue
        blocker_ids = current.blocker_placement_ids
        if not current.occupied or not blocker_ids:
            continue
        first = owners.get(blocker_ids[0])
        if first is None or any(owners.get(key) is not first for key in blocker_ids):
            continue
        old_ids = tuple(obstacle.placement_id for obstacle in member_group_obstacles(first))
        held_later = replace(later, candidate=current.placement)
        probe = obstacles.copy(excluded_ids=old_ids)
        probe.extend(member_group_obstacles(held_later))
        assert first.search is not None
        alternative = first.search.next_clear(probe)
        if alternative is None:
            continue
        # Neither accepted allocation nor the caller's index changes until both
        # names have normally clear completed geometry.
        first.candidate = alternative.placement
        later.candidate = current.placement
        first.exchanged = later.exchanged = True
        return first, old_ids
    return None


def repair_member_names(allocations: tuple[MemberLabelAllocation, ...],
                        obstacles: SurfaceObstacleIndex) -> SurfaceObstacleIndex:
    """Close the failed-name queue without reordering normal admission.

    Only the already-generated failed candidates and successful names' existing
    unconsumed domains are available. Every probe sees all completed normal
    groups and prior repairs, including later-admitted fixed names.
    """
    current = obstacles
    for index in range(len(allocations) - 1, -1, -1):
        allocation = allocations[index]
        exchanged = exchange_member_name(allocation, allocations[:index], current)
        if exchanged is None:
            continue
        earlier, old_ids = exchanged
        current = current.copy(excluded_ids=old_ids)
        current.extend(member_group_obstacles(earlier))
        current.extend(member_group_obstacles(allocation))
    return current
