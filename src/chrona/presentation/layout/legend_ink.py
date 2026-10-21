"""Shared potential/completed Actual ink witnesses; no Scene or source evaluation."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal

from chrona.presentation.layout.mark_geometry import (
    canonical_point_geometry, complete_point_outline, symbol_parts,
)
from chrona.presentation.layout.mark_role_geometry import (
    resolve_mark_band, resolve_mark_geometries, resolve_occurrence_mark_frame,
)
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.presentation import MarkBandFrame
from chrona.presentation.layout.path_geometry import rounded_diamond_path
from chrona.presentation.layout.pattern_placement import complete_pattern_placement
from chrona.presentation.layout.rounded_outline import resolve_corner_radius
from chrona.presentation.model.legend_paint import PointStateEncodingWitness, RealizedGlyphInk, RealizedLegendKey
from chrona.presentation.model.semantic_registry import mark_style_role
from chrona.presentation.model.mark_semantics import canonical_mark_semantic
from chrona.presentation.model.point_paint import resolve_point_paint_role
from chrona.presentation.model.actual_variance_paint import ACTUAL_VARIANCE_TRAIT_ROLES
from chrona.presentation.model.theme_paint import (
    PaintFamily, choose_fill_override, mark_paint_family, resolve_theme_paint_witness,
)


def _freeze(value):
    if isinstance(value, Mapping):
        return tuple((key, _freeze(item)) for key, item in sorted(value.items()) if key != "ref")
    if isinstance(value, (tuple, list)):
        return tuple(_freeze(item) for item in value)
    return value


def _actual_classes(source):
    if source is None:
        return ()
    return tuple(role.removeprefix("variance-") for role, _ in ACTUAL_VARIANCE_TRAIT_ROLES
                 if role in source.original_roles)


def pattern_ink_identity(tokens, role, *, completed_catalog=False):
    """Include emitted pattern treatment, not resource reference or host bounds."""
    pattern = tokens.optional_pattern(role)
    if pattern is None or pattern.get("kind") == "outline":
        return None
    if pattern.get("kind") != "catalog":
        return _freeze(pattern)
    if not completed_catalog:
        return None
    placed = complete_pattern_placement(pattern, Rect(Decimal(0), Decimal(0), Decimal(64), Decimal(32)), 0)
    return ("catalog", placed.tile_inline_size, placed.tile_block_size, placed.angle_degrees,
            placed.density_basis_points, placed.primitives)


def point_symbol_token(tokens, selected_role, point_state):
    """Resolve the same selected role/geometry variant used by chart points."""
    if selected_role is not None:
        return tokens.symbol(selected_role)
    return tokens.variant_symbol(mark_style_role(point_state))


def point_key_owner(content, point_state, selected_role):
    """Return the first semantic Detail owner eligible to own this point state."""
    entries = tuple(entry for entry in content.legend_entries
                    if entry.source_ref is None and entry.style_scope is None
                    and entry.view_scale_id is None and entry.encoding_scale_id is None
                    and not entry.encoding_value_is_wording
                    and not entry.role.startswith("scale:"))
    if selected_role is not None:
        selected = next((entry.role for entry in entries if entry.role == selected_role), None)
        if selected is not None:
            return selected
    if any(entry.role == "milestone" for entry in entries):
        return "milestone"
    if any(entry.role == point_state for entry in entries):
        return point_state
    return None


def _point_state_for_occurrence(key, tokens):
    """Recover a logical point state through the same canonical facet mapping as mark composition."""
    for state in ("planned", "actual", "forecast"):
        if canonical_mark_semantic(state, "point", gate_declared=tokens.has_role("gate")) == key.semantic_id:
            return state
    return None


def _point_witness_parts(content, tokens, key, point_state, mark_block_size):
    gate_declared = tokens.has_role("gate")
    state_intents = {}
    for semantic in ("planned", "actual", "forecast"):
        canonical = canonical_mark_semantic(semantic, "point", gate_declared=gate_declared)
        intent = content.style_intents.get(replace(key, semantic_id=canonical))
        if intent is not None:
            state_intents[semantic] = intent
    base_geometries = resolve_mark_geometries(tokens)
    base_allocation = resolve_mark_band(tokens, mark_block_size, role_geometries=base_geometries)
    frame = MarkBandFrame.zero_origin(None, mark_block_size, base_geometries, base_allocation)
    frame = resolve_occurrence_mark_frame(frame, tokens, state_intents)
    intent = state_intents.get(point_state)
    selected_role = intent.role if intent is not None else None
    geometries = frame.role_geometries
    geometry_role = mark_style_role(point_state)
    allocation = frame.allocation or resolve_mark_band(tokens, mark_block_size, role_geometries=geometries)
    offset, size = allocation.symbol_bounds(geometry_role)
    token = point_symbol_token(tokens, selected_role, point_state)
    geometry = geometries[geometry_role]
    radius = resolve_corner_radius(geometry.physical_corner_radius, width=size, height=size,
        legacy_radius=min(geometry.corner_radius * size, size / 2))
    outline = (rounded_diamond_path(inline=0.0, block=offset, inline_size=size,
        block_size=size, radius=radius)
        if radius > 0 and token.get("shape") == "diamond" else ())
    parts = symbol_parts(token, (0.0, offset, size, size), outline,
                         catalog_glyphs=getattr(tokens, "catalog_glyphs", None))
    paint_role = (selected_role if selected_role is not None else
                  resolve_point_paint_role(geometry_role,
                      gate_declared=point_state != "forecast" and tokens.has_role("gate")))
    if any(part.paint_mode == "fill" for part in parts):
        parts = complete_point_outline(parts, paint_role=paint_role, theme_tokens=tokens)
    return (selected_role, paint_role, parts, offset, size, token,
            radius / size if size else 0.0)


def encoding_legend_coverage(content, entry, *, painted=None):
    """Exact raw witnesses explained by this typed encoding key, including Other."""
    if entry.encoding_scale_id is None or not entry.swatch_visible or entry.swatch_shape == "rule-pair":
        return ()
    def owns_origin(witness):
        if entry.style_scope is not None:
            scope = entry.style_scope
            return any(source.kind == "style" and source.resource_id == scope.style_id
                       and source.rule_id == scope.rule_id for source in witness.sources)
        return any(source.kind == "view" for source in witness.sources)

    return tuple(dict.fromkeys(
        fill.encoding for occurrence in entry.style_occurrences
        if (painted is None or occurrence in painted)
        and (fill := content.style_fills.completed(occurrence)) is not None
        and fill.encoding.scale_id == entry.encoding_scale_id
        and owns_origin(fill.encoding)))


def _covered_point_encoding(content, key):
    fill = content.style_fills.completed(key)
    if fill is None:
        return None
    return next((fill.encoding for entry in content.legend_entries
                 if key in entry.style_occurrences
                 and fill.encoding in encoding_legend_coverage(content, entry)), None)


def _keys(content, tokens, capabilities, *, key, selected_role, parts,
          variance_classes=(), catalog=False, default_role="actual", family_id="actual", subject_id=None,
          glyph_footprint=None, point_state=None, point_geometry=None):
    role = selected_role or default_role
    result = []
    paints = []
    representative_paints = []
    covered_encoding = _covered_point_encoding(content, key) if point_state is not None else None
    neutralized = False
    for part in parts or (None,):
        mode = part.paint_mode if part is not None else None
        family = mark_paint_family(tokens, role, glyph_paint_mode=mode,
                                    has_completed_catalog_pattern=catalog)
        fill = choose_fill_override(
            style_fill=content.style_fills.get(key), legend_fill=None,
            actual_eligible=(point_state == "actual" if point_state is not None else
                             family_id == "actual" and selected_role is None and role == "actual")
                            and selected_role is None and family != PaintFamily.OUTLINE,
            actual_fill=dict(content.actual_variance_paints).get(key.subject_id if key else subject_id))
        paint = resolve_theme_paint_witness(
            tokens, role, family, fill_override=fill.color if fill is not None else None,
            gradient_supported=capabilities.gradient_supported,
            optional_gradient_omission=capabilities.optional_gradient_omission,
            part_mode=mode, part_color=part.paint_color if part is not None else None,
            catalog_pattern=catalog,
            catalog_glyph_stroke_width=part.stroke_width if part is not None and mode == "stroke" else None)
        paints.append(paint)
        if covered_encoding is not None and paint.channels.solid_override:
            representative_paints.append(resolve_theme_paint_witness(
                tokens, role, family,
                gradient_supported=capabilities.gradient_supported,
                optional_gradient_omission=capabilities.optional_gradient_omission,
                part_mode=mode, part_color=part.paint_color if part is not None else None,
                catalog_pattern=catalog,
                catalog_glyph_stroke_width=part.stroke_width if part is not None and mode == "stroke" else None))
            neutralized = True
        else:
            representative_paints.append(paint)
        channels = paint.effective_channels
        if channels.opacity == 0 or (channels.fill is None and channels.stroke is None):
            continue
        result.append(RealizedLegendKey(family_id, role, representative_paints[-1], (key,) if key else (), variance_classes,
                                       pattern_ink_identity(tokens, role, completed_catalog=catalog),
                                       point_state=point_state))
    if glyph_footprint is not None and result:
        # Keep the canonical normalized shape/outline and ordered paint, not
        # translated placement coordinates, resource IDs, or host bounds.
        glyph = RealizedGlyphInk(selected_role, point_geometry or (), tuple(representative_paints), glyph_footprint)
        witnesses = ((PointStateEncodingWitness(key, covered_encoding, tuple(paints)),)
                     if neutralized else ())
        return (replace(result[0], glyph=glyph,
                        point_state=point_state, encoding_witnesses=witnesses),)
    return tuple(result)


def source_actual_keys(content, tokens, *, mark_block_size, paint_capabilities):
    """Reserve potential ink using closed occurrence facts and shared mark geometry."""
    result = []
    for occurrence in content.legend_mark_occurrences:
        if occurrence.key.semantic_id != "actual" or occurrence.mark_shape == "point":
            continue
        key = occurrence.key
        intent = content.style_intents.get(key)
        selected_role = intent.role if intent is not None else None
        role = selected_role or "actual"
        parts = ()
        glyph_footprint = None
        pattern = tokens.optional_pattern(role)
        catalog = occurrence.mark_shape == "span" and isinstance(pattern, Mapping) and pattern.get("kind") == "catalog"
        classes = _actual_classes(occurrence)
        result.extend(_keys(content, tokens, paint_capabilities, key=key, selected_role=selected_role,
                            parts=parts, variance_classes=classes, catalog=catalog,
                            glyph_footprint=glyph_footprint))
    return tuple(result)


def actual_mark_keys(mark, content, tokens, paint_capabilities):
    """Resolve final parts by their closed source identity, never parsed placement IDs."""
    key = mark.source_occurrence_key or mark.style_occurrence_key
    if mark.semantic_id != "actual" or mark.mark_shape == "point":
        return ()
    source = next((item for item in content.legend_mark_occurrences if item.key == key), None)
    classes = _actual_classes(source)
    role = mark.theme_role or "actual"
    pattern = tokens.optional_pattern(role)
    catalog = mark.mark_shape == "span" and isinstance(pattern, Mapping) and pattern.get("kind") == "catalog"
    return _keys(content, tokens, paint_capabilities, key=key, selected_role=mark.theme_role,
                 parts=mark.symbol_parts, variance_classes=classes, catalog=catalog,
                 subject_id=mark.source_ref)


def source_point_keys(content, tokens, *, mark_block_size, paint_capabilities):
    """Measure potential point keys by semantic state and their declared Detail owner."""
    result = []
    for occurrence in content.legend_mark_occurrences:
        if occurrence.mark_shape != "point":
            continue
        key = occurrence.key
        state = _point_state_for_occurrence(key, tokens)
        if state is None:
            continue
        intent = content.style_intents.get(key)
        selected_role = intent.role if intent is not None else None
        owner = point_key_owner(content, state, selected_role)
        if owner is None:
            continue
        selected_role, paint_role, parts, offset, size, token, corner_fraction = _point_witness_parts(
            content, tokens, key, state, mark_block_size)
        # Point fills follow the actual semantic state, even where the selected
        # point paint is supplied by a shared planned/gate role.
        result.extend(_keys(content, tokens, paint_capabilities, key=key,
            selected_role=selected_role, parts=parts, default_role=paint_role,
            family_id=owner, subject_id=key.subject_id,
            glyph_footprint=(size, size), point_state=state,
            point_geometry=canonical_point_geometry(tokens, token, paint_role=paint_role,
                                                     corner_fraction=corner_fraction)))
    return tuple(result)


def point_mark_keys(mark, content, tokens, paint_capabilities):
    """Resolve final point ink against the exact source-state owner and glyph witness."""
    state = mark.semantic_id
    if mark.mark_shape != "point" or state not in {"planned", "actual", "forecast"}:
        return ()
    key = mark.source_occurrence_key or mark.style_occurrence_key
    source = next((item for item in content.legend_mark_occurrences if item.key == key), None)
    if source is None or source.mark_shape != "point":
        return ()
    selected_role = mark.theme_role
    owner = point_key_owner(content, state, selected_role)
    if owner is None:
        return ()
    parts = mark.symbol_parts
    token = point_symbol_token(tokens, selected_role, state)
    bounds = tuple(map(float, (mark.bounds.inline, mark.bounds.block,
                               mark.bounds.inline_size, mark.bounds.block_size)))
    corner_fraction = float(mark.corner_radius) / min(bounds[2], bounds[3]) if min(bounds[2:]) > 0 else 0.0
    paint_role = (selected_role if selected_role is not None else
                  resolve_point_paint_role(mark_style_role(state),
                      gate_declared=state != "forecast" and tokens.has_role("gate")))
    return _keys(content, tokens, paint_capabilities, key=key, selected_role=selected_role,
        parts=parts, default_role=paint_role, family_id=owner, subject_id=mark.source_ref,
        glyph_footprint=(bounds[2], bounds[3]), point_state=state,
        point_geometry=(mark.legend_geometry_identity or canonical_point_geometry(
            tokens, token, paint_role=paint_role, corner_fraction=corner_fraction)))


def mark_ink_keys(mark, content, tokens, paint_capabilities, *, base=False):
    """Compare a semantic base key with actual selected mark ink through one resolver."""
    key = None if base else mark.source_occurrence_key or mark.style_occurrence_key
    default_role = mark_style_role(mark.semantic_id)
    if mark.mark_shape == "point":
        default_role = resolve_point_paint_role(default_role,
            gate_declared=mark.semantic_id != "forecast" and tokens.has_role("gate"))
    selected = None if base else mark.theme_role
    role = selected or default_role
    pattern = tokens.optional_pattern(role)
    catalog = mark.mark_shape == "span" and isinstance(pattern, Mapping) and pattern.get("kind") == "catalog"
    parts = mark.symbol_parts
    if base and mark.mark_shape == "point":
        variant = "baseline" if mark.semantic_id in {"snapshot", "scenario"} else mark_style_role(mark.semantic_id)
        parts = complete_point_outline(symbol_parts(tokens.variant_symbol(variant),
            tuple(map(float, (mark.bounds.inline, mark.bounds.block, mark.bounds.inline_size, mark.bounds.block_size))),
            catalog_glyphs=getattr(tokens, "catalog_glyphs", None)), paint_role=role, theme_tokens=tokens)
    return _keys(content, tokens, paint_capabilities, key=key, selected_role=selected,
                 parts=parts, catalog=catalog, default_role=default_role,
                 family_id=mark.semantic_id, subject_id=mark.source_ref)


def progress_ink_key(tokens, paint_capabilities):
    """Progress uses its own complete Theme paint, not the host's paint.

    Both rectangular and contour-clipped progress placements retain all paint
    channels; a filled contour does not imply a fill-only paint restriction.
    """
    role = "progress-fill"
    pattern = tokens.optional_pattern(role)
    catalog = isinstance(pattern, Mapping) and pattern.get("kind") == "catalog"
    paint = resolve_theme_paint_witness(tokens, role, PaintFamily.SOLID, catalog_pattern=catalog,
        gradient_supported=paint_capabilities.gradient_supported,
        optional_gradient_omission=paint_capabilities.optional_gradient_omission)
    return RealizedLegendKey("progressFill", role, paint,
                            pattern_identity=pattern_ink_identity(tokens, role, completed_catalog=catalog))
