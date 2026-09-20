"""Deterministic Theme-owned resolution for comparison facet paint."""
from __future__ import annotations

from typing import Mapping


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
