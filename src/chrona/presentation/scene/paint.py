"""One-way resolution of Theme/Scheme policy into completed Scene paint."""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from math import cos, radians, sin
from typing import Mapping

from chrona.presentation.layout.canvas_overlays import RadialOverlayPlacement
from chrona.presentation.model.info_diagnostics import PaintOmission
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView
from chrona.presentation.scene.model import (
    DropShadow,
    Glow,
    LinearGradient,
    RadialGradient,
    RadialGradientStop,
    SceneIconPath,
    ScenePaint,
    StrokeFinish,
    StrokeWobble,
)
from chrona.presentation.scene.visual_capabilities import (
    DROP_SHADOW,
    GLOW,
    LINE_CAP,
    LINE_JOIN,
    LINEAR_GRADIENT,
    PATTERN_GEOMETRY,
    RADIAL_GRADIENT,
    WOBBLE,
    VisualProfile,
    first_supporting_visual_profile,
)


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


@dataclass(frozen=True)
class PaintResolution:
    paint: ScenePaint
    omissions: tuple[PaintOmission, ...] = ()


@dataclass(frozen=True)
class RadialOverlayResolution:
    paint: ScenePaint | None
    omissions: tuple[PaintOmission, ...] = ()


def resolve_scene_paint(tokens: ThemeTokenView, role: str, family: PaintFamily,
                        *, visual_profile: VisualProfile | None = None,
                        gradient_bounds: tuple[float, float, float, float] | None = None,
                        glow_extent: tuple[float, float, float, float] | None = None,
                        canvas_bounds: tuple[float, float, float, float] | None = None,
                        part_mode: str | None = None, part_color: str | None = None,
                        catalog_pattern: bool = False,
                        ink_only_pattern: bool = False,
                        pattern_has_substrate: bool = False,
                        catalog_glyph_stroke_width: float | None = None,
                        catalog_glyph_line_cap: str | None = None,
                        catalog_glyph_line_join: str | None = None) -> PaintResolution:
    """Resolve one closed role into renderer-neutral channels, without defaults."""
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
        raise ScenePaintError(error.diagnostic_id, error.path) from error
    path = f"/body/roles/{role}"
    if fill_required and fill is None:
        raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"{path}/fill")
    if stroke_required and stroke is None:
        raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"{path}/stroke")
    if stroke is None and (catalog_pattern or catalog_glyph_stroke_width is not None):
        raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"{path}/stroke")
    if stroke is None and (width is not None or dash):
        raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", path)
    if stroke is not None and width is None and not (catalog_pattern or catalog_glyph_stroke_width is not None
                                                    or part_mode == "fill"):
        raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"{path}/strokeWidth")
    if ink_only_pattern and (not catalog_pattern or fill is not None):
        raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", path)
    if ink_only_pattern and pattern_has_substrate:
        raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", path,
                              "ink-only pattern cannot contain substrate operations")
    if catalog_pattern and fill is None and not ink_only_pattern:
        raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"{path}/fill")
    if catalog_pattern and not ink_only_pattern and opacity not in (None, 1, 1.0):
        raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", f"{path}/opacity")
    if width is not None and width <= 0:
        raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", f"{path}/strokeWidth")
    if opacity is not None and (opacity < 0 or opacity > 1):
        raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", f"{path}/opacity")
    if fill is None and stroke is None:
        raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", path)
    try:
        gradient, gradient_omitted = _gradient(tokens, role, visual_profile, gradient_bounds)
        shadow, shadow_omitted = _shadow(tokens, role, visual_profile)
        glow, glow_omitted = _glow(tokens, role, visual_profile, glow_extent, canvas_bounds, shadow is not None or shadow_omitted)
        wobble, wobble_omitted = _wobble(tokens, role, visual_profile)
        finish, finish_omitted = _stroke_finish(tokens, role, visual_profile)
    except ThemeTokenError as error:
        raise ScenePaintError(error.diagnostic_id, error.path) from error
    if family == PaintFamily.OUTLINE:
        fill = None
    paint = ScenePaint(fill, stroke, float(width) if width is not None else None, dash,
                       1.0 if opacity is None else float(opacity), gradient, shadow, finish, glow=glow, wobble=wobble)
    if part_mode is not None:
        if part_mode not in {"fill", "stroke"}:
            raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", path)
        if family == PaintFamily.OUTLINE:
            paint = replace(paint, fill=None)
        elif part_mode == "fill":
            part_fill = part_color if part_color is not None else paint.fill
            if part_fill is None:
                raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"{path}/fill")
            paint = replace(paint, fill=part_fill, stroke=None, stroke_width=None, dash=())
        else:
            part_stroke = part_color if part_color is not None else paint.stroke
            part_width = (catalog_glyph_stroke_width if catalog_glyph_stroke_width is not None
                          else paint.stroke_width)
            if part_stroke is None or part_width is None:
                raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"{path}/stroke")
            paint = replace(paint, fill=None, stroke=part_stroke, stroke_width=part_width,
                            stroke_finish=(StrokeFinish(catalog_glyph_line_cap, catalog_glyph_line_join, "required")
                                           if catalog_glyph_line_cap is not None and catalog_glyph_line_join is not None
                                           else paint.stroke_finish))
    omissions = tuple(_omission(role, treatment, property_name, visual_profile, required)
                      for omitted, treatment, property_name, required in (
                          (gradient_omitted, "linear-gradient", "gradientAngle", frozenset((LINEAR_GRADIENT,))),
                          (shadow_omitted, "drop-shadow", "shadowBlur", frozenset((DROP_SHADOW,))),
                          (glow_omitted, "glow", "glowBlur", frozenset((GLOW,))),
                          (wobble_omitted, "wobble", "wobbleAmplitude", frozenset((WOBBLE,))),
                          (finish_omitted, "stroke-finish", "strokeLineCap", frozenset((LINE_CAP, LINE_JOIN))),
                      ) if omitted)
    return PaintResolution(paint, omissions)


