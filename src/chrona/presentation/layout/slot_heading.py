"""Completed slot headings owned by Layout: a caption over a slot, and the block it reserves (#1064).

A Layout Profile slot may declare `heading: {text, align, block}`. The engine records it with the slot's
completed bounds; this module completes one Text per drawable heading and the block each reserves at the top of
its slot. The slot keeps its full bounds (the heading is inside it); the slot's content is placed in a viewport
that starts below the heading, so no content can lie under the caption. A heading never moves another slot:
what it takes comes from its own slot, so the surface and every other bound are as they were.

Nothing here is random or depends on dictionary order: the manifest's decision order is the only order.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, TYPE_CHECKING

from chrona.presentation.layout.model import LayoutDecision, Measurement, Rect, ResolvedLayoutProfile
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.layout.surface_quality import CollisionDomain, FitWarning, SlotPlacement, TextPlacement
from chrona.presentation.layout.text import ellipsize_text, measure_text_width, metric_for_role, place_text

if TYPE_CHECKING:
    from chrona.presentation.layout.surface_axis import AxisLabelTierGeometry

SLOT_HEADING_SEMANTIC_ID = "slotHeading"
SLOT_HEADING_PLACEMENT_PREFIX = "slot-heading:"
_GAP_EM = Decimal("0.5")
_TWO = Decimal(2)


@dataclass(frozen=True)
class SlotHeadings:
    """The completed headings of one surface: Text, the block reserved per slot source, records."""

    text: tuple[TextPlacement, ...] = ()
    # Slot source -> block extent taken from the top of the slot (only for a drawn heading).
    reserve: Mapping[str, Decimal] | None = None
    diagnostics: tuple[str, ...] = ()
    warnings: tuple[FitWarning, ...] = ()
    # Slot source -> inline extent taken from the start of the slot by a `start-column` caption (#1290).
    inline_reserve: Mapping[str, Decimal] | None = None

    def reserved(self, source: str) -> Decimal:
        return (self.reserve or {}).get(source, Decimal(0))

    def reserved_inline(self, source: str) -> Decimal:
        return (self.inline_reserve or {}).get(source, Decimal(0))


def _headed_content_slots(node: Mapping[str, Any]) -> tuple[str, ...]:
    """The sources of content-block slots that declare a heading, in the profile's order."""
    found: list[str] = []
    if node.get("kind") == "slot":
        if "heading" in node and node.get("blockSize") == "content":
            found.append(str(node["source"]))
    for child in node.get("children", ()):
        found.extend(_headed_content_slots(child))
    return tuple(found)


def _start_column_slots(node: Mapping[str, Any]) -> dict[str, tuple[str, str]]:
    """Legend slots that declare `columns` and a `start-column` caption: source -> (node id, caption text) (#1290)."""
    found: dict[str, tuple[str, str]] = {}
    if node.get("kind") == "slot":
        heading = node.get("heading")
        if (isinstance(heading, Mapping) and heading.get("block") == "start-column"
                and node.get("source") == "legend" and node.get("columns")):
            found[str(node["source"])] = (str(node["id"]), str(heading["text"]))
    for child in node.get("children", ()):
        found.update(_start_column_slots(child))
    return found


def headed_slot_ids(resolved_layout: ResolvedLayoutProfile) -> frozenset[str]:
    """Declared caption targets, including optional slots omitted from a completed manifest."""
    found: set[str] = set()

    def visit(node: Mapping[str, Any]) -> None:
        if node.get("kind") == "slot" and "heading" in node:
            found.add(str(node["id"]))
        for child in node.get("children", ()):
            visit(child)

    visit(resolved_layout.profile["root"])
    return frozenset(found)


