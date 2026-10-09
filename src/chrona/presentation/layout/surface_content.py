"""Owns title/detail panels, notes, summary and footer source content in allocated slots; reads completed slots and Theme tokens."""

from dataclasses import dataclass, replace
from collections.abc import Mapping
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.sources import SourceInput
from chrona.presentation.layout.surface_observations import compose_observations, observations_table_content
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.layout.surface_visuals import (
    reserve_text_visuals,
)
from chrona.presentation.layout.text import ellipsize_text, measure_text_width, metric_for_role, place_text, wrap_text
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, FitWarning, SlotPlacement, SurfaceLayoutRequest,
    TextPlacement, intersects,
)
from chrona.presentation.layout.surface_geometry import (
    GEOMETRY_TOLERANCE,
)
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject


@dataclass(frozen=True)
class SurfaceLayoutComposition:
    """Completed common surface geometry and the semantic rows it was derived from."""



def detail_visual_requests(request: SurfaceLayoutRequest) -> dict[str, dict[str, Any]]:
    """Select detail-panel visual intents without assigning any Scene geometry."""
    result: dict[str, dict[str, Any]] = {}
    prefixes = {"group-detail": "group-detail", "milestone": "milestone"}
    for visual in request.visual_requests:
        prefix = prefixes.get(visual.target_kind)
        if prefix is None:
            continue
        selector = dict(visual.selector)
        identifier = selector.get("id")
        if not identifier:
            continue
        placement_id = f"{prefix}:{identifier}"
        if visual.side in result.setdefault(placement_id, {}):
            raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", visual.source_ref)
        result[placement_id][visual.side] = visual
    return result


def _detail_panel_entries(source: str, values: tuple[Any, ...]) -> tuple[tuple[str, str], ...]:
    """Keep Review Detail formatting semantic while delegating geometry to Layout."""
    if source == "group-details":
        return tuple((value[0], f"{value[1]}: {value[2]}") for value in values)
    return tuple((value[0], f"{value[1]} — {value[2].isoformat()}") for value in values)


def detail_source_inputs(content: SurfaceContentInput) -> dict[str, SourceInput]:
    """Measure the same immutable Detail facts the native owners will place."""
    return {
        "group-details": SourceInput(tuple(text for _, text in _detail_panel_entries(
            "group-details", content.group_details))),
        "milestones": SourceInput(tuple(text for _, text in _detail_panel_entries(
            "milestones", content.milestones))),
        "observations": SourceInput(tuple(source for _, source, _, _ in content.observation_rows),
            item_count=len(content.observation_rows), column_count=len(content.observation_columns),
            table=observations_table_content(content)),
    }


