"""Theme-selected point geometry completed in Layout coordinates."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from math import isfinite
from typing import Any

from chrona.presentation.icons.normalizer import IconNormalizationError, parse_path_commands
from chrona.presentation.layout.surface_quality import PathCommand, ScalePlacement
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.presentation import MarkBandFrame
from chrona.presentation.layout.path_geometry import open_span_path, rounded_diamond_path
from chrona.presentation.layout.rounded_outline import resolve_corner_radius, rounded_rect_commands
from chrona.presentation.layout.filled_contour import (
    ContourUnionError, WindowContourError, clip_span_contour, union_filled_contours,
    intersect_visible_host_contour,
)
from chrona.presentation.layout.surface_quality import MarkPlacement, PaintClip
from chrona.presentation.model.point_paint import resolve_point_paint_role
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject
from chrona.presentation.layout.semantic_mark_facets import (
    ItemMarkFacetSelection, MarkFacetAbsence, select_item_mark_facets,
)
from chrona.presentation.layout.mark_facet_visibility import (
    FacetDisposition, MarkFacetVisibility,
)


def _brief(value: object) -> str:
    if isinstance(value, str):
        clipped = value[:64]
        return repr(clipped + ("…" if len(value) > len(clipped) else ""))
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    if isinstance(value, (tuple, list)) and len(value) <= 4 and all(
            item is None or isinstance(item, (bool, int, float, str)) for item in value):
        return repr(type(value)(value))
    return f"<{type(value).__name__}>"


def _theme_error(detail: str) -> ValueError:
    return ValueError(f"E_THEME_TOKEN_TYPE: {detail}")


def _primitive_error(detail: str) -> ValueError:
    return ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: {detail}")


@dataclass(frozen=True)
class SymbolPartPlacement:
    commands: tuple[PathCommand, ...]
    paint_mode: str | None = None
    paint_color: str | None = None
    stroke_width: float | None = None
    line_cap: str | None = None
    line_join: str | None = None


def complete_point_outline(parts: tuple[SymbolPartPlacement, ...], *,
                           paint_role: str, theme_tokens: Any) -> tuple[SymbolPartPlacement, ...]:
    """Append a completed filled-region edge without resolving its ink in Layout."""
    fills = tuple(part.commands for part in parts if part.paint_mode == "fill")
    if not fills or not (theme_tokens.has_binding(paint_role, "stroke")
                         and theme_tokens.has_binding(paint_role, "strokeWidth")):
        return parts
    pattern = theme_tokens.optional_pattern(paint_role)
    if isinstance(pattern, Mapping) and pattern.get("kind") == "outline":
        return parts
    width = float(theme_tokens.optional_number(paint_role, "strokeWidth"))
    pointer_role = paint_role.replace("~", "~0").replace("/", "~1")
    source = f"/body/roles/{pointer_role}/strokeWidth"
    if not isfinite(width):
        raise LayoutError("E_LAYOUT_POINT_OUTLINE_INVALID", source,
                          detail="stage=input; reason=nonfinite; operand=strokeWidth")
    if width <= 0:
        return parts
    try:
        contour = union_filled_contours(fills)
    except ContourUnionError as error:
        raise LayoutError("E_LAYOUT_POINT_OUTLINE_INVALID", source,
                          detail=f"stage={error.stage}; reason={error.reason}; fillParts={len(fills)}") from error
    return (*parts, SymbolPartPlacement(contour, paint_mode="stroke", stroke_width=width))


@dataclass(frozen=True)
class MarkItemComposition:
    """Complete item mark closure, including observable omissions and warnings."""

    marks: tuple[MarkPlacement, ...]
    diagnostics: tuple[str, ...]
    absences: tuple[MarkFacetAbsence, ...]
    diagnostic_provenance: tuple[DiagnosticProvenance, ...] = ()


@dataclass(frozen=True)
class CompletedWindowMark:
    """Original source mark plus its explicit-window completed geometry."""

    original: MarkPlacement
    visible: MarkPlacement | None
    paint_clip: PaintClip | None
    visibility: MarkFacetVisibility


def _window_geometry_error(mark: MarkPlacement, visibility: MarkFacetVisibility,
                           reason: str) -> LayoutError:
    source_ref = mark.source_ref[:120] if isinstance(mark.source_ref, str) else "<invalid>"
    facet = visibility.source.facet[:64] if isinstance(visibility.source.facet, str) else "<invalid>"
    return LayoutError(
        "E_LAYOUT_WINDOW_CLIP", "/layout/windowContour", node_id=source_ref,
        detail=f"source_ref={source_ref!r} facet={facet!r} stage=geometry reason={reason}",
    )


def complete_mark_window_geometry(
    mark: MarkPlacement, facet_visibility: MarkFacetVisibility,
    scale: ScalePlacement, plot: Rect,
) -> CompletedWindowMark:
    """Complete one selected mark against its date visibility and plot rectangle.

    Contained marks preserve object identity. Omitted facets produce no visible
    mark. A clipped span gets a new contour and a finite plot paint clip while
    retaining the untouched original placement for paint/progress provenance.
    """
    if facet_visibility.disposition == FacetDisposition.OMITTED:
        return CompletedWindowMark(mark, None, None, facet_visibility)
    if facet_visibility.disposition == FacetDisposition.CONTAINED:
        return CompletedWindowMark(mark, mark, None, facet_visibility)
    if facet_visibility.disposition != FacetDisposition.CLIPPED:
        raise _window_geometry_error(mark, facet_visibility, "invalid-disposition")
    if (facet_visibility.source.shape not in {"span", "open-span"}
            or type(facet_visibility.visible_start) is not date
            or type(facet_visibility.visible_finish) is not date
            or facet_visibility.visible_start >= facet_visibility.visible_finish):
        raise _window_geometry_error(mark, facet_visibility, "unsupported-facet")
    if not isinstance(plot, Rect):
        raise _window_geometry_error(mark, facet_visibility, "invalid-plot-or-scale")
    try:
        plot_left, plot_top, plot_width, plot_height = map(
            float, (plot.inline, plot.block, plot.inline_size, plot.block_size))
        mark_x, y, mark_width, height = map(
            float, (mark.bounds.inline, mark.bounds.block,
                    mark.bounds.inline_size, mark.bounds.block_size))
        scale_values = tuple(float(value) for value in
                             (scale.range_start, scale.range_end, scale.origin, scale.unit_ratio))
        if any(isinstance(value, bool) for value in
               (scale.range_start, scale.range_end, scale.origin, scale.unit_ratio)):
            raise TypeError("boolean scale coordinate")
        x1 = _coordinate(facet_visibility.visible_start, scale)
        x2 = _coordinate(facet_visibility.visible_finish, scale)
    except Exception as error:
        raise _window_geometry_error(mark, facet_visibility, "invalid-plot-or-scale") from error
    plot_right, plot_bottom = plot_left + plot_width, plot_top + plot_height
    width = x2 - x1
    if (not all(isfinite(value) for value in
                (x1, x2, y, height, mark_x, mark_width, width,
                 plot_left, plot_top, plot_width, plot_height,
                 plot_right, plot_bottom, *scale_values))
            or plot_width <= 0 or plot_height <= 0 or scale_values[3] <= 0
            or mark_width <= 0
            or width <= 0 or height <= 0 or x1 < plot_left or x2 > plot_right
            or y < plot_top or y + height > plot_bottom):
        raise _window_geometry_error(mark, facet_visibility, "host-outside-plot")
    try:
        visible_host = Rect(Decimal(str(x1)), mark.bounds.block,
                            Decimal(str(width)), mark.bounds.block_size)
        source_contour = (mark.path_commands if mark.path_commands else
                          rounded_rect_commands(
                              (mark_x, y, mark_width, height), mark.corner_radius))
        contour = clip_span_contour(
            source_contour, visible_host,
            cut_start=facet_visibility.cut_start,
            cut_finish=facet_visibility.cut_finish,
            source_ref=mark.source_ref, facet=facet_visibility.source.facet,
        )
    except WindowContourError:
        raise
    except Exception as error:
        raise _window_geometry_error(mark, facet_visibility, "contour-operation-failed") from error

    closes_open_end = mark.mark_shape == "open-span" and facet_visibility.cut_finish
    completed_parts = []
    for part in mark.symbol_parts:
        if part.commands == source_contour:
            completed_parts.append(replace(part, commands=contour))
        else:
            # Preserve each part's paint, but never project its uncut source
            # geometry. The shared intersection fails closed on unsupported
            # or malformed contours rather than retaining outside ink.
            clipped_part = intersect_visible_host_contour(
                part.commands, contour, visible_host,
                source_ref=mark.source_ref, facet=facet_visibility.source.facet)
            if clipped_part:
                completed_parts.append(replace(part, commands=clipped_part))
    clip = PaintClip((plot_left, plot_top, float(plot.inline_size), float(plot.block_size)))
    visible = replace(
        mark, bounds=visible_host,
        start_port=mark.start_port if facet_visibility.start_port_visible else None,
        end_port=mark.end_port if facet_visibility.end_port_visible else None,
        mark_shape="span" if closes_open_end else mark.mark_shape,
        corner_radius=0.0, path_commands=contour,
        end_treatment="closed" if closes_open_end else mark.end_treatment,
        paint_clip=clip,
        symbol_parts=tuple(completed_parts),
    )
    return CompletedWindowMark(mark, visible, clip, facet_visibility)


def _coordinate(value: date, scale: ScalePlacement) -> float:
    """Use the shared temporal scale with the established automatic formula."""
    return scale.origin + (value - scale.domain_start).days * scale.unit_ratio


def compose_item_marks(*, item: Any, instance_id: str, source_kind: str,
                       frame: MarkBandFrame, as_of: date | None,
                       theme_tokens: object, slot_id: str, paint_order_base: int = 100,
                       emit_missing_actual: bool = True,
                       emit_diagnostics: bool = True,
                       selection: ItemMarkFacetSelection | None = None) -> MarkItemComposition:
    """Complete planned and observed marks for one selected Review item.

    The caller owns candidate identity and the mark-band frame. This function
    consumes a prepared source selection (or selects for direct callers), then
    owns date mapping, local bounds/ports, visible mark geometry, and the typed
    account of intentional omissions.
    """
    marks: list[MarkPlacement] = []
    planned_semantic = "snapshot" if source_kind in {"snapshot", "scenario"} else "planned"
    # Preserve the established eager role lookup order while leaving source
    # selection independent from the frame.
    role_bounds = {
        planned_semantic: frame.role_bounds(planned_semantic),
        "actual": frame.role_bounds("actual"),
        "missing-actual": frame.role_bounds("missing-actual"),
    }
    if selection is None:
        selection = select_item_mark_facets(item=item, source_kind=source_kind, as_of=as_of,
                                            emit_missing_actual=emit_missing_actual,
                                            emit_diagnostics=emit_diagnostics)
    elif (selection.source_kind != source_kind or selection.as_of != as_of
          or selection.missing_actual_eligible != bool(emit_missing_actual)):
        raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/items",
                          detail="stage=composition; reason=selection-mismatch")
    for facet in selection.facets:
        placement_id = f"{facet.facet}:{instance_id}"
        if facet.shape == "point":
            at = facet.at
            assert at is not None
            x = _coordinate(at, frame.inline_scale)
            # Point symbols retain each semantic role's own size and offset (#1066).
            symbol_block, symbol_size = frame.symbol_bounds(facet.semantic_id)
            bounds = Rect(Decimal(str(x - symbol_size / 2)), Decimal(str(symbol_block)),
                          Decimal(str(symbol_size)), Decimal(str(symbol_size)))
            port = (x, symbol_block + symbol_size / 2)
            marks.append(compose_mark_placement(
                frame=frame, placement_id=placement_id, source_ref=item.object_id,
                bounds=bounds, start_port=port, end_port=port, shape="point",
                semantic_id=facet.semantic_id, theme_tokens=theme_tokens, slot_id=slot_id,
                paint_order_base=paint_order_base,
            ))
            continue

        start = facet.start
        finish = facet.finish
        assert start is not None and finish is not None
        x1, x2 = _coordinate(start, frame.inline_scale), _coordinate(finish, frame.inline_scale)
        block, size = role_bounds[facet.semantic_id]
        if facet.geometry == "end-tick":
            width = max(1.0, size * 1.5)
            y = block
            start_port = end_port = (x1, block)
        elif facet.geometry == "open-span":
            width = x2 - x1
            y = block
            start_port = (x1, block + size / 2)
            end_port = (x2, block + size / 2)
        else:
            # Keep the legacy 1px minimum for ordinary planned/actual spans;
            # in-progress missing-Actual spans historically use exact duration.
            width = (x2 - x1 if facet.geometry == "in-progress"
                     else max(1.0, x2 - x1))
            y = block
            start_port = (x1, block + size / 2)
            end_port = (x2, block + size / 2)
        bounds = Rect(Decimal(str(x1)), Decimal(str(y)), Decimal(str(width)), Decimal(str(size)))
        marks.append(compose_mark_placement(
            frame=frame, placement_id=placement_id, source_ref=item.object_id,
            bounds=bounds, start_port=start_port, end_port=end_port, shape=facet.shape,
            semantic_id=facet.semantic_id, theme_tokens=theme_tokens, slot_id=slot_id,
            paint_order_base=paint_order_base, end_treatment=facet.end_treatment,
        ))

    subject = DiagnosticSubject.project_object(item.object_id, getattr(item, "title", None))
    diagnostics = selection.diagnostics if emit_diagnostics else ()
    provenance = tuple(DiagnosticProvenance(diagnostic, (subject,))
                       for diagnostic in diagnostics)
    marks = [replace(mark, subjects=(subject,)) for mark in marks]
    return MarkItemComposition(tuple(marks), diagnostics, selection.absences, provenance)


def symbol_parts(value: Mapping[str, object], bounds: tuple[float, float, float, float],
                 layout_outline: tuple[PathCommand, ...] = (), *,
                 catalog_glyphs: Mapping[str, Mapping[str, object]] | None = None
                 ) -> tuple[SymbolPartPlacement, ...]:
    """Return the exact completed built-in or glyph paths for one point mark."""
    shape_value = value.get("shape")
    if isinstance(shape_value, Mapping) and set(shape_value) == {"catalog"}:
        reference = shape_value.get("catalog")
        glyph = (catalog_glyphs.get(reference) if isinstance(reference, str)
                 and catalog_glyphs is not None else None)
        if not isinstance(glyph, Mapping):
            raise _theme_error(f"shape.catalog={_brief(reference)} has no matching catalog glyph; expected a declared glyph identifier")
        value = {"shape": "glyph", **glyph}
    elif shape_value == "catalog-glyph":
        value = {**value, "shape": "glyph"}
    if value.get("shape") != "glyph":
        if layout_outline:
            return (SymbolPartPlacement(layout_outline),)
        shape = _choice(value, "shape", {"diamond", "circle", "square", "chevron"})
        x, y, width, height = bounds
        if width < 0 or height < 0:
            raise _primitive_error(f"symbol bounds width={_brief(width)}, height={_brief(height)} must be nonnegative")
        if shape == "diamond":
            points = ((x + width / 2, y), (x + width, y + height / 2),
                      (x + width / 2, y + height), (x, y + height / 2))
            commands = _closed_lines(points)
        elif shape == "square":
            commands = _closed_lines(((x, y), (x + width, y), (x + width, y + height), (x, y + height)))
        elif shape == "chevron":
            commands = _closed_lines(((x, y), (x + width, y + height / 2),
                                      (x, y + height), (x + width / 3, y + height / 2)))
        else:
            cx, cy = x + width / 2, y + height / 2
            commands = (PathCommand("move", ((cx, y),)),
                        PathCommand("quadratic", ((x + width, y), (x + width, cy))),
                        PathCommand("quadratic", ((x + width, y + height), (cx, y + height))),
                        PathCommand("quadratic", ((x, y + height), (x, cy))),
                        PathCommand("quadratic", ((x, y), (cx, y))))
        return (SymbolPartPlacement(commands),)
    return tuple(SymbolPartPlacement(part.outline, part.paint, part.color,
                                     part.stroke_width, part.line_cap, part.line_join)
                 for part in glyph_parts(value, bounds))


def compose_mark_placement(*, frame: MarkBandFrame, placement_id: str, source_ref: str,
                           bounds: Rect, start_port: tuple[float, float], end_port: tuple[float, float],
                           shape: str, semantic_id: str, theme_tokens: object, slot_id: str,
                           paint_order_base: int = 100, end_treatment: str = "closed") -> MarkPlacement:
    """Complete a mark's outline, role paint order, and symbol in one frame-aware path."""
    geometry = frame.role_geometries[semantic_id]
    radius = min(geometry.corner_radius * float(min(bounds.inline_size, bounds.block_size)),
                 float(min(bounds.inline_size, bounds.block_size)) / 2)
    radius = resolve_corner_radius(geometry.physical_corner_radius,
                                  width=float(bounds.inline_size), height=float(bounds.block_size),
                                  legacy_radius=radius)
    commands = (open_span_path(inline=float(bounds.inline), block=float(bounds.block),
                               inline_size=float(bounds.inline_size), block_size=float(bounds.block_size), radius=radius)
                if shape == "open-span" else
                rounded_diamond_path(inline=float(bounds.inline), block=float(bounds.block),
                                     inline_size=float(bounds.inline_size), block_size=float(bounds.block_size), radius=radius)
                if shape == "point" and radius > 0 else ())
    completed_symbols = ()
    if shape in {"point", "open-span"}:
        variant = "baseline" if semantic_id in {"snapshot", "scenario"} else semantic_id
        token = theme_tokens.variant_symbol(variant)
        try:
            completed_symbols = symbol_parts(
                token, (float(bounds.inline), float(bounds.block),
                        float(bounds.inline_size), float(bounds.block_size)), commands,
                catalog_glyphs=getattr(theme_tokens, "catalog_glyphs", None),
            )
        except ValueError as error:
            raise LayoutError("E_LAYOUT_LANE_FOOTPRINT_UNAVAILABLE", placement_id) from error
        if shape == "point" and any(part.paint_mode == "fill" for part in completed_symbols):
            completed_symbols = complete_point_outline(
                completed_symbols, paint_role=resolve_point_paint_role(
                    semantic_id, gate_declared=theme_tokens.has_role("gate")),
                theme_tokens=theme_tokens)
    return MarkPlacement(placement_id, source_ref, bounds, start_port, end_port,
                         mark_shape=shape, corner_radius=radius, path_commands=commands,
                         slot_id=slot_id, semantic_id=semantic_id,
                         paint_order=paint_order_base + geometry.paint_order,
                         end_treatment=end_treatment, symbol_parts=completed_symbols)


