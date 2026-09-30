"""Owns legend entries and role-derived swatches in the fixed legend slot; reads completed slots and Theme tokens."""

from dataclasses import dataclass, replace
from decimal import Decimal
from collections.abc import Mapping
from typing import Any, Callable

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_marks import (
    MARK_GEOMETRY_ROLES,
)
from chrona.presentation.layout.text import ellipsize_text, measure_text_width, place_text
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.mark_geometry import symbol_parts
from chrona.presentation.layout.surface_quality import (
    CollisionDomain, FitWarning, MarkPlacement, RelationPlacement, ShapePlacement, SlotPlacement, SurfaceLayoutRequest,
    TextPlacement,
)


@dataclass(frozen=True)
class SurfaceLayoutComposition:
    """Completed common surface geometry and the semantic rows it was derived from."""



@dataclass(frozen=True)
class SurfaceLegendContext:
    request: SurfaceLayoutRequest
    legend: SlotPlacement
    metric_values: Mapping[str, Any]
    metric_for: Callable[[str], Any]


@dataclass(frozen=True)
class SurfaceLegendBatch:
    slot: SlotPlacement
    marks: tuple[MarkPlacement, ...]
    shapes: tuple[ShapePlacement, ...]
    relations: tuple[RelationPlacement, ...]
    text: tuple[TextPlacement, ...]
    warnings: tuple[FitWarning, ...]


