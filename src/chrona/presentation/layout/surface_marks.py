"""Owns Theme-to-Layout mark role geometry; reads declared Theme mark geometry only."""
from __future__ import annotations

from typing import Any

from chrona.presentation.layout.presentation import MarkGeometry

MARK_GEOMETRY_ROLES = ("planned", "actual", "snapshot", "scenario", "missing-actual")


def resolve_mark_geometries(theme_tokens: Any) -> dict[str, MarkGeometry]:
    """Close each Theme mark role to lane-relative Layout geometry."""
    result = {}
    for role in MARK_GEOMETRY_ROLES:
        height, offset, paint_order, corner_radius = theme_tokens.mark_geometry(role)
        result[role] = MarkGeometry(float(height), float(offset), paint_order, float(corner_radius))
    return result
