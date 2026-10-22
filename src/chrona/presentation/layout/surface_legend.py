"""Owns legend entries and role-derived swatches in the fixed legend slot; reads completed slots and Theme tokens."""

from dataclasses import dataclass, replace
from decimal import Decimal
from collections.abc import Mapping, Sequence
from typing import Any, Callable

from chrona.presentation.layout.model import LayoutError, Rect, geometry_sum
from chrona.presentation.layout.tracks import resolve_flexible_tracks
from chrona.presentation.layout.surface_marks import MARK_GEOMETRY_ROLES
from chrona.presentation.layout.sources import (MeasuredLegend, MeasuredLegendEntry, SourceInput,
                                                SourceTextRun)
from chrona.presentation.layout.text import (TextSegment, ellipsize_text, measure_text_segments, measure_text_width,
                                             metric_for_role, place_text, _wrap_units)
from chrona.presentation.layout.relation_terminals import marker_geometry
from chrona.presentation.layout.surface_periods import compose_period_decoration
from chrona.presentation.layout.mark_geometry import (
    SymbolPartPlacement, complete_point_outline, symbol_parts, place_canonical_point_geometry,
)
from chrona.presentation.layout.legend_ink import point_symbol_token
from chrona.presentation.model.point_paint import resolve_point_paint_role
from chrona.presentation.model.semantic_registry import semantic_binding, mark_style_role
from chrona.presentation.model.surface_content import SurfaceLegendEntry
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance
from chrona.presentation.model.font_metrics import FontMetricsError
from chrona.presentation.layout.rounded_outline import resolve_corner_radius
from chrona.presentation.layout.surface_quality import (
    GEOMETRY_TOLERANCE, CollisionDomain, FitWarning, MarkPlacement, RelationPlacement, ShapePlacement, SlotPlacement,
    SurfaceLayoutRequest, TextPlacement, TextRunPlacement, PathCommand,
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
    entries: tuple[SurfaceLegendEntry, ...] = ()
    measured_layout: MeasuredLegend | None = None


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
    return float(_legend_item_gap_decimal(declared, legend_size))


def _legend_item_gap_decimal(declared: Any, legend_size: float) -> Decimal:
    if declared is not None:
        return Decimal(str(declared))
    # Keep the documented half-of-legacy-swatch rule in Decimal arithmetic;
    # float 0.8 * 14 can otherwise turn the exact 5.6 gap into 5.6000000000000005.
    size = Decimal(str(legend_size))
    return max(Decimal("2"), size * Decimal("0.8")) / Decimal(2)


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
    if not entry.swatch_visible:
        return 0.0, 0.0, "none"
    glyph = entry.realized_key.glyph if entry.realized_key is not None else None
    return swatch_extent(entry.role, tokens, mark_block_size, legend_size, entry.swatch_shape,
                         glyph_footprint=glyph.footprint if glyph is not None else None,
                         paint_role=entry.realized_key.paint_role if entry.realized_key is not None else None)


def swatch_label_gap(declared: Any, tokens: Any, legend_size: float) -> float:
    """Return the distance from a swatch to its label: `swatchGap` when declared, else the entry gap (#1111)."""
    swatch_gap = tokens.legend_swatch_sizes()[0]
    return swatch_gap if swatch_gap is not None else legend_item_gap(declared, legend_size)


def entry_label_gap(entry: SurfaceLegendEntry, declared: Any, tokens: Any, legend_size: float) -> float:
    return swatch_label_gap(declared, tokens, legend_size) if entry.swatch_visible else 0.0


def _label_reservation(swatch_inline: float, label_gap: float) -> Decimal:
    """Share the measured swatch/gap grouping before composing source and slot geometry."""
    return Decimal(str(geometry_sum((swatch_inline, label_gap))))


def _legend_text_segments(entry: SurfaceLegendEntry, text_transform: str, *, include_scope: bool = False
                          ) -> tuple[TextSegment, ...] | None:
    """Keep encoded values literal while retaining the Theme transform on legend wording."""
    if entry.encoding_scale_id is None or text_transform == "none":
        return None
    segments: list[TextSegment] = []
    if entry.style_scope is not None:
        title = entry.style_scope.title
        visible_value = entry.style_display_value if entry.style_display_value is not None else entry.style_value or ""
        if title:
            segments.extend((TextSegment(title, text_transform), TextSegment(": ", text_transform)))
        segments.append(TextSegment(visible_value, text_transform if entry.encoding_value_is_wording else "none"))
    else:
        segments.append(TextSegment(entry.label, text_transform if entry.encoding_value_is_wording else "none"))
    if include_scope and entry.style_scope is not None and entry.style_scope.show_scope:
        segments.extend((TextSegment(" when ", text_transform),
                         TextSegment(entry.style_scope.selector, "none")))
    return tuple(segment for segment in segments if segment.content)


def _segment_width(segments: tuple[TextSegment, ...], *, font_size: float, font_metrics: Any,
                   treatment: Any) -> float:
    return measure_text_segments(segments, font_size=font_size, font_metrics=font_metrics,
                                letter_spacing=float(treatment.letter_spacing),
                                numeric_spacing=treatment.numeric_spacing,
                                horizontal_scale=float(treatment.horizontal_scale))[1]


def _entry_label_width(entry: SurfaceLegendEntry, *, font_size: float, font_metrics: Any,
                       treatment: Any) -> float:
    if entry.label_variants:
        return max(_entry_label_width(replace(entry, label=label, label_variants=()),
                                     font_size=font_size, font_metrics=font_metrics, treatment=treatment)
                   for label in (entry.label, *entry.label_variants))
    segments = _legend_text_segments(entry, treatment.transform)
    if segments is not None:
        return _segment_width(segments, font_size=font_size, font_metrics=font_metrics, treatment=treatment)
    return measure_text_width(entry.label, font_size=font_size, font_metrics=font_metrics,
                              letter_spacing=float(treatment.letter_spacing),
                              text_transform=treatment.transform, numeric_spacing=treatment.numeric_spacing)


def _minimum_label_unit_width(entry: SurfaceLegendEntry, *, font_size: float, font_metrics: Any,
                              treatment: Any) -> Decimal:
    """Measure the widest indivisible word/CJK unit using the shared text breaker."""
    # A scope qualifier is optional and must not raise the entry's mandatory
    # shrink floor; it is admitted later only when its full text fits.
    segments = _legend_text_segments(entry, treatment.transform)
    source = "".join(segment.content for segment in segments) if segments is not None else entry.label
    units = _wrap_units(source)
    if not units:
        return Decimal(0)
    if segments is not None:
        cursor = 0
        width_values = []
        for unit in units:
            start = source.find(unit, cursor)
            if start < 0:
                start = source.find(unit)
            cursor = start + len(unit)
            width_values.append(measure_text_segments(_slice_segments(segments, source, start,
                           start + len(unit)), font_size=font_size,
                           font_metrics=font_metrics, letter_spacing=float(treatment.letter_spacing),
                           numeric_spacing=treatment.numeric_spacing,
                           horizontal_scale=float(treatment.horizontal_scale))[1])
        widths = width_values
    else:
        widths = (measure_text_width(unit, font_size=font_size, font_metrics=font_metrics,
                                     letter_spacing=float(treatment.letter_spacing),
                                     text_transform=treatment.transform,
                                     numeric_spacing=treatment.numeric_spacing) for unit in units)
    return max(Decimal(str(width)) for width in widths)


def _slice_segments(segments: tuple[TextSegment, ...], source: str, start: int, end: int
                    ) -> tuple[TextSegment, ...]:
    result: list[TextSegment] = []
    offset = 0
    for segment in segments:
        segment_end = offset + len(segment.content)
        left, right = max(start, offset), min(end, segment_end)
        if left < right:
            result.append(TextSegment(segment.content[left - offset:right - offset], segment.text_transform))
        offset = segment_end
    return tuple(result)


def _split_segments_by_lines(segments: tuple[TextSegment, ...], source: str,
                             lines: tuple[str, ...]) -> tuple[tuple[TextSegment, ...], ...]:
    result = []
    cursor = 0
    for line in lines:
        while cursor < len(source) and source[cursor].isspace():
            cursor += 1
        start = source.find(line, cursor)
        if start < 0:
            return ()
        end = start + len(line)
        result.append(_slice_segments(segments, source, start, end))
        cursor = end
    return tuple(result)


def _wrap_segmented_text(source: str, segments: tuple[TextSegment, ...], *, available: Decimal,
                         font_size: float, metrics: Any, treatment: Any) -> tuple[str, ...]:
    """Use word/CJK boundaries while measuring candidates with their actual segment paint."""
    lines: list[str] = []
    cursor = 0
    line_start: int | None = None
    line_end = 0
    for unit in _wrap_units(source):
        start = source.find(unit, cursor)
        if start < 0:
            start = source.find(unit)
        end = start + len(unit)
        cursor = end
        if line_start is None:
            line_start, line_end = start, end
            continue
        candidate_segments = _slice_segments(segments, source, line_start, end)
        candidate_width = Decimal(str(_segment_width(candidate_segments, font_size=font_size,
                                                     font_metrics=metrics, treatment=treatment)))
        if candidate_width > available:
            lines.append(source[line_start:line_end].rstrip())
            line_start, line_end = start, end
        else:
            line_end = end
    if line_start is not None:
        lines.append(source[line_start:line_end].rstrip())
    return tuple(lines or [source])


def _fit_legend_label(entry: SurfaceLegendEntry, *, available: Decimal, font_size: float,
                      metrics: Any, treatment: Any) -> tuple[str, tuple[str, ...], tuple[str, ...],
                                                              tuple[tuple[TextSegment, ...], ...],
                                                              tuple[tuple[TextRunPlacement, ...], ...], Decimal]:
    source_text = entry.label
    segments = _legend_text_segments(entry, treatment.transform)
    if entry.style_scope is not None and entry.style_scope.show_scope:
        qualified = entry.label + " when " + entry.style_scope.selector
        qualified_segments = _legend_text_segments(entry, treatment.transform, include_scope=True)
        try:
            # Keep the established optional qualifier admission rule. The probe
            # also lets unavailable qualifier metrics fall back to the primary
            # label without rejecting the encoded entry.
            qualified_width = measure_text_width(
                qualified, font_size=font_size, font_metrics=metrics,
                letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                numeric_spacing=treatment.numeric_spacing)
            if qualified_segments is not None:
                qualified_width = _segment_width(qualified_segments, font_size=font_size,
                                                 font_metrics=metrics, treatment=treatment)
        except FontMetricsError:
            pass
        else:
            if Decimal(str(qualified_width)) <= available:
                source_text, segments = qualified, qualified_segments
    if segments is None:
        # Preserve authored spaces inside a completed line, including CJK
        # qualifiers. The same source-span breaker measures styled fragments.
        lines = _wrap_segmented_text(
            source_text, (TextSegment(source_text, treatment.transform),),
            available=available, font_size=font_size, metrics=metrics, treatment=treatment)
        width = max(Decimal(str(measure_text_width(
            line, font_size=font_size, font_metrics=metrics,
            letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
            numeric_spacing=treatment.numeric_spacing))) for line in lines)
        return source_text, lines, lines, (), (), width
    source = "".join(segment.content for segment in segments)
    lines = _wrap_segmented_text(source, segments, available=available, font_size=font_size,
                                 metrics=metrics, treatment=treatment)
    segment_lines = _split_segments_by_lines(segments, source, lines)
    if len(segment_lines) != len(lines):
        # A segment boundary that cannot be reconciled with shared line breaking
        # is kept whole; its measured overflow is reported rather than losing paint.
        lines = (source,)
        segment_lines = (segments,)
    painted, line_runs, widths = [], [], []
    for line_segments in segment_lines:
        text, width, runs = measure_text_segments(
            line_segments, font_size=font_size, font_metrics=metrics,
            letter_spacing=float(treatment.letter_spacing), numeric_spacing=treatment.numeric_spacing,
            horizontal_scale=float(treatment.horizontal_scale))
        painted.append(text)
        line_runs.append(runs)
        widths.append(Decimal(str(width)))
    return source_text, lines, tuple(painted), tuple(segment_lines), tuple(line_runs), max(widths, default=Decimal(0))


def complete_legend_layout(entries: tuple[SurfaceLegendEntry, ...], *, available_inline: Decimal,
                           item_min_inline: Decimal | None, gap: Decimal, tokens: Any,
                           mark_block_size: float, font_metrics: Any, direction: str = "inline",
                           columns: int | None = None, column_distribution: str = "start",
                           caption_inline: Decimal = Decimal(0)) -> MeasuredLegend:
    """Close entry lines and rows once for inline, grid, or stacked legends."""
    treatment = tokens.text_treatment("legend")
    font_size = float(treatment.font_size)
    metrics = metric_for_role(tokens, "legend", font_metrics)
    text_line_block = treatment.font_size * treatment.line_height
    reservations: list[Decimal] = []
    swatch_blocks: list[Decimal] = []
    natural_widths: list[Decimal] = []
    minimum_widths: list[Decimal] = []
    minimum_labels: list[Decimal] = []
    for entry in entries:
        swatch_width, swatch_height, _bucket = entry_swatch_extent(entry, tokens, mark_block_size, font_size)
        reservation = _label_reservation(swatch_width, entry_label_gap(entry, gap, tokens, font_size))
        minimum_label = _minimum_label_unit_width(entry, font_size=font_size, font_metrics=metrics,
                                                  treatment=treatment)
        natural_label = Decimal(str(_entry_label_width(entry, font_size=font_size,
                                                       font_metrics=metrics, treatment=treatment)))
        reservations.append(reservation)
        swatch_blocks.append(Decimal(str(swatch_height)))
        natural_widths.append(reservation + natural_label)
        minimum_labels.append(minimum_label)
        minimum_widths.append(reservation + minimum_label)

    # Column tracks preserve natural-fit geometry. When constrained, the shared
    # track allocator distributes between each column's mandatory minimum and
    # natural preference, exactly like other measured Layout tracks.
    column_widths: tuple[Decimal, ...] = ()
    if columns is not None:
        count = min(columns, len(entries))
        preferred = [max((natural_widths[index] for index in range(column, len(entries), columns)),
                         default=Decimal(0)) for column in range(count)]
        minima = [max((minimum_widths[index] for index in range(column, len(entries), columns)),
                      default=Decimal(0)) for column in range(count)]
        gap_total = gap * max(0, count - 1)
        budget = max(Decimal(0), available_inline - gap_total)
        natural_total = sum(preferred, Decimal(0))
        natural_fit = natural_total <= budget
        equal_share = budget / count if count else Decimal(0)
        if (column_distribution == "spread"
                and all(width <= equal_share for width in (minima if not natural_fit else preferred))):
            column_widths = tuple(equal_share for _ in range(count))
        elif natural_total <= budget:
            column_widths = tuple(preferred)
        else:
            column_widths = tuple(resolve_flexible_tracks(
                [(minimums, width, Decimal(1)) for minimums, width in zip(minima, preferred, strict=True)], budget))

    layouts: list[MeasuredLegendEntry] = []
    if columns is not None:
        count = len(column_widths)
        starts = []
        cursor = Decimal(0)
        for width in column_widths:
            starts.append(cursor)
            cursor += width + gap
        for index, entry in enumerate(entries):
            row, column = divmod(index, columns)
            start = starts[column]
            column_width = column_widths[column]
            label_available = max(Decimal(0), column_width - reservations[index])
            effective = max(label_available, minimum_labels[index])
            source_text, lines, painted_lines, segment_lines, segment_runs, line_width = _fit_legend_label(
                entry, available=effective, font_size=font_size, metrics=metrics, treatment=treatment)
            label_block = text_line_block * len(lines)
            overflow = "visible-overflow" if line_width > label_available else "fit"
            layouts.append(MeasuredLegendEntry(lines, start, Decimal(row), line_width, label_block,
                                               label_available, max(swatch_blocks[index], label_block), overflow,
                                               source_text, painted_lines, segment_lines, segment_runs))
        row_blocks: dict[Decimal, Decimal] = {}
        for row in range(-(-len(entries) // columns)):
            row_blocks[Decimal(row)] = max((item.row_block for item in layouts
                                            if item.block_offset == Decimal(row)), default=Decimal(0))
        row_top: dict[Decimal, Decimal] = {}
        top = Decimal(0)
        for row in range(-(-len(entries) // columns)):
            row_top[Decimal(row)] = top
            top += row_blocks[Decimal(row)] + (gap if row + 1 < -(-len(entries) // columns) else Decimal(0))
        layouts = [replace(item, block_offset=row_top[item.block_offset], row_block=row_blocks[item.block_offset])
                   for item in layouts]
        block_size = top
        return MeasuredLegend(tuple(layouts), block_size, entries, available_inline,
                              available_inline + caption_inline)

    used = top = current_row_block = Decimal(0)
    for index, entry in enumerate(entries):
        reservation = reservations[index]
        minimum_label = minimum_labels[index]
        minimum_entry = minimum_widths[index]
        if direction == "inline" and item_min_inline is not None and used > 0:
            remaining = available_inline - used
            if remaining < max(item_min_inline, minimum_entry):
                top += current_row_block + gap
                used = current_row_block = Decimal(0)
        cell_width = max(Decimal(0), available_inline - used)
        label_available = max(Decimal(0), min(available_inline - used, cell_width) - reservation)
        effective_available = max(label_available, minimum_label)
        source_text, lines, painted_lines, segment_lines, segment_runs, line_width = _fit_legend_label(
            entry, available=effective_available, font_size=font_size, metrics=metrics, treatment=treatment)
        label_block = text_line_block * len(lines)
        row_block = max(swatch_blocks[index], label_block)
        overflow = "visible-overflow" if line_width > label_available else "fit"
        layouts.append(MeasuredLegendEntry(lines, used, top, line_width, label_block,
                                           label_available, row_block, overflow, source_text,
                                           painted_lines, segment_lines, segment_runs))
        current_row_block = max(current_row_block, row_block)
        used += reservation + line_width + gap
        if direction == "stack":
            top += row_block + (gap if index + 1 < len(entries) else Decimal(0))
            current_row_block = Decimal(0)
            used = Decimal(0)
    row_blocks: dict[Decimal, Decimal] = {}
    for item in layouts:
        row_blocks[item.block_offset] = max(row_blocks.get(item.block_offset, Decimal(0)), item.row_block)
    if direction == "stack":
        # Each entry is its own row; offsets above already include inter-entry gaps.
        layouts = [replace(item, row_block=row_blocks[item.block_offset]) for item in layouts]
        block_size = max((item.block_offset + item.row_block for item in layouts), default=Decimal(0))
    else:
        layouts = [replace(item, row_block=row_blocks[item.block_offset]) for item in layouts]
        block_size = max((item.block_offset + item.row_block for item in layouts), default=Decimal(0))
    return MeasuredLegend(tuple(layouts), block_size, entries, available_inline,
                          available_inline + caption_inline)


def _ellipsize_segments(segments: tuple[TextSegment, ...], *, available_inline: float, font_size: float,
                        font_metrics: Any, treatment: Any) -> tuple[TextSegment, ...]:
    """Ellipsize a source prefix while retaining each surviving segment's transform."""
    content = "".join(segment.content for segment in segments)
    for keep in range(len(content), -1, -1):
        remaining = keep
        prefix: list[TextSegment] = []
        for segment in segments:
            piece = segment.content[:remaining]
            remaining -= len(piece)
            if piece:
                prefix.append(TextSegment(piece, segment.text_transform))
            if remaining <= 0:
                break
        candidate = (*prefix, TextSegment("…", "none"))
        if _segment_width(candidate, font_size=font_size, font_metrics=font_metrics, treatment=treatment) <= available_inline:
            return candidate
    return ()


@dataclass(frozen=True)
class LegendArrangement:
    """The legend slot's own declarations that decide how its entries are laid out."""

    direction: str = "block"
    gap: Decimal | None = None
    item_min_inline_size: Decimal | None = None
    overflow: str = "visible-overflow"
    columns: int | None = None
    column_distribution: str = "start"


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
        int(node["columns"]) if "columns" in node else None,
        str(node.get("columnDistribution", "start")))


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
    if not entries:
        return SourceInput(("legend",), typography_role="legend")
    # Size each potential key once using its widest possible final coverage label.
    metrics = metric_for_role(tokens, "legend", font_metrics)
    entries = tuple(replace(entry, label=max((entry.label, *entry.label_variants),
        key=lambda label: _entry_label_width(replace(entry, label=label, label_variants=()),
            font_size=legend_size, font_metrics=metrics, treatment=treatment)), label_variants=())
        if entry.label_variants else entry for entry in entries)
    gap = _legend_item_gap_decimal(arrangement.gap, legend_size)
    label_gaps = tuple(entry_label_gap(entry, arrangement.gap, tokens, legend_size) for entry in entries)
    entry_extents = tuple(entry_swatch_extent(entry, tokens, mark_block_size, legend_size)
                          for entry in entries)
    extents = tuple(width for width, _height, _bucket in entry_extents)
    runs = tuple(SourceTextRun(entry.label, "legend", entry.role,
                               _label_reservation(extent, label_gap),
                               segments=_legend_text_segments(entry, treatment.transform) or ())
                 for entry, extent, label_gap in zip(entries, extents, label_gaps, strict=True))
    grid = arrangement.columns is not None
    line = arrangement.direction == "inline" and not grid
    min_inline: Decimal | None = None
    if arrangement.overflow == "ellipsize-with-source":
        if line and arrangement.item_min_inline_size is not None:
            # Preserve enough room for the swatch, gap and one indivisible text unit.
            metrics = metric_for_role(tokens, "legend", font_metrics)
            min_inline = max(_label_reservation(extent, label_gap)
                             + _minimum_label_unit_width(entry, font_size=legend_size, font_metrics=metrics,
                                                         treatment=treatment)
                             for entry, extent, label_gap in zip(entries, extents, label_gaps, strict=True))
        elif grid:
            count = min(int(arrangement.columns or 1), len(entries))
            column_minima = tuple(max(
                (_label_reservation(extents[index], label_gaps[index])
                 + _minimum_label_unit_width(entries[index], font_size=legend_size,
                                             font_metrics=metrics, treatment=treatment)
                 for index in range(column, len(entries), int(arrangement.columns or 1))),
                default=Decimal(0)) for column in range(count))
            min_inline = sum(column_minima, Decimal(0)) + gap * max(0, count - 1)
        elif not line and not grid:
            metrics = metric_for_role(tokens, "legend", font_metrics)
            min_inline = max(_label_reservation(extent, label_gap)
                             + _minimum_label_unit_width(entry, font_size=legend_size, font_metrics=metrics,
                                                         treatment=treatment)
                             for entry, extent, label_gap in zip(entries, extents, label_gaps, strict=True))
    if grid:
        row_block = max([treatment.font_size * treatment.line_height]
                        + [Decimal(str(entry_swatch_extent(entry, tokens, mark_block_size, legend_size)[1]))
                           for entry in entries])
        return SourceInput(runs=runs, typography_role="legend", run_flow="grid", run_gap=Decimal(str(gap)),
                           columns=arrangement.columns, row_block=row_block, min_inline=min_inline)
    row_block = Decimal(0)
    if line:
        # The height of one drawn row, as `place_legend` draws it: the label line box or the tallest swatch (#1649).
        # The label line box is the exact product the measurement's one-row minimum uses, not its float product: a
        # float 12 * 1.4 is 16.799999999999997, below the minimum 16.8, and the slot would then be allocated less than
        # its own minimum and warn W_LAYOUT_VISIBLE_OVERFLOW though the row fits (#1649).
        row_block = max([treatment.font_size * treatment.line_height]
                        + [Decimal(str(entry_swatch_extent(entry, tokens, mark_block_size, legend_size)[1]))
                           for entry in entries])
    return SourceInput(
        runs=runs,
        typography_role="legend",
        run_flow="line" if line else "stack",
        run_gap=gap,
        min_inline=min_inline,
        row_block=row_block,
        run_block_minima=(tuple(Decimal(str(height)) for _width, height, _bucket in entry_extents)
                          if not line else None),
    )


def _legend_line_offsets(entry_inline_sizes: Sequence[Decimal], *, gap: Decimal, row_block: Decimal,
                         item_min_inline: Decimal | None, available_inline: Decimal
                         ) -> tuple[tuple[Decimal, Decimal], ...]:
    """Complete the same relative row positions for measurement and placement."""
    used, top = Decimal(0), Decimal(0)
    positions: list[tuple[Decimal, Decimal]] = []
    for size in entry_inline_sizes:
        if item_min_inline is not None and used > 0 and available_inline - used < item_min_inline:
            used = Decimal(0)
            top += row_block + gap
        positions.append((used, top))
        used += size + gap
    return tuple(positions)


def wrapped_legend_line_block(entry_inline_sizes: Sequence[Decimal], *, gap: Decimal, row_block: Decimal,
                              item_min_inline: Decimal | None, available_inline: Decimal) -> Decimal:
    """Return the block a `line` legend draws at a known inline size: the rows it wraps to (#1649).

    This is the wrapping rule of `place_legend`'s `inline` direction: an entry starts a new row only when the
    slot declares `itemMinInlineSize` and less than that is left on the current row. Without it the legend is
    one row. Each entry advances by its swatch, label gap, label and the entry gap (a `line` measurement's run).
    """
    positions = _legend_line_offsets(entry_inline_sizes, gap=gap, row_block=row_block,
                                     item_min_inline=item_min_inline, available_inline=available_inline)
    return (positions[-1][1] if positions else Decimal(0)) + row_block


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
    completed_layout = (request.measured_sources.legend_layout
                        if request.measured_sources is not None else None)
    entries = request.surface_content.legend_entries
    legend_treatment = request.theme_tokens.text_treatment("legend")
    legend_size = float(legend_treatment.font_size)
    text_line_block = legend_treatment.font_size * legend_treatment.line_height
    mark_block_size = float(metric_values["timeline.mark.blockSize"])
    gap = _legend_item_gap_decimal(legend.gap, legend_size)
    direction = legend.direction
    item_min_inline = legend.item_min_inline_size
    if completed_layout is not None and (
            completed_layout.entry_witnesses != entries
            or abs(completed_layout.slot_inline_size - legend.bounds.inline_size) > GEOMETRY_TOLERANCE):
        caption_inline = max(Decimal(0), completed_layout.slot_inline_size - completed_layout.available_inline)
        completed_layout = complete_legend_layout(
            entries, available_inline=max(Decimal(0), legend.bounds.inline_size - caption_inline),
            item_min_inline=item_min_inline, gap=gap, tokens=request.theme_tokens,
            mark_block_size=mark_block_size, font_metrics=metric_for("legend"),
            direction="inline" if direction == "inline" else "stack", columns=legend.columns,
            column_distribution=legend.column_distribution, caption_inline=caption_inline)

    def swatch_geometry(entry: SurfaceLegendEntry) -> tuple[float, float, str]:
        return entry_swatch_extent(entry, request.theme_tokens, mark_block_size, legend_size)

    def emit_swatch(entry: SurfaceLegendEntry, x: float, y: float, width: float, height: float, bucket: str) -> None:
        if not entry.swatch_visible:
            return
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
                if key.point_state is not None:
                    geometry_identity = key.glyph.geometry_identity
                    parts = place_canonical_point_geometry(geometry_identity, (x, y, width, height))
                else:
                    parts, geometry_identity = _completed_point_key_parts(
                        point_symbol_token(request.theme_tokens, key.glyph.selected_role, "actual"),
                        (x, y, width, height), key.paint_role, request.theme_tokens)
                assert len(parts) == len(key.glyph.paints), "composite key geometry and ink must stay aligned"
                center = (x + width / 2, y + height / 2)
                marks.append(MarkPlacement(swatch_id, entry.source_identity, bounds, center, center,
                    mark_shape="point", slot_id=legend.slot_id, semantic_id=key.point_state or "actual",
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

    def emit_label(entry: SurfaceLegendEntry, x: Decimal, baseline: Decimal, available: Decimal,
                   completed: MeasuredLegendEntry | None = None) -> Decimal:
        role = entry.role
        label = completed.source_text if completed is not None else entry.label
        text_segments = _legend_text_segments(entry, legend_treatment.transform)
        natural_width = (_segment_width(text_segments, font_size=legend_size, font_metrics=metric_for("legend"),
                                        treatment=legend_treatment) if text_segments is not None else
                         measure_text_width(label, font_size=legend_size, font_metrics=metric_for("legend"),
                                            letter_spacing=float(legend_treatment.letter_spacing),
                                            text_transform=legend_treatment.transform,
                                            numeric_spacing=legend_treatment.numeric_spacing))
        content = label
        if entry.style_scope is not None and entry.style_scope.show_scope:
            qualified = label + " when " + entry.style_scope.selector
            qualified_segments = _legend_text_segments(entry, legend_treatment.transform, include_scope=True)
            try:
                qualified_width = (_segment_width(qualified_segments, font_size=legend_size,
                                                  font_metrics=metric_for("legend"), treatment=legend_treatment)
                                   if qualified_segments is not None else measure_text_width(
                                       qualified, font_size=legend_size, font_metrics=metric_for("legend"),
                                       letter_spacing=float(legend_treatment.letter_spacing),
                                       text_transform=legend_treatment.transform,
                                       numeric_spacing=legend_treatment.numeric_spacing))
            except FontMetricsError:
                pass  # Optional scope alone must not reject the primary key.
            else:
                if Decimal(str(qualified_width)) <= available:
                    content = qualified
                    natural_width = qualified_width
                    text_segments = qualified_segments
        disposition = completed.overflow if completed is not None else "fit"
        ellipsized = False
        if completed is not None:
            content = "\n".join(completed.lines)
            available = completed.label_available_inline
        elif Decimal(str(natural_width)) > available and legend.overflow == "ellipsize-with-source":
            if entry.role == "forecast":
                raise LayoutError("E_PRESENTATION_LABEL_UNPLACEABLE", entry.text_placement_id)
            if text_segments is not None:
                text_segments = _ellipsize_segments(text_segments, available_inline=float(available),
                                                    font_size=legend_size, font_metrics=metric_for("legend"),
                                                    treatment=legend_treatment)
                content = "".join(segment.content for segment in text_segments)
            else:
                content = ellipsize_text(label, available_inline=float(available), font_size=legend_size,
                                         font_metrics=metric_for("legend"),
                                         letter_spacing=float(legend_treatment.letter_spacing),
                                         text_transform=legend_treatment.transform,
                                         numeric_spacing=legend_treatment.numeric_spacing)
            disposition = "ellipsized"
            ellipsized = True
        elif Decimal(str(natural_width)) > available and legend.overflow == "visible-overflow":
            disposition = "visible-overflow"
        placed = place_text(placement_id=entry.text_placement_id, source_ref=entry.source_identity, content=content,
                            inline=float(x), baseline_block=float(baseline), typography_role="legend",
                            theme_tokens=request.theme_tokens, font_metrics=request.font_metrics,
                            overflow=disposition, collision_region="legend",
                            collision_domain=CollisionDomain("legend", "content"), source_content=label,
                            available_inline_start=float(x), available_inline_size=float(available),
                            semantic_id="legendLabel", slot_id=legend.slot_id,
                            lines=completed.lines if completed is not None else None,
                            segments=text_segments if completed is None else None)
        if completed is not None and completed.segment_runs:
            placed = replace(placed, content="\n".join(completed.painted_lines),
                             lines=completed.painted_lines, text_transform="none",
                             runs=completed.segment_runs,
                             bounds=replace(placed.bounds,
                                            inline_size=Decimal(str(float(completed.label_inline_size)))))
        text.append(placed)
        label_targets.append((entry.role, placed.placement_id))
        if ellipsized:
            # An ellipsis is never silent: the Scene names the text, its natural size and the room it had (#497).
            side_content_warnings.append(FitWarning(
                "W_LAYOUT_TEXT_ELLIPSIZED", placed.placement_id, role, "legend-text", "ellipsize-with-source",
                natural_width, float(placed.bounds.block_size), float(available), float(legend.bounds.block_size),
            ))
        if disposition == "visible-overflow":
            side_content_warnings.append(FitWarning(
                "W_LAYOUT_VISIBLE_OVERFLOW", placed.placement_id, role, "legend-text", "visible-overflow",
                natural_width, float(placed.bounds.block_size), float(available), float(legend.bounds.block_size),
            ))
        return placed.bounds.block + placed.bounds.block_size

    geometries = tuple(swatch_geometry(entry) for entry in entries)
    reservations = tuple(_label_reservation(width, entry_label_gap(
        entry, legend.gap, request.theme_tokens, legend_size))
        for entry, (width, _height, _bucket) in zip(entries, geometries, strict=True))
    label_widths = tuple(Decimal(str(_entry_label_width(
        entry, font_size=legend_size, font_metrics=metric_for("legend"), treatment=legend_treatment)))
        for entry in entries)
    entry_widths = tuple(reservation + label for reservation, label in zip(reservations, label_widths, strict=True))
    row_block = max([text_line_block] + [Decimal(str(height)) for _width, height, _bucket in geometries])
    final_legend_end = legend.bounds.block
    if legend.columns:
        # A declared grid (#1290): entry k sits in column k mod columns of row k div columns; each column is as wide as
        # its widest entry (swatch, gap and label), `gap` apart, and every row is as tall as the tallest key.
        count = len(entries)
        column_widths = [max((entry_widths[index] for index in range(column, count, legend.columns)), default=Decimal(0))
                         for column in range(min(legend.columns, count))]
        if legend.column_distribution == "spread" and len(column_widths) > 1:
            # `spread` (#1392): equal columns across the slot, each at least the widest entry of any column; when they do not
            # fit the slot the columns stay packed as under `start`.
            share = (legend.bounds.inline_size - gap * (len(column_widths) - 1)) / len(column_widths)
            column_widths = [share] * len(column_widths) if max(column_widths) <= share else column_widths
        starts = [Decimal(0)]
        for width in column_widths[:-1]:
            starts.append(starts[-1] + width + gap)
        for index, entry in enumerate(entries):
            row, column = divmod(index, legend.columns)
            completed = completed_layout.entries[index] if completed_layout is not None else None
            x = legend.bounds.inline + (completed.inline_offset if completed is not None else starts[column])
            y = legend.bounds.block + (completed.block_offset if completed is not None
                                        else row * (row_block + gap))
            entry_row_block = completed.row_block if completed is not None else row_block
            width, height, bucket = geometries[index]
            remaining = max(Decimal(0), legend.bounds.inline_size - (x - legend.bounds.inline) - reservations[index])
            label_block = completed.label_block_size if completed is not None else text_line_block
            emit_swatch(entry, float(x), float(y + (entry_row_block - Decimal(str(height))) / 2), width, height, bucket)
            label_end = emit_label(entry, x + reservations[index],
                                   y + (entry_row_block - label_block) / 2 + legend_treatment.font_size,
                                   min(remaining, max(Decimal(0), column_widths[column] - reservations[index]))
                                   if completed is None and (entry.style_scope is not None or not entry.swatch_visible)
                                   else remaining, completed)
            final_legend_end = max(final_legend_end, label_end, y + entry_row_block)
    elif direction == "inline":
        # Every swatch and label of the legend is centred on one row centreline (#991), the way the block
        # direction centres each entry: the row is as tall as the tallest swatch or the label line box.
        positions = _legend_line_offsets(entry_widths, gap=gap, row_block=row_block,
                                         item_min_inline=item_min_inline, available_inline=legend.bounds.inline_size)
        if completed_layout is not None:
            positions = tuple((item.inline_offset, item.block_offset) for item in completed_layout.entries)
        for index, (entry, (inline_offset, block_offset)) in enumerate(zip(entries, positions, strict=True)):
            completed = completed_layout.entries[index] if completed_layout is not None else None
            entry_row_block = completed.row_block if completed is not None else row_block
            x, y = legend.bounds.inline + inline_offset, legend.bounds.block + block_offset
            width, height, bucket = geometries[index]
            remaining = max(Decimal(0), legend.bounds.inline_size - inline_offset - reservations[index])
            label_block = completed.label_block_size if completed is not None else text_line_block
            emit_swatch(entry, float(x), float(y + (entry_row_block - Decimal(str(height))) / 2), width, height, bucket)
            label_end = emit_label(entry, x + reservations[index],
                                   y + (entry_row_block - label_block) / 2 + legend_treatment.font_size,
                                   min(remaining, label_widths[index]) if entry.style_scope is not None else remaining,
                                   completed)
            final_legend_end = max(final_legend_end, label_end, y + entry_row_block)
    else:
        cursor = legend.bounds.block
        for index, entry in enumerate(entries):
            completed = completed_layout.entries[index] if completed_layout is not None else None
            width, height, bucket = geometries[index]
            row_height = (completed.row_block if completed is not None
                          else max(Decimal(str(height)), text_line_block))
            if completed is not None:
                cursor = legend.bounds.block + completed.block_offset
            swatch_top = cursor + (row_height - Decimal(str(height))) / 2
            label_block = completed.label_block_size if completed is not None else text_line_block
            baseline = cursor + (row_height - label_block) / 2 + legend_treatment.font_size
            text_inline = legend.bounds.inline + reservations[index]
            text_available = max(Decimal(0), legend.bounds.inline_size - reservations[index])
            emit_swatch(entry, float(legend.bounds.inline), float(swatch_top), width, height, bucket)
            label_end = emit_label(entry, text_inline, baseline, text_available, completed)
            row_end = cursor + row_height
            final_legend_end = max(final_legend_end, label_end, row_end)
            cursor = row_end + (gap if index + 1 < len(entries) else Decimal(0))
    final_size = max(legend.bounds.block_size, final_legend_end - legend.bounds.block)
    if (direction == "inline" and not legend.columns and legend.bounds.block_size >= text_line_block
            and final_legend_end - legend.bounds.block > legend.bounds.block_size + GEOMETRY_TOLERANCE):
        # The wrapped rows are known only now: a legend that needs more rows than its slot has still warns, with the
        # block its rows really need (a slot shorter than one row is reported by the track check) (#1273).
        side_content_warnings.append(FitWarning(
            "W_LAYOUT_VISIBLE_OVERFLOW", legend.slot_id, "legend", "layout-track", "visible-overflow",
            float(legend.bounds.inline_size), float(final_legend_end - legend.bounds.block),
            float(legend.bounds.inline_size), float(legend.bounds.block_size)))
    drawn_inline_ends = [item.bounds.inline + item.bounds.inline_size for item in (*marks, *shapes, *text)]
    drawn_inline_ends.extend(Decimal(str(point[0])) for relation in relations for point in relation.points)
    final_inline_size = max(
        legend.bounds.inline_size,
        max(drawn_inline_ends, default=legend.bounds.inline) - legend.bounds.inline)
    if final_inline_size > legend.bounds.inline_size + GEOMETRY_TOLERANCE:
        side_content_warnings.append(FitWarning(
            "W_LAYOUT_VISIBLE_OVERFLOW", legend.slot_id, "legend", "layout-track", "visible-overflow",
            float(final_inline_size), float(final_size), float(legend.bounds.inline_size),
            float(legend.bounds.block_size)))
    replacement = replace(legend, bounds=Rect(legend.bounds.inline, legend.bounds.block,
                                               final_inline_size, final_size))
    coverage = {}
    for entry, (_, _, bucket) in zip(entries, geometries, strict=True):
        witness = (entry.realized_key.legend_encoding_coverage
                   if entry.realized_key is not None else entry.legend_encoding_coverage)
        if witness is not None and witness.kind == "encoding":
            witness = replace(witness, paint_channel="stroke" if bucket == "rule-pair" else "fill")
        coverage[entry.source_identity] = witness
    marks = [replace(mark, legend_encoding_coverage=coverage.get(mark.source_ref)) for mark in marks]
    shapes = [replace(shape, legend_encoding_coverage=coverage.get(shape.source_ref)) for shape in shapes]
    return SurfaceLegendBatch(replacement, tuple(marks), tuple(shapes), tuple(relations), tuple(text),
                              tuple(side_content_warnings), legend, tuple(label_targets),
                              entries=entries, measured_layout=completed_layout)
