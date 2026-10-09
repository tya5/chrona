"""Owns legend entries and role-derived swatches in the fixed legend slot; reads completed slots and Theme tokens."""

from dataclasses import dataclass, replace
from decimal import Decimal
from collections.abc import Mapping
from typing import Any, Callable

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.surface_marks import (
    MARK_GEOMETRY_ROLES,
)
from chrona.presentation.layout.sources import SourceInput, SourceTextRun
from chrona.presentation.layout.text import ellipsize_text, measure_text_width, metric_for_role, place_text
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.mark_geometry import complete_point_outline, symbol_parts
from chrona.presentation.model.point_paint import resolve_point_paint_role
from chrona.presentation.layout.rounded_outline import resolve_corner_radius
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


def _legacy_swatch_size(legend_size: float) -> float:
    return max(2.0, legend_size * 0.8)


def legend_item_gap(declared: Any, legend_size: float) -> float:
    """Return the space between entries and between a swatch and its label.

    Today's fixed swatch->label offset was `swatch_size * 1.5`, i.e. one
    swatch width plus a "gap" of exactly half a swatch; an unmigrated (no
    declared `gap`) legend slot reproduces that split (#427).
    """
    return float(declared) if declared is not None else _legacy_swatch_size(legend_size) * 0.5


def swatch_extent(role: str, tokens: Any, mark_block_size: float, legend_size: float) -> tuple[float, float, str]:
    """Return one legend entry's (inline size, block size, dispatch bucket) (#427).

    The size is the role's own mark geometry against the document's own
    `timeline.mark.blockSize` for a `mark`/`point` role -- literally the
    size the chart draws it -- or `legend-swatch.swatchInlineSize` (or its
    documented fallback) for a role with no single on-chart length. A role
    this table does not recognize keeps today's fixed square. Measuring the
    legend slot and drawing the legend both call this function (#497).
    """
    legacy = _legacy_swatch_size(legend_size)
    declared_inline = tokens.optional_number("legend-swatch", "swatchInlineSize")
    fallback_inline = float(declared_inline) if declared_inline is not None else legacy
    text_line_block = legend_size * float(tokens.text_treatment("legend").line_height)
    _, area_block, point_size = tokens.legend_swatch_sizes()
    if role == "milestone":
        height_ratio, *_ = tokens.mark_geometry("planned")
        side = point_size if point_size is not None else float(height_ratio) * mark_block_size
        return side, side, "point"
    if role in MARK_GEOMETRY_ROLES:
        return fallback_inline, float(tokens.mark_geometry(role)[0]) * mark_block_size, "mark"
    if role in ("asOf", "dependency", "dependency-critical", "deadlineMark"):
        return fallback_inline, text_line_block, "line"
    if area_block is not None:
        # An area (background) key is a declared rectangle (#1111): opt-in through `swatchBlockSize`.
        return (float(declared_inline) if declared_inline is not None else legacy), area_block, "legacy"
    return legacy, legacy, "legacy"


def swatch_label_gap(declared: Any, tokens: Any, legend_size: float) -> float:
    """Return the distance from a swatch to its label: `swatchGap` when declared, else the entry gap (#1111)."""
    swatch_gap = tokens.legend_swatch_sizes()[0]
    return swatch_gap if swatch_gap is not None else legend_item_gap(declared, legend_size)


@dataclass(frozen=True)
class LegendArrangement:
    """The legend slot's own declarations that decide how its entries are laid out."""

    direction: str = "block"
    gap: Decimal | None = None
    item_min_inline_size: Decimal | None = None
    overflow: str = "visible-overflow"


def legend_arrangement(resolved_profile: Any) -> LegendArrangement:
    """Read the legend slot's direction, gap, itemMinInlineSize and overflow from a resolved Layout Profile."""
    distances = resolved_profile.distances

    def find(node: Mapping[str, Any], path: str) -> tuple[Mapping[str, Any], str] | None:
        if node.get("kind") == "slot":
            return (node, path) if node.get("source") == "legend" else None
        for index, child in enumerate(node.get("children", ())):
            found = find(child, f"{path}/children/{index}")
            if found is not None:
                return found
        return None

    found = find(resolved_profile.profile["root"], "/root")
    if found is None:
        return LegendArrangement()
    node, path = found
    return LegendArrangement(
        str(node.get("direction", "block")),
        distances.get(f"{path}/gap") if "gap" in node else None,
        distances.get(f"{path}/itemMinInlineSize") if "itemMinInlineSize" in node else None,
        str(node.get("overflow", "visible-overflow")))


