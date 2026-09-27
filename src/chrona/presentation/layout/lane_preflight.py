"""Direct Layout kernel for lane preflight over closed, renderer-neutral inputs.

This partial implementation assumes semantic projection and footprint closure
have already supplied candidates. It freezes the allocation result, lane table
envelope, and seed-inline contract; it does not integrate those steps with the
render pipeline or construct candidates from Project/Actual/Comparison inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Mapping, Sequence

from chrona.presentation.layout.lane_allocation import LaneAllocationResult, LaneCandidate, allocate_lanes
from chrona.presentation.layout.model import LayoutError, LayoutManifest
from chrona.presentation.model.surface_content import (
    TableCellContent, TableColumnContent, TableColumnWidth, TableContent,
)


@dataclass(frozen=True)
class LaneInlineFrame:
    """Seed manifest geometry that is allowed to drive lane membership."""

    table_inline: Decimal
    table_inline_size: Decimal
    timeline_inline: Decimal
    timeline_inline_size: Decimal
    temporal_scale: Decimal

    def __post_init__(self) -> None:
        values = (self.table_inline, self.table_inline_size, self.timeline_inline,
                  self.timeline_inline_size, self.temporal_scale)
        if (any(not value.is_finite() for value in values)
                or self.table_inline_size <= 0 or self.timeline_inline_size <= 0
                or self.temporal_scale <= 0):
            raise LayoutError("E_LAYOUT_LANE_SEED_INVALID", "/layoutManifest")


def lane_inline_frame_for_manifest(
    manifest: LayoutManifest, *, window: tuple[date, date],
) -> LaneInlineFrame:
    """Read the exact lane-driving table/timeline inline frame from one solve."""
    if (not isinstance(manifest, LayoutManifest) or len(window) != 2
            or any(type(value) is not date for value in window)
            or window[0] >= window[1]):
        raise LayoutError("E_LAYOUT_LANE_SEED_INVALID", "/layoutManifest")
    sources = {name: tuple(item for item in manifest.decisions if item.source == name)
               for name in ("table", "timeline")}
    if any(len(items) != 1 for items in sources.values()):
        raise LayoutError("E_LAYOUT_LANE_SEED_INVALID", "/layoutManifest")
    table = sources["table"][0].bounds
    timeline = sources["timeline"][0].bounds
    # The ordinary ScalePlacement uses the same float inline-size conversion.
    ratio = float(timeline.inline_size) / max(1, (window[1] - window[0]).days)
    return LaneInlineFrame(table.inline, table.inline_size,
                           timeline.inline, timeline.inline_size, Decimal(str(ratio)))


@dataclass(frozen=True)
class LaneTableCell:
    """Exact group/lane summary values, keyed by generated lane identity."""

    lane_id: str
    label: str
    count: int | None


@dataclass(frozen=True)
class LaneMeasurementIdentity:
    """Theme/font/scale authorities used to close the seed measurements."""

    theme_identity: str
    font_asset_identity: str
    scale_identity: str

    def __post_init__(self) -> None:
        if not all((self.theme_identity, self.font_asset_identity, self.scale_identity)):
            raise LayoutError("E_LAYOUT_LANE_PLAN_INVALID", "/measuredSources")


@dataclass(frozen=True)
class SurfaceLanePlan:
    """One allocation authority retained unchanged through final realization."""

    candidates: tuple[LaneCandidate, ...]
    allocation: LaneAllocationResult
    table_cells: tuple[LaneTableCell, ...]
    natural_block_requirement: Decimal
    group_block_requirements: tuple[tuple[str, Decimal], ...]
    seed_inline_frame: LaneInlineFrame
    measurement_identity: LaneMeasurementIdentity
    as_of: date | None

    def __post_init__(self) -> None:
        if (not isinstance(self.candidates, tuple)
                or any(not isinstance(candidate, LaneCandidate) for candidate in self.candidates)
                or (self.as_of is not None and not isinstance(self.as_of, date))):
            raise LayoutError("E_LAYOUT_LANE_PLAN_INVALID", "/layoutManifest")
        if not self.natural_block_requirement.is_finite() or self.natural_block_requirement < 0:
            raise LayoutError("E_LAYOUT_LANE_PLAN_INVALID", "/layoutManifest")
        if len(self.table_cells) != len(self.allocation.lanes):
            raise LayoutError("E_LAYOUT_LANE_PLAN_INVALID", "/layoutManifest")
        expected_members = tuple(
            member.member_id
            for candidate in self.candidates
            for member in candidate.members_for_placement
        )
        allocated_members = tuple(
            member_id for lane in self.allocation.lanes for member_id in lane.members
        )
        if (len(set(expected_members)) != len(expected_members)
                or len(set(allocated_members)) != len(allocated_members)
                or set(expected_members) != set(allocated_members)):
            raise LayoutError("E_LAYOUT_LANE_PLAN_INVALID", "/body/rows/items")


def assert_lane_inline_stable(seed: LaneInlineFrame, final: LaneInlineFrame) -> None:
    """Reject block-coupled profiles that change lane-driving final inline geometry."""
    if seed != final:
        raise LayoutError("E_LAYOUT_LANE_INLINE_UNSTABLE", "/layoutManifest")


def assert_lane_plan_compatible(
    plan: SurfaceLanePlan, *, final_inline_frame: LaneInlineFrame,
    measurement_identity: LaneMeasurementIdentity, as_of: date | None,
) -> None:
    """Fail closed when final realization no longer matches its preflight closure."""
    assert_lane_inline_stable(plan.seed_inline_frame, final_inline_frame)
    if plan.measurement_identity != measurement_identity or plan.as_of != as_of:
        raise LayoutError("E_LAYOUT_LANE_PLAN_INVALID", "/layoutManifest")


def preflight_surface_lanes(
    candidates: Sequence[LaneCandidate], *,
    seed_inline_frame: LaneInlineFrame,
    measurement_identity: LaneMeasurementIdentity,
    as_of: date | None = None,
    group_titles: Mapping[str, str],
    candidate_titles: Mapping[str, str],
    lane_label: str,
    include_count: bool,
    mark_row_height: float,
    label_row_height: float,
    group_header_block_size: Decimal = Decimal(0),
    clearance: float = 0.0,
    canvas_left: float | None = None,
    canvas_right: float | None = None,
) -> SurfaceLanePlan:
    """Allocate once from closed inputs and freeze exact per-lane summary facts.

    ``candidate_titles`` and ``group_titles`` are semantic text already chosen
    by View/normalization. Their font measurement is supplied in each candidate
    width; this function does not measure fonts or derive missing footprints.
    """
    if (lane_label not in {"group", "lane"} or not group_header_block_size.is_finite()
            or group_header_block_size < 0):
        raise LayoutError("E_LAYOUT_LANE_PLAN_INVALID", "/body/rows/laneTable/label")
    candidates = tuple(candidates)
    identifiers = {item.candidate_id for item in candidates}
    if len(identifiers) != len(candidates):
        raise LayoutError("E_LAYOUT_LANE_PLAN_INVALID", "/body/rows/items")
    groups = {item.group_key for item in candidates if item.group_key}
    if identifiers != set(candidate_titles) or not groups.issubset(group_titles):
        raise LayoutError("E_LAYOUT_LANE_PLAN_INVALID", "/body/rows/laneTable")
    allocation = allocate_lanes(
        candidates, mark_row_height=mark_row_height,
        label_row_height=label_row_height, clearance=clearance,
        canvas_left=canvas_left, canvas_right=canvas_right,
    )
    cells: list[LaneTableCell] = []
    first_lane_for_group: set[str] = set()
    for lane in allocation.lanes:
        if lane_label == "group":
            label = group_titles.get(lane.group_key, "") if lane.group_key not in first_lane_for_group else ""
            first_lane_for_group.add(lane.group_key)
        else:
            label = candidate_titles[lane.representative_id]
        cells.append(LaneTableCell(lane.lane_id, label, len(lane.members) if include_count else None))
    group_requirements: dict[str, Decimal] = {}
    for lane in allocation.lanes:
        group_requirements[lane.group_key] = group_requirements.get(lane.group_key, Decimal(0)) + Decimal(str(lane.block_extent))
    for group_key in group_requirements:
        if group_key and group_header_block_size:
            group_requirements[group_key] += group_header_block_size
    # Every operand is Decimal; this is profile/block-requirement arithmetic,
    # not completed float geometry (classified by the Layout conformance gate).
    natural = sum(group_requirements.values(), Decimal(0))
    return SurfaceLanePlan(
        candidates=candidates,
        allocation=allocation,
        table_cells=tuple(cells),
        natural_block_requirement=natural,
        group_block_requirements=tuple(sorted(group_requirements.items())),
        seed_inline_frame=seed_inline_frame,
        measurement_identity=measurement_identity,
        as_of=as_of,
    )


def lane_table_measurement_content(
    *, lane_label: str, include_count: bool, group_titles: Mapping[str, str],
    candidate_titles: Mapping[str, str], selected_item_count: int,
) -> TableContent:
    """Build the conservative finite cell set measured through #487's table path."""
    if lane_label not in {"group", "lane"} or selected_item_count < 0:
        raise LayoutError("E_LAYOUT_LANE_TABLE_ENVELOPE", "/body/rows/laneTable")
    columns = (TableColumnContent("Lane", "Lane", "start", TableColumnWidth("content", "content")),)
    if include_count:
        columns += (TableColumnContent("Items", "Items", "end", TableColumnWidth("content", "content")),)
    # The envelope is independent of eventual membership and reserves both
    # possible label sources before the allocator runs.
    label_candidates = tuple(sorted(set(group_titles.values()) | set(candidate_titles.values())))
    count_bound = str(selected_item_count)
    cells = [TableCellContent(f"envelope:{index}", "Lane", text, "tableCell")
             for index, text in enumerate(label_candidates)]
    if include_count:
        cells.append(TableCellContent("envelope:count", "Items", count_bound, "tableCell"))
    return TableContent(columns, tuple(cells), (), None, ())
