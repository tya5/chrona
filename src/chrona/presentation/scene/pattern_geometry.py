"""Projection of Layout-completed pattern geometry into Scene values."""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite

from chrona.presentation.scene.model import PatternGeometry, PatternStroke
from chrona.presentation.layout.pattern_placement import PatternPlacement


def project_pattern_placement(value: PatternPlacement) -> PatternGeometry:
    """Copy closed Layout facts; do not infer tile phase, clipping, or paint."""
    def bounds(rect: object) -> tuple[float, float, float, float]:
        return (float(rect.inline), float(rect.block),
                float(rect.inline_size), float(rect.block_size))

    return PatternGeometry(value.tile_inline_size, value.tile_block_size,
                           value.angle_degrees, density_basis_points=value.density_basis_points,
                           primitives=value.primitives, origin=value.origin,
                           region_bounds=bounds(value.region), clip_bounds=bounds(value.clip),
                           corner_radius=value.corner_radius)


def pattern_geometry(value: Mapping[str, object]) -> PatternGeometry | None:
    kind = _choice(value, "kind", {"outline", "diagonal-hatch"})
    if kind == "outline":
        if set(value) != {"kind"}:
            raise ValueError("E_THEME_TOKEN_TYPE")
        return None
    inline, block, angle, width = (_number(value, name) for name in
                                   ("tileInlineSize", "tileBlockSize", "angle", "strokeWidth"))
    if inline <= 0 or block <= 0 or width <= 0 or not 0 <= angle < 360:
        raise ValueError("E_THEME_TOKEN_TYPE")
    return PatternGeometry(inline, block, angle, (PatternStroke((0.0, 0.0), (0.0, block), width),))


def pattern_kind(value: Mapping[str, object]) -> str:
    return _choice(value, "kind", {"outline", "diagonal-hatch"})


def _choice(value: Mapping[str, object], name: str, choices: set[str]) -> str:
    result = value.get(name)
    if not isinstance(result, str) or result not in choices:
        raise ValueError("E_THEME_TOKEN_TYPE")
    return result


def _number(value: Mapping[str, object], name: str) -> float:
    raw = value.get(name)
    if not isinstance(raw, (int, float)) or isinstance(raw, bool) or not isfinite(float(raw)):
        raise ValueError("E_THEME_TOKEN_TYPE")
    return float(raw)