AS_OF_CONE_ROLE = "as-of-cone"
ARTWORK_ROLE = "annotation-artwork"


@dataclass(frozen=True)
class ArtworkAdmission:
    """Whether the selected profile paints an annotation artwork, and the omission it reports when it does not (#848)."""

    admitted: bool
    omissions: tuple[PaintOmission, ...] = ()


def is_ink_only_surface_pattern(tokens: ThemeTokenView, role: str) -> bool:
    """Select only the explicitly declared surface-pattern contracts."""
    if role == "canvas-overlay":
        return True
    if role != "canvas-texture":
        return False
    binding = tokens._body["roles"].get(role, {})
    return isinstance(binding, Mapping) and binding.get("patternMode") == "ink-only"


def resolve_surface_pattern_admission(tokens: ThemeTokenView, role: str, *,
                                      visual_profile: VisualProfile | None) -> ArtworkAdmission:
    """Admit or omit the whole transparent pattern before adapter invocation."""
    required = frozenset((PATTERN_GEOMETRY,))
    try:
        fidelity = _fidelity(tokens, role, "textureFidelity")
        profile = visual_profile
        # The legacy capability belongs to baseline for every target; that
        # does not assert transparent tile serialization on Typst or TikZ.
        if profile is not None and profile.target_kind not in {"svg", "png"}:
            profile = replace(profile, capabilities=profile.capabilities - required)
        admitted = _admit(profile, required, fidelity, f"/body/roles/{role}/textureFidelity")
    except ThemeTokenError as error:
        raise ScenePaintError(error.diagnostic_id, error.path) from error
    if admitted:
        return ArtworkAdmission(True)
    return ArtworkAdmission(False, (_omission(role, role, "textureFidelity", visual_profile, required),))


def resolve_radial_overlay_paint(tokens: ThemeTokenView, placement: RadialOverlayPlacement, *,
                                  visual_profile: VisualProfile | None) -> RadialOverlayResolution:
    """Attach resolved ink to already completed Layout radial geometry."""
    role = "canvas-overlay-gradient"
    path = f"/body/roles/{role}"
    try:
        fill = tokens.optional_color(role, "fill")
        opacity = tokens.optional_number(role, "opacity")
        fidelity = _fidelity(tokens, role, "gradientFidelity")
        if fill is None:
            raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"{path}/fill")
        if opacity is not None and not 0 <= opacity <= 1:
            raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", f"{path}/opacity")
        required = frozenset((RADIAL_GRADIENT,))
        if not _admit(visual_profile, required, fidelity, f"{path}/gradientFidelity"):
            return RadialOverlayResolution(
                None,
                (_omission(role, role, "gradientFidelity", visual_profile, required),))
    except ThemeTokenError as error:
        raise ScenePaintError(error.diagnostic_id, error.path) from error
    gradient = RadialGradient(
        tuple(float(value) for value in placement.center),
        tuple(float(value) for value in placement.radii),
        tuple(RadialGradientStop(float(offset), fill, 1.0 if offset == 1 else 0.0)
              for offset in placement.stop_offsets), fidelity)
    return RadialOverlayResolution(ScenePaint(fill, None, None, (), 1.0 if opacity is None else float(opacity),
                                      radial_gradient=gradient))


