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
from chrona.presentation.layout.rounded_outline import resolve_corner_radius
from chrona.presentation.layout.surface_quality import MarkPlacement
from chrona.presentation.model.projection import ObservationState
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject


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


@dataclass(frozen=True)
class MarkFacetAbsence:
    """One deliberately unprojected facet and the semantic reason it is absent."""

    facet: str
    reason: str


@dataclass(frozen=True)
class MarkItemComposition:
    """Complete item mark closure, including observable omissions and warnings."""

    marks: tuple[MarkPlacement, ...]
    diagnostics: tuple[str, ...]
    absences: tuple[MarkFacetAbsence, ...]
    diagnostic_provenance: tuple[DiagnosticProvenance, ...] = ()


def _coordinate(value: date, scale: ScalePlacement) -> float:
    """Use the shared temporal scale with the established automatic formula."""
    return scale.origin + (value - scale.domain_start).days * scale.unit_ratio


def compose_item_marks(*, item: Any, instance_id: str, source_kind: str,
                       frame: MarkBandFrame, as_of: date | None,
                       theme_tokens: object, slot_id: str, paint_order_base: int = 100,
                       emit_missing_actual: bool = True,
                       emit_diagnostics: bool = True) -> MarkItemComposition:
    """Complete planned and observed marks for one selected Review item.

    The caller owns candidate identity and the mark-band frame. This function
    owns facet selection, date mapping, local bounds/ports, visible mark
    geometry, and the typed account of intentional omissions.
    """
    marks: list[MarkPlacement] = []
    diagnostics: list[str] = []
    absences: list[MarkFacetAbsence] = []
    planned = item.planned
    actual = item.actual or {}
    planned_semantic = "snapshot" if source_kind in {"snapshot", "scenario"} else "planned"
    planned_block, planned_size = frame.role_bounds(planned_semantic)
    actual_block, actual_size = frame.role_bounds("actual")
    missing_block, missing_size = frame.role_bounds("missing-actual")

    if source_kind == "actual":
        absences.append(MarkFacetAbsence("planned", "actual-only-member"))
    elif item.source_type == "point":
        x = _coordinate(planned["at"], frame.inline_scale)
        # A point mark's symbol takes the role's own size and offset when the Theme declares them (#1066).
        symbol_block, symbol_size = frame.symbol_bounds(planned_semantic)
        bounds = Rect(Decimal(str(x - symbol_size / 2)), Decimal(str(symbol_block)),
                      Decimal(str(symbol_size)), Decimal(str(symbol_size)))
        port = (x, symbol_block + symbol_size / 2)
        marks.append(compose_mark_placement(
            frame=frame, placement_id=f"planned:{instance_id}", source_ref=item.object_id,
            bounds=bounds, start_port=port, end_port=port, shape="point",
            semantic_id=planned_semantic, theme_tokens=theme_tokens, slot_id=slot_id,
            paint_order_base=paint_order_base,
        ))
    else:
        x1, x2 = _coordinate(planned["start"], frame.inline_scale), _coordinate(planned["end"], frame.inline_scale)
        bounds = Rect(Decimal(str(x1)), Decimal(str(planned_block)),
                      Decimal(str(max(1.0, x2 - x1))), Decimal(str(planned_size)))
        marks.append(compose_mark_placement(
            frame=frame, placement_id=f"planned:{instance_id}", source_ref=item.object_id,
            bounds=bounds, start_port=(x1, planned_block + planned_size / 2),
            end_port=(x2, planned_block + planned_size / 2), shape="span",
            semantic_id=planned_semantic, theme_tokens=theme_tokens, slot_id=slot_id,
            paint_order_base=paint_order_base,
        ))

    # An Actual that runs to as-of: declared `openUntil: asOf`, or marked in progress by the View (#991).
    runs_to_as_of = (actual.get("openUntil") == "asOf"
                     or (emit_missing_actual and getattr(item, "missing_actual_mark", "due-end") == "in-progress"))
    open_actual = (source_kind in {"actual", "combined"} and item.source_type == "span"
                   and runs_to_as_of and isinstance(actual.get("start"), date)
                   and as_of is not None)
    if (source_kind in {"actual", "combined"} and item.source_type == "span"
            and isinstance(actual.get("start"), date) and isinstance(actual.get("finish"), date)):
        x1, x2 = _coordinate(actual["start"], frame.inline_scale), _coordinate(actual["finish"], frame.inline_scale)
        bounds = Rect(Decimal(str(x1)), Decimal(str(actual_block)),
                      Decimal(str(max(1.0, x2 - x1))), Decimal(str(actual_size)))
        marks.append(compose_mark_placement(
            frame=frame, placement_id=f"actual:{instance_id}", source_ref=item.object_id,
            bounds=bounds, start_port=(x1, actual_block + actual_size / 2),
            end_port=(x2, actual_block + actual_size / 2), shape="span",
            semantic_id="actual", theme_tokens=theme_tokens, slot_id=slot_id,
            paint_order_base=paint_order_base,
        ))
    elif open_actual:
        x1, x2 = _coordinate(actual["start"], frame.inline_scale), _coordinate(as_of, frame.inline_scale)
        if x2 <= x1:
            if emit_diagnostics:
                diagnostics.append(f"W_LAYOUT_OPEN_ACTUAL_INVALID:{item.object_id}")
            absences.append(MarkFacetAbsence("actual", "invalid-open-actual"))
        else:
            if emit_missing_actual and getattr(item, "missing_actual_mark", "due-end") == "in-progress":
                # An in-progress span (#991) is drawn as the missing-actual span from its actual start to
                # as-of, in place of its open actual.
                bounds = Rect(Decimal(str(x1)), Decimal(str(missing_block)),
                              Decimal(str(x2 - x1)), Decimal(str(missing_size)))
                marks.append(compose_mark_placement(
                    frame=frame, placement_id=f"missing-actual:{instance_id}", source_ref=item.object_id,
                    bounds=bounds, start_port=(x1, missing_block + missing_size / 2),
                    end_port=(x2, missing_block + missing_size / 2), shape="span",
                    semantic_id="missing-actual", theme_tokens=theme_tokens, slot_id=slot_id,
                    paint_order_base=paint_order_base,
                ))
            else:
                bounds = Rect(Decimal(str(x1)), Decimal(str(actual_block)),
                              Decimal(str(x2 - x1)), Decimal(str(actual_size)))
                marks.append(compose_mark_placement(
                    frame=frame, placement_id=f"actual:{instance_id}", source_ref=item.object_id,
                    bounds=bounds, start_port=(x1, actual_block + actual_size / 2),
                    end_port=(x2, actual_block + actual_size / 2), shape="open-span",
                    semantic_id="actual", theme_tokens=theme_tokens, slot_id=slot_id,
                    paint_order_base=paint_order_base, end_treatment="open",
                ))
    elif (source_kind in {"actual", "combined"} and item.source_type == "point"
          and isinstance(actual.get("at"), date)):
        x = _coordinate(actual["at"], frame.inline_scale)
        symbol_block, symbol_size = frame.symbol_bounds("actual")
        bounds = Rect(Decimal(str(x - symbol_size / 2)), Decimal(str(symbol_block)),
                      Decimal(str(symbol_size)), Decimal(str(symbol_size)))
        port = (x, symbol_block + symbol_size / 2)
        marks.append(compose_mark_placement(
            frame=frame, placement_id=f"actual:{instance_id}", source_ref=item.object_id,
            bounds=bounds, start_port=port, end_port=port, shape="point",
            semantic_id="actual", theme_tokens=theme_tokens, slot_id=slot_id,
            paint_order_base=paint_order_base,
        ))
    elif source_kind in {"actual", "combined", "primary"}:
        if source_kind == "primary" and item.observation_state == ObservationState.RECORDED:
            absences.append(MarkFacetAbsence("actual", "recorded-on-companion-member"))
        elif actual.get("openUntil") == "asOf" and isinstance(actual.get("start"), date) and as_of is None:
            if emit_diagnostics:
                diagnostics.append(f"W_LAYOUT_OPEN_ACTUAL_AS_OF_REQUIRED:{item.object_id}")
            absences.append(MarkFacetAbsence("actual", "as-of-required"))
        elif actual:
            if emit_diagnostics:
                diagnostics.append(f"W_LAYOUT_ACTUAL_INCOMPLETE:{item.object_id}")
            absences.append(MarkFacetAbsence("actual", "incomplete-observation"))
        elif (emit_missing_actual and item.observation_state == ObservationState.DUE_UNOBSERVED
              and getattr(item, "missing_actual_mark", "due-end") == "due-end"):
            anchor = planned.get("end", planned.get("at"))
            if isinstance(anchor, date):
                x = _coordinate(anchor, frame.inline_scale)
                bounds = Rect(Decimal(str(x)), Decimal(str(missing_block)),
                              Decimal(str(max(1.0, missing_size * 1.5))), Decimal(str(missing_size)))
                marks.append(compose_mark_placement(
                    frame=frame, placement_id=f"missing-actual:{instance_id}", source_ref=item.object_id,
                    bounds=bounds, start_port=(x, missing_block), end_port=(x, missing_block),
                    shape="span", semantic_id="missing-actual", theme_tokens=theme_tokens,
                    slot_id=slot_id, paint_order_base=paint_order_base,
                ))
            else:
                absences.append(MarkFacetAbsence("missing-actual", "planned-anchor-unavailable"))
        else:
            absences.append(MarkFacetAbsence("actual", "no-selected-observation"))
    else:
        absences.append(MarkFacetAbsence("actual", "member-has-no-actual-facet"))

    subject = DiagnosticSubject.project_object(item.object_id, getattr(item, "title", None))
    provenance = tuple(DiagnosticProvenance(diagnostic, (subject,)) for diagnostic in diagnostics)
    marks = [replace(mark, subjects=(subject,)) for mark in marks]
    return MarkItemComposition(tuple(marks), tuple(diagnostics), tuple(absences), provenance)


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
