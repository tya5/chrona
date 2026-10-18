"""Semantic diagnostics over the final, completed legend figures."""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from itertools import combinations

from chrona.presentation.layout.legend_ink import mark_ink_keys, pattern_ink_identity
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject
from chrona.presentation.model.theme_paint import (
    PaintFamily, mark_paint_family, resolve_legend_shape_ink, resolve_theme_paint_witness,
)
from chrona.presentation.model.semantic_registry import semantic_binding


def _unit(value: float, origin: float, extent: float) -> float:
    return round((value - origin) / extent, 9) if extent else 0.0


def _color(value):
    return value.upper() if isinstance(value, str) and value.startswith("#") else value


def _commands(commands, bounds):
    x, y, width, height = bounds
    return tuple((command.kind, tuple((_unit(px, x, width), _unit(py, y, height))
                                      for px, py in command.points)) for command in commands)


def _role_paint(request, role, *, family=None, fill_override=None):
    tokens = request.theme_tokens
    capabilities = request.paint_capabilities
    family = family or mark_paint_family(tokens, role)
    witness = resolve_theme_paint_witness(
        tokens, role, family,
        gradient_supported=capabilities.gradient_supported,
        optional_gradient_omission=capabilities.optional_gradient_omission,
        fill_override=fill_override,
        catalog_pattern=False,
    )
    return witness.identity


def _mark_signature(request, entry, mark):
    key = entry.realized_key
    if mark.legend_paints:
        paints = mark.legend_paints
        patterns = tuple(key.pattern_identity for _ in paints) if key is not None else (None,) * len(paints)
    elif key is not None:
        paints = key.glyph.paints if key.glyph is not None else (key.paint,)
        patterns = tuple(key.pattern_identity for _ in paints)
    else:
        realized = mark_ink_keys(mark, request.surface_content, request.theme_tokens,
                                 request.paint_capabilities)
        if not realized:
            return None
        paints = tuple(paint for realized_key in realized
                       for paint in (realized_key.glyph.paints if realized_key.glyph else (realized_key.paint,)))
        patterns = tuple(realized_key.pattern_identity for realized_key in realized
                         for _ in (realized_key.glyph.paints if realized_key.glyph else (realized_key.paint,)))
    bounds = tuple(map(float, (mark.bounds.inline, mark.bounds.block,
                               mark.bounds.inline_size, mark.bounds.block_size)))
    parts = tuple((part.paint_mode,
                   part.line_cap if part.paint_mode == "stroke" else None,
                   part.line_join if part.paint_mode == "stroke" else None,
                   _commands(part.commands, bounds)) for part in mark.symbol_parts)
    if not parts:
        shape = "Rect" if mark.mark_shape == "span" else mark.mark_shape
        radius = _unit(mark.corner_radius, 0, min(bounds[2:])) if min(bounds[2:]) else 0.0
        parts = ((None, None, None, ((shape, radius),)),)
    return (parts, tuple(paint.identity for paint in paints), patterns)


def _shape_signature(request, entry, shape):
    key = entry.realized_key
    role = shape.visual_role or (key.paint_role if key is not None else entry.role)
    if shape.legend_swatch_shape is not None:
        scale_paint = dict(request.surface_content.scale_legend_paints).get(shape.source_ref)
        channels = key.paint.effective_channels if key is not None else (
            shape.legend_paint.effective_channels if shape.legend_paint is not None else None)
        fill_override = ((channels.fill or channels.stroke) if channels is not None else scale_paint)
        ink = resolve_legend_shape_ink(request.theme_tokens, role, shape.legend_swatch_shape,
                                       fill_override=fill_override)
        fill = ("solid", _color(ink.fill)) if ink.fill is not None else None
        paint_identity = (fill, _color(ink.stroke), ink.stroke_width, (), ink.opacity)
        pattern = None
    elif key is not None:
        paint_identity = key.paint.identity
        pattern = key.pattern_identity
    elif shape.legend_paint is not None:
        paint_identity = shape.legend_paint.identity
        tokens = request.theme_tokens
        declared_pattern = tokens.optional_pattern(role)
        completed_catalog = (shape.kind == "Rect" and isinstance(declared_pattern, Mapping)
                             and declared_pattern.get("kind") == "catalog")
        pattern = pattern_ink_identity(tokens, role, completed_catalog=completed_catalog)
    else:
        tokens = request.theme_tokens
        declared_pattern = tokens.optional_pattern(role)
        completed_catalog = (shape.kind == "Rect" and isinstance(declared_pattern, Mapping)
                             and declared_pattern.get("kind") == "catalog")
        fill_override = dict(request.surface_content.scale_legend_paints).get(shape.source_ref)
        paint_identity = _role_paint(request, role, fill_override=fill_override)
        pattern = pattern_ink_identity(tokens, role, completed_catalog=completed_catalog)
    if shape.legend_swatch_shape is None and shape.paint_channels is not None:
        fill_ink, stroke, stroke_width, dash, opacity = paint_identity
        if shape.paint_channels == "fill":
            paint_identity = (fill_ink, None, None, (), opacity)
        else:
            paint_identity = (None, stroke, stroke_width, dash, opacity)
            pattern = None
    bounds = tuple(map(float, (shape.bounds.inline, shape.bounds.block,
                               shape.bounds.inline_size, shape.bounds.block_size)))
    geometry = _commands(shape.path_commands, bounds)
    if not geometry and shape.points:
        x, y, width, height = bounds
        geometry = tuple(("point", ((_unit(px, x, width), _unit(py, y, height)),))
                         for px, py in shape.points)
    if not geometry:
        geometry = (("Rect" if shape.kind == "Rect" else shape.kind,
                     round(shape.corner_radius / min(bounds[2:]), 9)
                     if min(bounds[2:]) else 0.0),)
    mode = ("fill" if shape.legend_swatch_shape == "circle" else
            "stroke" if shape.legend_swatch_shape == "rule-pair" or shape.kind == "Path" else
            shape.paint_channels)
    parts = ((mode, None, None, geometry),)
    return (parts, (paint_identity,), (pattern,))


