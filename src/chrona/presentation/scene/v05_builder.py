"""Validated v0.5 Scene construction input boundary.

This module is intentionally renderer-neutral.  Primitive composition follows
in I27-R2; this seam ensures that it can only receive completed current inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from chrona.presentation.layout.model import LayoutManifest
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.model.theme_tokens import ThemeTokenView


class SceneBuildError(ValueError):
    """Stable diagnostic emitted before v0.5 primitive construction."""

    def __init__(self, diagnostic_id: str, path: str):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.path = path


@dataclass(frozen=True)
class SceneBuildInput:
    """Closed current-runtime inputs for one v0.5 Scene construction."""

    projection: Any
    surface_content: SurfaceContentInput
    layout_manifest: LayoutManifest
    theme_tokens: ThemeTokenView
    font_metrics: Any
    measured_sources: MeasuredSources
    capabilities: Mapping[str, bool]


_REQUIRED_SOURCES = frozenset(("title", "table", "timeline", "timeline-axis"))


def build_scene_input(*, projection: Any, surface_content: SurfaceContentInput,
                      layout_manifest: LayoutManifest, resolved_theme: Mapping[str, Any],
                      font_metrics: Any, measured_sources: MeasuredSources,
                      capabilities: Mapping[str, bool]) -> SceneBuildInput:
    """Bind validated v0.5 inputs without reopening authoring or legacy contracts."""
    if not isinstance(layout_manifest, LayoutManifest):
        raise SceneBuildError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    if not isinstance(measured_sources, MeasuredSources):
        raise SceneBuildError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    sources = {decision.source for decision in layout_manifest.decisions if decision.source}
    missing = sorted(_REQUIRED_SOURCES - sources)
    if missing:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_MISSING", "/layoutManifest/sources/" + missing[0])
    if not all(isinstance(name, str) and isinstance(enabled, bool) for name, enabled in capabilities.items()):
        raise SceneBuildError("E_PRESENTATION_CAPABILITY_SCHEMA", "/capabilities")
    return SceneBuildInput(projection, surface_content, layout_manifest,
                           ThemeTokenView(resolved_theme), font_metrics, measured_sources,
                           dict(capabilities))
