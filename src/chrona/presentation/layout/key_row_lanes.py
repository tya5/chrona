"""Owns key-row lane assignment (#1501); reads the closed scale, mark composition and label measurement.

The View moves every point into one row; only Layout knows pixels, so only Layout decides which points share
a lane.  Lanes are the same greedy interval packing as folded group-header points (#1498): a point's extent is
its marks plus its title label on the placed side, so two points share a lane only when nothing of either meets.
"""
from __future__ import annotations

from dataclasses import replace
from typing import Any

from chrona.presentation.layout.chip_geometry import chip_padding
from chrona.presentation.layout.mark_facet_visibility import admitted_source_selection
from chrona.presentation.layout.label_footprint_measurement import measure_label_footprint
from chrona.presentation.layout.mark_geometry import compose_item_marks
from chrona.presentation.layout.presentation import MarkBandFrame
from chrona.presentation.layout.surface_marks import pack_extent_lanes
from chrona.presentation.layout.surface_mark_visibility import MarkOccurrence, MarkOccurrenceKind
from chrona.presentation.layout.style_occurrences import StyleSourceOccurrences
from chrona.presentation.layout.style_text import resolve_label_candidate_styles
from chrona.presentation.layout.text import measure_text_width, metric_for_role
from chrona.presentation.model.projection import finish_delta_semantic, finish_delta_text
from chrona.presentation.model.semantic_registry import label_chip_semantic


def key_row_label_ladder(side: str) -> tuple[str, ...]:
    """The sides a key-row label may take: inside its own lane band, never above or below (#1501)."""
    return ("start", "end") if side == "start" else ("end", "start")