def reserve_slot_heading_blocks(measured: MeasuredSources, resolved_layout: Any, tokens: Any, *,
                                content: Any, font_metrics: Any = None) -> MeasuredSources:
    """Add a heading's block to the measurement of each content-sized slot that declares one.

    A slot sized by its content is allocated what its content measures, so the caption's line and gap are part
    of that measurement; a fixed or filling slot takes the caption from its allocation. Nothing changes without
    a declared heading.
    """
    start_column = _start_column_slots(resolved_layout.profile["root"])
    sources = [source for source in _headed_content_slots(resolved_layout.profile["root"])
               if source in measured.measurements and source not in start_column
               and source_has_content(content, source, measured_inputs=measured.inputs)]
    columns = [source for source in start_column if source in measured.measurements
               and source_has_content(content, source, measured_inputs=measured.inputs)]
    if not sources and not columns:
        return measured
    treatment = tokens.text_treatment(tokens.slot_heading_role())
    size = Decimal(str(treatment.font_size))
    reserve = size * Decimal(str(treatment.line_height)) + size * _GAP_EM
    measurements = dict(measured.measurements)
    overrides = dict(getattr(content, "slot_heading_text", ()) or ())
    for source in columns:
        # A start-column caption takes inline room beside the entries, not a block above them (#1290).
        node_id, text = start_column[source]
        metrics = metric_for_role(tokens, tokens.slot_heading_role(), font_metrics)
        width = Decimal(str(measure_text_width(
            overrides.get(node_id, text), font_size=float(treatment.font_size), font_metrics=metrics,
            letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
            numeric_spacing=treatment.numeric_spacing))) + size * _GAP_EM
        line = size * Decimal(str(treatment.line_height))
        item = measurements[source]
        measurements[source] = Measurement(
            item.min_inline + width, item.preferred_inline + width, item.max_inline + width,
            max(item.min_block, line), max(item.preferred_block, line), max(item.max_block, line),
            item.first_baseline, item.last_baseline)
    for source in sources:
        item = measurements[source]
        measurements[source] = Measurement(
            item.min_inline, item.preferred_inline, item.max_inline, item.min_block + reserve,
            item.preferred_block + reserve, item.max_block + reserve,
            None if item.first_baseline is None else item.first_baseline + reserve,
            None if item.last_baseline is None else item.last_baseline + reserve)
    return replace(measured, measurements=measurements)


def inline_content_slot(slot: SlotPlacement, reserved: Decimal) -> SlotPlacement:
    """The slot as its entries see it when a caption holds its inline-start column (#1290)."""
    if not reserved:
        return slot
    bounds = slot.bounds
    return replace(slot, bounds=Rect(bounds.inline + reserved, bounds.block,
                                     max(Decimal(0), bounds.inline_size - reserved), bounds.block_size))


def inline_full_slot(original: SlotPlacement, completed: SlotPlacement, reserved: Decimal) -> SlotPlacement:
    """The completed slot with its caption column restored before what its entries completed to."""
    if not reserved:
        return completed
    bounds = completed.bounds
    return replace(completed, bounds=Rect(original.bounds.inline, bounds.block,
                                          original.bounds.inline_size, bounds.block_size))


def content_slot(slot: SlotPlacement, reserved: Decimal) -> SlotPlacement:
    """The slot as its content sees it: the same inline extent, starting below the heading."""
    if not reserved:
        return slot
    bounds = slot.bounds
    return replace(slot, bounds=Rect(bounds.inline, bounds.block + reserved, bounds.inline_size,
                                     max(Decimal(0), bounds.block_size - reserved)))


def full_slot(original: SlotPlacement, completed_content: SlotPlacement, reserved: Decimal) -> SlotPlacement:
    """The completed slot with its heading band restored above what its content completed to."""
    if not reserved:
        return completed_content
    content = completed_content.bounds
    size = max(original.bounds.block_size, reserved + content.block_size)
    return replace(completed_content, bounds=Rect(content.inline, content.block - reserved,
                                                  original.bounds.inline_size, size))


def source_has_content(content: Any, source: str, *, measured_inputs: Mapping[str, Any] | None = None) -> bool:
    """Whether the surface has anything to put in the slot of `source`: a caption over nothing is not drawn."""
    source_input = (measured_inputs or {}).get(source)
    if source_input is not None and not source_input.content_present:
        return False
    if source == "annotations":
        return bool(content.annotations)
    if source == "notes":
        return bool(content.notes)
    if source == "legend":
        return bool(content.legend_entries)
    if source == "summary":
        return bool(content.summary.runs)
    if source == "group-details":
        return bool(content.group_details)
    if source == "milestones":
        return bool(content.milestones)
    if source == "observations":
        return bool(content.observation_rows)
    if source == "timeline-axis":
        return bool(content.axis_tiers)
    return True


