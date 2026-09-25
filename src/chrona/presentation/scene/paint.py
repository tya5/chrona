"""One-way resolution of Theme/Scheme policy into completed Scene paint."""
from __future__ import annotations

from enum import StrEnum
from math import cos, radians, sin
from typing import Mapping

from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from chrona.presentation.scene.model import DropShadow, LinearGradient, ScenePaint, StrokeFinish
from chrona.presentation.scene.visual_capabilities import DROP_SHADOW, LINEAR_GRADIENT, LINE_CAP, LINE_JOIN


class PaintFamily(StrEnum):
    TEXT = "text"
    SOLID = "solid"
    OUTLINE = "outline"
    HATCH = "hatch"
    PATH = "path"
    CANVAS = "canvas"


class ScenePaintError(ValueError):
    """Stable pre-render failure for an incomplete completed paint."""

    def __init__(self, diagnostic_id: str, path: str, detail: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.path = path
        self.detail = detail


def resolve_scene_paint(tokens: ThemeTokenView, role: str, family: PaintFamily,
                        *, visual_capabilities: frozenset[str] | None = None,
                        optional_omission: bool = False,
                        gradient_bounds: tuple[float, float, float, float] | None = None) -> ScenePaint:
    """Resolve one closed role into renderer-neutral channels, without defaults."""
    fill_required = family in {PaintFamily.TEXT, PaintFamily.SOLID, PaintFamily.CANVAS}
    stroke_required = family in {PaintFamily.OUTLINE, PaintFamily.HATCH, PaintFamily.PATH}
    try:
        fill = tokens.optional_color(role, "fill")
        stroke = tokens.optional_color(role, "stroke")
        width = tokens.optional_number(role, "strokeWidth")
        binding = tokens._body["roles"].get(role)
        dash = tokens.dash(role) if isinstance(binding, Mapping) and "dash" in binding else ()
        opacity = tokens.optional_number(role, "opacity")
    except ThemeTokenError as error:
        raise ScenePaintError(error.diagnostic_id, error.path) from error
    path = f"/body/roles/{role}"
    if fill_required and fill is None:
        raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"{path}/fill")
    if stroke_required and stroke is None:
        raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"{path}/stroke")
    if stroke is None and (width is not None or dash):
        raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", path)
    if stroke is not None and width is None:
        raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"{path}/strokeWidth")
    if width is not None and width <= 0:
        raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", f"{path}/strokeWidth")
    if opacity is not None and (opacity < 0 or opacity > 1):
        raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", f"{path}/opacity")
    if fill is None and stroke is None:
        raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", path)
    try:
        gradient = _gradient(tokens, role, visual_capabilities, optional_omission, gradient_bounds)
        shadow = _shadow(tokens, role, visual_capabilities, optional_omission)
        finish = _stroke_finish(tokens, role, visual_capabilities, optional_omission)
    except ThemeTokenError as error:
        raise ScenePaintError(error.diagnostic_id, error.path) from error
    if family == PaintFamily.OUTLINE:
        fill = None
    return ScenePaint(fill, stroke, float(width) if width is not None else None, dash,
                      1.0 if opacity is None else float(opacity), gradient, shadow, finish)


def _fidelity(tokens: ThemeTokenView, role: str, property_name: str) -> str:
    try:
        value = tokens.optional_token(role, property_name, "fidelity")
    except ThemeTokenError as error:
        raise ThemeTokenError("E_VISUAL_CAPABILITY_FIDELITY", error.path) from error
    if value is None: return "required"
    if value not in {"required", "decorative-optional"}:
        raise ScenePaintError("E_VISUAL_CAPABILITY_FIDELITY", f"/body/roles/{role}/{property_name}",
                              f"{property_name} {value!r} must be required or decorative-optional")
    return str(value)


def _admit(capabilities: frozenset[str] | None, required: frozenset[str], fidelity: str,
           optional_omission: bool, path: str) -> bool:
    if capabilities is None or required.issubset(capabilities):
        return True
    if fidelity == "decorative-optional" and optional_omission:
        return False
    raise ThemeTokenError("E_VISUAL_CAPABILITY_UNSUPPORTED", path)