def compose_detail_panel_blocks(*, slots: tuple[SlotPlacement, ...], request: SurfaceLayoutRequest,
                                 requested_canvas: Rect,
                                 caption_reserves: Mapping[str, Decimal] | None = None
                                 ) -> tuple[tuple[SlotPlacement, ...], list[Any], list[FitWarning], frozenset[str]]:
    """Complete Review Detail panel lines, rectangles, and visible-fit records."""
    slot_by_source = {slot.source_ref: slot for slot in slots}
    sources = (("group-details", request.surface_content.group_details, "group-detail"),
               ("milestones", request.surface_content.milestones, "milestone"),
               ("observations", request.surface_content.observation_rows, "observations"))
    visual_requests = detail_visual_requests(request)
    completed: list[Any] = []
    warnings: list[FitWarning] = []
    replacements: dict[str, SlotPlacement] = {}
    allocated: list[SlotPlacement] = []
    pre_reserved: set[str] = set()
    treatment = request.theme_tokens.text_treatment("text")
    font_size = float(treatment.font_size)
    metrics = metric_for_role(request.theme_tokens, "text", request.font_metrics)
    requested_end = requested_canvas.block + requested_canvas.block_size

    # Review Detail's milestone IDs are validated Project-object references
    # before they reach this module. Join only those explicit references to
    # typed projection objects; group and observation row IDs are not objects.
    projection_items = {str(item.object_id): item for item in getattr(request.projection, "items", ())}
    milestone_ids = tuple(object_id for object_id, _, _ in request.surface_content.milestones)

    def milestone_subjects(source_ref: str | None = None) -> tuple[DiagnosticSubject, ...]:
        selected = (source_ref,) if source_ref in milestone_ids else milestone_ids if source_ref is None else ()
        return tuple(DiagnosticSubject.project_object(object_id, getattr(projection_items[object_id], "title", None))
                     for object_id in selected if object_id in projection_items)

    for source, values, prefix in sources:
        slot = slot_by_source.get(source)
        if slot is None or not values:
            continue
        available = float(slot.bounds.inline_size)
        block = slot.bounds.block
        for previous in allocated:
            left, right = slot.bounds.inline, slot.bounds.inline + slot.bounds.inline_size
            previous_left = previous.bounds.inline
            previous_right = previous.bounds.inline + previous.bounds.inline_size
            if left < previous_right and previous_left < right:
                # Stack the whole panel, not its content over the predecessor's last line.
                block = max(block, previous.bounds.block + previous.bounds.block_size
                            + (caption_reserves or {}).get(source, Decimal(0)))
        cursor = block
        if source == "observations":
            batch = compose_observations(slot=replace(slot, bounds=Rect(
                slot.bounds.inline, block, slot.bounds.inline_size, slot.bounds.block_size)), request=request)
            replacements[source] = batch.slot
            allocated.append(batch.slot)
            completed.extend(batch.text)
            warnings.extend(batch.warnings)
            continue
        item_overflows: list[tuple[Any, float, float]] = []
        for source_ref, content in _detail_panel_entries(source, values):
            placement_id = f"{prefix}:{source_ref}"
            reservation = reserve_text_visuals(
                typography_role="text", font_size=font_size,
                visuals=visual_requests.get(placement_id, {}), request=request,
            )
            leading, trailing = reservation.leading, reservation.trailing
            text_available = max(0.0, available - leading - trailing)
            lines = ((content,) if text_available == 0 else
                     wrap_text(content, available_inline=text_available, font_size=font_size, font_metrics=metrics,
                               letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                               numeric_spacing=treatment.numeric_spacing))
            natural_width = max(measure_text_width(line, font_size=font_size, font_metrics=metrics,
                                                   letter_spacing=float(treatment.letter_spacing),
                                                   text_transform=treatment.transform,
                                                   numeric_spacing=treatment.numeric_spacing) for line in lines)
            disposition = "fit"
            if natural_width > text_available:
                ellipsis_width = measure_text_width("…", font_size=font_size, font_metrics=metrics,
                                                     letter_spacing=float(treatment.letter_spacing),
                                                     text_transform=treatment.transform,
                                                     numeric_spacing=treatment.numeric_spacing)
                if slot.overflow == "ellipsize-with-source" and text_available >= ellipsis_width:
                    lines = tuple(ellipsize_text(line, available_inline=text_available, font_size=font_size,
                                                  font_metrics=metrics, letter_spacing=float(treatment.letter_spacing),
                                                  text_transform=treatment.transform,
                                                  numeric_spacing=treatment.numeric_spacing) for line in lines)
                    disposition = "ellipsized"
                elif slot.overflow == "clip-optional":
                    suppressed = place_text(placement_id=placement_id, source_ref=source_ref, content=content,
                                            inline=float(slot.bounds.inline), baseline_block=float(cursor + Decimal(str(font_size))),
                                            typography_role="text", theme_tokens=request.theme_tokens,
                                            font_metrics=request.font_metrics, overflow="suppressed", required=False,
                                            collision_region=f"{source}:{source_ref}",
                                            collision_domain=CollisionDomain(source, "content"), source_content=content,
                                            lines=lines, available_inline_start=float(slot.bounds.inline),
                                            available_inline_size=text_available, slot_id=slot.slot_id)
                    completed.append(suppressed)
                    warnings.append(FitWarning("W_LAYOUT_DETAIL_PANEL_CLIPPED", placement_id, source_ref,
                                               "detail-panel", "clip-optional", natural_width,
                                               float(suppressed.bounds.block_size), text_available,
                                               float(slot.bounds.block_size),
                                               subjects=milestone_subjects(source_ref) if source == "milestones" else ()))
                    continue
                else:
                    disposition = "visible-overflow"
            placed = place_text(placement_id=placement_id, source_ref=source_ref, content="\n".join(lines),
                                inline=float(slot.bounds.inline), baseline_block=float(cursor + Decimal(str(font_size))),
                                typography_role="text", theme_tokens=request.theme_tokens,
                                font_metrics=request.font_metrics, overflow=disposition,
                                collision_region=f"{source}:{source_ref}",
                                collision_domain=CollisionDomain(source, "content"), source_content=content,
                                lines=lines, available_inline_start=float(slot.bounds.inline),
                                available_inline_size=available, slot_id=slot.slot_id)
            completed.append(placed)
            pre_reserved.add(placement_id)
            cursor += placed.bounds.block_size
            if disposition == "visible-overflow":
                item_overflows.append((placed, leading + natural_width + trailing, max(0.0, available)))
        final_size = max(slot.bounds.block_size, cursor - block)
        final_slot = replace(slot, bounds=Rect(slot.bounds.inline, block, slot.bounds.inline_size,
                                                final_size))
        replacements[source] = final_slot
        allocated.append(final_slot)
        for placed, required_inline, available_inline in item_overflows:
            warnings.append(FitWarning("W_LAYOUT_VISIBLE_OVERFLOW", placed.placement_id, placed.source_ref,
                                       "detail-panel", "visible-overflow", required_inline,
                                       float(placed.bounds.block_size), available_inline, float(final_size),
                                       subjects=milestone_subjects(placed.source_ref) if source == "milestones" else ()))
        if final_slot.bounds.block + final_slot.bounds.block_size > requested_end + GEOMETRY_TOLERANCE:
            warnings.append(FitWarning("W_LAYOUT_VISIBLE_OVERFLOW", f"detail-panel:{source}", source,
                                       "detail-panel", "visible-overflow", float(final_slot.bounds.inline_size),
                                       float(final_slot.bounds.block_size), float(final_slot.bounds.inline_size),
                                       max(0.0, float(requested_end - final_slot.bounds.block)),
                                       subjects=milestone_subjects() if source == "milestones" else ()))
    final_slots = tuple(replacements.get(slot.source_ref, slot) for slot in slots)
    return final_slots, completed, warnings, frozenset(pre_reserved)