def complete_slot_headings(*, request: Any, slots: Mapping[str, SlotPlacement],
                           decisions: Mapping[str, LayoutDecision],
                           axis_label_tiers: tuple[AxisLabelTierGeometry, ...] = (),
                           prepared: Mapping[str, SlotHeadings] | None = None) -> SlotHeadings:
    """Complete every declared heading of a Layout manifest, in the profile's order.

    The line box is `font size * line height` of the heading's role (`slot-heading`, else `text`), the gap under it
    half the font size. `block: top` puts the line at the slot's block start; `block: header-row` centres it in the
    `timeline-axis` slot's band when that band lies beside the slot (their block extents intersect), otherwise it
    falls back to `top` and records `I_LAYOUT_SLOT_HEADING_NO_HEADER_ROW`. The slot's content starts below the
    line and its gap, and below the band when the heading sits in it. A slot with no area, or too short for its
    heading, draws none and reserves nothing (`I_LAYOUT_SLOT_HEADING_OMITTED:<node>:too-small`). An absent
    optional slot has no decision and so no heading. A heading wider than its slot is cut with its source kept.
    A source in `prepared` reuses its already completed batch, including an omitted heading's records. This
    lets the axis's own caption establish its content viewport before native tier geometry exists, while the
    final batch still follows global node order and never measures that caption twice.
    """
    declared = tuple(item for item in decisions.values() if item.heading is not None)
    if not declared:
        return SlotHeadings()
    tokens = request.theme_tokens
    role = tokens.slot_heading_role()
    treatment = tokens.text_treatment(role)
    metrics = metric_for_role(tokens, role, request.font_metrics)
    size = Decimal(str(treatment.font_size))
    line = size * Decimal(str(treatment.line_height))
    gap = size * _GAP_EM
    shape = dict(font_size=float(treatment.font_size), font_metrics=metrics,
                 letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                 numeric_spacing=treatment.numeric_spacing)
    axis = slots.get("timeline-axis")
    text: list[TextPlacement] = []
    reserve: dict[str, Decimal] = {}
    inline_reserve: dict[str, Decimal] = {}
    diagnostics: list[str] = []
    warnings: list[FitWarning] = []
    copy_overrides = dict(request.surface_content.slot_heading_text)
    measured_sources = getattr(request, "measured_sources", None)
    measured_inputs = measured_sources.inputs if measured_sources is not None else None
    for decision in sorted(declared, key=lambda item: item.node_id):
        source = decision.source or ""
        if prepared is not None and source in prepared:
            completed = prepared[source]
            text.extend(completed.text)
            reserve.update(completed.reserve or {})
            inline_reserve.update(completed.inline_reserve or {})
            diagnostics.extend(completed.diagnostics)
            warnings.extend(completed.warnings)
            continue
        slot = slots.get(source)
        heading = decision.heading
        if slot is None or heading is None:
            continue
        if not source_has_content(request.surface_content, source, measured_inputs=measured_inputs):
            diagnostics.append(f"I_LAYOUT_SLOT_HEADING_OMITTED:{decision.node_id}:no-content")
            continue
        bounds = slot.bounds
        top, bottom = bounds.block, bounds.block + bounds.block_size
        line_top, content_start = top, top + line + gap
        aligned_baseline: float | None = None
        start_column = heading.block == "start-column"
        if start_column and not (source == "legend" and decision.columns):
            diagnostics.append(f"I_LAYOUT_SLOT_HEADING_NO_START_COLUMN:{decision.node_id}")
            start_column = False
        if start_column:
            # The caption holds the slot's inline-start column and the entries start after it (#1290).
            if bounds.inline_size <= 0 or line > bounds.block_size:
                diagnostics.append(f"I_LAYOUT_SLOT_HEADING_OMITTED:{decision.node_id}:too-small")
                continue
            available = float(bounds.inline_size)
            source_content = copy_overrides.get(decision.node_id, heading.text)
            content, disposition = source_content, "fit"
            natural = measure_text_width(content, **shape)
            if natural > available:
                content, disposition = ellipsize_text(content, available_inline=available, **shape), "ellipsized"
                warnings.append(FitWarning(
                    "W_LAYOUT_TEXT_ELLIPSIZED", f"{SLOT_HEADING_PLACEMENT_PREFIX}{decision.node_id}", source,
                    "slot-heading-text", "ellipsize-with-source", natural, float(line), available, float(line)))
            width = measure_text_width(content, **shape)
            text.append(place_text(
                placement_id=f"{SLOT_HEADING_PLACEMENT_PREFIX}{decision.node_id}", source_ref=source,
                content=content, overflow=disposition, inline=float(bounds.inline),
                baseline_block=float(top) + float(size), typography_role=role,
                theme_tokens=tokens, font_metrics=request.font_metrics,
                collision_region=f"slot-heading:{decision.node_id}",
                collision_domain=CollisionDomain("slot-heading", decision.node_id),
                source_content=source_content, semantic_id=SLOT_HEADING_SEMANTIC_ID, slot_id=slot.slot_id,
                available_inline_start=float(bounds.inline), available_inline_size=available))
            inline_reserve[source] = min(Decimal(str(width)) + gap, bounds.inline_size)
            continue
        if heading.block in {"header-row", "axis-tier"}:
            beside = (axis is not None and axis.slot_id != slot.slot_id
                      and axis.bounds.block < bottom and top < axis.bounds.block + axis.bounds.block_size)
            if heading.block == "header-row" and beside:
                band = axis.bounds
                line_top = min(max(top, band.block + (band.block_size - line) / _TWO), bottom - line)
                content_start = max(line_top + line + gap, band.block + band.block_size)
            elif heading.block == "header-row":
                diagnostics.append(f"I_LAYOUT_SLOT_HEADING_NO_HEADER_ROW:{decision.node_id}")
            else:
                tier = min(axis_label_tiers, key=lambda item: (item.bounds.block, item.tier_index), default=None)
                candidate_top = Decimal(str(tier.baseline_block)) - size if tier is not None else None
                if (beside and candidate_top is not None and top <= candidate_top
                        and candidate_top + line <= bottom):
                    line_top, aligned_baseline = candidate_top, tier.baseline_block
                    content_start = max(line_top + line + gap, axis.bounds.block + axis.bounds.block_size)
                else:
                    diagnostics.append(f"I_LAYOUT_SLOT_HEADING_NO_AXIS_TIER:{decision.node_id}")
        if bounds.inline_size <= 0 or content_start >= bottom:
            diagnostics.append(f"I_LAYOUT_SLOT_HEADING_OMITTED:{decision.node_id}:too-small")
            continue
        available = float(bounds.inline_size)
        source_content = copy_overrides.get(decision.node_id, heading.text)
        content, disposition = source_content, "fit"
        natural = measure_text_width(content, **shape)
        if natural > available:
            content, disposition = ellipsize_text(content, available_inline=available, **shape), "ellipsized"
            warnings.append(FitWarning(
                "W_LAYOUT_TEXT_ELLIPSIZED", f"{SLOT_HEADING_PLACEMENT_PREFIX}{decision.node_id}", source,
                "slot-heading-text", "ellipsize-with-source", natural, float(line), available, float(line)))
        width = measure_text_width(content, **shape)
        inline = float(bounds.inline) + {"start": 0.0, "center": max(0.0, (available - width) / 2),
                                         "end": max(0.0, available - width)}[heading.align]
        text.append(place_text(
            placement_id=f"{SLOT_HEADING_PLACEMENT_PREFIX}{decision.node_id}", source_ref=source,
            content=content, overflow=disposition, inline=inline,
            baseline_block=(aligned_baseline if aligned_baseline is not None else float(line_top) + float(size)),
            typography_role=role,
            theme_tokens=tokens, font_metrics=request.font_metrics,
            collision_region=f"slot-heading:{decision.node_id}",
            collision_domain=CollisionDomain("slot-heading", decision.node_id),
            source_content=source_content, semantic_id=SLOT_HEADING_SEMANTIC_ID, slot_id=slot.slot_id,
            available_inline_start=float(bounds.inline), available_inline_size=available))
        reserve[source] = content_start - top
    return SlotHeadings(tuple(text), reserve, tuple(diagnostics), tuple(warnings), inline_reserve)