def resolve_artwork_admission(tokens: ThemeTokenView, *, needs_finish: bool,
                              visual_profile: VisualProfile | None, role: str = ARTWORK_ROLE,
                              treatment: str = "annotation-artwork") -> ArtworkAdmission:
    """Decide whether the profile paints one completed artwork layer.

    A fill part needs only the symbol outline every profile admits. A stroke part carries a required line cap and
    join, so an artwork with one needs `stroke.line-cap` and `stroke.line-join`. Where the profile has neither, the
    role's `artworkFidelity` decides: `required` (the default) fails with `E_VISUAL_CAPABILITY_UNSUPPORTED`;
    `decorative-optional` omits the whole artwork (never a frame with its rods dropped) and reports one omission.
    The decision reads no geometry: the box and the text are exactly what they are with the artwork.
    """
    required = frozenset((LINE_CAP, LINE_JOIN))
    if not needs_finish or visual_profile is None or required.issubset(visual_profile.capabilities):
        return ArtworkAdmission(True)
    try:
        fidelity = _fidelity(tokens, role, "artworkFidelity")
        admitted = _admit(visual_profile, required, fidelity, f"/body/roles/{role}/artworkFidelity")
    except ThemeTokenError as error:
        raise ScenePaintError(error.diagnostic_id, error.path) from error
    if admitted:
        return ArtworkAdmission(True)
    return ArtworkAdmission(False, (_omission(role, treatment, "artworkFidelity",
                                              visual_profile, required),))


@dataclass(frozen=True)
class ConeResolution:
    """The completed paint of the as-of cone, or no paint when the profile omits the cone (#890)."""

    paint: ScenePaint | None
    omissions: tuple[PaintOmission, ...] = ()


def resolve_cone_paint(tokens: ThemeTokenView, role: str, *, visual_profile: VisualProfile | None,
                       bounds: tuple[float, float, float, float]) -> ConeResolution:
    """Complete the as-of cone's gradient from its polygon bounds: ink at the apex, transparent at the foot.

    The cone is gradient paint, so it needs ``paint.linear-gradient``. Where the selected profile
    cannot paint one, a ``decorative-optional`` cone is omitted whole (never a flat ink polygon) and
    reported; a ``required`` one fails before serialization. The strength is the role's ``opacity``;
    the fade is the gradient's own stop opacity, so the ground it lies on is never named here.
    """
    path = f"/body/roles/{role}"
    try:
        fill = tokens.optional_color(role, "fill")
        opacity = tokens.optional_number(role, "opacity")
        if fill is None:
            raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"{path}/fill")
        if opacity is not None and not 0 <= opacity <= 1:
            raise ScenePaintError("E_PRESENTATION_PAINT_INVALID", f"{path}/opacity")
        fidelity = _fidelity(tokens, role, "gradientFidelity")
        if not _admit(visual_profile, frozenset((LINEAR_GRADIENT,)), fidelity, f"{path}/coneSpread"):
            return ConeResolution(None, (_omission(role, "as-of-cone", "coneSpread", visual_profile,
                                                   frozenset((LINEAR_GRADIENT,))),))
    except ThemeTokenError as error:
        raise ScenePaintError(error.diagnostic_id, error.path) from error
    inline, block, inline_size, block_size = bounds
    centre = inline + inline_size / 2
    gradient = LinearGradient((centre, block), (centre, block + block_size), ((0.0, fill), (1.0, fill)), fidelity,
                              stop_opacities=(1.0, 0.0))
    return ConeResolution(ScenePaint(fill, None, None, (), 1.0 if opacity is None else float(opacity), gradient))


