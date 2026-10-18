"""Owns legend entries and role-derived swatches in the fixed legend slot; reads completed slots and Theme tokens."""

from dataclasses import dataclass, replace
from decimal import Decimal
from collections.abc import Mapping, Sequence
from typing import Any, Callable

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_marks import MARK_GEOMETRY_ROLES
from chrona.presentation.layout.sources import SourceInput, SourceTextRun
from chrona.presentation.layout.text import ellipsize_text, measure_text_width, metric_for_role, place_text
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.surface_periods import compose_period_decoration
from chrona.presentation.layout.mark_geometry import SymbolPartPlacement, complete_point_outline, symbol_parts
from chrona.presentation.layout.legend_ink import actual_symbol_token
from chrona.presentation.model.point_paint import resolve_point_paint_role
from chrona.presentation.model.semantic_registry import semantic_binding, mark_style_role
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance
from chrona.presentation.model.font_metrics import FontMetricsError
from chrona.presentation.layout.rounded_outline import resolve_corner_radius
from chrona.presentation.layout.surface_quality import (
    GEOMETRY_TOLERANCE, CollisionDomain, FitWarning, MarkPlacement, RelationPlacement, ShapePlacement, SlotPlacement,
    SurfaceLayoutRequest, TextPlacement, PathCommand,
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
    """Completed extent plus the original allocation used for final fit checks."""

    slot: SlotPlacement
    marks: tuple[MarkPlacement, ...]
    shapes: tuple[ShapePlacement, ...]
    relations: tuple[RelationPlacement, ...]
    text: tuple[TextPlacement, ...]
    warnings: tuple[FitWarning, ...]
    allocated_slot: SlotPlacement
    label_targets: tuple[tuple[str, str], ...] = ()
    diagnostics: tuple[str, ...] = ()
    diagnostic_provenance: tuple[DiagnosticProvenance, ...] = ()


def _completed_point_key_parts(token: Mapping[str, Any], bounds: tuple[float, float, float, float],
                               paint_role: str, theme_tokens: Any
                               ) -> tuple[tuple[SymbolPartPlacement, ...], tuple[object, ...]]:
    """Pair the unchanged placed parts with their canonical local completed geometry."""
    placed = complete_point_outline(
        symbol_parts(token, bounds, catalog_glyphs=getattr(theme_tokens, "catalog_glyphs", None)),
        paint_role=paint_role, theme_tokens=theme_tokens)
    local = complete_point_outline(
        symbol_parts(token, (0.0, 0.0, 1.0, 1.0),
                     catalog_glyphs=getattr(theme_tokens, "catalog_glyphs", None)),
        paint_role=paint_role, theme_tokens=theme_tokens)
    identity = tuple((part.paint_mode,
                      part.line_cap if part.paint_mode == "stroke" else None,
                      part.line_join if part.paint_mode == "stroke" else None,
                      tuple((command.kind, command.points) for command in part.commands))
                     for part in local)
    return placed, identity


def _legacy_swatch_size(legend_size: float) -> float:
    return max(2.0, legend_size * 0.8)


def _swatch_paint_role(role: str, tokens: Any) -> str:
    if role.startswith("scale:"):
        return semantic_binding("scaleLegendEntry").scene_role
    role = mark_style_role(role)
    if role in ("asOf", "deadlineMark", "progressFill"):
        return semantic_binding(role).scene_role
    return resolve_point_paint_role(role, gate_declared=tokens.has_role("gate"), legend=True)


def legend_item_gap(declared: Any, legend_size: float) -> float:
    """Return the space between entries and between a swatch and its label.

    Today's fixed swatch->label offset was `swatch_size * 1.5`, i.e. one
    swatch width plus a "gap" of exactly half a swatch; an unmigrated (no
    declared `gap`) legend slot reproduces that split (#427).
    """
    return float(declared) if declared is not None else _legacy_swatch_size(legend_size) * 0.5


def swatch_extent(role: str, tokens: Any, mark_block_size: float, legend_size: float,
                  shape: str | None = None, *,
                  glyph_footprint: tuple[float, float] | None = None,
                  paint_role: str | None = None) -> tuple[float, float, str]:
    """Return one legend entry's (inline size, block size, dispatch bucket) (#427).

    The size is the role's own mark geometry against the document's own
    `timeline.mark.blockSize` for a `mark`/`point` role -- literally the
    size the chart draws it -- or `legend-swatch.swatchInlineSize` (or its
    documented fallback) for a role with no single on-chart length. A role
    this table does not recognize keeps today's fixed square. Measuring the
    legend slot and drawing the legend both call this function (#497).
    """
    # Detail's per-entry value wins; otherwise the Theme's one shared default
    # applies equally to authored and generated keys. Resolve it here so every
    # measurement and drawing path consumes the same dispatch bucket.
    role = mark_style_role(role)
    if shape is None:
        shape = tokens.legend_swatch_shape()
    legacy = _legacy_swatch_size(legend_size)
    declared_inline = tokens.optional_number("legend-swatch", "swatchInlineSize")
    fallback_inline = float(declared_inline) if declared_inline is not None else legacy
    text_line_block = legend_size * float(tokens.text_treatment("legend").line_height)
    _, area_block, point_size = tokens.legend_swatch_sizes()
    if shape == "circle":
        side = area_block if area_block is not None else legacy
        return side, side, shape
    if shape == "rule-pair":
        stroke = tokens.optional_number(paint_role or _swatch_paint_role(role, tokens), "strokeWidth")
        width = float(stroke) if stroke is not None else 0.0
        return max(fallback_inline, 3 * width), max(area_block or legacy, 2 * width), shape
    if glyph_footprint is not None:
        return ((point_size, point_size, "glyph") if point_size is not None
                else (*glyph_footprint, "glyph"))
    if role == "milestone":
        height_ratio, *_ = tokens.mark_geometry("planned")
        side = point_size if point_size is not None else float(height_ratio) * mark_block_size
        return side, side, "point"
    if role in MARK_GEOMETRY_ROLES:
        block = float(tokens.mark_geometry(role)[0]) * mark_block_size
        # A key without a declared `swatchInlineSize` is a miniature of the bar it names: landscape, as the bars are (#499).
        # A declared size is the author's and is kept as written.
        inline = fallback_inline if declared_inline is not None else max(fallback_inline, 2.0 * block)
        return inline, block, "mark"
    if role in ("asOf", "dependency", "dependency-critical", "critical-edge", "deadlineMark"):
        return fallback_inline, text_line_block, "line"
    if area_block is not None:
        # An area (background) key is a declared rectangle (#1111): opt-in through `swatchBlockSize`.
        return (float(declared_inline) if declared_inline is not None else legacy), area_block, "legacy"
    return legacy, legacy, "legacy"


def entry_swatch_extent(entry: SurfaceLegendEntry, tokens: Any, mark_block_size: float,
                        legend_size: float) -> tuple[float, float, str]:
    glyph = entry.realized_key.glyph if entry.realized_key is not None else None
    return swatch_extent(entry.role, tokens, mark_block_size, legend_size, entry.swatch_shape,
                         glyph_footprint=glyph.footprint if glyph is not None else None,
                         paint_role=entry.realized_key.paint_role if entry.realized_key is not None else None)


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
    columns: int | None = None


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
        str(node.get("overflow", "visible-overflow")),
        int(node["columns"]) if "columns" in node else None)


