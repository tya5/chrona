"""Layout-owned completed geometry for independent above-content canvas treatments."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, DecimalException
from math import isfinite
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.pattern_placement import (
    PatternPlacement,
    complete_pattern_placement,
)
from chrona.presentation.layout.seeded_pattern import complete_seeded_pattern
from chrona.presentation.layout.surface_quality import SlotPlacement

CANVAS_OVERLAY_ROLE = "canvas-overlay"
CANVAS_OVERLAY_GRADIENT_ROLE = "canvas-overlay-gradient"
_RADIAL_PROPERTIES = (
    "radialCenterInline", "radialCenterBlock", "radialRadiusInline", "radialRadiusBlock", "radialInnerStop",
)


@dataclass(frozen=True)
class PatternOverlayPlacement:
    """One Layout-completed periodic ink overlay, with no resolved paint."""

    placement_id: str
    slot: SlotPlacement
    pattern: PatternPlacement


@dataclass(frozen=True)
class RadialOverlayPlacement:
    """One completed radial canvas field; Scene later supplies ink, alpha, and fidelity."""

    placement_id: str
    slot: SlotPlacement
    center: tuple[Decimal, Decimal]
    radii: tuple[Decimal, Decimal]
    stop_offsets: tuple[Decimal, ...]


@dataclass(frozen=True)
class CanvasOverlays:
    """Independent optional canvas overlays; their paint order belongs to Scene."""

    pattern: PatternOverlayPlacement | None = None
    radial: RadialOverlayPlacement | None = None


def complete_canvas_overlays(theme_tokens: Any, canvas: Rect) -> CanvasOverlays:
    """Complete the declared overlay geometries against the final canvas without allocating content."""
    has_role = getattr(theme_tokens, "has_role", None)
    if not callable(has_role):
        return CanvasOverlays()

    pattern = _pattern_overlay(theme_tokens, canvas) if has_role(CANVAS_OVERLAY_ROLE) else None
    radial = _radial_overlay(theme_tokens, canvas) if has_role(CANVAS_OVERLAY_GRADIENT_ROLE) else None
    return CanvasOverlays(pattern=pattern, radial=radial)


def _slot(role: str, canvas: Rect) -> SlotPlacement:
    return SlotPlacement(role, role, canvas)


def _pattern_overlay(theme_tokens: Any, canvas: Rect) -> PatternOverlayPlacement:
    pointer = f"/body/roles/{CANVAS_OVERLAY_ROLE}/pattern"
    value = theme_tokens.optional_pattern(CANVAS_OVERLAY_ROLE)
    if value is None:
        raise LayoutError("E_THEME_ROLE_REQUIRED", pointer)
    if not isinstance(value, Mapping):
        raise LayoutError("E_THEME_TOKEN_TYPE", pointer)
    kind = value.get("kind")
    if kind == "catalog":
        completed = complete_pattern_placement(value, canvas)
    elif kind == "seeded":
        completed = complete_seeded_pattern(value, canvas, pointer=pointer)
    else:
        raise LayoutError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", pointer)
    role_slot = _slot(CANVAS_OVERLAY_ROLE, canvas)
    return PatternOverlayPlacement(CANVAS_OVERLAY_ROLE, role_slot, completed)


def _radial_overlay(theme_tokens: Any, canvas: Rect) -> RadialOverlayPlacement:
    role = CANVAS_OVERLAY_GRADIENT_ROLE
    base = f"/body/roles/{role}"
    values: dict[str, Decimal] = {}
    for name in _RADIAL_PROPERTIES:
        raw = theme_tokens.optional_number(role, name)
        pointer = f"{base}/{name}"
        if raw is None:
            raise LayoutError("E_THEME_ROLE_REQUIRED", pointer)
        # ThemeTokenView's public contract returns Decimal. Do not silently
        # coerce test doubles or malformed callers (notably bool/string) into
        # geometry values here.
        if not isinstance(raw, Decimal):
            raise LayoutError("E_VISUAL_CAPABILITY_LIMIT", pointer)
        value = raw
        if not value.is_finite():
            raise LayoutError("E_VISUAL_CAPABILITY_LIMIT", pointer)
        values[name] = value

    for name in ("radialCenterInline", "radialCenterBlock"):
        if not Decimal(0) <= values[name] <= Decimal(1):
            raise LayoutError("E_VISUAL_CAPABILITY_LIMIT", f"{base}/{name}")
    for name in ("radialRadiusInline", "radialRadiusBlock"):
        if values[name] <= 0:
            raise LayoutError("E_VISUAL_CAPABILITY_LIMIT", f"{base}/{name}")
    inner = values["radialInnerStop"]
    if not Decimal(0) <= inner < Decimal(1):
        raise LayoutError("E_VISUAL_CAPABILITY_LIMIT", f"{base}/radialInnerStop")

    completed: dict[str, Decimal] = {}
    for name, operation in (
        ("radialCenterInline", lambda: canvas.inline + canvas.inline_size * values["radialCenterInline"]),
        ("radialCenterBlock", lambda: canvas.block + canvas.block_size * values["radialCenterBlock"]),
        ("radialRadiusInline", lambda: canvas.inline_size * values["radialRadiusInline"]),
        ("radialRadiusBlock", lambda: canvas.block_size * values["radialRadiusBlock"]),
    ):
        try:
            completed[name] = operation()
        except DecimalException as error:
            raise LayoutError("E_VISUAL_CAPABILITY_LIMIT", f"{base}/{name}") from error
    center = (completed["radialCenterInline"], completed["radialCenterBlock"])
    radii = (completed["radialRadiusInline"], completed["radialRadiusBlock"])
    for name, value in zip(("radialCenterInline", "radialCenterBlock"), center):
        if not _binary64_finite(value):
            raise LayoutError("E_VISUAL_CAPABILITY_LIMIT", f"{base}/{name}")
    for name, value in zip(("radialRadiusInline", "radialRadiusBlock"), radii):
        if not _binary64_finite(value) or float(value) <= 0:
            raise LayoutError("E_VISUAL_CAPABILITY_LIMIT", f"{base}/{name}")

    offsets = (Decimal(0), Decimal(1)) if inner == 0 else (Decimal(0), inner, Decimal(1))
    return RadialOverlayPlacement(role, _slot(role, canvas), center, radii, offsets)


def _binary64_finite(value: Decimal) -> bool:
    """Ensure completed Layout geometry remains serializable by Scene adapters."""
    try:
        return value.is_finite() and isfinite(float(value))
    except (OverflowError, ValueError):
        return False