def legend_source_input(entries: tuple[tuple[str, str], ...], *, tokens: Any, mark_block_size: float,
                        font_metrics: Any, arrangement: LegendArrangement) -> SourceInput:
    """Describe the legend slot's content for measurement: the entries Layout will draw (#497).

    Each entry is its swatch, the item gap and its drawn label, so the measured
    width of a run is the width of the entry. A `block` legend stacks the entries
    (the slot is as wide as the widest); an `inline` legend lays them on one line.
    Under `ellipsize-with-source` the declared floor is what the content can shrink
    to; under any other overflow nothing shrinks and the floor is the preferred size.
    """
    treatment = tokens.text_treatment("legend")
    legend_size = float(treatment.font_size)
    gap = legend_item_gap(arrangement.gap, legend_size)
    label_gap = swatch_label_gap(arrangement.gap, tokens, legend_size)
    if not entries:
        return SourceInput(("legend",), typography_role="legend")
    extents = {role: swatch_extent(role, tokens, mark_block_size, legend_size)[0] for role, _ in entries}
    runs = tuple(SourceTextRun(label, "legend", role, Decimal(str(extents[role] + label_gap))) for role, label in entries)
    line = arrangement.direction == "inline"
    min_inline: Decimal | None = None
    if arrangement.overflow == "ellipsize-with-source":
        if line and arrangement.item_min_inline_size is not None:
            # A wrapping line never needs more than its widest single entry.
            metrics = metric_for_role(tokens, "legend", font_metrics)
            min_inline = max(Decimal(str(measure_text_width(
                run.content, font_size=legend_size, font_metrics=metrics,
                letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform))) + run.inline_advance
                for run in runs)
        elif not line:
            metrics = metric_for_role(tokens, "legend", font_metrics)
            ellipsis = measure_text_width("\u2026", font_size=legend_size, font_metrics=metrics,
                                          letter_spacing=float(treatment.letter_spacing),
                                          text_transform=treatment.transform)
            min_inline = Decimal(str(max(extents.values()) + label_gap + ellipsis))
    return SourceInput(runs=runs, typography_role="legend", run_flow="line" if line else "stack",
                       run_gap=Decimal(str(gap)), min_inline=min_inline)


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
    gap = legend_item_gap(legend.gap, legend_size)
    label_gap = swatch_label_gap(legend.gap, request.theme_tokens, legend_size)
    direction = legend.direction
    item_min_inline = float(legend.item_min_inline_size) if legend.item_min_inline_size is not None else None

    def swatch_geometry(role: str) -> tuple[float, float, str]:
        return swatch_extent(role, request.theme_tokens, mark_block_size, legend_size)

    def emit_swatch(role: str, x: float, y: float, width: float, height: float, bucket: str) -> None:
        if bucket == "point":
            bounds = Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height)))
            parts = symbol_parts(
                request.theme_tokens.variant_symbol("planned"), (x, y, width, height),
                catalog_glyphs=getattr(request.theme_tokens, "catalog_glyphs", None),
            )
            parts = complete_point_outline(
                parts, paint_role=resolve_point_paint_role(
                    role, gate_declared=request.theme_tokens.has_role("gate"), legend=True),
                theme_tokens=request.theme_tokens)
            marks.append(MarkPlacement(f"legend-swatch:{role}", role,
                                       bounds,
                                       (x + width / 2, y + height / 2), (x + width / 2, y + height / 2),
                                       mark_shape="point", slot_id=legend.slot_id, semantic_id="planned",
                                       symbol_parts=parts))
        elif bucket == "mark":
            height_ratio, offset_ratio, paint_order, corner_ratio = request.theme_tokens.mark_geometry(role)
            corner_radius = min(float(corner_ratio) * min(width, height), min(width, height) / 2)
            corner_radius = resolve_corner_radius(request.theme_tokens.optional_token(role, "cornerRadius", "radius"),
                                                  width=width, height=height, legacy_radius=corner_radius)
            shapes.append(ShapePlacement(f"legend-swatch:{role}", role, "Rect",
                                         Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height))),
                                         slot_id=legend.slot_id, corner_radius=corner_radius, paint_order=paint_order))
        elif bucket == "line":
            marker_token = request.theme_tokens.optional_token(role, "marker", "marker")
            relations.append(RelationPlacement(f"legend-swatch:{role}", f"legend-swatch:{role}:start",
                                               f"legend-swatch:{role}:end",
                                               points=((x, y + height / 2), (x + width, y + height / 2)),
                                               semantic_id=role, slot_id=legend.slot_id, source_ref=role,
                                               marker_end=marker_geometry(marker_token, stroke_width=float(
                                                   request.theme_tokens.number(role, "strokeWidth")))
                                               if marker_token else None))
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
        ellipsized = False
        if natural_width > available and legend.overflow == "ellipsize-with-source":
            content = ellipsize_text(label, available_inline=available, font_size=legend_size,
                                     font_metrics=metric_for("legend"),
                                     letter_spacing=float(legend_treatment.letter_spacing),
                                     text_transform=legend_treatment.transform,
                                     numeric_spacing=legend_treatment.numeric_spacing)
            disposition = "ellipsized"
            ellipsized = True
        elif natural_width > available and legend.overflow == "visible-overflow":
            disposition = "visible-overflow"
        placed = place_text(placement_id=f"legend:{role}", source_ref=role, content=content,
                            inline=x, baseline_block=baseline, typography_role="legend",
                            theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                            overflow=disposition, collision_region="legend",
                            collision_domain=CollisionDomain("legend", "content"), source_content=label,
                            available_inline_start=x, available_inline_size=available)
        text.append(placed)
        if ellipsized:
            # An ellipsis is never silent: the Scene names the text, its natural size and the room it had (#497).
            side_content_warnings.append(FitWarning(
                "W_LAYOUT_TEXT_ELLIPSIZED", placed.placement_id, role, "legend-text", "ellipsize-with-source",
                natural_width, float(placed.bounds.block_size), available, float(legend.bounds.block_size),
            ))
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
        # Every swatch and label of the legend is centred on one row centreline (#991), the way the block
        # direction centres each entry: the row is as tall as the tallest swatch or the label line box.
        row_block = max([text_line_block] + [swatch_geometry(role)[1] for role, _ in request.surface_content.legend_entries])
        for role, label in request.surface_content.legend_entries:
            width, height, bucket = swatch_geometry(role)
            if item_min_inline is not None and x > float(legend.bounds.inline) and slot_end - x < item_min_inline:
                y += row_height + gap
                x = float(legend.bounds.inline)
                row_height = 0.0
            emit_swatch(role, x, y + (row_block - height) / 2.0, width, height, bucket)
            label_end = emit_label(role, label, x + width + label_gap, y + (row_block - text_line_block) / 2.0 + legend_size,
                                   max(0.0, slot_end - (x + width + label_gap)))
            row_height = row_block
            final_legend_end = max(final_legend_end, Decimal(str(label_end)), Decimal(str(y + row_height)))
            x += width + label_gap + measure_text_width(label, font_size=legend_size, font_metrics=metric_for("legend"),
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
            text_inline = float(legend.bounds.inline) + width + label_gap
            text_available = max(0.0, float(legend.bounds.inline_size) - width - label_gap)
            emit_swatch(role, float(legend.bounds.inline), swatch_top, width, height, bucket)
            label_end = emit_label(role, label, text_inline, baseline, text_available)
            final_legend_end = max(final_legend_end, Decimal(str(label_end)))
            cursor += row_height + gap
    final_size = max(legend.bounds.block_size, final_legend_end - legend.bounds.block)
    replacement = replace(legend, bounds=Rect(legend.bounds.inline, legend.bounds.block,
                                               legend.bounds.inline_size, final_size))
    return SurfaceLegendBatch(replacement, tuple(marks), tuple(shapes), tuple(relations), tuple(text),
                              tuple(side_content_warnings))