def _relation_signature(request, entry, relation):
    key = entry.realized_key
    role = key.paint_role if key is not None else semantic_binding(relation.semantic_id).scene_role
    if key is not None:
        paint, pattern = key.paint.identity, key.pattern_identity
    else:
        paint = _role_paint(request, role, family=PaintFamily.PATH)
        pattern = None  # relation swatches emit no catalogue pattern primitive
    if len(relation.points) < 2:
        return None
    xs, ys = zip(*relation.points)
    bounds = (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
    geometry = _commands(relation.path_commands, bounds) if relation.path_commands else tuple(
        ("point", ((_unit(x, bounds[0], bounds[2]), _unit(y, bounds[1], bounds[3])),))
        for x, y in relation.points)
    return ((("stroke", None, None, geometry),), (paint,), (pattern,),
            relation.marker_start, relation.marker_end)


def _figure_signature(request, entry, marks, shapes, relations):
    source = entry.source_identity
    figures = []
    figures.extend(signature for mark in marks if mark.source_ref == source
                   if (signature := _mark_signature(request, entry, mark)) is not None)
    figures.extend(signature for shape in shapes if shape.source_ref == source
                   if (signature := _shape_signature(request, entry, shape)) is not None)
    swatch_id = entry.swatch_placement_id
    figures.extend(signature for relation in relations
                   if relation.relation_id == swatch_id and not relation.suppressed
                   if (signature := _relation_signature(request, entry, relation)) is not None)
    if not figures:
        return None
    return tuple(figures)


def _subject(entry):
    key_id = entry.realized_key.key_id if entry.realized_key is not None else entry.source_identity
    return DiagnosticSubject(f"legend-key:{key_id}", f"{entry.label} ({entry.role})")


def completed_legend_diagnostics(request, entries, marks, shapes, relations, text):
    """Compare only final labels and swatches, with source identities kept as subjects."""
    texts = {item.placement_id: item for item in text}
    visible = tuple(entry for entry in entries if entry.text_placement_id in texts
                    and texts[entry.text_placement_id].overflow != "suppressed")
    diagnostics: list[str] = []
    provenance: list[DiagnosticProvenance] = []

    def emit(code, left, right):
        diagnostics.append(code)
        provenance.append(DiagnosticProvenance(code, (_subject(left), _subject(right))))

    figures = {entry.source_identity: _figure_signature(request, entry, marks, shapes, relations)
               for entry in visible}
    for left, right in combinations(visible, 2):
        if left.source_identity == right.source_identity:
            continue
        left_text, right_text = texts[left.text_placement_id], texts[right.text_placement_id]
        if left_text.content == right_text.content:
            emit("W_LEGEND_LABEL_DUPLICATE", left, right)
        left_figure = figures[left.source_identity]
        right_figure = figures[right.source_identity]
        if left_figure is not None and left_figure == right_figure:
            emit("W_LEGEND_SWATCH_COLLISION", left, right)
    return tuple(diagnostics), tuple(provenance)
