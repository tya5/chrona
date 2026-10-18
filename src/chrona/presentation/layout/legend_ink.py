"""Shared potential/completed Actual ink witnesses; no Scene or source evaluation."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from decimal import Decimal

from chrona.presentation.layout.mark_geometry import complete_point_outline, symbol_parts
from chrona.presentation.layout.mark_role_geometry import resolve_mark_band, resolve_mark_geometries
from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.pattern_placement import complete_pattern_placement
from chrona.presentation.model.legend_paint import RealizedLegendKey
from chrona.presentation.model.semantic_registry import mark_style_role
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


def _keys(content, tokens, capabilities, *, key, selected_role, parts,
          variance_classes=(), catalog=False, default_role="actual", family_id="actual", subject_id=None):
    role = selected_role or default_role
    result = []
    for part in parts or (None,):
        mode = part.paint_mode if part is not None else None
        family = mark_paint_family(tokens, role, glyph_paint_mode=mode,
                                    has_completed_catalog_pattern=catalog)
        fill = choose_fill_override(
            style_fill=content.style_fills.get(key), legend_fill=None,
            actual_eligible=family_id == "actual" and selected_role is None and role == "actual" and family != PaintFamily.OUTLINE,
            actual_fill=dict(content.actual_variance_paints).get(key.subject_id if key else subject_id))
        paint = resolve_theme_paint_witness(
            tokens, role, family, fill_override=fill,
            gradient_supported=capabilities.gradient_supported,
            optional_gradient_omission=capabilities.optional_gradient_omission,
            part_mode=mode, part_color=part.paint_color if part is not None else None,
            catalog_pattern=catalog,
            catalog_glyph_stroke_width=part.stroke_width if part is not None and mode == "stroke" else None)
        channels = paint.effective_channels
        if channels.opacity == 0 or (channels.fill is None and channels.stroke is None):
            continue
        result.append(RealizedLegendKey(family_id, role, paint, (key,) if key else (), variance_classes,
                                       pattern_ink_identity(tokens, role, completed_catalog=catalog)))
    return tuple(result)


def source_actual_keys(content, tokens, *, mark_block_size, paint_capabilities):
    """Reserve potential ink using closed occurrence facts and shared mark geometry."""
    result = []
    for occurrence in content.legend_mark_occurrences:
        if occurrence.key.semantic_id != "actual":
            continue
        key = occurrence.key
        intent = content.style_intents.get(key)
        selected_role = intent.role if intent is not None else None
        role = selected_role or "actual"
        parts = ()
        if occurrence.mark_shape == "point":
            selected = {"actual": selected_role} if selected_role is not None else {}
            for semantic in ("planned", "gate", "forecast"):
                planned = content.style_intents.get(replace(key, semantic_id=semantic))
                if planned is not None and planned.role is not None:
                    selected["planned"] = planned.role
            geometries = resolve_mark_geometries(tokens, theme_role_by_geometry_role=selected)
            size = resolve_mark_band(tokens, mark_block_size, role_geometries=geometries).symbol_bounds("actual")[1]
            token = tokens.symbol(role) if selected_role is not None else tokens.variant_symbol("actual")
            parts = complete_point_outline(symbol_parts(token, (0, 0, size, size),
                catalog_glyphs=getattr(tokens, "catalog_glyphs", None)), paint_role=role, theme_tokens=tokens)
        pattern = tokens.optional_pattern(role)
        catalog = occurrence.mark_shape == "span" and isinstance(pattern, Mapping) and pattern.get("kind") == "catalog"
        classes = _actual_classes(occurrence)
        result.extend(_keys(content, tokens, paint_capabilities, key=key, selected_role=selected_role,
                            parts=parts, variance_classes=classes, catalog=catalog))
    return tuple(result)


def actual_mark_keys(mark, content, tokens, paint_capabilities):
    """Resolve final parts by their closed source identity, never parsed placement IDs."""
    key = mark.source_occurrence_key or mark.style_occurrence_key
    if mark.semantic_id != "actual":
        return ()
    source = next((item for item in content.legend_mark_occurrences if item.key == key), None)
    classes = _actual_classes(source)
    role = mark.theme_role or "actual"
    pattern = tokens.optional_pattern(role)
    catalog = mark.mark_shape == "span" and isinstance(pattern, Mapping) and pattern.get("kind") == "catalog"
    return _keys(content, tokens, paint_capabilities, key=key, selected_role=mark.theme_role,
                 parts=mark.symbol_parts, variance_classes=classes, catalog=catalog, subject_id=mark.source_ref)


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
