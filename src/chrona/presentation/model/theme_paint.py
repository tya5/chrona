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


@dataclass(frozen=True)
class GradientPaintIntent:
    """Geometry-free identity and admission for one Theme linear gradient."""

    start: str
    end: str
    angle: Decimal
    fidelity: str
    admitted: bool

    @property
    def identity(self) -> tuple[str, str, Decimal, str]:
        return self.start, self.end, self.angle, self.fidelity


@dataclass(frozen=True)
class ThemePaintWitness:
    """Shared key-relevant Theme ink after channel precedence and gradient admission."""

    channels: ThemePaintInputs
    effective_channels: ThemePaintInputs
    gradient: GradientPaintIntent | None

    @property
    def identity(self) -> tuple[object, ...]:
        """Effective emitted ink identity; an omitted gradient is not paint."""
        channels = self.effective_channels
        gradient = self.gradient.identity if self.gradient is not None and self.gradient.admitted else None
        return (channels.fill, channels.stroke, channels.stroke_width, channels.dash,
                channels.opacity, gradient)


def choose_fill_override(*, style_fill: str | None, legend_fill: str | None,
                         actual_eligible: bool, actual_fill: str | None) -> str | None:
    """Preserve Scene precedence: declared legend ink, then Style, then eligible Actual."""
    if legend_fill is not None:
        return legend_fill
    if style_fill is not None:
        return style_fill
    return actual_fill if actual_eligible else None


def _effective_channels(channels: ThemePaintInputs, family: PaintFamily, role: str,
                        part_mode: str | None, part_color: str | None,
                        catalog_glyph_stroke_width: float | None) -> ThemePaintInputs:
    path = f"/body/roles/{role}"
    effective = channels
    if family == PaintFamily.OUTLINE and not channels.solid_override:
        effective = ThemePaintInputs(None, channels.stroke, channels.stroke_width,
                                     channels.dash, channels.opacity, False)
    if part_mode is None:
        return effective
    if part_mode not in {"fill", "stroke"}:
        raise ThemePaintError("E_PRESENTATION_PAINT_INVALID", path)
    if family == PaintFamily.OUTLINE:
        return ThemePaintInputs(None, channels.stroke, channels.stroke_width,
                                channels.dash, channels.opacity, False)
    if part_mode == "fill":
        part_fill = part_color if part_color is not None else channels.fill
        if part_fill is None:
            raise ThemePaintError("E_THEME_ROLE_REQUIRED", f"{path}/fill")
        return ThemePaintInputs(part_fill, None, None, (), channels.opacity, False)
    part_stroke = part_color if part_color is not None else channels.stroke
    part_width = (catalog_glyph_stroke_width if catalog_glyph_stroke_width is not None
                  else channels.stroke_width)
    if part_stroke is None or part_width is None:
        missing = "stroke" if part_stroke is None else "strokeWidth"
        raise ThemePaintError("E_THEME_ROLE_REQUIRED", f"{path}/{missing}")
    return ThemePaintInputs(None, part_stroke, Decimal(str(part_width)), (), channels.opacity, False)


@dataclass(frozen=True)
class LegendShapeInk:
    """The finite fill/stroke projection borrowed by a legend key shape."""

    fill: str | None
    stroke: str | None
    stroke_width: Decimal | None
    opacity: Decimal