def complete_icon_path_paints(role_paint: ScenePaint, path_intents: tuple[object, ...],
                              role: str) -> tuple[SceneIconPath, ...]:
    """Convert Layout path paint modes into completed icon paints."""
    if role_paint.fill is None:
        raise ScenePaintError("E_THEME_ROLE_REQUIRED", f"/body/roles/{role}/fill")
    paths = []
    for path in path_intents:
        mode = getattr(path, "paint", None)
        if mode == "fill":
            paths.append(SceneIconPath(path.commands, role_paint.fill, None, None,
                                       opacity=role_paint.opacity))
        elif (mode == "stroke" and path.stroke_width is not None
              and path.line_cap in {"butt", "round", "square"}
              and path.line_join in {"miter", "round", "bevel"}):
            paths.append(SceneIconPath(path.commands, None, role_paint.fill, path.stroke_width,
                                       path.line_cap, path.line_join, role_paint.opacity))
        else:
            raise ScenePaintError("E_PRESENTATION_PRIMITIVE_INVALID", role)
    return tuple(paths)


def _omission(role: str, treatment: str, property_name: str, profile: VisualProfile | None,
              required: frozenset[str]) -> PaintOmission:
    if profile is None:
        raise AssertionError("an absent profile cannot omit a treatment")
    return PaintOmission(role, treatment, f"/body/roles/{role}/{property_name}", profile.identifier,
                         profile.target_kind, first_supporting_visual_profile(profile.target_kind, required))


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


def _admit(profile: VisualProfile | None, required: frozenset[str], fidelity: str, path: str) -> bool:
    if profile is None or required.issubset(profile.capabilities):
        return True
    if fidelity == "decorative-optional" and profile.optional_omission:
        return False
    raise ThemeTokenError("E_VISUAL_CAPABILITY_UNSUPPORTED", path)


def _gradient(tokens: ThemeTokenView, role: str, profile: VisualProfile | None,
              bounds: tuple[float, float, float, float] | None) -> tuple[LinearGradient | None, bool]:
    start, end = tokens.optional_color(role, "gradientStart"), tokens.optional_color(role, "gradientEnd")
    angle = tokens.optional_number(role, "gradientAngle")
    if start is None and end is None and angle is None: return None, False
    if start is None or end is None or angle is None:
        raise ScenePaintError("E_VISUAL_CAPABILITY_VALUE", f"/body/roles/{role}/gradientAngle",
                              "gradientStart, gradientEnd, and gradientAngle must be declared together")
    if not 0 <= float(angle) < 360:
        raise ScenePaintError("E_VISUAL_CAPABILITY_LIMIT", f"/body/roles/{role}/gradientAngle",
                              f"gradientAngle {float(angle):g} must be in [0, 360)")
    fidelity = _fidelity(tokens, role, "gradientFidelity")
    if not _admit(profile, frozenset((LINEAR_GRADIENT,)), fidelity,
                  f"/body/roles/{role}/gradientAngle"):
        return None, True
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
    return LinearGradient(*endpoints, ((0.0, start), (1.0, end)), fidelity), False


def _shadow(tokens: ThemeTokenView, role: str, profile: VisualProfile | None) -> tuple[DropShadow | None, bool]:
    color = tokens.optional_color(role, "shadowColor")
    values = tuple(tokens.optional_number(role, name) for name in ("shadowOffsetX", "shadowOffsetY", "shadowBlur", "shadowOpacity"))
    if color is None and not any(value is not None for value in values): return None, False
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
    if not _admit(profile, frozenset((DROP_SHADOW,)), fidelity,
                  f"/body/roles/{role}/shadowBlur"):
        return None, True
    return DropShadow(color, float(values[0]), float(values[1]), float(values[2]), float(values[3]), fidelity), False