_DETAIL_PANEL_SOURCES = frozenset({"group-details", "milestones", "observations"})
_FOOTER_SOURCES = _DETAIL_PANEL_SOURCES | {"legend", "notes"}


def complete_footer_band(*, provisional_slots: tuple[SlotPlacement, ...],
                          completed_slots: tuple[SlotPlacement, ...]) -> tuple[SlotPlacement, ...]:
    """Translate the physical annotations successor from the final footer union."""
    provisional_by_source = {slot.source_ref: slot for slot in provisional_slots}
    completed_by_source = {slot.source_ref: slot for slot in completed_slots}
    panel_start = min((slot.bounds.block for source, slot in provisional_by_source.items()
                       if source in _DETAIL_PANEL_SOURCES), default=None)
    if panel_start is None:
        return completed_slots
    panel_line = max((slot.bounds.block_size for source, slot in provisional_by_source.items()
                      if source in _DETAIL_PANEL_SOURCES), default=Decimal(0))
    provisional_footer = tuple(slot for source, slot in provisional_by_source.items()
                               if source in _FOOTER_SOURCES
                               and panel_start <= slot.bounds.block <= panel_start + panel_line + GEOMETRY_TOLERANCE)
    if not provisional_footer:
        return completed_slots
    provisional_end = max(slot.bounds.block + slot.bounds.block_size for slot in provisional_footer)
    # The allocated first line determines the predecessor end and its declared
    # successor gap. Completion must include later Flow lines as well: a wrapped
    # notes slot can start exactly where that successor was provisionally placed.
    completed_footer = tuple(completed_by_source[source]
                             for source, slot in provisional_by_source.items()
                             if source in _FOOTER_SOURCES and slot.bounds.block >= panel_start)
    completed_end = max(slot.bounds.block + slot.bounds.block_size for slot in completed_footer)
    annotation = completed_by_source.get("annotations")
    overlaps_footer_inline = annotation is not None and any(
        annotation.bounds.inline < slot.bounds.inline + slot.bounds.inline_size
        and slot.bounds.inline < annotation.bounds.inline + annotation.bounds.inline_size
        for slot in completed_footer
    )
    growth = completed_end - provisional_end
    if (growth <= GEOMETRY_TOLERANCE or annotation is None
            or annotation.bounds.block < provisional_end or not overlaps_footer_inline):
        return completed_slots
    translated = replace(annotation, bounds=Rect(annotation.bounds.inline, annotation.bounds.block + growth,
                                                 annotation.bounds.inline_size, annotation.bounds.block_size))
    return tuple(translated if slot.source_ref == "annotations" else slot for slot in completed_slots)


