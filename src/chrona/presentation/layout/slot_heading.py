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
from typing import Any

from chrona.presentation.layout.model import LayoutDecision, Measurement, Rect
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.layout.surface_quality import CollisionDomain, FitWarning, SlotPlacement, TextPlacement
from chrona.presentation.layout.text import ellipsize_text, measure_text_width, metric_for_role, place_text

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

    def reserved(self, source: str) -> Decimal:
        return (self.reserve or {}).get(source, Decimal(0))


def _headed_content_slots(node: Mapping[str, Any]) -> tuple[str, ...]:
    """The sources of content-block slots that declare a heading, in the profile's order."""
    found: list[str] = []
    if node.get("kind") == "slot":
        if "heading" in node and node.get("blockSize") == "content":
            found.append(str(node["source"]))
    for child in node.get("children", ()):
        found.extend(_headed_content_slots(child))
    return tuple(found)


def reserve_slot_heading_blocks(measured: MeasuredSources, resolved_layout: Any, tokens: Any, *,
                                content: Any) -> MeasuredSources:
    """Add a heading's block to the measurement of each content-sized slot that declares one.

    A slot sized by its content is allocated what its content measures, so the caption's line and gap are part
    of that measurement; a fixed or filling slot takes the caption from its allocation. Nothing changes without
    a declared heading.
    """
    sources = [source for source in _headed_content_slots(resolved_layout.profile["root"])
               if source in measured.measurements and source_has_content(content, source)]
    if not sources:
        return measured
    treatment = tokens.text_treatment(tokens.slot_heading_role())
    size = Decimal(str(treatment.font_size))
    reserve = size * Decimal(str(treatment.line_height)) + size * _GAP_EM
    measurements = dict(measured.measurements)
    for source in sources:
        item = measurements[source]
        measurements[source] = Measurement(
            item.min_inline, item.preferred_inline, item.max_inline, item.min_block + reserve,
            item.preferred_block + reserve, item.max_block + reserve,
            None if item.first_baseline is None else item.first_baseline + reserve,
            None if item.last_baseline is None else item.last_baseline + reserve)
    return replace(measured, measurements=measurements)


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
    return replace(completed_content, bounds=Rect(original.bounds.inline, original.bounds.block,
                                                  original.bounds.inline_size, size))


def source_has_content(content: Any, source: str) -> bool:
    """Whether the surface has anything to put in the slot of `source`: a caption over nothing is not drawn."""
    if source == "annotations":
        return bool(content.annotations)
    if source == "notes":
        return bool(content.notes)
    if source == "legend":
        return bool(content.legend_entries)
    if source == "summary":
        return bool(content.summary.runs)
    return True


def complete_slot_headings(*, request: Any, slots: Mapping[str, SlotPlacement],
                           decisions: Mapping[str, LayoutDecision]) -> SlotHeadings:
    """Complete every declared heading of a Layout manifest, in the profile's order.

    The line box is `font size * line height` of the heading's role (`slot-heading`, else `text`), the gap under it
    half the font size. `block: top` puts the line at the slot's block start; `block: header-row` centres it in the
    `timeline-axis` slot's band when that band lies beside the slot (their block extents intersect), otherwise it
    falls back to `top` and records `I_LAYOUT_SLOT_HEADING_NO_HEADER_ROW`. The slot's content starts below the
    line and its gap, and below the band when the heading sits in it. A slot with no area, or too short for its
    heading, draws none and reserves nothing (`I_LAYOUT_SLOT_HEADING_OMITTED:<node>:too-small`). An absent
    optional slot has no decision and so no heading. A heading wider than its slot is cut with its source kept.
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
    diagnostics: list[str] = []
    warnings: list[FitWarning] = []
    for decision in sorted(declared, key=lambda item: item.node_id):
        source = decision.source or ""
        slot = slots.get(source)
        heading = decision.heading
        if slot is None or heading is None:
            continue
        if not source_has_content(request.surface_content, source):
            diagnostics.append(f"I_LAYOUT_SLOT_HEADING_OMITTED:{decision.node_id}:no-content")
            continue
        bounds = slot.bounds
        top, bottom = bounds.block, bounds.block + bounds.block_size
        line_top, content_start = top, top + line + gap
        if heading.block == "header-row":
            beside = (axis is not None and axis.slot_id != slot.slot_id
                      and axis.bounds.block < bottom and top < axis.bounds.block + axis.bounds.block_size)
            if beside:
                band = axis.bounds
                line_top = min(max(top, band.block + (band.block_size - line) / _TWO), bottom - line)
                content_start = max(line_top + line + gap, band.block + band.block_size)
            else:
                diagnostics.append(f"I_LAYOUT_SLOT_HEADING_NO_HEADER_ROW:{decision.node_id}")
        if bounds.inline_size <= 0 or content_start >= bottom:
            diagnostics.append(f"I_LAYOUT_SLOT_HEADING_OMITTED:{decision.node_id}:too-small")
            continue
        available = float(bounds.inline_size)
        content, disposition = heading.text, "fit"
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
            baseline_block=float(line_top) + float(size), typography_role=role,
            theme_tokens=tokens, font_metrics=request.font_metrics,
            collision_region=f"slot-heading:{decision.node_id}",
            collision_domain=CollisionDomain("slot-heading", decision.node_id),
            source_content=heading.text, semantic_id=SLOT_HEADING_SEMANTIC_ID, slot_id=slot.slot_id,
            available_inline_start=float(bounds.inline), available_inline_size=available))
        reserve[source] = content_start - top
    return SlotHeadings(tuple(text), reserve, tuple(diagnostics), tuple(warnings))
