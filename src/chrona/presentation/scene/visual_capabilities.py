"""Closed target-profile policy evaluated outside renderer adapters."""
from __future__ import annotations

from dataclasses import dataclass

from chrona.presentation.scene.model import SceneSurface


BASELINE_PROFILE = "chrona-output/visual/v0.5-baseline"
RICH_PROFILE = "chrona-output/visual/v0.6"
LINEAR_GRADIENT = "paint.linear-gradient"
DROP_SHADOW = "effect.drop-shadow"
LINE_CAP = "stroke.line-cap"
LINE_JOIN = "stroke.line-join"
RICH_CAPABILITIES = frozenset((LINEAR_GRADIENT, DROP_SHADOW, LINE_CAP, LINE_JOIN))


class VisualCapabilityError(ValueError):
    """Stable failure raised before a renderer serializes an artifact."""

    def __init__(self, diagnostic_id: str):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id


@dataclass(frozen=True)
class VisualProfile:
    identifier: str
    capabilities: frozenset[str]
    optional_omission: bool


def resolve_visual_profile(identifier: str, target_kind: str) -> VisualProfile:
    """Resolve one Context-selected profile and verify its target route."""
    if identifier == BASELINE_PROFILE:
        return VisualProfile(identifier, frozenset(), True)
    if identifier == RICH_PROFILE and target_kind in {"svg", "png", "pdf"}:
        return VisualProfile(identifier, RICH_CAPABILITIES, False)
    raise VisualCapabilityError("E_VISUAL_CAPABILITY_PROFILE")


def validate_surface_visual_profile(surface: SceneSurface, profile: VisualProfile) -> None:
    """Reject a required completed treatment before adapter invocation."""
    paints = (surface.canvas_paint, *(node.paint for node in surface.primitives))
    for paint in paints:
        if paint is None:
            continue
        _require(profile, LINEAR_GRADIENT, paint.gradient.fidelity if paint.gradient else None)
        _require(profile, DROP_SHADOW, paint.shadow.fidelity if paint.shadow else None)
        if paint.stroke_finish is not None:
            _require(profile, LINE_CAP, paint.stroke_finish.fidelity)
            _require(profile, LINE_JOIN, paint.stroke_finish.fidelity)


def _require(profile: VisualProfile, capability: str, fidelity: str | None) -> None:
    if fidelity is not None and capability not in profile.capabilities:
        raise VisualCapabilityError("E_VISUAL_CAPABILITY_UNSUPPORTED")
