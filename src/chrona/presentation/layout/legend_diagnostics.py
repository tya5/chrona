"""Semantic diagnostics over the final, completed legend figures."""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal
from itertools import combinations

from chrona.presentation.layout.legend_ink import mark_ink_keys, pattern_ink_identity
from chrona.presentation.model.color_separability import (
    CHECKED_VISIONS, MINIMUM_CATEGORY_DELTA_E, delta_e_2000,
)
from chrona.presentation.model.diagnostic_sources import (
    ColorPairFinding, DiagnosticProvenance, DiagnosticSubject,
)
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


def _completed_parts(parts):
    """Use one part representation for canonical point and placed figure witnesses."""
    if len(parts) == 2 and isinstance(parts[0], str):
        # The canonical shape tag is not another drawn part or a colour channel.
        parts = parts[1]
    return tuple((part[0], part[1] if part[0] == "stroke" else None,
                  part[2] if part[0] == "stroke" else None, part[-1]) for part in parts)


def _role_paint(request, role, *, family=None, fill_override=None, completed_catalog=False):
    tokens = request.theme_tokens
    capabilities = request.paint_capabilities
    family = family or mark_paint_family(tokens, role, has_completed_catalog_pattern=completed_catalog)
    witness = resolve_theme_paint_witness(
        tokens, role, family,
        gradient_supported=capabilities.gradient_supported,
        optional_gradient_omission=capabilities.optional_gradient_omission,
        fill_override=fill_override,
        catalog_pattern=completed_catalog,
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
    parts = getattr(mark, "legend_geometry_identity", None)
    if parts is None:
        parts = tuple((part.paint_mode,
                       part.line_cap if part.paint_mode == "stroke" else None,
                       part.line_join if part.paint_mode == "stroke" else None,
                       _commands(part.commands, bounds)) for part in mark.symbol_parts)
    if not parts:
        shape = "Rect" if mark.mark_shape == "span" else mark.mark_shape
        radius = _unit(mark.corner_radius, 0, min(bounds[2:])) if min(bounds[2:]) else 0.0
        parts = ((None, None, None, ((shape, radius),)),)
    return (_completed_parts(parts), tuple(paint.identity for paint in paints), patterns)


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
        paint_identity = (fill, _color(ink.stroke), ink.stroke_width, ink.dash, ink.opacity)
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
        if shape.paint_channels == "fill":
            family = PaintFamily.SOLID
        elif shape.paint_channels == "stroke" or (shape.kind == "Path" and not completed_catalog):
            family = PaintFamily.PATH
        else:
            family = mark_paint_family(tokens, role, has_completed_catalog_pattern=completed_catalog)
        paint_identity = _role_paint(request, role, family=family, fill_override=fill_override,
                                     completed_catalog=completed_catalog)
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
            "stroke" if shape.legend_swatch_shape == "rule-pair" else
            shape.paint_channels or ("stroke" if shape.kind == "Path" else None))
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


def _figure_ink_colours(figure):
    """Return the concrete visible inks for a completed figure, in paint order.

    ``_figure_signature`` contains completed paint identities.  These
    retain the completed fill/stroke channels, while the corresponding part
    mode tells us which channel was actually emitted for that component.
    Gradients count as visible fill, but are not sampled as a representative
    colour.
    """
    if figure is None:
        return ()
    fills: list[str] = []
    strokes: list[str] = []
    has_visible_fill = False

    for signature in figure:
        parts, paints = _completed_parts(signature[0]), signature[1]
        for index, paint in enumerate(paints):
            if not isinstance(paint, tuple) or len(paint) != 5:
                continue
            fill, stroke, stroke_width, _dash, opacity = paint
            if opacity is not None and opacity <= 0:
                continue
            mode = parts[index][0] if index < len(parts) and parts[index] else None
            permits_fill = mode != "stroke"
            permits_stroke = mode != "fill"

            if permits_fill and fill is not None:
                has_visible_fill = True
                if (isinstance(fill, tuple) and len(fill) == 2 and fill[0] == "solid"
                        and isinstance(fill[1], str) and fill[1].startswith("#")):
                    fills.append(fill[1].upper())
            if (permits_stroke and isinstance(stroke, str) and stroke.startswith("#")
                    and stroke_width is not None and stroke_width > 0):
                strokes.append(stroke.upper())

    selected = fills if has_visible_fill else strokes
    return tuple(dict.fromkeys(selected))


