"""Select and recompose Style legends from completed placements, never source fields."""
from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Any

from chrona.presentation.layout.surface_legend import SurfaceLegendBatch, SurfaceLegendContext, place_legend
from chrona.presentation.layout.surface_quality import FitWarning, MarkPlacement, SurfaceLayoutRequest, TextPlacement
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.style_fills import StyleFillIndex
from chrona.presentation.model.style_rules import StyleOccurrenceKey
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.model.theme_paint import PaintFamily, mark_paint_family, resolve_theme_paint_inputs
from chrona.presentation.model.theme_tokens import ThemeTokenView


def painted_style_occurrences(
    marks: tuple[MarkPlacement, ...], text: tuple[TextPlacement, ...], *,
    fills: StyleFillIndex, tokens: ThemeTokenView,
) -> frozenset[StyleOccurrenceKey]:
    """Count a value only if an emitted host actually accepts its encoded ink."""
    painted: set[StyleOccurrenceKey] = set()

    def visible(placement):
        bounds = placement.bounds
        if bounds.inline_size <= 0 or bounds.block_size <= 0:
            return False
        clip = getattr(placement, "paint_clip", None)
        if clip is not None:
            x, y, width, height = clip.bounds
            return (float(bounds.inline) < x + width and float(bounds.inline + bounds.inline_size) > x
                    and float(bounds.block) < y + height and float(bounds.block + bounds.block_size) > y)
        return True

    for mark in marks:
        key = mark.style_occurrence_key
        color = fills.get(key)
        if key is None or color is None or not visible(mark):
            continue
        role = mark.theme_role or semantic_binding(key.semantic_id).scene_role
        pattern = tokens.optional_pattern(role)
        catalog_pattern = isinstance(pattern, Mapping) and pattern.get("kind") == "catalog"
        # A catalogue glyph's explicit colours/stroke parts are not fill
        # encoding consumers. The same finite channel contract paints Scene.
        parts = mark.symbol_parts or (None,)
        for part in parts:
            mode = part.paint_mode if part is not None else None
            family = mark_paint_family(tokens, role, glyph_paint_mode=mode,
                                      has_completed_catalog_pattern=catalog_pattern)
            paint = resolve_theme_paint_inputs(
                tokens, role, family, fill_override=color, part_mode=mode,
                part_color=part.paint_color if part is not None else None,
                catalog_pattern=catalog_pattern,
                catalog_glyph_stroke_width=(part.stroke_width if part is not None and mode == "stroke" else None))
            if paint.solid_override and paint.opacity != 0:
                painted.add(key)
                break
    for placement in text:
        key = placement.style_occurrence_key
        color = fills.get(key)
        if (key is None or color is None or not placement.content.strip()
                or placement.overflow == "suppressed" or not visible(placement)):
            continue
        paint = resolve_theme_paint_inputs(
            tokens, placement.theme_role or placement.typography_role, PaintFamily.TEXT, fill_override=color)
        if paint.solid_override and paint.opacity != 0:
            painted.add(key)
    return frozenset(painted)


def filtered_style_legend_entries(
    entries: tuple[SurfaceLegendEntry, ...], painted: frozenset[StyleOccurrenceKey],
) -> tuple[SurfaceLegendEntry, ...]:
    """Preserve existing Detail/View policy; Style entries need a painted witness."""
    return tuple(entry for entry in entries
                 if entry.style_scope is None or any(key in painted for key in entry.style_occurrences))


def initial_style_legend_warnings(request: SurfaceLayoutRequest, legend: SurfaceLegendBatch) -> tuple[FitWarning, ...]:
    """Keep conservative-slot warnings deferred when final Style filtering can change entries."""
    if any(entry.style_scope is not None for entry in request.surface_content.legend_entries):
        return ()
    return legend.warnings


def recompose_scoped_style_legend(
    request: SurfaceLayoutRequest, legend: SurfaceLegendBatch | None,
    marks: tuple[MarkPlacement, ...], text: tuple[TextPlacement, ...],
    metric_values: Mapping[str, Any], metric_for: Callable[[str], Any],
    warnings: list[FitWarning],
) -> SurfaceLegendBatch | None:
    """Filter scoped entries against completed paint and recompose in their fixed slot."""
    if legend is None or not any(entry.style_scope is not None for entry in request.surface_content.legend_entries):
        return legend
    painted = painted_style_occurrences(
        marks, text, fills=request.surface_content.style_fills, tokens=request.theme_tokens)
    filtered = filtered_style_legend_entries(request.surface_content.legend_entries, painted)
    # The footer/annotation candidates already use conservative slots; final composition
    # changes entries only and must not trigger a layout retry or allocation change.
    legend_request = replace(request, surface_content=replace(request.surface_content, legend_entries=filtered))
    completed = place_legend(SurfaceLegendContext(legend_request, legend.slot, metric_values, metric_for))
    warnings.extend(completed.warnings)
    return completed
