"""Shared Theme role selection for point-mark paint (#1287)."""
from __future__ import annotations


def resolve_point_paint_role(role: str, *, gate_declared: bool, legend: bool = False) -> str:
    """Select the existing gate paint role where point and legend behavior already does so.

    A declared gate role substitutes for planned point marks and milestone
    legend swatches. Every other role, and both cases without a gate role,
    retain their original name exactly.
    """
    if gate_declared and ((legend and role == "milestone") or (not legend and role == "planned")):
        return "gate"
    return role