def place_legend(context: SurfaceLegendContext) -> SurfaceLegendBatch:
    """Place every legend entry inside the allocated legend slot and return its completed extent."""
    request, legend = context.request, context.legend
    metric_values, metric_for = context.metric_values, context.metric_for
    marks: list[MarkPlacement] = []
    shapes: list[ShapePlacement] = []
    relations: list[RelationPlacement] = []
    text: list[TextPlacement] = []
    side_content_warnings: list[FitWarning] = []
    legend_treatment = request.theme_tokens.text_treatment("legend")
    legend_size = float(legend_treatment.font_size)
    legend_step = legend_size * float(legend_treatment.line_height)
    text_line_block = legend_size * float(legend_treatment.line_height)
    mark_block_size = float(metric_values["timeline.mark.blockSize"])
    legacy_swatch_size = max(2.0, legend_size * 0.8)
    declared_inline = request.theme_tokens.optional_number("legend-swatch", "swatchInlineSize")
    fallback_inline = float(declared_inline) if declared_inline is not None else legacy_swatch_size
    # Today's fixed swatch->label offset was `swatch_size * 1.5`, i.e. one
    # swatch width plus a "gap" of exactly half a swatch; reproduce that
    # split so an unmigrated (no declared `gap`) legend slot lays out
    # byte-identically to before this change (#427).
    gap = float(legend.gap) if legend.gap is not None else legacy_swatch_size * 0.5
    direction = legend.direction
    item_min_inline = float(legend.item_min_inline_size) if legend.item_min_inline_size is not None else None

    def swatch_geometry(role: str) -> tuple[float, float, str]:
        """Return one legend entry's (inline size, block size, dispatch bucket) (#427).

        The size is the role's own mark geometry against the document's own
        `timeline.mark.blockSize` for a `mark`/`point` role -- literally the
        size the chart draws it -- or `legend-swatch.swatchInlineSize` (or its
        documented fallback) for a role with no single on-chart length. A
        role this table does not recognize keeps today's fixed square.
        """
        if role == "milestone":
            height_ratio, *_ = request.theme_tokens.mark_geometry("planned")
            side = float(height_ratio) * mark_block_size
            return side, side, "point"
        if role in MARK_GEOMETRY_ROLES:
            return fallback_inline, float(request.theme_tokens.mark_geometry(role)[0]) * mark_block_size, "mark"
        if role in ("asOf", "dependency", "dependency-critical"):
            return fallback_inline, text_line_block, "line"
        return legacy_swatch_size, legacy_swatch_size, "legacy"

    def emit_swatch(role: str, x: float, y: float, width: float, height: float, bucket: str) -> None:
        if bucket == "point":
            bounds = Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height)))
            parts = symbol_parts(
                request.theme_tokens.variant_symbol("planned"), (x, y, width, height),
                catalog_glyphs=getattr(request.theme_tokens, "catalog_glyphs", None),
            )
            marks.append(MarkPlacement(f"legend-swatch:{role}", role,
                                       bounds,
                                       (x + width / 2, y + height / 2), (x + width / 2, y + height / 2),
                                       mark_shape="point", slot_id=legend.slot_id, semantic_id="planned",
                                       symbol_parts=parts))
        elif bucket == "mark":
            height_ratio, offset_ratio, paint_order, corner_ratio = request.theme_tokens.mark_geometry(role)
            corner_radius = min(float(corner_ratio) * min(width, height), min(width, height) / 2)
            shapes.append(ShapePlacement(f"legend-swatch:{role}", role, "Rect",
                                         Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height))),
                                         slot_id=legend.slot_id, corner_radius=corner_radius, paint_order=paint_order))
        elif bucket == "line":
            marker_token = request.theme_tokens.optional_token(role, "marker", "marker")
            relations.append(RelationPlacement(f"legend-swatch:{role}", f"legend-swatch:{role}:start",
                                               f"legend-swatch:{role}:end",
                                               points=((x, y + height / 2), (x + width, y + height / 2)),
                                               semantic_id=role, slot_id=legend.slot_id, source_ref=role,
                                               marker_end=marker_geometry(marker_token) if marker_token else None))
        else:
            shapes.append(ShapePlacement(f"legend-swatch:{role}", role, "Rect",
                                         Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height))),
                                         slot_id=legend.slot_id))

    def emit_label(role: str, label: str, x: float, baseline: float, available: float) -> float:
        natural_width = measure_text_width(label, font_size=legend_size, font_metrics=metric_for("legend"),
                                           letter_spacing=float(legend_treatment.letter_spacing),
                                           text_transform=legend_treatment.transform,
                                           numeric_spacing=legend_treatment.numeric_spacing)
        content = label
        disposition = "fit"
        if natural_width > available and legend.overflow == "ellipsize-with-source":
            content = ellipsize_text(label, available_inline=available, font_size=legend_size,
                                     font_metrics=metric_for("legend"),
                                     letter_spacing=float(legend_treatment.letter_spacing),
                                     text_transform=legend_treatment.transform,
                                     numeric_spacing=legend_treatment.numeric_spacing)
            disposition = "ellipsized"
        elif natural_width > available and legend.overflow == "visible-overflow":
            disposition = "visible-overflow"
        placed = place_text(placement_id=f"legend:{role}", source_ref=role, content=content,
                            inline=x, baseline_block=baseline, typography_role="legend",
                            theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                            overflow=disposition, collision_region="legend",
                            collision_domain=CollisionDomain("legend", "content"), source_content=label,
                            available_inline_start=x, available_inline_size=available)
        text.append(placed)
        if disposition == "visible-overflow":
            side_content_warnings.append(FitWarning(
                "W_LAYOUT_VISIBLE_OVERFLOW", placed.placement_id, role, "legend-text", "visible-overflow",
                natural_width, float(placed.bounds.block_size), available, float(legend.bounds.block_size),
            ))
        return placed.bounds.block + placed.bounds.block_size

    final_legend_end = legend.bounds.block
    if direction == "inline":
        x = float(legend.bounds.inline)
        y = float(legend.bounds.block)
        row_height = 0.0
        slot_end = float(legend.bounds.inline) + float(legend.bounds.inline_size)
        for role, label in request.surface_content.legend_entries:
            width, height, bucket = swatch_geometry(role)
            if item_min_inline is not None and x > float(legend.bounds.inline) and slot_end - x < item_min_inline:
                y += row_height + gap
                x = float(legend.bounds.inline)
                row_height = 0.0
            emit_swatch(role, x, y, width, height, bucket)
            label_end = emit_label(role, label, x + width + gap, y + legend_size, max(0.0, slot_end - (x + width + gap)))
            row_height = max(row_height, height, text_line_block)
            final_legend_end = max(final_legend_end, Decimal(str(label_end)), Decimal(str(y + row_height)))
            x += width + gap + measure_text_width(label, font_size=legend_size, font_metrics=metric_for("legend"),
                                                   letter_spacing=float(legend_treatment.letter_spacing),
                                                   text_transform=legend_treatment.transform,
                                                   numeric_spacing=legend_treatment.numeric_spacing) + gap
    else:
        cursor = float(legend.bounds.block)
        for role, label in request.surface_content.legend_entries:
            width, height, bucket = swatch_geometry(role)
            row_height = max(height, text_line_block)
            swatch_top = cursor + (row_height - height) / 2.0
            baseline = cursor + (row_height - text_line_block) / 2.0 + legend_size
            text_inline = float(legend.bounds.inline) + width + gap
            text_available = max(0.0, float(legend.bounds.inline_size) - width - gap)
            emit_swatch(role, float(legend.bounds.inline), swatch_top, width, height, bucket)
            label_end = emit_label(role, label, text_inline, baseline, text_available)
            final_legend_end = max(final_legend_end, Decimal(str(label_end)))
            cursor += row_height + gap
    final_size = max(legend.bounds.block_size, final_legend_end - legend.bounds.block)
    replacement = replace(legend, bounds=Rect(legend.bounds.inline, legend.bounds.block,
                                               legend.bounds.inline_size, final_size))
    return SurfaceLegendBatch(replacement, tuple(marks), tuple(shapes), tuple(relations), tuple(text),
                              tuple(side_content_warnings))
