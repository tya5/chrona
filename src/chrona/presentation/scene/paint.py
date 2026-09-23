"""One-way resolution of Theme/Scheme policy into completed Scene paint."""
from __future__ import annotations

from enum import StrEnum
from typing import Mapping

from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from chrona.presentation.scene.model import ScenePaint


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


def resolve_scene_paint(tokens: ThemeTokenView, role: str, family: PaintFamily) -> ScenePaint:
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
    if opacity is None:
        raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"{path}/opacity")
    if opacity < 0 or opacity > 1:
        raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", f"{path}/opacity")
    if fill is None and stroke is None:
        raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", path)
    return ScenePaint(fill, stroke, float(width) if width is not None else None, dash, float(opacity))
