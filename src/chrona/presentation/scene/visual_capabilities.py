"""Closed target-profile policy evaluated outside renderer adapters."""
from __future__ import annotations

from dataclasses import dataclass

from chrona.presentation.scene.model import SceneSurface


BASELINE_PROFILE = "chrona-output/visual/v0.5-baseline"
SVG_PROFILE = "chrona-output/visual/v0.6-svg"
PNG_PROFILE = "chrona-output/visual/v0.6-png"
SVG_ICON_PROFILE = "chrona-output/visual/v0.7-svg"
PNG_ICON_PROFILE = "chrona-output/visual/v0.7-png"
LINEAR_GRADIENT = "paint.linear-gradient"
DROP_SHADOW = "effect.drop-shadow"
LINE_CAP = "stroke.line-cap"
LINE_JOIN = "stroke.line-join"
RICH_CAPABILITIES = frozenset((LINEAR_GRADIENT, DROP_SHADOW, LINE_CAP, LINE_JOIN))
ICON_VECTOR = "icon.vector"
ICON_RASTER = "icon.raster"

_MESSAGES = {
    "E_VISUAL_CAPABILITY_UNSUPPORTED": "required visual treatment is not supported by the selected visual profile",
    "E_VISUAL_CAPABILITY_PROFILE": "visual profile is not available for the selected target",
    "E_VISUAL_CAPABILITY_VALUE": "visual treatment binding is incomplete or malformed",
    "E_VISUAL_CAPABILITY_FIDELITY": "visual treatment fidelity must be required or decorative-optional",
    "E_VISUAL_CAPABILITY_LIMIT": "visual treatment value exceeds its declared limit",
}


class VisualCapabilityError(ValueError):
    """Stable failure raised before a renderer serializes an artifact."""

    def __init__(self, diagnostic_id: str, path: str = "/", message: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.path = path
        self.message = message or diagnostic_id


@dataclass(frozen=True)
class VisualProfile:
    identifier: str
    capabilities: frozenset[str]
    optional_omission: bool


def visual_capability_message(diagnostic_id: str, capability: str | None = None) -> str:
    """Return the public explanation for a closed visual-capability diagnostic."""
    if diagnostic_id == "E_VISUAL_CAPABILITY_UNSUPPORTED" and capability is not None:
        return f"required {capability} is not supported by the selected visual profile"
    return _MESSAGES.get(diagnostic_id, diagnostic_id)


def resolve_visual_profile(identifier: str, target_kind: str) -> VisualProfile:
    """Resolve one Context-selected profile and verify its target route."""
    if identifier == BASELINE_PROFILE:
        return VisualProfile(identifier, frozenset(), True)
    if identifier == SVG_PROFILE and target_kind == "svg":
        return VisualProfile(identifier, RICH_CAPABILITIES, False)
    if identifier == PNG_PROFILE and target_kind == "png":
        return VisualProfile(identifier, RICH_CAPABILITIES, False)
    if identifier == SVG_ICON_PROFILE and target_kind == "svg":
        return VisualProfile(identifier, RICH_CAPABILITIES | {ICON_VECTOR, ICON_RASTER}, False)
    if identifier == PNG_ICON_PROFILE and target_kind == "png":
        return VisualProfile(identifier, RICH_CAPABILITIES | {ICON_VECTOR, ICON_RASTER}, False)
    raise VisualCapabilityError("E_VISUAL_CAPABILITY_PROFILE", "/body/target/visualProfile",
                                f"{identifier} is not available for {target_kind}")


def validate_surface_visual_profile(surface: SceneSurface, profile: VisualProfile) -> None:
    """Reject a required completed treatment before adapter invocation."""
    paints = ((surface.canvas_paint, "/body/roles/background"),
              *((node.paint, node.visual_capability_source_ref) for node in surface.primitives))
    for paint, path in paints:
        if paint is None:
            continue
        _require(profile, LINEAR_GRADIENT, paint.gradient.fidelity if paint.gradient else None, path)
        _require(profile, DROP_SHADOW, paint.shadow.fidelity if paint.shadow else None, path)
        if paint.stroke_finish is not None:
            _require(profile, LINE_CAP, paint.stroke_finish.fidelity, path)
            _require(profile, LINE_JOIN, paint.stroke_finish.fidelity, path)
    for node in surface.primitives:
        if node.kind == "Icon":
            _require(profile, ICON_VECTOR if node.icon_kind == "vector" else ICON_RASTER, "required",
                     node.visual_capability_source_ref)


def _require(profile: VisualProfile, capability: str, fidelity: str | None, path: str) -> None:
    if fidelity is not None and capability not in profile.capabilities:
        raise VisualCapabilityError("E_VISUAL_CAPABILITY_UNSUPPORTED", path,
                                    visual_capability_message("E_VISUAL_CAPABILITY_UNSUPPORTED", capability))
