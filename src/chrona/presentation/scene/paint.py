"""Deterministic Theme-owned resolution for comparison facet paint."""
from __future__ import annotations

from typing import Any, Mapping


_GLOBAL_ROLE = {
    "planned": "planned",
    "actual": "actual",
    "baseline": "planned",
    "variance": "varianceBehind",
}


def resolve_facet_paint(theme: Mapping[str, object], group_id: str, facet: str) -> Mapping[str, object]:
    """Resolve group override, default facet paint, then the existing global role.

    The function consumes resolved Theme only; source IDs are data and never renderer
    branches.  It returns the concrete `{color, opacity}` paint for Scene/render use.
    """
    if facet not in _GLOBAL_ROLE:
        raise ValueError("E_PRESENTATION_FACET_UNKNOWN")
    facet_paints = theme.get("facetPaints", {})
    groups = facet_paints.get("groups", {}) if isinstance(facet_paints, Mapping) else {}
    override = groups.get(group_id, {}) if isinstance(groups, Mapping) else {}
    if isinstance(override, Mapping) and facet in override:
        return override[facet]
    default = facet_paints.get("default", {}) if isinstance(facet_paints, Mapping) else {}
    if isinstance(default, Mapping) and facet in default:
        return default[facet]
    paints = theme.get("paints", {})
    if not isinstance(paints, Mapping) or _GLOBAL_ROLE[facet] not in paints:
        raise ValueError("E_PRESENTATION_FACET_PAINT")
    return paints[_GLOBAL_ROLE[facet]]


def legacy_theme_colors(theme: Mapping[str, Any]) -> dict[str, str]:
    """Resolve the legacy v0.1 role palette without depending on review code."""
    return {
        "background": legacy_theme_color(theme, "background", "#faf8f6"),
        "text": legacy_theme_color(theme, "text", "#111827"),
        "grid": legacy_theme_color(theme, "axis-major", "#9ca3af"),
        "gridMinor": legacy_theme_color(theme, "axis-minor", "#e5e7eb"),
        "planned": legacy_theme_color(theme, "planned", "#2563eb"),
        "actual": legacy_theme_color(theme, "actual", "#16a34a"),
        "behind": legacy_theme_color(theme, "variance-behind", "#b45309"),
    }


def legacy_theme_color(theme: Mapping[str, Any], role: str, fallback: str) -> str:
    values = {key: str(value.get("value")) for key, value in theme.get("body", {}).get("values", {}).items()}
    binding = theme.get("body", {}).get("roles", {}).get(role, {})
    return values.get(binding.get("fill") or binding.get("stroke"), fallback)


def legacy_theme_font(theme: Mapping[str, Any]) -> str:
    values = {key: str(value.get("value")) for key, value in theme.get("body", {}).get("values", {}).items()}
    binding = theme.get("body", {}).get("roles", {}).get("text", {})
    return values.get(binding.get("fontFamily"), "Inter, Arial, sans-serif")
