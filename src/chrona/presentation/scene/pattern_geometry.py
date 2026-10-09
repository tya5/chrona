"""Projection of Layout-completed pattern geometry into Scene values."""
from __future__ import annotations

from collections.abc import Mapping
from math import isfinite

from chrona.presentation.scene.model import PatternGeometry, PatternStroke
from chrona.presentation.layout.pattern_placement import PatternPlacement


def _brief(value: object) -> str:
    if isinstance(value, str):
        clipped = value[:64]
        return repr(clipped + ("…" if len(value) > len(clipped) else ""))
    if value is None or isinstance(value, (bool, int, float)):
        return repr(value)
    return f"<{type(value).__name__}>"


def _token_error(detail: str) -> ValueError:
    return ValueError(f"E_THEME_TOKEN_TYPE: {detail}")


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
            extras = sorted(str(key)[:48] for key in set(value) - {"kind"})[:8]
            raise _token_error(f"pattern.kind='outline' forbids extra fields; unexpected keys={extras!r}")
        return None
    inline, block, angle, width = (_number(value, name) for name in
                                   ("tileInlineSize", "tileBlockSize", "angle", "strokeWidth"))
    if inline <= 0 or block <= 0 or width <= 0 or not 0 <= angle < 360:
        raise _token_error(f"pattern geometry requires positive finite tileInlineSize={inline!r}, tileBlockSize={block!r}, strokeWidth={width!r} and angle in [0, 360); received angle={angle!r}")
    return PatternGeometry(inline, block, angle, (PatternStroke((0.0, 0.0), (0.0, block), width),))


def pattern_kind(value: Mapping[str, object]) -> str:
    return _choice(value, "kind", {"outline", "diagonal-hatch"})


def _choice(value: Mapping[str, object], name: str, choices: set[str]) -> str:
    result = value.get(name)
    if not isinstance(result, str) or result not in choices:
        raise _token_error(f"pattern.{name}={_brief(result)}; expected one of {sorted(choices)!r}")
    return result


def _number(value: Mapping[str, object], name: str) -> float:
    raw = value.get(name)
    if not isinstance(raw, (int, float)) or isinstance(raw, bool) or not isfinite(float(raw)):
        raise _token_error(f"pattern.{name}={_brief(raw)}; expected a finite number (booleans are not numeric tokens)")
    return float(raw)