def resolve_theme_paint_witness(
    tokens: ThemeTokenView,
    role: str,
    family: PaintFamily,
    *,
    gradient_supported: bool = True,
    optional_gradient_omission: bool = False,
    fill_override: str | None = None,
    part_mode: str | None = None,
    part_color: str | None = None,
    catalog_pattern: bool = False,
    ink_only_pattern: bool = False,
    pattern_has_substrate: bool = False,
    catalog_glyph_stroke_width: float | None = None,
) -> ThemePaintWitness:
    """Resolve the shared key-relevant ink without importing Scene/profile types.

    Scene still owns bounds-dependent gradient construction, effects and completed
    ``ScenePaint`` assembly. Layout can consume this same witness with the selected
    profile's neutral gradient admission flags.
    """
    channels = resolve_theme_paint_inputs(
        tokens, role, family, fill_override=fill_override, part_mode=part_mode,
        part_color=part_color, catalog_pattern=catalog_pattern,
        ink_only_pattern=ink_only_pattern, pattern_has_substrate=pattern_has_substrate,
        catalog_glyph_stroke_width=catalog_glyph_stroke_width,
    )
    effective = _effective_channels(channels, family, role, part_mode, part_color,
                                    catalog_glyph_stroke_width)
    if channels.solid_override:
        return ThemePaintWitness(channels, effective, None)

    path = f"/body/roles/{role}"
    try:
        start = tokens.optional_color(role, "gradientStart")
        end = tokens.optional_color(role, "gradientEnd")
        angle = tokens.optional_number(role, "gradientAngle")
        if start is None and end is None and angle is None:
            return ThemePaintWitness(channels, effective, None)
        if start is None or end is None or angle is None:
            raise ThemePaintError(
                "E_VISUAL_CAPABILITY_VALUE", f"{path}/gradientAngle",
                "gradientStart, gradientEnd, and gradientAngle must be declared together",
            )
        if not 0 <= float(angle) < 360:
            raise ThemePaintError(
                "E_VISUAL_CAPABILITY_LIMIT", f"{path}/gradientAngle",
                f"gradientAngle {float(angle):g} must be in [0, 360)",
            )
        fidelity_value = tokens.optional_token(role, "gradientFidelity", "fidelity")
        fidelity = "required" if fidelity_value is None else str(fidelity_value)
        if fidelity not in {"required", "decorative-optional"}:
            raise ThemePaintError(
                "E_VISUAL_CAPABILITY_FIDELITY", f"{path}/gradientFidelity",
                f"gradientFidelity {fidelity!r} must be required or decorative-optional",
            )
    except ThemeTokenError as error:
        diagnostic = ("E_VISUAL_CAPABILITY_FIDELITY" if error.diagnostic_id == "E_THEME_TOKEN_TYPE"
                     and error.path.endswith("/gradientFidelity") else error.diagnostic_id)
        raise ThemePaintError(diagnostic, error.path) from error

    admitted = gradient_supported
    if not admitted and not (fidelity == "decorative-optional" and optional_gradient_omission):
        raise ThemePaintError("E_VISUAL_CAPABILITY_UNSUPPORTED", f"{path}/gradientAngle")
    return ThemePaintWitness(channels, effective, GradientPaintIntent(start, end, angle, fidelity, admitted))


def resolve_legend_shape_ink(tokens: ThemeTokenView, role: str, shape: str,
                             *, fill_override: str | None = None) -> LegendShapeInk:
    """Resolve only the finite ink channels used by circle and rule-pair keys."""
    try:
        opacity = tokens.optional_number(role, "opacity")
        if opacity is not None and not 0 <= opacity <= 1:
            raise ThemePaintError("E_PRESENTATION_PAINT_INVALID", f"/body/roles/{role}/opacity")
        if shape == "circle":
            fill = (fill_override if fill_override is not None else
                    tokens.optional_color(role, "fill") or tokens.optional_color(role, "stroke"))
            if fill is None:
                raise ThemePaintError("E_THEME_ROLE_REQUIRED", f"/body/roles/{role}/fill")
            return LegendShapeInk(fill, None, None, opacity if opacity is not None else Decimal(1))
        if shape == "rule-pair":
            stroke = fill_override if fill_override is not None else tokens.color(role, "stroke")
            width = tokens.number(role, "strokeWidth")
            if width <= 0:
                raise ThemePaintError("E_PRESENTATION_PAINT_INVALID", f"/body/roles/{role}/strokeWidth")
            return LegendShapeInk(None, stroke, width, opacity if opacity is not None else Decimal(1))
    except ThemeTokenError as error:
        raise ThemePaintError(error.diagnostic_id, error.path) from error
    raise ThemePaintError("E_PRESENTATION_PAINT_INVALID", f"/body/roles/{role}")


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
