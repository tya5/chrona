"""One-way resolution of Theme/Scheme policy into completed Scene paint."""
from __future__ import annotations

from enum import StrEnum
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

    def __init__(self, diagnostic_id: str, path: str):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.path = path


def resolve_scene_paint(tokens: ThemeTokenView, role: str, family: PaintFamily,
                        *, visual_capabilities: frozenset[str] | None = None,
                        optional_omission: bool = False) -> ScenePaint:
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
        gradient = _gradient(tokens, role, visual_capabilities, optional_omission)
        shadow = _shadow(tokens, role, visual_capabilities, optional_omission)
        finish = _stroke_finish(tokens, role, visual_capabilities, optional_omission)
    except ThemeTokenError as error:
        raise ScenePaintError(error.diagnostic_id, error.path) from error
    return ScenePaint(fill, stroke, float(width) if width is not None else None, dash,
                      1.0 if opacity is None else float(opacity), gradient, shadow, finish)


def _fidelity(tokens: ThemeTokenView, role: str, property_name: str) -> str:
    try:
        value = tokens.optional_token(role, property_name, "fidelity")
    except ThemeTokenError as error:
        raise ThemeTokenError("E_VISUAL_CAPABILITY_FIDELITY", error.path) from error
    if value is None: return "required"
    if value not in {"required", "decorative-optional"}:
        raise ThemeTokenError("E_VISUAL_CAPABILITY_FIDELITY", f"/body/roles/{role}/{property_name}")
    return str(value)


def _admit(capabilities: frozenset[str] | None, required: frozenset[str], fidelity: str,
           optional_omission: bool, path: str) -> bool:
    if capabilities is None or required.issubset(capabilities):
        return True
    if fidelity == "decorative-optional" and optional_omission:
        return False
    raise ThemeTokenError("E_VISUAL_CAPABILITY_UNSUPPORTED", path)


def _gradient(tokens: ThemeTokenView, role: str, capabilities: frozenset[str] | None,
              optional_omission: bool) -> LinearGradient | None:
    start, end = tokens.optional_color(role, "gradientStart"), tokens.optional_color(role, "gradientEnd")
    angle = tokens.optional_number(role, "gradientAngle")
    if start is None and end is None and angle is None: return None
    if start is None or end is None or angle is None:
        raise ThemeTokenError("E_VISUAL_CAPABILITY_VALUE", f"/body/roles/{role}/gradientAngle")
    if not 0 <= float(angle) < 360:
        raise ThemeTokenError("E_VISUAL_CAPABILITY_LIMIT", f"/body/roles/{role}/gradientAngle")
    fidelity = _fidelity(tokens, role, "gradientFidelity")
    if not _admit(capabilities, frozenset((LINEAR_GRADIENT,)), fidelity, optional_omission,
                  f"/body/roles/{role}/gradientAngle"):
        return None
    return LinearGradient(float(angle), ((0.0, start), (1.0, end)), fidelity)


def _shadow(tokens: ThemeTokenView, role: str, capabilities: frozenset[str] | None,
            optional_omission: bool) -> DropShadow | None:
    color = tokens.optional_color(role, "shadowColor")
    values = tuple(tokens.optional_number(role, name) for name in ("shadowOffsetX", "shadowOffsetY", "shadowBlur", "shadowOpacity"))
    if color is None and not any(value is not None for value in values): return None
    if color is None or any(value is None for value in values):
        raise ThemeTokenError("E_VISUAL_CAPABILITY_VALUE", f"/body/roles/{role}/shadowBlur")
    if float(values[2]) > 64:
        raise ThemeTokenError("E_VISUAL_CAPABILITY_LIMIT", f"/body/roles/{role}/shadowBlur")
    if not 0 <= float(values[3]) <= 1:
        raise ThemeTokenError("E_VISUAL_CAPABILITY_LIMIT", f"/body/roles/{role}/shadowOpacity")
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
        raise ThemeTokenError("E_VISUAL_CAPABILITY_VALUE", f"/body/roles/{role}/strokeLineCap")
    fidelity = _fidelity(tokens, role, "strokeFinishFidelity")
    if not _admit(capabilities, frozenset((LINE_CAP, LINE_JOIN)), fidelity, optional_omission,
                  f"/body/roles/{role}/strokeLineCap"):
        return None
    return StrokeFinish(str(cap), str(join), fidelity)
