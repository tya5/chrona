"""Theme-selected mark role geometry shared by Layout composition owners."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Any

from chrona.presentation.layout.mark_band_allocation import MarkBandAllocation, compose_mark_band
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.presentation import MarkBandFrame, MarkGeometry
from chrona.presentation.model.semantic_registry import mark_style_role
from chrona.presentation.model.style_rules import OccurrenceStyleIntent
from chrona.presentation.model.theme_tokens import ThemeTokenError


MARK_GEOMETRY_ROLES = ("planned", "actual", "snapshot", "scenario", "missing-actual")


def resolve_mark_geometries(
    theme_tokens: Any,
    *,
    theme_role_by_geometry_role: Mapping[str, str] | None = None,
) -> dict[str, MarkGeometry]:
    """Close canonical mark roles to lane-relative geometry from selected Theme roles."""
    def aligned_offset(height: float, alignment: str) -> float:
        return 0.0 if alignment == "start" else 1.0 - height if alignment == "end" else (1.0 - height) / 2

    selected_roles = dict(theme_role_by_geometry_role or {})
    result = {}
    actual_explicit_offset = False
    for role in MARK_GEOMETRY_ROLES:
        theme_role = selected_roles.get(role, role)
        height, offset, paint_order, corner_radius = theme_tokens.mark_geometry(theme_role)
        symbol_height, symbol_offset = theme_tokens.symbol_geometry(theme_role)
        if role == "actual":
            actual_explicit_offset = offset is not None
        alignment_reader = getattr(theme_tokens, "mark_alignment", None)
        alignment = alignment_reader(theme_role) if alignment_reader is not None else "center"
        completed_offset = float(offset) if offset is not None else aligned_offset(float(height), alignment)
        if offset is None:
            if symbol_height is None:
                symbol_height = (max(float(height), result["planned"].symbol_extent[1])
                                 if role == "actual" else height)
            if symbol_offset is None:
                symbol_offset = aligned_offset(float(symbol_height), alignment)
        result[role] = MarkGeometry(
            float(height), completed_offset, paint_order, float(corner_radius),
            None if symbol_height is None else float(symbol_height),
            None if symbol_offset is None else float(symbol_offset),
            physical_corner_radius=theme_tokens.optional_token(theme_role, "cornerRadius", "radius"))
    if actual_explicit_offset:
        result["actual"] = _default_actual_symbol(result["actual"], result["planned"])
    return result


def resolve_mark_band(theme_tokens: Any, track_size: float, *,
                      role_geometries: Mapping[str, MarkGeometry] | None = None) -> MarkBandAllocation:
    """The shared closure for natural requirements, provisional and final marks."""
    stack_reader = getattr(theme_tokens, "mark_stack", None)
    return compose_mark_band(track_size=track_size,
                             role_geometries=(role_geometries if role_geometries is not None
                                              else resolve_mark_geometries(theme_tokens)),
                             stack=stack_reader() if stack_reader is not None else None)


def _default_actual_symbol(actual: MarkGeometry, planned: MarkGeometry) -> MarkGeometry:
    """An actual gate is no smaller than the planned gate unless the Theme says otherwise (#1074)."""
    planned_offset, planned_height = planned.symbol_extent
    height = actual.symbol_height if actual.symbol_height is not None else max(actual.height, planned_height)
    offset = actual.symbol_offset
    if offset is None:
        if height <= actual.height:
            offset = actual.offset
        elif height == planned_height:
            offset = planned_offset
        else:
            offset = min(max(planned_offset + planned_height / 2 - height / 2, 0.0), 1.0 - height)
    return replace(actual, symbol_height=height, symbol_offset=offset)


def resolve_occurrence_mark_frame(
    frame: MarkBandFrame,
    theme_tokens: Any,
    style_intents: Mapping[str, OccurrenceStyleIntent] | None,
) -> MarkBandFrame:
    """Complete a fresh geometry/stack frame for this source occurrence's selected mark roles."""
    supported = {"planned", "forecast", "actual", "snapshot", "scenario", "missing-actual"}
    selected_roles: dict[str, str] = {}
    intents_by_role: dict[str, OccurrenceStyleIntent] = {}
    for semantic_id, intent in (style_intents or {}).items():
        if semantic_id not in supported or intent.role is None:
            continue
        geometry_role = mark_style_role(semantic_id)
        prior = selected_roles.get(geometry_role)
        if prior is not None and prior != intent.role:
            raise LayoutError(
                "E_STYLE_ROLE_INCOMPATIBLE", f"/body/roles/{intent.role}", intent.key.subject_id,
                f"ruleIds={','.join(intent.role_rule_ids)}; subject={intent.key!r}; "
                f"source={intent.key.subject_id!r}; canonicalGeometryRole={geometry_role!r}; "
                f"conflictingSelectedRole={prior!r}")
        selected_roles[geometry_role] = intent.role
        intents_by_role[intent.role] = intent
    if not selected_roles:
        return frame
    try:
        geometries = resolve_mark_geometries(theme_tokens, theme_role_by_geometry_role=selected_roles)
        allocation = resolve_mark_band(theme_tokens, frame.block_size, role_geometries=geometries)
    except ThemeTokenError as error:
        role = next((candidate for candidate in selected_roles.values()
                     if f"/roles/{candidate}/" in error.path or error.path.endswith(f"/roles/{candidate}")), None)
        intent = intents_by_role.get(role) if role is not None else None
        if intent is None:
            raise
        raise LayoutError(
            "E_STYLE_ROLE_INCOMPATIBLE", error.path, intent.key.subject_id,
            f"ruleIds={','.join(intent.role_rule_ids)}; subject={intent.key!r}; "
            f"source={intent.key.subject_id!r}; themeRole={role!r}; cause={error.diagnostic_id}; "
            f"detail={error.detail or ''}") from error
    return MarkBandFrame(frame.inline_scale, frame.block_origin, frame.block_size, geometries, allocation)


def selected_mark_style_intents(
    selection: Any,
    theme_tokens: Any,
    style_intents: Mapping[str, OccurrenceStyleIntent] | None,
) -> dict[str, OccurrenceStyleIntent]:
    """Join canonical evaluated semantics back to this selection's logical facets."""
    if not style_intents:
        return {}
    from chrona.presentation.model.mark_semantics import canonical_mark_semantic

    role_reader = getattr(theme_tokens, "has_role", None)
    gate_declared = bool(role_reader("gate")) if role_reader is not None else False
    selected: dict[str, OccurrenceStyleIntent] = {}
    for facet in selection.facets:
        canonical = canonical_mark_semantic(facet.semantic_id, facet.shape,
                                            gate_declared=gate_declared)
        intent = style_intents.get(canonical)
        if intent is not None:
            selected[facet.semantic_id] = intent
    return selected
