"""Shared complete Theme card measurements for ordered annotation rails."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Callable, NamedTuple

from chrona.presentation.layout.annotation_border import NO_BORDER, resolve_border
from chrona.presentation.layout.annotation_inline_size import (
    FilledNote,
    fill_note,
    fill_target,
)
from chrona.presentation.layout.annotation_kind_frame import (
    KindFrameMeasure,
    complete_kind_frame,
    measure_kind_frame,
)
from chrona.presentation.layout.annotation_tilt import rotated_extent, tilt_for
from chrona.presentation.layout.model import LayoutError, geometry_sum
from chrona.presentation.layout.rounded_outline import CORNER_CLEARANCE
from chrona.presentation.layout.surface_quality import annotation_presentation
from chrona.presentation.layout.text import measure_text_width, wrap_text
from chrona.presentation.layout.viewer_fit import require_followable_content
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.theme_tokens import ViewerFitToken


class NoteVariant(NamedTuple):
    content: str
    lines: tuple[str, ...]
    measured_width: float
    frame_size: tuple[float, float]
    search_size: tuple[float, float]
    filled: FilledNote | None
    fill_size: tuple[float, float] | None
    filled_kind: KindFrameMeasure


def _capsule_axis_radius(size: float, before: float, after: float) -> float:
    k = CORNER_CLEARANCE
    content = max(0.0, size - before - after)
    low, high = sorted((before, after))
    candidates = (((content + before + after) / 2, low / k),
                  ((content + high) / (2 - k), high / k),
                  (content / (2 - 2 * k), float("inf")))
    lower = 0.0
    for radius, upper in candidates:
        if lower - 1e-9 <= radius <= upper + 1e-9:
            return max(0.0, radius)
        lower = upper
    return max(0.0, candidates[-1][0])


def _physical_radius_clearance(value: Any, width: float, height: float,
                               insets: tuple[float, float, float, float]) -> float:
    if value == "capsule":
        top, right, bottom, left = insets
        return CORNER_CLEARANCE * min(_capsule_axis_radius(width, left, right),
                                      _capsule_axis_radius(height, top, bottom))
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(float(value)) or value < 0:
        raise ValueError("Corner radius requires finite nonnegative px or capsule")
    return CORNER_CLEARANCE * float(value)


@dataclass(frozen=True)
class AnnotationCardMeasurement:
    container: Any
    role_corner_radius: Any
    box_border: Any
    viewer_fit: Any
    fill_declared: bool
    filled: FilledNote | None
    fill_size: tuple[float, float] | None
    content_top: float
    content_right: float
    content_bottom: float
    content_left: float
    kind_measure: KindFrameMeasure
    kind_theme: Any
    tilt_angle: float
    plot_variant: NoteVariant
    list_variant: NoteVariant
    wrap: str
    wrap_declared: str | None
    plot_wrap_em: float | None


def suffix_block_capacity(cards: tuple[tuple[str, float], ...], rail_height: float
                          ) -> dict[str, float]:
    """Return each admitted card's required complete block below it, only if all fit."""
    if geometry_sum(height for _, height in cards) > rail_height:
        return {}
    result: dict[str, float] = {}
    suffix = 0.0
    for card_id, height in reversed(cards):
        result[card_id] = suffix
        suffix = geometry_sum((suffix, height))
    return result