def _gradient(tokens: ThemeTokenView, role: str, capabilities: frozenset[str] | None,
              optional_omission: bool, bounds: tuple[float, float, float, float] | None) -> LinearGradient | None:
    start, end = tokens.optional_color(role, "gradientStart"), tokens.optional_color(role, "gradientEnd")
    angle = tokens.optional_number(role, "gradientAngle")
    if start is None and end is None and angle is None: return None
    if start is None or end is None or angle is None:
        raise ScenePaintError("E_VISUAL_CAPABILITY_VALUE", f"/body/roles/{role}/gradientAngle",
                              "gradientStart, gradientEnd, and gradientAngle must be declared together")
    if not 0 <= float(angle) < 360:
        raise ScenePaintError("E_VISUAL_CAPABILITY_LIMIT", f"/body/roles/{role}/gradientAngle",
                              f"gradientAngle {float(angle):g} must be in [0, 360)")
    fidelity = _fidelity(tokens, role, "gradientFidelity")
    if not _admit(capabilities, frozenset((LINEAR_GRADIENT,)), fidelity, optional_omission,
                  f"/body/roles/{role}/gradientAngle"):
        return None
    if bounds is None:
        raise ScenePaintError("E_VISUAL_CAPABILITY_VALUE", f"/body/roles/{role}/gradientAngle",
                              "gradient bounds are required for a declared gradient")
    inline, block, inline_size, block_size = bounds
    centre = (inline + inline_size / 2, block + block_size / 2)
    direction = (cos(radians(float(angle))), sin(radians(float(angle))))
    extent = abs(inline_size / 2 * direction[0]) + abs(block_size / 2 * direction[1])
    coordinate = lambda value: 0.0 if abs(value) < 1e-12 else value
    endpoints = ((coordinate(centre[0] - direction[0] * extent), coordinate(centre[1] - direction[1] * extent)),
                 (coordinate(centre[0] + direction[0] * extent), coordinate(centre[1] + direction[1] * extent)))
    return LinearGradient(*endpoints, ((0.0, start), (1.0, end)), fidelity)


def _shadow(tokens: ThemeTokenView, role: str, capabilities: frozenset[str] | None,
            optional_omission: bool) -> DropShadow | None:
    color = tokens.optional_color(role, "shadowColor")
    values = tuple(tokens.optional_number(role, name) for name in ("shadowOffsetX", "shadowOffsetY", "shadowBlur", "shadowOpacity"))
    if color is None and not any(value is not None for value in values): return None
    if color is None or any(value is None for value in values):
        raise ScenePaintError("E_VISUAL_CAPABILITY_VALUE", f"/body/roles/{role}/shadowBlur",
                              "shadowColor, shadowOffsetX, shadowOffsetY, shadowBlur, and shadowOpacity must be declared together")
    if float(values[2]) > 64:
        raise ScenePaintError("E_VISUAL_CAPABILITY_LIMIT", f"/body/roles/{role}/shadowBlur",
                              f"shadowBlur {float(values[2]):g} exceeds 64")
    if not 0 <= float(values[3]) <= 1:
        raise ScenePaintError("E_VISUAL_CAPABILITY_LIMIT", f"/body/roles/{role}/shadowOpacity",
                              f"shadowOpacity {float(values[3]):g} must be in [0, 1]")
    fidelity = _fidelity(tokens, role, "shadowFidelity")
    if not _admit(capabilities, frozenset((DROP_SHADOW,)), fidelity, optional_omission,
                  f"/body/roles/{role}/shadowBlur"):
        return None
    return DropShadow(color, float(values[0]), float(values[1]), float(values[2]), float(values[3]), fidelity)


def _stroke_finish(tokens: ThemeTokenView, role: str, capabilities: frozenset[str] | None,
                   optional_omission: bool) -> StrokeFinish | None:
    cap = tokens.optional_token(role, "strokeLineCap", "lineCap")
    join = tokens.optional_token(role, "strokeLineJoin", "lineJoin")
    if cap is None and join is None: return None
    if cap not in {"butt", "round", "square"} or join not in {"miter", "round", "bevel"}:
        raise ScenePaintError("E_VISUAL_CAPABILITY_VALUE", f"/body/roles/{role}/strokeLineCap",
                              f"strokeLineCap {cap!r} and strokeLineJoin {join!r} must be declared values")
    fidelity = _fidelity(tokens, role, "strokeFinishFidelity")
    if not _admit(capabilities, frozenset((LINE_CAP, LINE_JOIN)), fidelity, optional_omission,
                  f"/body/roles/{role}/strokeLineCap"):
        return None
    return StrokeFinish(str(cap), str(join), fidelity)
