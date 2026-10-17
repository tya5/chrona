"""Canonical semantic identity for logical and realized mark facets."""
from __future__ import annotations

from chrona.presentation.model.point_paint import resolve_point_paint_role
from chrona.presentation.model.semantic_registry import SemanticBinding, semantic_binding, semantic_ids


def _mark_bindings() -> tuple[SemanticBinding, ...]:
    return tuple(binding for semantic_id in semantic_ids()
                 if (binding := semantic_binding(semantic_id)).primitive_kind == "mark")


def _logical_binding(logical_semantic: str) -> SemanticBinding:
    try:
        binding = semantic_binding(logical_semantic)
    except ValueError:
        # A few existing Layout callers name a Theme role rather than its
        # registered semantic (notably ``missing-actual``). Resolve that
        # spelling from the one vocabulary authority; never maintain aliases.
        matches = tuple(binding for binding in _mark_bindings()
                        if binding.theme_role == logical_semantic)
        if len(matches) == 1:
            return matches[0]
        # Preserve the established unknown-semantic failure for unknown and
        # ambiguous legacy spellings alike.
        return semantic_binding(logical_semantic)
    if binding.primitive_kind != "mark":
        raise ValueError(f"E_PRESENTATION_SEMANTIC_UNKNOWN:{logical_semantic}")
    return binding


def canonical_mark_semantic(logical_semantic: str, shape: str, *, gate_declared: bool) -> str:
    """Resolve a logical mark to its existing canonical mark binding.

    Point marks use the existing gate-paint substitution only where that
    substitution already applies. Forecast remains a distinct temporal
    semantic even though its default Theme paint role is ``planned``.
    """
    binding = _logical_binding(logical_semantic)
    if shape != "point" or binding.semantic_id == "forecast":
        return binding.semantic_id

    selected_role = resolve_point_paint_role(binding.scene_role, gate_declared=gate_declared)
    if selected_role == binding.scene_role:
        return binding.semantic_id
    canonical = _logical_binding(selected_role)
    if (canonical.scene_role == selected_role and canonical.purpose == binding.purpose
            and canonical.primitive_kind == binding.primitive_kind):
        return canonical.semantic_id
    raise ValueError(f"E_PRESENTATION_SEMANTIC_UNKNOWN:{logical_semantic}")