def _glow(tokens: ThemeTokenView, role: str, profile: VisualProfile | None,
          extent: tuple[float, float, float, float] | None,
          canvas: tuple[float, float, float, float] | None,
          has_shadow: bool) -> tuple[Glow | None, bool]:
    color = tokens.optional_color(role, "glowColor")
    blur, opacity = tokens.optional_number(role, "glowBlur"), tokens.optional_number(role, "glowOpacity")
    if color is None and blur is None and opacity is None:
        return None, False
    pointer = f"/body/roles/{role}/glowBlur"
    if color is None or blur is None or opacity is None:
        raise ScenePaintError("E_VISUAL_CAPABILITY_VALUE", pointer,
                              "glowColor, glowBlur, and glowOpacity must be declared together")
    if has_shadow:
        raise ScenePaintError("E_VISUAL_CAPABILITY_VALUE", pointer,
                              "a role declares a shadow or a glow, not both")
    if not 0 < float(blur) <= 64:
        raise ScenePaintError("E_VISUAL_CAPABILITY_LIMIT", pointer, f"glowBlur {float(blur):g} must be in (0, 64]")
    if not 0 <= float(opacity) <= 1:
        raise ScenePaintError("E_VISUAL_CAPABILITY_LIMIT", f"/body/roles/{role}/glowOpacity",
                              f"glowOpacity {float(opacity):g} must be in [0, 1]")
    fidelity = _fidelity(tokens, role, "glowFidelity")
    if not _admit(profile, frozenset((GLOW,)), fidelity, pointer):
        return None, True
    if extent is None or canvas is None:
        raise ScenePaintError("E_VISUAL_CAPABILITY_VALUE", pointer, "glow extent and canvas are required for a declared glow")
    reach = 3 * float(blur)
    left, top = max(canvas[0], extent[0] - reach), max(canvas[1], extent[1] - reach)
    right = min(canvas[0] + canvas[2], extent[0] + extent[2] + reach)
    bottom = min(canvas[1] + canvas[3], extent[1] + extent[3] + reach)
    region = (left, top, max(0.0, right - left), max(0.0, bottom - top))
    return Glow(color, float(blur), float(opacity), fidelity, region), False


def _wobble(tokens: ThemeTokenView, role: str, profile: VisualProfile | None) -> tuple[StrokeWobble | None, bool]:
    """The declared parameters of a hand-wobble; Scene completes the outline from the primitive (#588)."""
    amplitude = tokens.optional_number(role, "wobbleAmplitude")
    wavelength = tokens.optional_number(role, "wobbleWavelength")
    seed = tokens.optional_number(role, "wobbleSeed")
    if amplitude is None and wavelength is None and seed is None:
        return None, False
    pointer = f"/body/roles/{role}/wobbleAmplitude"
    if amplitude is None or wavelength is None or seed is None:
        raise ScenePaintError("E_VISUAL_CAPABILITY_VALUE", pointer,
                              "wobbleAmplitude, wobbleWavelength, and wobbleSeed must be declared together")
    if not 0 < float(amplitude) <= 16:
        raise ScenePaintError("E_VISUAL_CAPABILITY_LIMIT", pointer,
                              f"wobbleAmplitude {float(amplitude):g} must be in (0, 16]")
    if not 4 <= float(wavelength) <= 1000:
        raise ScenePaintError("E_VISUAL_CAPABILITY_LIMIT", f"/body/roles/{role}/wobbleWavelength",
                              f"wobbleWavelength {float(wavelength):g} must be in [4, 1000]")
    if seed != seed.to_integral_value() or not 0 <= seed < 2 ** 32:
        raise ScenePaintError("E_VISUAL_CAPABILITY_LIMIT", f"/body/roles/{role}/wobbleSeed",
                              f"wobbleSeed {seed} must be an integer in [0, 2^32)")
    fidelity = _fidelity(tokens, role, "wobbleFidelity")
    if not _admit(profile, frozenset((WOBBLE,)), fidelity, pointer):
        return None, True
    return StrokeWobble(float(amplitude), float(wavelength), int(seed), fidelity), False


def _stroke_finish(tokens: ThemeTokenView, role: str, profile: VisualProfile | None) -> tuple[StrokeFinish | None, bool]:
    cap = tokens.optional_token(role, "strokeLineCap", "lineCap")
    join = tokens.optional_token(role, "strokeLineJoin", "lineJoin")
    if cap is None and join is None: return None, False
    if cap not in {"butt", "round", "square"} or join not in {"miter", "round", "bevel"}:
        raise ScenePaintError("E_VISUAL_CAPABILITY_VALUE", f"/body/roles/{role}/strokeLineCap",
                              f"strokeLineCap {cap!r} and strokeLineJoin {join!r} must be declared values")
    fidelity = _fidelity(tokens, role, "strokeFinishFidelity")
    if not _admit(profile, frozenset((LINE_CAP, LINE_JOIN)), fidelity,
                  f"/body/roles/{role}/strokeLineCap"):
        return None, True
    return StrokeFinish(str(cap), str(join), fidelity), False
