"""Finite Theme channel requirements shared before Scene paint completion."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView


class PaintFamily(StrEnum):
    TEXT = "text"
    SOLID = "solid"
    OUTLINE = "outline"
    HATCH = "hatch"
    PATH = "path"
    CANVAS = "canvas"


class ThemePaintError(ValueError):
    """A required Theme paint channel is absent or inconsistent."""

    def __init__(self, diagnostic_id: str, path: str, detail: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.path = path
        self.detail = detail


@dataclass(frozen=True)
class ThemePaintInputs:
    """Validated Theme channels that Scene needs to complete paint effects."""

    fill: str | None
    stroke: str | None
    stroke_width: Decimal | None
    dash: tuple[float, ...]
    opacity: Decimal | None
    solid_override: bool


def resolve_theme_paint_inputs(
    tokens: ThemeTokenView,
    role: str,
    family: PaintFamily,
    *,
    fill_override: str | None = None,
    part_mode: str | None = None,
    part_color: str | None = None,
    catalog_pattern: bool = False,
    ink_only_pattern: bool = False,
    pattern_has_substrate: bool = False,
    catalog_glyph_stroke_width: float | None = None,
) -> ThemePaintInputs:
    """Resolve and validate only the finite role channels required by a consumer.

    Scene owns effects, visual-profile admission, and ``ScenePaint`` assembly.
    This model-level boundary lets Layout validate the same required bindings
    before measuring a Style-selected Theme role without importing Scene.
    """
    fill_required = family in {PaintFamily.TEXT, PaintFamily.SOLID, PaintFamily.CANVAS} and not ink_only_pattern
    stroke_required = family in {PaintFamily.OUTLINE, PaintFamily.HATCH, PaintFamily.PATH}
    try:
        fill = tokens.optional_color(role, "fill")
        stroke = tokens.optional_color(role, "stroke")
        width = tokens.optional_number(role, "strokeWidth")
        binding = tokens._body["roles"].get(role)
        dash = tokens.dash(role) if isinstance(binding, Mapping) and "dash" in binding else ()
        opacity = tokens.optional_number(role, "opacity")
    except ThemeTokenError as error:
        # The Scene boundary historically keeps the diagnostic identity and
        # pointer, while omitting ThemeTokenError's explanatory detail here.
        raise ThemePaintError(error.diagnostic_id, error.path) from error

    solid_override = (fill_override is not None and part_color is None
                      and part_mode != "stroke"
                      and family != PaintFamily.PATH
                      and not (family == PaintFamily.OUTLINE and part_mode is not None))
    if solid_override:
        fill = fill_override
    path = f"/body/roles/{role}"
    if fill_required and fill is None:
        raise ThemePaintError("E_THEME_ROLE_REQUIRED", f"{path}/fill")
    if stroke_required and stroke is None:
        raise ThemePaintError("E_THEME_ROLE_REQUIRED", f"{path}/stroke")
    if stroke is None and (catalog_pattern or catalog_glyph_stroke_width is not None):
        raise ThemePaintError("E_THEME_ROLE_REQUIRED", f"{path}/stroke")
    if stroke is None and (width is not None or dash):
        raise ThemePaintError("E_PRESENTATION_PAINT_INVALID", path)
    if stroke is not None and width is None and not (catalog_pattern or catalog_glyph_stroke_width is not None
                                                    or part_mode == "fill"):
        raise ThemePaintError("E_THEME_ROLE_REQUIRED", f"{path}/strokeWidth")
    if ink_only_pattern and (not catalog_pattern or fill is not None):
        raise ThemePaintError("E_PRESENTATION_PAINT_INVALID", path)
    if ink_only_pattern and pattern_has_substrate:
        raise ThemePaintError("E_PRESENTATION_PAINT_INVALID", path,
                              "ink-only pattern cannot contain substrate operations")
    if catalog_pattern and fill is None and not ink_only_pattern:
        raise ThemePaintError("E_THEME_ROLE_REQUIRED", f"{path}/fill")
    if catalog_pattern and not ink_only_pattern and opacity not in (None, 1, 1.0):
        raise ThemePaintError("E_PRESENTATION_PAINT_INVALID", f"{path}/opacity")
    if width is not None and width <= 0:
        raise ThemePaintError("E_PRESENTATION_PAINT_INVALID", f"{path}/strokeWidth")
    if opacity is not None and (opacity < 0 or opacity > 1):
        raise ThemePaintError("E_PRESENTATION_PAINT_INVALID", f"{path}/opacity")
    if fill is None and stroke is None:
        raise ThemePaintError("E_PRESENTATION_PAINT_INVALID", path)

    return ThemePaintInputs(fill, stroke, width, dash, opacity, solid_override)


def mark_paint_family(tokens: ThemeTokenView, role: str, *,
                      glyph_paint_mode: str | None = None,
                      has_completed_catalog_pattern: bool = False) -> PaintFamily:
    """Classify the shared mark-role pattern/part branch used by Layout and Scene.

    Shape/background/path dispatch remains with its owning caller.  A completed
    catalogue pattern is already geometry and makes its host a solid substrate;
    otherwise the Theme's inline outline/hatch treatment precedes glyph part
    paint mode, matching Scene's former mark branch.
    """
    if has_completed_catalog_pattern:
        return PaintFamily.SOLID
    pattern = tokens.optional_pattern(role)
    if pattern is not None:
        kind = pattern.get("kind") if isinstance(pattern, Mapping) else None
        if kind == "outline":
            return PaintFamily.OUTLINE
        if kind == "diagonal-hatch":
            return PaintFamily.HATCH
        if kind == "catalog":
            return PaintFamily.SOLID
        shown = repr(kind)
        if isinstance(kind, str) and len(kind) > 64:
            shown = repr(kind[:64] + "…")
        elif not isinstance(kind, (str, int, float, bool, type(None))):
            shown = f"<{type(kind).__name__}>"
        raise ThemePaintError(
            "E_THEME_TOKEN_TYPE", f"/body/roles/{role}/pattern",
            f"pattern.kind={shown}; expected one of ['diagonal-hatch', 'outline']",
        )
    if glyph_paint_mode == "stroke":
        return PaintFamily.PATH
    return PaintFamily.SOLID