def measure_annotation_card(*, annotation: Any, index: int, intent: Any,
                            body_content: str, list_content: str,
                            has_index_suppression: bool, annotation_visuals: tuple[Any, ...],
                            annotation_leading: float, annotation_trailing: float,
                            size: float, line_height: float, annotation_metrics: Any,
                            annotation_treatment: Any, text_available: float,
                            request: Any, metric_for: Callable[[str], Any],
                            kind_theme: Any, annotation_slot: Any) -> AnnotationCardMeasurement:
    """Measure the same full card used by placement, retaining all paint inputs."""
    wrap_declared = ((intent or {}).get("text") or {}).get("wrap") if isinstance(intent, dict) else None
    wrap = wrap_declared or "forbid"
    plot_wrap_em = max((candidate.search.max_inline_em for candidate in annotation.candidates
                        if candidate.search.max_inline_em is not None), default=None)
    wrap_available = float(plot_wrap_em) * size if plot_wrap_em is not None else text_available
    annotation_box_role = semantic_binding(annotation_presentation(annotation.purpose).box_semantic_id).theme_role
    container = request.theme_tokens.annotation_container(annotation_box_role)
    role_corner_radius = request.theme_tokens.optional_token(annotation_box_role, "cornerRadius", "radius")
    kind_token = request.theme_tokens.annotation_kind(annotation.kind)
    if kind_token is not None and kind_theme is None:
        kind_theme = request.theme_tokens.annotation_kind_frame()
    kind_measure = measure_kind_frame(
        kind=kind_token, subject=annotation.subject, subject_id=annotation.subject_id,
        frame=kind_theme, theme_tokens=request.theme_tokens, metric_for=metric_for,
        outline=container.outline if container is not None else None,
        pointer=f"/annotations/{index}", text_size=size,
        header_texts=annotation.kind_header_lines, heading_content=annotation.kind_heading_text)
    viewer_fit = (request.theme_tokens.viewer_fit(annotation_box_role)
                  if annotation.purpose in {"callout", "highlight", "note", "explanatory-arrow"}
                  else ViewerFitToken())
    require_followable_content(viewer_fit, has_kind_frame=not kind_measure.empty,
                               has_visual=bool(annotation_visuals), pointer=f"/annotations/{index}")
    wrap_available = max(1.0, wrap_available - kind_measure.inline_insets)
    if plot_wrap_em is not None:
        wrap = "allow"
    content_top = content_right = content_bottom = content_left = 0.0
    if container is not None and container.content_insets_em is not None:
        content_top, content_right, content_bottom, content_left = (
            float(value) * size for value in container.content_insets_em)
    box_border = resolve_border(container.border) if container is not None else NO_BORDER
    border_top, border_right, border_bottom, border_left = box_border.insets
    content_top += border_top
    content_right += border_right
    content_bottom += border_bottom
    content_left += border_left
    if (container is not None and container.outline == "rectangle"
            and role_corner_radius is None and container.corner_radius > 0):
        clearance = float(container.corner_radius) * size * CORNER_CLEARANCE
        content_top, content_right, content_bottom, content_left = (
            max(value, clearance) for value in (content_top, content_right, content_bottom, content_left))
    bar_extra_inline = (max(0.0, content_left + content_right - box_border.start - box_border.end)
                        if kind_measure.bar_bleed == "border" else 0.0)

    def measure_note(measured_content: str, wrap_bound: float, may_wrap: bool,
                     *, complete_frame: bool = False) -> tuple[tuple[str, ...], float, tuple[float, float]]:
        frame = (complete_kind_frame(
            kind_measure, available_inline=wrap_bound + annotation_leading + annotation_trailing,
            may_wrap=may_wrap, bar_extra_inline=bar_extra_inline,
            theme_tokens=request.theme_tokens, metric_for=metric_for) if complete_frame else kind_measure)
        lines = (wrap_text(measured_content, available_inline=wrap_bound, font_size=size,
                           font_metrics=annotation_metrics,
                           letter_spacing=float(annotation_treatment.letter_spacing),
                           text_transform=annotation_treatment.transform)
                 if may_wrap else (measured_content,))
        widest = max(measure_text_width(
            line, font_size=size, font_metrics=annotation_metrics,
            letter_spacing=float(annotation_treatment.letter_spacing),
            text_transform=annotation_treatment.transform) for line in lines)
        body_inline = annotation_leading + widest + annotation_trailing
        return lines, widest, (
            max(body_inline, frame.header_inline) + frame.inline_insets + content_left + content_right,
            max(size * line_height * len(lines) + frame.header_block, frame.stamp_block)
            + content_top + content_bottom)

    tilt_angle = tilt_for(container.tilt_degrees if container is not None else None, index)
    if tilt_angle and annotation_visuals:
        raise LayoutError("E_LAYOUT_ANNOTATION_TILT_VISUAL", f"/annotations/{index}")
    fill_declared = container is not None and container.inline_size == "fill"

    def measure_variant(measured_content: str, *, list_entry: bool) -> NoteVariant:
        may_wrap = (wrap == "allow" or (list_entry and has_index_suppression))
        lines, measured_width, frame_size = measure_note(measured_content, wrap_available, may_wrap)
        search_size = rotated_extent(*frame_size, tilt_angle) if tilt_angle else frame_size
        filled_variant = None
        filled_kind = kind_measure
        if fill_declared and annotation_slot is not None:
            fill_may_wrap = (wrap_declared != "forbid" or plot_wrap_em is not None or list_entry)
            filled_variant = fill_note(
                lambda bound: measure_note(measured_content, bound, fill_may_wrap, complete_frame=True),
                target=fill_target(float(annotation_slot.bounds.inline_size),
                                   max_inline_em=(float(container.max_inline_em)
                                                  if container.max_inline_em is not None else None),
                                   text_size=size),
                chrome=(annotation_leading + annotation_trailing + kind_measure.inline_insets
                        + content_left + content_right), tilt_degrees=tilt_angle)
            filled_kind = complete_kind_frame(
                kind_measure,
                available_inline=filled_variant.wrap_inline + annotation_leading + annotation_trailing,
                may_wrap=fill_may_wrap, bar_extra_inline=bar_extra_inline,
                theme_tokens=request.theme_tokens, metric_for=metric_for)
        measured_fill_size = (
            rotated_extent(filled_variant.frame_inline, filled_variant.frame_block, tilt_angle)
            if filled_variant is not None and tilt_angle else
            (filled_variant.frame_inline, filled_variant.frame_block) if filled_variant is not None else None)
        return NoteVariant(measured_content, lines, measured_width, frame_size, search_size,
                           filled_variant, measured_fill_size, filled_kind)

    plot_variant = measure_variant(body_content, list_entry=False)
    list_variant = measure_variant(list_content, list_entry=True) if has_index_suppression else plot_variant
    if (role_corner_radius is not None
            and (container is None or container.outline in {"rectangle", "balloon"})):
        variants = (plot_variant,) if list_variant is plot_variant else (plot_variant, list_variant)
        base_insets = (content_top, content_right, content_bottom, content_left)
        required = 0.0
        for variant in variants:
            dimensions = [(*variant.frame_size, False)]
            if variant.filled is not None:
                dimensions.append((variant.filled.frame_inline, variant.filled.frame_block, True))
            for dimension in dimensions:
                measured_width, measured_height = dimension[:2]
                filled_width = len(dimension) == 3 and dimension[2]
                if role_corner_radius == "capsule" and filled_width:
                    clearance = (CORNER_CLEARANCE * measured_width / (2 * (1 - CORNER_CLEARANCE)))
                else:
                    clearance = _physical_radius_clearance(role_corner_radius, measured_width,
                                                           measured_height, base_insets)
                required = max(required, clearance)
        content_top, content_right, content_bottom, content_left = (
            max(value, required) for value in base_insets)
        if base_insets != (content_top, content_right, content_bottom, content_left):
            plot_variant = measure_variant(body_content, list_entry=False)
            list_variant = measure_variant(list_content, list_entry=True) if has_index_suppression else plot_variant
    return AnnotationCardMeasurement(
        container, role_corner_radius, box_border, viewer_fit, fill_declared,
        plot_variant.filled, plot_variant.fill_size,
        content_top, content_right, content_bottom, content_left,
        kind_measure, kind_theme, tilt_angle, plot_variant, list_variant, wrap, wrap_declared, plot_wrap_em)