def validate_detail_panel_placement(text: list[Any], slots: tuple[SlotPlacement, ...]) -> None:
    """Keep final detail text and final panel rectangles consistent after visual projection."""
    slot_by_id = {slot.slot_id: slot for slot in slots}
    panels = [item for item in text if item.placement_id.startswith(("group-detail:", "milestone:", "observations:"))]
    for item in panels:
        if item.overflow in {"suppressed", "visible-overflow"}:
            continue
        slot = slot_by_id.get(item.slot_id)
        if slot is None:
            raise LayoutError("E_LAYOUT_SLOT_OWNERSHIP_INVALID", item.placement_id)
        if (item.bounds.inline < slot.bounds.inline - GEOMETRY_TOLERANCE
                or item.bounds.inline + item.bounds.inline_size > slot.bounds.inline + slot.bounds.inline_size + GEOMETRY_TOLERANCE
                or item.bounds.block < slot.bounds.block - GEOMETRY_TOLERANCE
                or item.bounds.block + item.bounds.block_size > slot.bounds.block + slot.bounds.block_size + GEOMETRY_TOLERANCE):
            raise LayoutError("E_LAYOUT_DETAIL_PANEL_CONTAINMENT", item.placement_id)
    groups = [item for item in panels if item.placement_id.startswith("group-detail:") and item.overflow != "suppressed"]
    milestones = [item for item in panels if item.placement_id.startswith("milestone:") and item.overflow != "suppressed"]
    for group in groups:
        for milestone in milestones:
            if (group.overflow != "visible-overflow" and milestone.overflow != "visible-overflow"
                    and intersects(group.bounds, milestone.bounds)):
                raise LayoutError("E_LAYOUT_DETAIL_PANEL_OVERLAP", f"{group.placement_id}:{milestone.placement_id}")


def place_notes(request: SurfaceLayoutRequest, notes: SlotPlacement, body_size: float) -> tuple[SlotPlacement, tuple[TextPlacement, ...]]:
    """Place the note lines and return the notes slot with its completed extent."""
    text: list[TextPlacement] = []
    cursor = notes.bounds.block
    for index, (source, content) in enumerate(request.surface_content.notes):
        placed = place_text(placement_id=f"note:{source}", source_ref=source, content=content,
                            inline=float(notes.bounds.inline), baseline_block=float(cursor) + body_size,
                            typography_role="text", theme_tokens=request.theme_tokens,
                            font_metrics=request.font_metrics, collision_region=f"notes:{source}",
                            collision_domain=CollisionDomain("notes", f"line:{index}"), source_content=content,
                            available_inline_start=float(notes.bounds.inline),
                            available_inline_size=float(notes.bounds.inline_size))
        text.append(placed)
        cursor = placed.bounds.block + placed.bounds.block_size
    final_size = max(notes.bounds.block_size, cursor - notes.bounds.block)
    replacement = replace(notes, bounds=Rect(notes.bounds.inline, notes.bounds.block,
                                              notes.bounds.inline_size, final_size))
    return replacement, tuple(text)


def place_summary(request: SurfaceLayoutRequest, summary_slot: SlotPlacement) -> tuple[TextPlacement, ...]:
    """Place the summary runs in the allocated summary slot."""
    if any(panel.arrangement == "inline" for panel in request.surface_content.summary.panels):
        measured = request.measured_sources.summary_flows.get("summary")
        if measured is None:
            raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "summary")
        runs = {run.placement_id: run for run in request.surface_content.summary.runs}
        closed_runs = {run.source_ref: run for run in request.measured_sources.run_measurements["summary"]}
        return tuple(place_text(
            placement_id=placed.placement_id, source_ref=runs[placed.placement_id].source_ref,
            content=closed_runs[placed.placement_id].content,
            inline=float(summary_slot.bounds.inline + placed.inline),
            baseline_block=float(summary_slot.bounds.block + placed.baseline),
            typography_role=runs[placed.placement_id].typography_role,
            theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
            collision_region="summary", collision_domain=CollisionDomain("summary", "content"),
            source_content=runs[placed.placement_id].content,
            semantic_id=runs[placed.placement_id].semantic_id,
            available_inline_start=float(summary_slot.bounds.inline),
            available_inline_size=float(summary_slot.bounds.inline_size)) for placed in measured.runs)
    text: list[TextPlacement] = []
    cursor = float(summary_slot.bounds.block)
    for run in request.surface_content.summary.runs:
        summary_treatment = request.theme_tokens.text_treatment(run.typography_role)
        font_size, line_height = summary_treatment.font_size, summary_treatment.line_height
        text.append(place_text(placement_id=run.placement_id, source_ref=run.source_ref, content=run.content,
                               inline=float(summary_slot.bounds.inline), baseline_block=cursor + float(font_size),
                               typography_role=run.typography_role, theme_tokens=request.theme_tokens,
                               font_metrics=request.font_metrics, collision_region="summary",
                               collision_domain=CollisionDomain("summary", "content"), source_content=run.content,
                               available_inline_start=float(summary_slot.bounds.inline),
                               available_inline_size=float(summary_slot.bounds.inline_size)))
        cursor += float(font_size) * float(line_height)
    return tuple(text)
