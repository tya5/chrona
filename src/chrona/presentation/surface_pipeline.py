"""Presentation coordination: closed intent -> completed Layout -> Scene projection."""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Mapping

from chrona.presentation.layout.canvas_viewport import DeclaredViewport
from chrona.presentation.layout.dependency_network import compose_dependency_network_surface
from chrona.presentation.layout.lane_subtracks import FixedLanePreflight
from chrona.presentation.layout.model import LayoutError, LayoutManifest
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.layout.surface_count_closure import CountReadInput, CountTrial, complete_surface_render_plan
from chrona.presentation.layout.surface_render_plan import PreparedSurfaceRenderPlan
from chrona.presentation.layout.surface_row_identity import complete_row_identity_warning
from chrona.presentation.layout.surface_preparation import SurfacePreRowGeometry
from chrona.presentation.layout.surface_quality import CapacitySourceEvidence, SurfaceLayoutRequest
from chrona.presentation.layout.temporal_capacity import TemporalInlineCapacity
from chrona.presentation.layout.relation_hint_model import PreviousRouteHints
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.render_progress import RenderProgress
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.scene.model import SceneSurface
from chrona.presentation.scene.v05_builder import SceneBuildError, SceneBuildInput, project_review_surface
from chrona.presentation.scene.visual_capabilities import VisualProfile, paint_witness_capabilities


@dataclass(frozen=True)
class PreparedSurfaceInput:
    """Validated surface intent before Layout completion; never passed to Scene."""

    projection: Any
    surface_content: SurfaceContentInput
    layout_manifest: LayoutManifest
    theme_tokens: ThemeTokenView
    font_metrics: Any
    measured_sources: MeasuredSources
    capabilities: Mapping[str, bool]
    visual_profile: VisualProfile | None = None
    viewport: tuple[float, float] = (0.0, 0.0)
    icon_assets: dict[str, Any] | None = None
    visual_requests: tuple[Any, ...] = ()
    fixed_lane_preflight: FixedLanePreflight | None = None
    capacity_short_sources: tuple[CapacitySourceEvidence, ...] = ()
    surface_preparation: SurfacePreRowGeometry | None = None
    declared_viewport: DeclaredViewport | None = None
    auto_block_limit: Decimal | None = None
    progress: RenderProgress | None = field(default=None, compare=False, repr=False)
    previous_route_hints: PreviousRouteHints | None = None


_REQUIRED_SOURCES = {
    "table-timeline": frozenset(("table", "timeline", "timeline-axis")),
    "dependency-network": frozenset(("network",)),
}


def build_surface_input(*, projection: Any, surface_content: SurfaceContentInput,
                      layout_manifest: LayoutManifest, resolved_theme: Mapping[str, Any],
                      font_metrics: Any, measured_sources: MeasuredSources,
                      capabilities: Mapping[str, bool],
                      visual_profile: VisualProfile | None = None,
                      viewport: tuple[float, float] = (0.0, 0.0),
                      icon_assets: dict[str, Any] | None = None,
                      visual_requests: tuple[Any, ...] = (),
                      fixed_lane_preflight: FixedLanePreflight | None = None,
                      capacity_short_sources: tuple[CapacitySourceEvidence, ...] = (),
                      surface_preparation: SurfacePreRowGeometry | None = None,
                      declared_viewport: DeclaredViewport | None = None,
                      auto_block_limit: Decimal | None = None,
                      progress: RenderProgress | None = None,
                      previous_route_hints: PreviousRouteHints | None = None) -> PreparedSurfaceInput:
    """Bind validated v0.5 inputs without reopening authoring or legacy contracts."""
    if not isinstance(layout_manifest, LayoutManifest):
        raise SceneBuildError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    if not isinstance(measured_sources, MeasuredSources):
        raise SceneBuildError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    surface = getattr(projection, "surface", "table-timeline")
    if surface not in _REQUIRED_SOURCES:
        raise SceneBuildError("E_PRESENTATION_SURFACE_UNSUPPORTED", "/projection/surface")
    required_sources = {decision.source for decision in layout_manifest.decisions
                        if decision.source and decision.priority in {None, "required"}}
    missing = sorted(_REQUIRED_SOURCES[surface] - required_sources)
    if missing:
        source = missing[0]
        raise SceneBuildError(
            "E_PRESENTATION_PRIMITIVE_MISSING", "/layoutManifest/sources/" + source,
            f"surface={surface}; missing source={source!r}; add this slot to a matching Layout Profile "
            "and select it with --layout <profile>")
    if surface == "dependency-network":
        table_sources = {"table", "timeline", "timeline-axis"}
        if required_sources & table_sources:
            raise SceneBuildError("E_PRESENTATION_SURFACE_SLOT_SET", "/layoutManifest/sources")
    if not all(isinstance(name, str) and isinstance(enabled, bool) for name, enabled in capabilities.items()):
        raise SceneBuildError("E_PRESENTATION_CAPABILITY_SCHEMA", "/capabilities")
    if fixed_lane_preflight is not None and not isinstance(fixed_lane_preflight, FixedLanePreflight):
        raise SceneBuildError("E_LAYOUT_LANE_PREFLIGHT_INVALID", "/layoutManifest")
    return PreparedSurfaceInput(projection, surface_content, layout_manifest,
                           ThemeTokenView(resolved_theme), font_metrics, measured_sources,
                           dict(capabilities), visual_profile, viewport, icon_assets, visual_requests,
                           fixed_lane_preflight, capacity_short_sources, surface_preparation, declared_viewport,
                           progress=progress, auto_block_limit=auto_block_limit,
                           previous_route_hints=previous_route_hints)