def assign_key_row_lanes(review_rows: tuple[Any, ...], *, request: Any, scale: Any, as_of: Any,
                         slot_id: str, mark_block_size: float, role_geometries: Any,
                         mark_band_allocation: Any) -> tuple[Any, ...]:
    """Return the rows with each key-row item carrying its packed `key_lane`; other rows are returned as they are."""
    if not any(getattr(row, "key_row", False) for row in review_rows):
        return review_rows
    theme, projection = request.theme_tokens, request.projection
    role = request.surface_content.label_text_role or "text"
    treatment = theme.text_treatment(role)
    gap = max(1.0, float(treatment.font_size) * 0.25)
    pad = chip_padding(theme, label_chip_semantic("memberLabel"), float(treatment.font_size),
                       float(treatment.font_size) * float(treatment.line_height))[0]
    label_at_start = request.presentation_contract.labels.side == "start"
    metrics = metric_for_role(theme, role, request.font_metrics)
    finish_delta_labelled = "finishDelta" in request.presentation_contract.labels.content
    probe = MarkBandFrame.zero_origin(scale, mark_block_size, role_geometries, mark_band_allocation)
    index = request.mark_visibility_index
    style_index = getattr(request.surface_content, "style_intents", None)
    style_sources = (StyleSourceOccurrences.from_projection(projection, as_of=as_of)
                     if style_index is not None and style_index.intents else None)

    def extent(row: Any, point_items: list[Any]) -> tuple[float, float]:
        lefts: list[float] = []
        rights: list[float] = []
        for item in point_items:
            visibility = (index.lookup(MarkOccurrence(MarkOccurrenceKind.ROW, row.row_id, item.item_id or item.object_id,
                                                      item.object_id, item.source_kind),
                                       projection=projection, as_of=as_of) if index is not None else None)
            composition = compose_item_marks(
                item=item, instance_id=f"{row.row_id}:{item.item_id or item.object_id}", source_kind=item.source_kind,
                frame=probe, as_of=as_of, theme_tokens=theme, slot_id=slot_id, emit_missing_actual=True,
                emit_diagnostics=False,
                selection=admitted_source_selection(visibility) if visibility is not None else None,
                style_intents=(MarkOccurrence(MarkOccurrenceKind.ROW, row.row_id,
                                             item.item_id or item.object_id, item.object_id,
                                             item.source_kind).style_intents(request.surface_content.style_intents)
                               if getattr(request.surface_content, "style_intents", None) is not None else None))
            for mark in composition.marks:
                lefts.append(float(mark.bounds.inline))
                rights.append(float(mark.bounds.inline) + float(mark.bounds.inline_size))
        if not lefts:
            return (0.0, 0.0)
        width = measure_text_width(point_items[0].title or "", font_size=float(treatment.font_size), font_metrics=metrics,
                                   letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                                   numeric_spacing="proportional") + 2 * pad
        span = width + gap if width > 0 else 0.0
        if style_sources is not None:
            candidates = key_row_label_ladder(request.presentation_contract.labels.side)
            selected_by_item = []
            for item in point_items:
                key = style_sources.label_key(item, row.row_id, "memberLabel")
                selected = resolve_label_candidate_styles(key, candidates, style_index, theme)
                selected_by_item.append((item, selected))
            if any(intent is not None for _, selected in selected_by_item
                   for intent in selected.values()):
                candidate_widths = []
                for item, selected in selected_by_item:
                    for side in candidates:
                        intent = selected.get(side)
                        candidate_role = intent.role if intent is not None and intent.role else role
                        candidate_treatment = theme.text_treatment(candidate_role)
                        candidate_metrics = metric_for_role(theme, candidate_role, request.font_metrics)
                        candidate_pad = chip_padding(
                            theme, label_chip_semantic("memberLabel"),
                            float(candidate_treatment.font_size),
                            float(candidate_treatment.font_size) * float(candidate_treatment.line_height),
                        )[0]
                        candidate_width = measure_text_width(
                            item.title or "", font_size=float(candidate_treatment.font_size),
                            font_metrics=candidate_metrics,
                            letter_spacing=float(candidate_treatment.letter_spacing),
                            text_transform=candidate_treatment.transform,
                            numeric_spacing="proportional",
                        ) + 2 * candidate_pad
                        candidate_widths.append((candidate_width,
                                                 max(1.0, float(candidate_treatment.font_size) * 0.25)))
                width = max(width, *(candidate_width for candidate_width, _ in candidate_widths))
                span = max(span, *(candidate_width + candidate_gap
                                   for candidate_width, candidate_gap in candidate_widths))
        forecast_items = [item for item in point_items if getattr(item, "forecast", None) is not None
                          and finish_delta_text(item) is not None]
        if forecast_items and getattr(request.presentation_contract.labels, "enabled", True) \
                and "finishDelta" in request.presentation_contract.labels.content:
            # A forecast delta is a member of the title's label packing (#1681): the point's extent holds the
            # delta and its gap on either side the delta may take, as a folded group-header point does.
            delta = measure_label_footprint(f"variance:{row.row_id}:{forecast_items[0].item_id or forecast_items[0].object_id}",
                finish_delta_text(forecast_items[0]), role, finish_delta_semantic(forecast_items[0]), request)
            reach = span + delta.size[0] + delta.gap
            return (min(lefts) - reach, max(rights) + reach)
        return (min(lefts) - span, max(rights)) if label_at_start else (min(lefts), max(rights) + span)

    # A lane is at least as tall as the labels it holds, so a label never meets the one in the next lane (#1681).
    allocation = mark_band_allocation
    base_pitch = float(allocation.outer_extent if allocation is not None else mark_block_size)
    label_block = float(measure_label_footprint("key-row-probe", "M", role, "memberLabel", request).size[1])
    if finish_delta_labelled:
        label_block = max(label_block, float(measure_label_footprint(
            "key-row-probe", "+0d", role, "finishDelta", request).size[1]))
    lane_pitch = label_block if label_block > base_pitch else None

    result = []
    for row in review_rows:
        if not getattr(row, "key_row", False):
            result.append(row)
            continue
        # One point is its primary item plus comparison variants (same object); variants share the point's lane.
        order: list[str] = []
        by_object: dict[str, list[Any]] = {}
        for item in row.items:
            if item.object_id not in by_object:
                order.append(item.object_id)
            by_object.setdefault(item.object_id, []).append(item)
        lanes = pack_extent_lanes([extent(row, by_object[object_id]) for object_id in order])
        lane_of = dict(zip(order, lanes, strict=True))
        result.append(replace(row, items=tuple(replace(item, key_lane=lane_of[item.object_id], key_pitch=lane_pitch) for item in row.items)))
    return tuple(result)