def _non_colour_figure(figure):
    """Keep completed shape/channel and line-pattern distinctions, never palette values."""
    if not figure:
        return None
    components = []
    for signature in figure:
        parts, paints, patterns = _completed_parts(signature[0]), signature[1], signature[2]
        visible = []
        for index, paint in enumerate(paints):
            fill, stroke, width, dash, opacity = paint
            if opacity is not None and opacity <= 0:
                continue
            if index >= len(parts) or not parts[index][-1]:
                return None  # no completed geometry means no proven distinction
            mode, cap, join, geometry = parts[index]
            filled = mode != "stroke" and fill is not None
            stroked = mode != "fill" and stroke is not None and width is not None and width > 0
            if not filled and not stroked:
                continue
            visible.append((filled, stroked, width if stroked else None, geometry,
                            cap if stroked else None, join if stroked else None,
                            tuple(dash) if stroked and dash else (),
                            patterns[index] if index < len(patterns) else None))
        if visible:
            components.append(tuple(visible))
    return tuple(components) or None


def _palette_separation_failures(first_figure, second_figure):
    """Return the minimum below-floor distance once per affected vision."""
    first_shape, second_shape = _non_colour_figure(first_figure), _non_colour_figure(second_figure)
    if first_shape is not None and second_shape is not None and first_shape != second_shape:
        return ()
    first, second = _figure_ink_colours(first_figure), _figure_ink_colours(second_figure)
    if not first or not second:
        return ()
    failures = []
    for vision in CHECKED_VISIONS:
        distance = min(delta_e_2000(left, right, vision=vision)
                       for left in first for right in second)
        if distance < MINIMUM_CATEGORY_DELTA_E:
            failures.append((vision, distance))
    return tuple(failures)


def _subject(entry):
    key_id = entry.realized_key.key_id if entry.realized_key is not None else entry.source_identity
    return DiagnosticSubject(f"legend-key:{key_id}", f"{entry.label} ({entry.role})")


def _colour_pair_diagnostics(key_entries, figures):
    """Compare completed legend ink across distinct encoded and semantic meanings."""
    diagnostics: list[str] = []
    provenance: list[DiagnosticProvenance] = []
    for (left, left_scale), (right, right_scale) in combinations(tuple(key_entries), 2):
        if left.source_identity == right.source_identity:
            continue
        for vision, min_delta in _palette_separation_failures(
                figures.get(left.source_identity), figures.get(right.source_identity)):
            if _covered_by_scale_collision(left, left_scale, right, right_scale, vision, min_delta):
                continue
            display_delta = round(min_delta, 3)
            identity = f"W_LEGEND_COLOR_NOT_SEPARABLE:{vision}:{display_delta}"
            diagnostics.append(identity)
            provenance.append(DiagnosticProvenance(
                identity, (_subject(left), _subject(right)), ColorPairFinding(vision, min_delta)))
    return tuple(diagnostics), tuple(provenance)


def _covered_by_scale_collision(left, left_scale, right, right_scale, vision, min_delta):
    """Whether an existing typed domain finding exactly covers this completed pair."""
    left_value, right_value = left.encoding_domain_value, right.encoding_domain_value
    if (not left_scale or left_scale != right_scale or left_value is None or right_value is None
            or left_value == right_value):
        return False
    return any(
        collision.scale_id == left_scale
        and {collision.first, collision.second} == {left_value, right_value}
        and collision.vision == vision
        and collision.delta_e == min_delta
        for collision in (*left.scale_collisions, *right.scale_collisions)
    )


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
    key_entries = tuple((entry, entry.encoding_scale_id) for entry in visible)
    pair_diagnostics, pair_provenance = _colour_pair_diagnostics(key_entries, figures)
    diagnostics.extend(pair_diagnostics)
    provenance.extend(pair_provenance)
    return tuple(diagnostics), tuple(provenance)
