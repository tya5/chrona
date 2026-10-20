"""Shared normalized and measured lane member-label intent."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from chrona.presentation.layout.chip_geometry import chip_padding
from chrona.presentation.layout.label_chip_measurement import MeasuredLabelChip, measure_label_chip
from chrona.presentation.layout.label_visual_measurement import resolve_label_visual_advances
from chrona.presentation.layout.model import geometry_sum
from chrona.presentation.layout.text import measure_text_width, metric_for_role, wrap_text
from chrona.presentation.model.semantic_registry import label_chip_semantic
from chrona.presentation.model.projection import WindowMode, signed_delta_text
from chrona.presentation.layout.surface_mark_visibility import (
    MarkOccurrence, MarkOccurrenceKind, ensure_item_mark_visibility_index,
)
from chrona.presentation.layout.style_occurrences import StyleSourceOccurrences
from chrona.presentation.layout.style_text import resolve_label_candidate_styles
from chrona.presentation.model.hierarchy_names import member_name_key


@dataclass(frozen=True)
class MeasuredLaneMemberLabel:
    """One immutable member name and its complete Theme-measured footprint."""

    placement_id: str
    source_ref: str
    lane_id: str
    member_id: str
    source_kind: str
    content: str
    candidates: tuple[str, ...]
    wrap: str
    lines: tuple[str, ...]
    width: float
    height: float
    text_inline_inset: float
    gap: float
    visuals: tuple[tuple[Any, Any, float, float], ...]
    chip_padding: tuple[float, float]
    leading_advance: float
    trailing_advance: float
    text_width: float
    font_family: str
    font_weight: int
    font_size: float
    line_height: float
    letter_spacing: float
    text_transform: str
    numeric_spacing: str
    chip_measurement: MeasuredLabelChip | None = None
    candidate_measurements: tuple[tuple[str, MeasuredLaneMemberLabel], ...] = ()


def _candidates(side: str, fallback: tuple[str, ...], preferred: str | None) -> tuple[str, ...]:
    ordered = []
    if preferred and preferred != "auto":
        ordered.append(preferred)
    if side != "auto":
        ordered.append(side)
    ordered.extend(fallback if fallback else (("end", "start") if side == "auto" else ()))
    result = []
    for candidate in ordered:
        if candidate == "suppress":
            break
        if candidate not in result:
            result.append(candidate)
    return tuple(result)


def measure_lane_member_labels(projection: Any, surface_content: Any, *,
                               timeline_inline_size: float, theme_tokens: Any,
                               font_metrics: Any, visual_requests: tuple[Any, ...],
                               icon_assets: dict[str, Any],
                               mark_visibility_index: Any = None,
                               scene_precision: int = 3) -> tuple[MeasuredLaneMemberLabel, ...]:
    """Normalize lane member text once and measure the exact placement box.

    The wrap allowance, Theme text treatment, selected icon advances, chip
    footprint, and end-gap inset intentionally match surface composition.
    """
    attached_labels = dict(surface_content.attached_labels)
    explicit = getattr(projection, "window_mode", None) == WindowMode.EXPLICIT
    if explicit:
        mark_visibility_index = ensure_item_mark_visibility_index(
            projection, as_of=surface_content.as_of, index=mark_visibility_index)
    labels = []
    style_index = getattr(surface_content, "style_intents", None)
    style_sources = (StyleSourceOccurrences.from_projection(
        projection, as_of=getattr(surface_content, "as_of", None))
        if style_index is not None and style_index.intents else None)
    for lane_row in projection.lane_rows:
        for item, member_id in zip(lane_row.items, lane_row.member_item_ids, strict=True):
            if not getattr(item, "member_label_eligible", True):
                continue
            instance_id = (f"{lane_row.lane_id}:{item.item_id or item.object_id}"
                           if getattr(projection, "rows", ()) else item.object_id)
            placement_id = f"member-label:{instance_id}"
            attached = attached_labels.get(member_name_key(item, lane_row.lane_id)) if getattr(item, "attached_to", None) else None
            components = []
            if attached is not None:
                components.append(("attached", attached))
            elif not surface_content.show_member_labels:
                continue
            if attached is None and "title" in surface_content.label_content:
                components.append(("title", surface_content.member_name(item, lane_row.lane_id)))
            if (attached is None and getattr(item, "forecast", None) is None and "finishDelta" in surface_content.label_content
                    and item.finish_delta is not None):
                components.append(("finishDelta", signed_delta_text(item.finish_delta, item)))
            parts = tuple(value for _, value in components)
            if explicit:
                occurrence = MarkOccurrence(MarkOccurrenceKind.LANE_FINAL, lane_row.lane_id,
                    item.item_id or item.object_id, item.object_id, item.source_kind)
                admission = mark_visibility_index.lookup_label(occurrence, projection=projection,
                                                               as_of=surface_content.as_of)
                parts = admission.admit_components(tuple(components))
            if not parts:
                continue
            intent = item.presentation or {}
            preferred = (intent.get("label") or {}).get("side") if isinstance(intent, dict) else None
            wrap = ((intent.get("text") or {}).get("wrap", "forbid")
                    if isinstance(intent, dict) else "forbid")
            candidates = _candidates(surface_content.label_side,
                                     surface_content.label_fallback, preferred)

            content = " ".join(parts)
            candidate_styles = {}
            if style_sources is not None:
                key = style_sources.label_key(item, lane_row.lane_id, "memberLabel")
                candidate_styles = resolve_label_candidate_styles(
                    key, candidates, style_index, theme_tokens)

            def measure_for_role(role: str) -> MeasuredLaneMemberLabel:
                treatment = theme_tokens.text_treatment(role)
                metrics = metric_for_role(theme_tokens, role, font_metrics)
                visuals = resolve_label_visual_advances(
                    placement_id, role, visual_requests=visual_requests,
                    icon_assets=icon_assets, theme_tokens=theme_tokens,
                )
                leading = geometry_sum(width + gap for visual, icon, width, gap in visuals
                                       if visual.side == "leading")
                trailing = geometry_sum(width + gap for visual, icon, width, gap in visuals
                                        if visual.side == "trailing")
                available = max(1.0, timeline_inline_size * 0.4 - leading - trailing)
                lines = (wrap_text(content, available_inline=available,
                                   font_size=float(treatment.font_size), font_metrics=metrics,
                                   letter_spacing=float(treatment.letter_spacing),
                                   text_transform=treatment.transform,
                                   numeric_spacing=treatment.numeric_spacing)
                         if wrap == "allow" else (content,))
                text_width = max(measure_text_width(
                    line, font_size=float(treatment.font_size), font_metrics=metrics,
                    letter_spacing=float(treatment.letter_spacing),
                    text_transform=treatment.transform,
                    numeric_spacing=treatment.numeric_spacing,
                ) for line in lines)
                text_height = float(treatment.font_size) * float(treatment.line_height) * len(lines)
                chip_pad = chip_padding(theme_tokens, label_chip_semantic("memberLabel"),
                                        float(treatment.font_size), text_height)
                chip_measurement = measure_label_chip(theme_tokens, "memberLabel",
                    text_inline=leading + text_width + trailing, text_block=text_height,
                    font_size=float(treatment.font_size), padding=chip_pad,
                    scene_precision=scene_precision)
                width = (float(chip_measurement.footprint.inline_size) if chip_measurement is not None
                         else leading + text_width + trailing + 2 * chip_pad[0])
                height = (float(chip_measurement.footprint.block_size) if chip_measurement is not None
                          else text_height + 2 * chip_pad[1])
                text_inset = (chip_measurement.text_inline_inset
                              if chip_measurement is not None else chip_pad[0])
                return MeasuredLaneMemberLabel(
                    placement_id, item.object_id, lane_row.lane_id, member_id,
                    item.source_kind, content, candidates, wrap, lines,
                    width, height, text_inset + leading,
                    max(1.0, float(treatment.font_size) * 0.25),
                    visuals, chip_pad, leading, trailing, text_width,
                    treatment.family, int(treatment.weight), float(treatment.font_size),
                    float(treatment.line_height), float(treatment.letter_spacing),
                    treatment.transform, treatment.numeric_spacing, chip_measurement,
                )

            default_role = surface_content.label_text_role or "text"
            candidate_roles = tuple((side, candidate_styles[side].role if candidate_styles.get(side)
                                     and candidate_styles[side].role else default_role)
                                    for side in candidates)
            if any(role != default_role for _, role in candidate_roles):
                leaves = tuple((side, measure_for_role(role)) for side, role in candidate_roles)
                widest = max(leaves, key=lambda entry: entry[1].width)[1]
                labels.append(replace(widest,
                    width=max(measure.width for _, measure in leaves),
                    height=max(measure.height for _, measure in leaves),
                    candidate_measurements=leaves))
            else:
                labels.append(measure_for_role(default_role))
    return tuple(labels)