@dataclass(frozen=True)
class _GlyphPart:
    outline: tuple[PathCommand, ...]
    paint: str
    color: str | None
    stroke_width: float | None = None
    line_cap: str | None = None
    line_join: str | None = None


def glyph_parts(value: Mapping[str, object], bounds: tuple[float, float, float, float]) -> tuple[_GlyphPart, ...]:
    catalog_glyph = "viewport" in value
    view_box = value.get("viewport") if catalog_glyph else value.get("viewBox")
    if catalog_glyph and isinstance(view_box, Mapping):
        view_box = (view_box.get("inlineSize"), view_box.get("blockSize"))
    if (not isinstance(view_box, (list, tuple)) or len(view_box) != 2
            or any(not isinstance(item, (int, float)) or isinstance(item, bool) or item <= 0 for item in view_box)):
        raise _theme_error(f"glyph viewport must contain two positive dimensions; received {_brief(view_box)}")
    view_width, view_height = float(view_box[0]), float(view_box[1])
    parts = value.get("parts")
    if not isinstance(parts, (list, tuple)) or not parts:
        raise _theme_error(f"glyph parts must be a non-empty sequence; received {_brief(parts)}")
    x, y, width, height = bounds
    if width < 0 or height < 0:
        raise _primitive_error(f"glyph destination bounds width={_brief(width)}, height={_brief(height)} must be nonnegative")
    scale = min(width / view_width, height / view_height)
    offset_x = x + (width - view_width * scale) / 2
    offset_y = y + (height - view_height * scale) / 2
    def transform(point: tuple[float, float]) -> tuple[float, float]:
        return (offset_x + point[0] * scale, offset_y + point[1] * scale)
    result = []
    for part in parts:
        if not isinstance(part, Mapping):
            raise _theme_error(f"glyph part entry must be a mapping; received {type(part).__name__}")
        paint = _choice(part, "paint", {"fill", "stroke", "none"})
        if catalog_glyph and paint not in {"fill", "stroke"}:
            raise _theme_error(f"catalog glyph part.paint={_brief(paint)}; expected 'fill' or 'stroke'")
        color = part.get("color")
        if color is not None and not isinstance(color, str):
            raise _theme_error(f"glyph part.color must be a string when present; received {_brief(color)}")
        if paint == "none":
            continue
        raw = part.get("data") if catalog_glyph else part.get("d")
        if not isinstance(raw, str) or not raw:
            raise _theme_error(f"glyph path data must be a non-empty string; received {_brief(raw)}")
        try:
            parsed = parse_path_commands(raw)
        except IconNormalizationError as error:
            raise _theme_error(f"glyph path data is not valid normalized geometry (length={len(raw)}, parser={type(error).__name__})") from error
        if catalog_glyph and any(command.kind not in {"move", "line", "quadratic", "close"}
                                 for command in parsed):
            raise _theme_error("catalog glyph commands must use only move, line, quadratic, or close")
        outline = []
        start = None
        for command in parsed:
            if command.kind == "move":
                point = transform(command.points[0])
                outline.append(PathCommand("move", (point,)))
                start = point
            elif command.kind == "line":
                outline.append(PathCommand("line", (transform(command.points[0]),)))
            elif command.kind == "quadratic" and catalog_glyph:
                outline.append(PathCommand("quadratic", tuple(transform(point) for point in command.points)))
            elif command.kind == "close":
                if start is None:
                    raise _theme_error("glyph path close command requires a preceding move command")
                outline.append(PathCommand("line", (start,)))
            else:
                raise _theme_error(f"glyph command kind={_brief(command.kind)} is unsupported for this glyph; expected move, line, quadratic, or close")
        if not outline:
            raise _theme_error("glyph path must produce at least one completed outline command")
        stroke_width = part.get("strokeWidth") if catalog_glyph else None
        line_cap = part.get("lineCap") if catalog_glyph else None
        line_join = part.get("lineJoin") if catalog_glyph else None
        if catalog_glyph and paint == "stroke":
            if (not isinstance(stroke_width, (int, float)) or isinstance(stroke_width, bool)
                    or not isfinite(float(stroke_width)) or float(stroke_width) <= 0
                    or line_cap not in {"butt", "round", "square"}
                    or line_join not in {"miter", "round", "bevel"}):
                raise _theme_error(f"catalog glyph stroke requires positive finite strokeWidth and supported lineCap/lineJoin; width={_brief(stroke_width)}, cap={_brief(line_cap)}, join={_brief(line_join)}")
            stroke_width = float(stroke_width) * scale
        result.append(_GlyphPart(tuple(outline), paint, color,
                                 float(stroke_width) if stroke_width is not None else None,
                                 line_cap if isinstance(line_cap, str) else None,
                                 line_join if isinstance(line_join, str) else None))
    return tuple(result)


def _closed_lines(points: tuple[tuple[float, float], ...]) -> tuple[PathCommand, ...]:
    return (PathCommand("move", (points[0],)), *(PathCommand("line", (point,)) for point in points[1:]),
            PathCommand("line", (points[0],)))


def _choice(value: Mapping[str, object], name: str, choices: set[str]) -> str:
    result = value.get(name)
    if not isinstance(result, str) or result not in choices:
        raise _theme_error(f"symbol {name}={_brief(result)}; expected one of {sorted(choices)!r}")
    return result
