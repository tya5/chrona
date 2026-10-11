"""Shared Theme role selection for point-mark paint (#1287)."""
from __future__ import annotations


def resolve_point_paint_role(role: str, *, gate_declared: bool, legend: bool = False) -> str:
    """Select the existing gate paint role where point and legend behavior already does so.

    A declared gate role substitutes for planned point marks and milestone
    legend swatches. The milestone key is a miniature of the chart's planned
    point, so without a gate role it takes the paint of `planned` (filled or
    hollow exactly as the planned milestones are, #499). Every other role
    retains its original name exactly.
    """
    if legend and role == "milestone":
        return "gate" if gate_declared else "planned"
    if gate_declared and not legend and role == "planned":
        return "gate"
    return role
