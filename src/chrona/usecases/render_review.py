"""Render one immutable Render Context closure into a review surface.

This is the whole render use case: it owns the order of the pipeline —
closure, schedule, projection, content, measurement, layout, scene, render —
so that no adapter has to know it. A caller supplies an already-resolved
closure and receives an SVG or a stable diagnostic; nothing here reads
command-line arguments, writes files, or prints.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from chrona.core.diagnostics import Diagnostic
from chrona.core.ports import RenderArtifact, Renderer, Scheduler
from chrona.extensions.profiles import validate_profiles
from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.profile import resolve_layout_profile
from chrona.presentation.layout.sources import SourceInput, SourceTextRun, measure_sources
from chrona.presentation.model.closure import RenderClosure
from chrona.presentation.model.font_metrics import resolve_font_metrics
from chrona.presentation.model.color_scale import ColorScaleError, resolve_color_scale
from chrona.presentation.model.projection import build_review_projection
from chrona.presentation.model.surface_content import SummaryContent
from chrona.presentation.contracts.resources import ReviewDetailInput, ViewInput
from chrona.presentation.review.v05_content import normalize_summary_content, normalize_v05_surface_content
from chrona.presentation.scene.model import SceneSurface
from chrona.presentation.scene.v05_builder import SceneBuildError, build_scene_input, compose_review_surface
from chrona.presentation.scene.visual_capabilities import (
    VisualCapabilityError,
    resolve_visual_profile,
    validate_surface_visual_profile,
    visual_capability_message,
)
from chrona.presentation.renderers.registry import renderer_for
from chrona.core.scenarios import resolve_scenario, ScenarioError
from chrona.core.scenarios import ScenarioProvenance

# Consumed through ``context["resolvedTheme"]`` rather than through the closure
# accessor, so they are read by construction.
_IMPLICITLY_READ = frozenset({"color-scheme", "theme"})


class RenderRejected(Exception):
    """The closure is valid but its Project cannot be scheduled."""

    def __init__(self, diagnostics: list[Diagnostic], component: str = "core"):
        super().__init__(component)
        self.diagnostics = diagnostics
        self.component = component


class RenderFailed(Exception):
    """The render cannot proceed, reported as one stable diagnostic code."""

    def __init__(self, code: str, message: str, component: str, source_ref: str = "/"):
        super().__init__(code)
        self.code = code
        self.message = message
        self.component = component
        self.source_ref = source_ref


@dataclass(frozen=True)
class RenderRequest:
    """One resolved closure and the store it was read from."""

    closure: RenderClosure
    snapshot_root: Path
    scheduler: Scheduler
    renderer: Renderer
    require_all_inputs_read: bool = False
    asset_root: Path | None = None


@dataclass(frozen=True)
class RenderedReview:
    """The rendered surface and the closure inputs the render actually read."""

    artifact: RenderArtifact
    surface: SceneSurface
    read_inputs: frozenset[str] = field(default_factory=frozenset)
    scenario_provenance: tuple[ScenarioProvenance, ...] = ()


class ClosureReadLedger:
    """Records named typed-closure dependencies without generic kind lookup."""

    def __init__(self, closure: RenderClosure):
        self._declared = {item.kind for item in closure.resources}
        self.read: set[str] = set()

    def required(self) -> None:
        self.read.update({"project", "view", "layout-profile", "theme", "color-scheme"})

    def actual(self) -> None:
        self.read.add("actual-set")

    def snapshot(self) -> None:
        self.read.update({"snapshot-ref", "snapshot-project"})

    def detail(self) -> None:
        self.read.add("review-detail-profile")

    def summary(self) -> None:
        self.read.add("summary-profile")

    def packages(self) -> None:
        self.read.add("profile-package")

    def icons(self) -> None:
        self.read.add("icon-catalog")

    def unused(self) -> tuple[str, ...]:
        return tuple(sorted(self._declared - self.read - _IMPLICITLY_READ))


def render_review(request: RenderRequest) -> RenderedReview:
    """Render one closure, in the one order the pipeline has."""
    render_closure, ledger = request.closure, ClosureReadLedger(request.closure)
    project, view, layout = (render_closure.project.scheduler_input, render_closure.view.view,
                             render_closure.layout_profile.layout_input)
    theme = render_closure.resolved_theme.resolved_input
    try:
        visual_profile = resolve_visual_profile(render_closure.context.target.visual_profile,
                                                render_closure.context.target.kind)
    except VisualCapabilityError as error:
        raise RenderFailed(error.diagnostic_id, error.message, "presentation", error.path) from error
    ledger.required()
    manifests = {item.package_id: item.profile_input for item in render_closure.profile_packages}
    if manifests:
        ledger.packages()
    projection, scenario_provenance = _project_review(project, view, render_closure, manifests, request.scheduler)
    try:
        color_scale = resolve_color_scale(view.color_encoding, theme["body"].get("colorScales"),
                                          theme["body"].get("categorySlots"))
    except ColorScaleError as error:
        raise RenderFailed(str(error), str(error), "presentation") from error
    if render_closure.actual_set is not None:
        ledger.actual()
    if render_closure.snapshot is not None:
        ledger.snapshot()

    environment = render_closure.context.environment
    asset_root = request.asset_root or request.snapshot_root / render_closure.context.theme.revision_token
    font_metrics = _font_metrics(theme, environment.font_metrics, asset_root)
    summary = normalize_summary_content(render_closure.summary_profile.summary if render_closure.summary_profile else None,
                                        projection, render_closure.actual_set.observations_input if render_closure.actual_set else None,
                                        project)
    if render_closure.summary_profile is not None:
        ledger.summary()
    source_inputs = _source_inputs(project, view, projection, summary,
                                   render_closure.detail_profile.detail if render_closure.detail_profile else None)
    required_metrics = (("timeline.groupHeader.blockSize",)
                        if view.grouping is not None and view.grouping.presentation == "header" else ())
    measured = measure_sources(source_inputs, theme, font_metrics=font_metrics,
                               required_metrics=required_metrics)
    resolved_layout = resolve_layout_profile(layout, available_sources=set(source_inputs), theme=theme)
    viewport = {"inlineSize": environment.viewport_inline, "blockSize": environment.viewport_block}
    manifest = solve_layout(
        resolved_layout,
        viewport_inline=viewport["inlineSize"],
        viewport_block=viewport["blockSize"],
        measurements=_slot_measurements(resolved_layout.profile["root"], measured),
    )

    surface_content = normalize_v05_surface_content(
        projection, project, view,
        actual_set=render_closure.actual_set.observations_input if render_closure.actual_set else None,
        detail=render_closure.detail_profile.detail if render_closure.detail_profile else None,
        summary=summary,
        locale=environment.locale,
        color_scale=color_scale,
    )
    if render_closure.detail_profile is not None:
        ledger.detail()
    scene_input = build_scene_input(
        projection=projection, surface_content=surface_content, layout_manifest=manifest,
        resolved_theme=theme, font_metrics=font_metrics, measured_sources=measured,
        capabilities={name: True for name in render_closure.context.target.capabilities},
        locale=environment.locale,
        visual_profile=visual_profile,
        viewport=(float(viewport["inlineSize"]), float(viewport["blockSize"])),
        icon_bindings=(),
        icon_assets={item.icon_id: item for item in render_closure.icon_assets},
    )

    unused = ledger.unused()
    if request.require_all_inputs_read and unused:
        raise RenderFailed("E_CLOSURE_INPUT_UNUSED",
                           "closure inputs loaded but never read: " + ", ".join(unused), "closure")

    try:
        surface = compose_review_surface(scene_input)
    except SceneBuildError as error:
        raise RenderFailed(error.diagnostic_id, visual_capability_message(error.diagnostic_id),
                           "presentation", error.path) from error
    try:
        validate_surface_visual_profile(surface, visual_profile)
    except VisualCapabilityError as error:
        raise RenderFailed(error.diagnostic_id, error.message, "presentation", error.path) from error
    renderer = request.renderer or renderer_for(
        {"kind": render_closure.context.target.kind, "capabilities": list(render_closure.context.target.capabilities)},
        environment.renderer_environment(),
    )
    artifact = renderer.render(surface, viewport=(float(viewport["inlineSize"]), float(viewport["blockSize"])))
    if artifact.target_kind != render_closure.context.target.kind:
        raise RenderFailed("E_PRESENTATION_TARGET", "renderer target does not match Context target", "renderer")
    return RenderedReview(artifact, surface, frozenset(ledger.read), scenario_provenance)


def _project_review(project: dict[str, Any], view: ViewInput, closure: RenderClosure,
                    manifests: dict[str, dict[str, Any]], scheduler: Scheduler) -> Any:
    """Schedule the Project, and its Snapshot when one is bound, then project the review."""
    result = scheduler.schedule(project, extension_diagnostics=validate_profiles(project, manifests))
    if not result.ok:
        raise RenderRejected(result.diagnostics)
    actual = closure.actual_set.observations_input if closure.actual_set is not None else None
    snapshot_project = closure.snapshot_project.scheduler_input if closure.snapshot_project is not None else None
    snapshot_result = scheduler.schedule(snapshot_project) if snapshot_project is not None else None
    if snapshot_result is not None and not snapshot_result.ok:
        raise RenderRejected(snapshot_result.diagnostics)
    scenario_ids = ({view.comparison.scenario_id} if view.comparison.baseline == "scenario" else set())
    scenario_ids.update(item.scenario_id for row in view.rows.items for item in row.items if item.source_kind == "scenario")
    if None in scenario_ids:
        raise RenderFailed("E_SCENARIO_REQUIRED", "Scenario source requires a scenario id", "view")
    scenarios = {}
    provenance = []
    for scenario_id in sorted(scenario_ids):
        try:
            resolved = resolve_scenario(project, scenario_id)
            scenario_project = resolved.project
        except ScenarioError as error:
            raise RenderFailed(error.diagnostic.id, error.diagnostic.message, "scenario") from error
        scenario_result = scheduler.schedule(scenario_project)
        if not scenario_result.ok:
            raise RenderRejected(scenario_result.diagnostics)
        scenarios[scenario_id] = (scenario_project, scenario_result.placements)
        provenance.append(resolved.provenance)
    return build_review_projection(
        project, result.placements, view, actual,
        snapshot_project=snapshot_project,
        snapshot_placements=snapshot_result.placements if snapshot_result is not None else None,
        scenarios=scenarios,
        analysis=result.analysis,
        snapshot_analysis=snapshot_result.analysis if snapshot_result is not None else None,
    ), tuple(provenance)


def _font_metrics(theme: dict[str, Any], font_metrics: dict[str, Any], asset_root: Path) -> Any:
    body = theme["body"]
    family_token = body.get("roles", {}).get("text", {}).get("fontFamily")
    family = body.get("values", {}).get(family_token, {}).get("value")
    if not isinstance(family, str):
        raise RenderFailed("E_THEME_ROLE_REQUIRED", "text.fontFamily is required", "theme")
    return resolve_font_metrics(family, font_metrics, asset_root=asset_root)


def _source_inputs(project: dict[str, Any], view: ViewInput, projection: Any,
                   summary: SummaryContent, detail: ReviewDetailInput | None = None) -> dict[str, SourceInput]:
    """Declare what each slot will hold, for measurement before layout."""
    rows = projection.rows or ()
    row_count = len(rows) or len(projection.items)
    span_days = max(1, (projection.window[1] - projection.window[0]).days)
    network = getattr(projection, "network", None)
    notes = tuple(str(item.get("text", "")) for item in project.get("annotations", {}).values())
    legend = tuple(item.label for item in detail.legend) if detail is not None else ()
    return {
        "title": SourceInput((project["project"].get("title", "Chrona"),), typography_role="heading"),
        "table": SourceInput(
            tuple(row.label for row in rows) or tuple(item.title for item in projection.items),
            row_count, len(view.table_columns) or 1),
        "timeline": SourceInput(item_count=row_count, span_days=span_days),
        "timeline-axis": SourceInput(span_days=span_days, typography_role="axis"),
        "network": SourceInput(
            runs=tuple(SourceTextRun(node.title, "text", node.object_id)
                       for node in network.nodes) if network is not None else (),
            typography_role="text"),
        "summary": SourceInput(runs=tuple(SourceTextRun(run.content, run.typography_role) for run in summary.runs)),
        "legend": SourceInput(legend or ("legend",), typography_role="legend"),
        "group-details": SourceInput(("group details",)),
        "observations": SourceInput(("observations",)),
        "milestones": SourceInput(("milestones",)),
        "annotations": SourceInput(("annotations",), typography_role="annotation"),
        "notes": SourceInput(notes or ("notes",), typography_role="annotation"),
    }


def _slot_measurements(root: Mapping[str, Any], measured: Any) -> dict[str, Any]:
    measurements: dict[str, Any] = {}

    def bind(node: Mapping[str, Any]) -> None:
        if node["kind"] == "slot":
            measurements[node["id"]] = measured.measurements[node["source"]]
        for child in node.get("children", ()):
            bind(child)

    bind(root)
    return measurements