def compose_review_surface(value: PreparedSurfaceInput) -> SceneSurface:
    """Complete Layout once, then project accepted placements without layout replay."""
    surface = getattr(value.projection, "surface", "table-timeline")
    if surface == "table-timeline":
        placement = _complete_table_timeline(value)
    elif surface == "dependency-network":
        placement = _complete_network(value)
    else:
        raise SceneBuildError("E_PRESENTATION_SURFACE_UNSUPPORTED", "/projection/surface")
    completed = SceneBuildInput(value.projection, value.surface_content, value.layout_manifest,
        value.theme_tokens, value.capabilities, placement, value.visual_profile, value.viewport)
    return project_review_surface(completed)


@dataclass(frozen=True)
class SurfaceRenderResult:
    surface: SceneSurface
    plan: PreparedSurfaceRenderPlan
    projection: Any
    trials: tuple[CountTrial, ...]


def compose_resolved_review_surface(seed: CountReadInput, *, visual_profile: VisualProfile | None = None,
                                    initial: PreparedSurfaceRenderPlan | None = None,
                                    admitted: PreparedSurfaceInput | None = None) -> SurfaceRenderResult:
    """Project one accepted Layout completion; never measure or implement count trials here."""
    completed = complete_surface_render_plan(seed, initial=initial)
    plan, value = completed.plan, seed.value
    if admitted is None:
        admitted = build_surface_input(
            projection=completed.projection, surface_content=plan.content, layout_manifest=plan.manifest,
            resolved_theme=value.theme, font_metrics=value.font_metrics, measured_sources=plan.measured,
            capabilities=value.capabilities, visual_profile=visual_profile, viewport=plan.viewport,
            icon_assets=value.icon_assets, visual_requests=value.visual_requests,
            surface_preparation=plan.preparation,
            fixed_lane_preflight=(plan.preparation.inline.request.fixed_lane_preflight if plan.preparation else None),
            capacity_short_sources=plan.capacity_short_sources, declared_viewport=plan.declared_viewport,
            auto_block_limit=plan.profile.distances.get("/reviewSurface/maxBlockSize"), progress=value.progress,
            previous_route_hints=value.previous_route_hints)
    elif admitted.layout_manifest is not plan.manifest:
        raise ValueError("admitted ordinary plan does not match accepted completion")
    composition = completed.composition
    if completed.projection.surface == "table-timeline":
        composition = complete_row_identity_warning(
            composition, row_mode=value.view.rows.mode,
            has_table_columns=bool(value.view.table_columns),
            name_selected=bool({"title", "path"}.intersection(plan.content.label_content)))
    scene_input = SceneBuildInput(completed.projection, plan.content, plan.manifest,
        admitted.theme_tokens, admitted.capabilities, composition, visual_profile, plan.viewport)
    surface = project_review_surface(scene_input)
    return SurfaceRenderResult(surface, plan, completed.projection, completed.trials)


def _complete_table_timeline(value: PreparedSurfaceInput):
    projection = value.projection
    if not hasattr(projection, "items") or not hasattr(projection, "window"):
        raise SceneBuildError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection")
    metric = value.measured_sources.metric_values
    if "text.body.size" not in metric or "text.body.lineHeight" not in metric:
        raise SceneBuildError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues")
    try:
        request = (value.surface_preparation.inline.request if value.surface_preparation is not None
                   else SurfaceLayoutRequest(
            projection=projection, presentation_contract=normalize_presentation_input(value.surface_content),
            surface_content=value.surface_content, layout_manifest=value.layout_manifest,
            measured_sources=value.measured_sources, theme_tokens=value.theme_tokens,
            temporal_capacity=TemporalInlineCapacity.from_manifest(value.layout_manifest, value.measured_sources),
            font_metrics=value.font_metrics,
            capabilities=dict(value.capabilities), icon_assets=value.icon_assets or {},
            paint_capabilities=paint_witness_capabilities(value.visual_profile),
            visual_requests=value.visual_requests,
            fixed_lane_preflight=value.fixed_lane_preflight,
            capacity_short_sources=value.capacity_short_sources,
            declared_viewport=value.declared_viewport,
            auto_block_limit=value.auto_block_limit,
            progress=value.progress,
            previous_route_hints=value.previous_route_hints,
        ))
        composition = compose_surface_layout(request, prepared=value.surface_preparation)
    except LayoutError as error:
        raise SceneBuildError(error.diagnostic_id, error.path, error.detail) from error
    return composition


def _complete_network(value: PreparedSurfaceInput):
    projection = value.projection
    network = getattr(projection, "network", None)
    if network is None:
        raise SceneBuildError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/network")
    try:
        placed = compose_dependency_network_surface(SurfaceLayoutRequest(
            projection=projection, surface_content=value.surface_content,
            layout_manifest=value.layout_manifest, measured_sources=value.measured_sources,
            theme_tokens=value.theme_tokens, font_metrics=value.font_metrics,
            declared_viewport=value.declared_viewport, progress=value.progress,
            previous_route_hints=value.previous_route_hints))
    except LayoutError as error:
        raise SceneBuildError(error.diagnostic_id, error.path) from error
    return placed