def legend_source_input(entries: tuple[SurfaceLegendEntry, ...], *, tokens: Any, mark_block_size: float,
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
    extents = tuple(entry_swatch_extent(entry, tokens, mark_block_size, legend_size)[0]
                    for entry in entries)
    runs = tuple(SourceTextRun(entry.label, "legend", entry.role,
                               Decimal(str(extent + label_gap))) for entry, extent in zip(entries, extents))
    grid = arrangement.columns is not None
    line = arrangement.direction == "inline" and not grid
    min_inline: Decimal | None = None
    if arrangement.overflow == "ellipsize-with-source":
        if line and arrangement.item_min_inline_size is not None:
            # A wrapping line never needs more than its widest single entry.
            metrics = metric_for_role(tokens, "legend", font_metrics)
            min_inline = max(Decimal(str(measure_text_width(
                run.content, font_size=legend_size, font_metrics=metrics,
                letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform))) + run.inline_advance
                for run in runs)
        elif not line and not grid:
            metrics = metric_for_role(tokens, "legend", font_metrics)
            ellipsis = measure_text_width("\u2026", font_size=legend_size, font_metrics=metrics,
                                          letter_spacing=float(treatment.letter_spacing),
                                          text_transform=treatment.transform)
            min_inline = Decimal(str(max(extents) + label_gap + ellipsis))
    if grid:
        text_line = legend_size * float(treatment.line_height)
        row_block = max([text_line] + [entry_swatch_extent(entry, tokens, mark_block_size, legend_size)[1]
                                       for entry in entries])
        return SourceInput(runs=runs, typography_role="legend", run_flow="grid", run_gap=Decimal(str(gap)),
                           columns=arrangement.columns, row_block=Decimal(str(row_block)))
    row_block = Decimal(0)
    if line:
        # The height of one drawn row, as `place_legend` draws it: the label line box or the tallest swatch (#1649).
        # The label line box is the exact product the measurement's one-row minimum uses, not its float product: a
        # float 12 * 1.4 is 16.799999999999997, below the minimum 16.8, and the slot would then be allocated less than
        # its own minimum and warn W_LAYOUT_VISIBLE_OVERFLOW though the row fits (#1649).
        row_block = max([treatment.font_size * treatment.line_height]
                        + [Decimal(str(entry_swatch_extent(entry, tokens, mark_block_size, legend_size)[1]))
                           for entry in entries])
    return SourceInput(runs=runs, typography_role="legend", run_flow="line" if line else "stack",
                       run_gap=Decimal(str(gap)), min_inline=min_inline, row_block=row_block)


def wrapped_legend_line_block(entry_inline_sizes: Sequence[Decimal], *, gap: Decimal, row_block: Decimal,
                              item_min_inline: Decimal | None, available_inline: Decimal) -> Decimal:
    """Return the block a `line` legend draws at a known inline size: the rows it wraps to (#1649).

    This is the wrapping rule of `place_legend`'s `inline` direction: an entry starts a new row only when the
    slot declares `itemMinInlineSize` and less than that is left on the current row. Without it the legend is
    one row. Each entry advances by its swatch, label gap, label and the entry gap (a `line` measurement's run).
    """
    rows, used = 1, Decimal(0)
    for size in entry_inline_sizes:
        if item_min_inline is not None and used > 0 and available_inline - used < item_min_inline:
            rows, used = rows + 1, Decimal(0)
        used += size + gap
    return rows * row_block + (rows - 1) * gap


def place_legend(context: SurfaceLegendContext) -> SurfaceLegendBatch:
    """Place every legend entry inside the allocated legend slot and return its completed extent."""
    request, legend = context.request, context.legend
    metric_values, metric_for = context.metric_values, context.metric_for
    marks: list[MarkPlacement] = []
    shapes: list[ShapePlacement] = []
    relations: list[RelationPlacement] = []
    text: list[TextPlacement] = []
    label_targets: list[tuple[str, str]] = []
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

    def swatch_geometry(entry: SurfaceLegendEntry) -> tuple[float, float, str]:
        return entry_swatch_extent(entry, request.theme_tokens, mark_block_size, legend_size)

    def emit_swatch(entry: SurfaceLegendEntry, x: float, y: float, width: float, height: float, bucket: str) -> None:
        role = mark_style_role(entry.role)
        swatch_id = entry.swatch_placement_id
        if bucket in ("circle", "rule-pair"):
            if entry.source_ref is not None and entry.style_scope is None and request.theme_tokens.background(role)[0] == "none":
                return
            bounds = Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height)))
            paint_role = (entry.realized_key.paint_role if entry.realized_key is not None
                          else _swatch_paint_role(role, request.theme_tokens))
            if bucket == "circle":
                commands = symbol_parts({"shape": "circle"}, (x, y, width, height))[0].commands
            else:
                half_stroke = float(request.theme_tokens.number(paint_role, "strokeWidth")) / 2
                commands = tuple(command for inline in (x + width / 4, x + 3 * width / 4)
                                 for command in (PathCommand("move", ((inline, y + half_stroke),)),
                                                 PathCommand("line", ((inline, y + height - half_stroke),))))
            shapes.append(ShapePlacement(swatch_id, entry.source_identity,
                                         "Symbol" if bucket == "circle" else "Path", bounds,
                                         points=(tuple(command.points[0] for command in commands)
                                                 if bucket == "rule-pair" else ()),
                                         path_commands=commands, visual_role=paint_role, slot_id=legend.slot_id,
                                         semantic_id="legendEntry", legend_swatch_shape=bucket,
                                         legend_paint=entry.realized_key.paint if entry.realized_key else None))
            return
        if entry.realized_key is not None:
            key = entry.realized_key
            if key.glyph is not None:
                bounds = Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height)))
                parts, geometry_identity = _completed_point_key_parts(
                    actual_symbol_token(request.theme_tokens, key.glyph.selected_role),
                    (x, y, width, height), key.paint_role, request.theme_tokens)
                assert len(parts) == len(key.glyph.paints), "composite key geometry and ink must stay aligned"
                center = (x + width / 2, y + height / 2)
                marks.append(MarkPlacement(swatch_id, entry.source_identity, bounds, center, center,
                    mark_shape="point", slot_id=legend.slot_id, semantic_id="actual",
                    theme_role=key.paint_role, symbol_parts=parts, legend_paints=key.glyph.paints,
                    legend_geometry_identity=geometry_identity))
                return
            corner_radius = 0.0
            if bucket == "mark":
                corner_ratio = request.theme_tokens.mark_geometry(role)[3]
                corner_radius = resolve_corner_radius(
                    request.theme_tokens.optional_token(role, "cornerRadius", "radius"),
                    width=width, height=height,
                    legacy_radius=min(float(corner_ratio) * min(width, height), min(width, height) / 2))
            shapes.append(ShapePlacement(
                swatch_id, entry.source_identity, "Rect",
                Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height))),
                slot_id=legend.slot_id, semantic_id="legendEntry", corner_radius=corner_radius,
                visual_role=entry.realized_key.paint_role, legend_paint=entry.realized_key.paint))
            return
        if entry.style_scope is not None:
            shapes.append(ShapePlacement(swatch_id, entry.source_identity, "Rect",
                Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height))),
                slot_id=legend.slot_id, semantic_id="legendEntry"))
            return
        if entry.source_ref is not None:
            treatment, paint_order = request.theme_tokens.background(role)
            # A declared `none` still reserves and labels the entry, but has no visible swatch.
            if treatment == "none":
                return
            bounds = Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height)))
            shapes.extend(compose_period_decoration(
                bounds=bounds, placement_id=swatch_id, source_ref=entry.source_ref,
                visual_role=role, slot_id=legend.slot_id, paint_order=paint_order,
                theme_tokens=request.theme_tokens, semantic_id="legendEntry"))
            return
        if bucket == "point":
            bounds = Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height)))
            paint_role = resolve_point_paint_role(
                role, gate_declared=request.theme_tokens.has_role("gate"), legend=True)
            parts, geometry_identity = _completed_point_key_parts(
                request.theme_tokens.variant_symbol("planned"), (x, y, width, height),
                paint_role, request.theme_tokens)
            marks.append(MarkPlacement(swatch_id, role,
                                       bounds,
                                       (x + width / 2, y + height / 2), (x + width / 2, y + height / 2),
                                       mark_shape="point", slot_id=legend.slot_id, semantic_id="planned",
                                       symbol_parts=parts, legend_geometry_identity=geometry_identity))
        elif bucket == "mark":
            height_ratio, offset_ratio, paint_order, corner_ratio = request.theme_tokens.mark_geometry(role)
            corner_radius = min(float(corner_ratio) * min(width, height), min(width, height) / 2)
            corner_radius = resolve_corner_radius(request.theme_tokens.optional_token(role, "cornerRadius", "radius"),
                                                  width=width, height=height, legacy_radius=corner_radius)
            shapes.append(ShapePlacement(swatch_id, role, "Rect",
                                         Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height))),
                                         slot_id=legend.slot_id, corner_radius=corner_radius, paint_order=paint_order))
        elif bucket == "line":
            marker_token = request.theme_tokens.optional_token(role, "marker", "marker")
            semantic_id = "criticalEdge" if role == "critical-edge" else role
            relations.append(RelationPlacement(swatch_id, f"{swatch_id}:start",
                                               f"{swatch_id}:end",
                                               points=((x, y + height / 2), (x + width, y + height / 2)),
                                               semantic_id=semantic_id, slot_id=legend.slot_id, source_ref=role,
                                               marker_end=marker_geometry(marker_token, stroke_width=float(
                                                   request.theme_tokens.number(role, "strokeWidth")))
                                               if marker_token else None))
        else:
            shapes.append(ShapePlacement(swatch_id, role, "Rect",
                                         Rect(Decimal(str(x)), Decimal(str(y)), Decimal(str(width)), Decimal(str(height))),
                                         slot_id=legend.slot_id))

    def emit_label(entry: SurfaceLegendEntry, x: float, baseline: float, available: float) -> float:
        role, label = entry.role, entry.label
        natural_width = measure_text_width(label, font_size=legend_size, font_metrics=metric_for("legend"),
                                           letter_spacing=float(legend_treatment.letter_spacing),
                                           text_transform=legend_treatment.transform,
                                           numeric_spacing=legend_treatment.numeric_spacing)
        content = label
        if entry.style_scope is not None and entry.style_scope.show_scope:
            qualified = label + " when " + entry.style_scope.selector
            try:
                qualified_width = measure_text_width(
                    qualified, font_size=legend_size, font_metrics=metric_for("legend"),
                    letter_spacing=float(legend_treatment.letter_spacing),
                    text_transform=legend_treatment.transform,
                    numeric_spacing=legend_treatment.numeric_spacing)
            except FontMetricsError:
                pass  # Optional scope alone must not reject the primary key.
            else:
                if qualified_width <= available:
                    content = qualified
                    natural_width = qualified_width
        disposition = "fit"
        ellipsized = False
        if natural_width > available and legend.overflow == "ellipsize-with-source":
            if entry.role == "forecast":
                raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", entry.text_placement_id)
            content = ellipsize_text(label, available_inline=available, font_size=legend_size,
                                     font_metrics=metric_for("legend"),
                                     letter_spacing=float(legend_treatment.letter_spacing),
                                     text_transform=legend_treatment.transform,
                                     numeric_spacing=legend_treatment.numeric_spacing)
            disposition = "ellipsized"
            ellipsized = True
        elif natural_width > available and legend.overflow == "visible-overflow":
            disposition = "visible-overflow"
        placed = place_text(placement_id=entry.text_placement_id, source_ref=entry.source_identity, content=content,
                            inline=x, baseline_block=baseline, typography_role="legend",
                            theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                            overflow=disposition, collision_region="legend",
                            collision_domain=CollisionDomain("legend", "content"), source_content=label,
                            available_inline_start=x, available_inline_size=available)
        text.append(placed)
        label_targets.append((entry.role, placed.placement_id))
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
    if legend.columns:
        # A declared grid (#1290): entry k sits in column k mod columns of row k div columns; each column is as wide as
        # its widest entry (swatch, gap and label), `gap` apart, and every row is as tall as the tallest key.
        entries = request.surface_content.legend_entries
        row_block = max([text_line_block] + [swatch_geometry(entry)[1] for entry in entries])
        label_width = [measure_text_width(entry.label, font_size=legend_size, font_metrics=metric_for("legend"),
                                                letter_spacing=float(legend_treatment.letter_spacing),
                                                text_transform=legend_treatment.transform,
                                                numeric_spacing=legend_treatment.numeric_spacing)
                       for entry in entries]
        entry_width = [swatch_geometry(entry)[0] + label_gap + label_width[index]
                       for index, entry in enumerate(entries)]
        count = len(entries)
        column_widths = [max((entry_width[index] for index in range(column, count, legend.columns)), default=0.0)
                         for column in range(min(legend.columns, count))]
        slot_end = float(legend.bounds.inline) + float(legend.bounds.inline_size)
        if legend.column_distribution == "spread" and len(column_widths) > 1:
            # `spread` (#1392): equal columns across the slot, each at least the widest entry of any column; when they do not
            # fit the slot the columns stay packed as under `start`.
            share = (float(legend.bounds.inline_size) - gap * (len(column_widths) - 1)) / len(column_widths)
            column_widths = [share] * len(column_widths) if max(column_widths) <= share else column_widths
        starts = [float(legend.bounds.inline)]
        for width in column_widths[:-1]:
            starts.append(starts[-1] + width + gap)
        for index, entry in enumerate(entries):
            role = entry.role
            row, column = divmod(index, legend.columns)
            x = starts[column]
            y = float(legend.bounds.block) + row * (row_block + gap)
            width, height, bucket = swatch_geometry(entry)
            emit_swatch(entry, x, y + (row_block - height) / 2.0, width, height, bucket)
            label_end = emit_label(entry, x + width + label_gap, y + (row_block - text_line_block) / 2.0 + legend_size,
                                   min(max(0.0, slot_end - (x + width + label_gap)),
                                       max(0.0, column_widths[column] - width - label_gap))
                                   if entry.style_scope is not None else max(0.0, slot_end - (x + width + label_gap)))
            final_legend_end = max(final_legend_end, Decimal(str(label_end)), Decimal(str(y + row_block)))
    elif direction == "inline":
        x = float(legend.bounds.inline)
        y = float(legend.bounds.block)
        row_height = 0.0
        slot_end = float(legend.bounds.inline) + float(legend.bounds.inline_size)
        # Every swatch and label of the legend is centred on one row centreline (#991), the way the block
        # direction centres each entry: the row is as tall as the tallest swatch or the label line box.
        row_block = max([text_line_block] + [swatch_geometry(entry)[1] for entry in request.surface_content.legend_entries])
        for entry in request.surface_content.legend_entries:
            role, label = entry.role, entry.label
            width, height, bucket = swatch_geometry(entry)
            if item_min_inline is not None and x > float(legend.bounds.inline) and slot_end - x < item_min_inline:
                y += row_height + gap
                x = float(legend.bounds.inline)
                row_height = 0.0
            emit_swatch(entry, x, y + (row_block - height) / 2.0, width, height, bucket)
            label_end = emit_label(entry, x + width + label_gap, y + (row_block - text_line_block) / 2.0 + legend_size,
                                   min(max(0.0, slot_end - (x + width + label_gap)),
                                       measure_text_width(label, font_size=legend_size, font_metrics=metric_for("legend"),
                                           letter_spacing=float(legend_treatment.letter_spacing),
                                           text_transform=legend_treatment.transform,
                                           numeric_spacing=legend_treatment.numeric_spacing))
                                   if entry.style_scope is not None else max(0.0, slot_end - (x + width + label_gap)))
            row_height = row_block
            final_legend_end = max(final_legend_end, Decimal(str(label_end)), Decimal(str(y + row_height)))
            x += width + label_gap + measure_text_width(label, font_size=legend_size, font_metrics=metric_for("legend"),
                                                   letter_spacing=float(legend_treatment.letter_spacing),
                                                   text_transform=legend_treatment.transform,
                                                   numeric_spacing=legend_treatment.numeric_spacing) + gap
    else:
        cursor = float(legend.bounds.block)
        for entry in request.surface_content.legend_entries:
            role, label = entry.role, entry.label
            width, height, bucket = swatch_geometry(entry)
            row_height = max(height, text_line_block)
            swatch_top = cursor + (row_height - height) / 2.0
            baseline = cursor + (row_height - text_line_block) / 2.0 + legend_size
            text_inline = float(legend.bounds.inline) + width + label_gap
            text_available = max(0.0, float(legend.bounds.inline_size) - width - label_gap)
            emit_swatch(entry, float(legend.bounds.inline), swatch_top, width, height, bucket)
            label_end = emit_label(entry, text_inline, baseline, text_available)
            final_legend_end = max(final_legend_end, Decimal(str(label_end)))
            cursor += row_height + gap
    final_size = max(legend.bounds.block_size, final_legend_end - legend.bounds.block)
    if (direction == "inline" and not legend.columns and legend.bounds.block_size >= text_line_block
            and final_legend_end - legend.bounds.block > legend.bounds.block_size + GEOMETRY_TOLERANCE):
        # The wrapped rows are known only now: a legend that needs more rows than its slot has still warns, with the
        # block its rows really need (a slot shorter than one row is reported by the track check) (#1273).
        side_content_warnings.append(FitWarning(
            "W_LAYOUT_VISIBLE_OVERFLOW", legend.slot_id, "legend", "layout-track", "visible-overflow",
            float(legend.bounds.inline_size), float(final_legend_end - legend.bounds.block),
            float(legend.bounds.inline_size), float(legend.bounds.block_size)))
    replacement = replace(legend, bounds=Rect(legend.bounds.inline, legend.bounds.block,
                                               legend.bounds.inline_size, final_size))
    return SurfaceLegendBatch(replacement, tuple(marks), tuple(shapes), tuple(relations), tuple(text),
                              tuple(side_content_warnings), legend, tuple(label_targets))
