"""Render one immutable Render Context closure into a review surface.

This is the whole render use case: it owns the order of the pipeline —
closure, schedule, projection, content, measurement, layout, scene, render —
so that no adapter has to know it. A caller supplies an already-resolved
closure and receives an SVG or a stable diagnostic; nothing here reads
command-line arguments, writes files, or prints.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from decimal import Decimal
from importlib.metadata import version
from pathlib import Path
from typing import Any, Mapping
import re

from chrona.core.diagnostics import Diagnostic
from chrona.core.ports import RenderArtifact, Renderer, Scheduler
from chrona.extensions.profiles import validate_profiles
from chrona.presentation.layout.engine import resolve_draft_block_extent, solve_layout
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.profile import resolve_layout_profile
from chrona.presentation.layout.sources import SourceInput, SourceTextRun, measure_sources
from chrona.presentation.layout.surface_composer import resolve_label_visual_advances, resolve_mark_geometries, timeline_content_block_requirement
from chrona.presentation.layout.surface_quality import VisualRequest
from chrona.presentation.model.closure import ClosureError, RenderClosure
from chrona.presentation.model.font_metrics import FontGlyphSubstitution, FontMetricsError, resolve_font_metrics_catalog
from chrona.presentation.fonts.system import DraftFontResolution
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.model.color_scale import ColorScaleError, resolve_color_scale
from chrona.presentation.model.projection import build_review_projection
from chrona.presentation.model.surface_content import SummaryContent
from chrona.presentation.contracts.resources import ReviewDetailInput, ViewInput
from chrona.presentation.review.v05_content import normalize_summary_content, normalize_v05_surface_content
from chrona.presentation.scene.model import (
    ContentFamilyCounts, InspectionScene, SceneManifest, SceneProvenance,
    SceneSurface,
)
from chrona.presentation.scene.perceptibility import ScenePerceptibilityFinding, evaluate_scene_perceptibility
from chrona.presentation.scene.serialization import scene_document
from chrona.presentation.scene.v05_builder import SceneBuildError, build_scene_input, compose_review_surface
from chrona.presentation.scene.visual_capabilities import (
    VisualCapabilityError,
    resolve_visual_profile,
    validate_surface_visual_profile,
    visual_capability_message,
)
from chrona.presentation.renderers.registry import renderer_for
from chrona.storage.snapshot_paths import snapshot_directory
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
    renderer: Renderer | None = None
    require_all_inputs_read: bool = False
    asset_root: Path | None = None
    draft_auto_block: bool = False
    draft_font_resolution: DraftFontResolution | None = None


@dataclass(frozen=True)
class RenderedReview:
    """The rendered surface and the closure inputs the render actually read."""

    artifact: RenderArtifact
    surface: SceneSurface
    scene: InspectionScene
    read_inputs: frozenset[str] = field(default_factory=frozenset)
    scenario_provenance: tuple[ScenarioProvenance, ...] = ()
    font_warnings: tuple["FontGlyphWarning", ...] = ()
    perceptibility_warnings: tuple["ScenePerceptibilityWarning", ...] = ()


@dataclass(frozen=True)
class FontGlyphWarning:
    """One target-honest draft font substitution warning."""

    requested_family: str
    fallback_family: str
    weight: int
    codepoint: int
    text: str
    drawn: bool | None = None


@dataclass(frozen=True)
class ScenePerceptibilityWarning:
    """Draft-only transport of one error finding over the completed Scene."""

    code: str
    finding_code: str
    scene_path: str
    primitive_ids: tuple[str, ...]
    slot_id: str | None
    measured_facts: tuple[tuple[str, float | str], ...]
    disposition: str | None


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
    asset_root = request.asset_root or snapshot_directory(request.snapshot_root, render_closure.context.theme.revision_token)
    resolution = request.draft_font_resolution
    if resolution is not None and render_closure.context.identity.revision != "draft":
        raise RenderFailed("E_FONT_SYSTEM_IMMUTABLE", "system font resolution cannot render immutable Context", "presentation")
    if resolution is not None and render_closure.context.target.kind not in {"svg", "png"}:
        raise RenderFailed("E_FONT_SYSTEM_IMMUTABLE", "system font resolution cannot render this target", "presentation")
    font_metrics = resolution.metrics if resolution is not None else _font_metrics(theme, environment.font_metrics, asset_root)
    summary = normalize_summary_content(render_closure.summary_profile.summary if render_closure.summary_profile else None,
                                        projection, render_closure.actual_set.observations_input if render_closure.actual_set else None,
                                        project)
    if render_closure.summary_profile is not None:
        ledger.summary()
    icon_assets = {item.icon_id: item for item in render_closure.icon_assets}
    visual_requests = tuple(_visual_request(visual, projection, index, render_closure)
                            for index, visual in enumerate(render_closure.view.view.visuals))
    if visual_requests:
        ledger.icons()
    source_inputs = _source_inputs(project, view, projection, summary,
                                   render_closure.detail_profile.detail if render_closure.detail_profile else None,
                                   annotation_input=_annotation_source_input(
                                       view, visual_requests, icon_assets, theme),
                                   color_scale=color_scale)
    required_metrics = (("timeline.groupHeader.blockSize",)
                        if view.grouping is not None and view.grouping.presentation == "header" else ())
    try:
        measured = measure_sources(source_inputs, theme, font_metrics=font_metrics,
                                   required_metrics=required_metrics)
    except FontMetricsError as error:
        raise _font_failure(error) from error
    resolved_layout = resolve_layout_profile(layout, available_sources=set(source_inputs), theme=theme)
    viewport = {"inlineSize": environment.viewport_inline, "blockSize": environment.viewport_block}
    measurements = _slot_measurements(resolved_layout.profile["root"], measured)
    try:
        required_block = None
        if view.surface == "table-timeline":
            timeline_requirement = timeline_content_block_requirement(
                projection=projection,
                group_presentation=view.grouping.presentation if view.grouping and view.grouping.presentation else "band",
                metric_values=measured.metric_values,
                role_geometries=resolve_mark_geometries(ThemeTokenView(theme)),
            )
            required_block = resolve_draft_block_extent(
                resolved_layout, viewport_inline=viewport["inlineSize"],
                seed_block=viewport["blockSize"], measurements=measurements,
                required_blocks={"timeline": timeline_requirement},
            )
        if request.draft_auto_block:
            if required_block is None:
                raise LayoutError("E_LAYOUT_DRAFT_AUTO_UNSUPPORTED", "/projection/surface",
                                  detail=f"surface={view.surface}")
            viewport["blockSize"] = required_block
        manifest = solve_layout(
            resolved_layout, viewport_inline=viewport["inlineSize"],
            viewport_block=viewport["blockSize"], measurements=measurements,
        )
    except LayoutError as error:
        raise RenderFailed(error.diagnostic_id, error.detail or error.diagnostic_id,
                           "presentation", error.path) from error

    surface_content = normalize_v05_surface_content(
        projection, project, view,
        actual_set=render_closure.actual_set.observations_input if render_closure.actual_set else None,
        detail=render_closure.detail_profile.detail if render_closure.detail_profile else None,
        summary=summary,
        layout_manifest=manifest,
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
        icon_assets=icon_assets,
        visual_requests=visual_requests,
    )

    unused = ledger.unused()
    if request.require_all_inputs_read and unused:
        raise RenderFailed("E_CLOSURE_INPUT_UNUSED",
                           "closure inputs loaded but never read: " + ", ".join(unused), "closure")

    try:
        surface = compose_review_surface(scene_input)
    except SceneBuildError as error:
        detail = error.detail or visual_capability_message(error.diagnostic_id)
        if (error.diagnostic_id == "E_LAYOUT_REQUIRED_OVERFLOW"
                and render_closure.context.identity.revision != "draft"):
            detail = re.sub(r"use --viewport \d+x(\d+)",
                            r"set environment.viewport.blockSize to \1 and rematerialize the Context", detail)
            if "environment.viewport.blockSize" not in detail:
                detail += "; set environment.viewport.blockSize and rematerialize the Context"
        raise RenderFailed(error.diagnostic_id, detail,
                           "presentation", error.path) from error
    try:
        validate_surface_visual_profile(surface, visual_profile)
    except VisualCapabilityError as error:
        raise RenderFailed(error.diagnostic_id, error.message, "presentation", error.path) from error
    scene = _inspection_scene(render_closure, surface, projection, surface_content,
                              (surface.canvas_bounds[2], surface.canvas_bounds[3]))
    perceptibility_warnings = (_scene_perceptibility_warnings(scene)
                               if render_closure.context.identity.revision == "draft" else ())
    renderer = request.renderer or renderer_for(
        {"kind": render_closure.context.target.kind, "capabilities": list(render_closure.context.target.capabilities)},
        environment.renderer_environment(),
        asset_root=asset_root,
        font_files=resolution.font_files if resolution is not None else None,
    )
    try:
        artifact = renderer.render(surface)
    except FontMetricsError as error:
        raise _font_failure(error) from error
    if artifact.target_kind != render_closure.context.target.kind:
        raise RenderFailed("E_PRESENTATION_TARGET", "renderer target does not match Context target", "renderer")
    if surface.canvas_bounds is None:
        raise RenderFailed("E_PRESENTATION_RENDER_INPUT", "completed Scene surface has no canvas bounds", "presentation")
    return RenderedReview(artifact, surface, scene, frozenset(ledger.read), scenario_provenance,
                          _font_warnings(font_metrics.warnings, artifact.target_kind), perceptibility_warnings)


def _inspection_scene(closure: RenderClosure, surface: SceneSurface, projection: Any,
                      content: Any, viewport: tuple[float, float]) -> InspectionScene:
    """Build inspection evidence from completed runtime values without reopening policy."""
    primitive_roles = Counter(item.visual_role for item in surface.primitives)
    capabilities: set[str] = set()
    for primitive in surface.primitives:
        if primitive.marker_start is not None or primitive.marker_end is not None:
            capabilities.add("mark.marker-geometry")
        if primitive.pattern is not None:
            capabilities.add("paint.pattern-geometry")
        if primitive.symbol is not None:
            capabilities.add("mark.symbol-outline")
        if primitive.kind == "Icon":
            capabilities.add("icon.vector" if primitive.icon_kind == "vector" else "icon.raster")
    scales = (surface.scale_manifest,) if surface.scale_manifest is not None else ()
    manifest = SceneManifest(
        "chrona/scene-manifest/v0.1", closure.context.version, viewport,
        tuple(item.object_id for item in projection.items),
        tuple(sorted({item.text_layout.asset_identity for item in surface.primitives
                      if item.text_layout is not None})),
        ContentFamilyCounts(len(content.relations), len(content.annotations), len(content.notes),
                            len(content.legend_entries), len(content.summary.panels),
                            len(content.group_details), len(content.milestones),
                            len(content.observation_rows)),
        scales, tuple(sorted(primitive_roles.items())),
    )
    context_identity = closure.context.identity
    resources = tuple((item.kind, item.id, item.revision, item.content_identity)
                      for item in closure.resources)
    if context_identity.revision != "draft":
        resources = (("render-context", context_identity.id, context_identity.revision,
                      context_identity.content_identity), *resources)
    provenance = SceneProvenance(
        "draft" if context_identity.revision == "draft" else "immutable",
        version("chrona"), tuple(sorted(resources)),
    )
    return InspectionScene(provenance, viewport, tuple(sorted(capabilities)), (surface,), manifest, surface.diagnostics)


def _font_warnings(substitutions: tuple[FontGlyphSubstitution, ...], target_kind: str) -> tuple[FontGlyphWarning, ...]:
    """Project metric substitutions once the completed output target is known."""
    drawn = False if target_kind in {"png", "pdf"} else None
    return tuple(FontGlyphWarning(
        item.requested_family, item.fallback_family, item.weight, item.codepoint, item.text, drawn,
    ) for item in substitutions)


def _scene_perceptibility_warnings(scene: InspectionScene) -> tuple[ScenePerceptibilityWarning, ...]:
    """Project only evaluator errors into ordered draft feedback facts."""
    return _warnings_from_findings(evaluate_scene_perceptibility(scene_document(scene)))


def _warnings_from_findings(findings: tuple[ScenePerceptibilityFinding, ...]) -> tuple[ScenePerceptibilityWarning, ...]:
    return tuple(ScenePerceptibilityWarning(
        "W_" + finding.code.removeprefix("E_"), finding.code, finding.scene_path,
        finding.primitive_ids, finding.slot_id, finding.measured_facts, finding.disposition,
    ) for finding in findings if finding.severity == "error")


def _visual_request(visual: Any, projection: Any, index: int, closure: RenderClosure) -> VisualRequest:
    """Resolve View-owned direct/field icon selection before Layout geometry."""
    selector = tuple((str(key), str(value)) for key, value in visual.selector.items() if key != "kind")
    ref = visual.ref
    if visual.encoding is not None:
        object_id = visual.selector.get("id", visual.selector.get("object"))
        item = next((candidate for candidate in projection.items if candidate.object_id == object_id), None)
        field = visual.encoding.get("field")
        value = item.fields.get(field) if item is not None and item.fields is not None else None
        domain = visual.encoding.get("domain", {})
        ref = domain.get(str(value)) if isinstance(domain, Mapping) else None
        if ref is None:
            raise RenderFailed("E_ICON_ENCODING_UNKNOWN", "icon encoding has no matching field value", "presentation",
                               f"/body/visuals/{index}/encoding")
    try:
        canonical_ref = closure.icon_asset(str(ref)).icon_id if ref is not None else None
    except ClosureError as error:
        raise RenderFailed(error.diagnostic_id, error.detail or error.diagnostic_id, "closure",
                           f"/body/visuals/{index}") from error
    return VisualRequest(visual.target_kind, selector, canonical_ref,
                         str(visual.encoding["field"]) if visual.encoding else None,
                         tuple((str(key), str(value)) for key, value in visual.encoding.get("domain", {}).items()) if visual.encoding else (),
                         visual.side, visual.decorative, f"/body/visuals/{index}")


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
    try:
        return resolve_font_metrics_catalog(font_metrics, asset_root=asset_root)
    except FontMetricsError as error:
        raise _font_failure(error) from error


def _font_failure(error: FontMetricsError) -> RenderFailed:
    return RenderFailed(error.diagnostic_id, error.detail or "declared font metrics are unavailable",
                        "presentation", "/body/environment/fontMetrics")


def _source_inputs(project: dict[str, Any], view: ViewInput, projection: Any,
                   summary: SummaryContent, detail: ReviewDetailInput | None = None,
                   annotation_input: SourceInput | None = None, *, color_scale: Any = None) -> dict[str, SourceInput]:
    """Declare what each slot will hold, for measurement before layout."""
    rows = projection.rows or ()
    row_count = len(rows) or len(projection.items)
    span_days = max(1, (projection.window[1] - projection.window[0]).days)
    network = getattr(projection, "network", None)
    notes = tuple(str(item.get("text", "")) for item in project.get("annotations", {}).values())
    legend = tuple(item.label for item in detail.legend) if detail is not None else ()
    if color_scale is not None:
        # The colour-scale legend rows are drawn after the fixed legend; measure them too.
        used = {item.fields.get(color_scale.source_field) for item in projection.items
                if isinstance(item.fields, Mapping) and item.source_kind in {"primary", "combined"}}
        legend += tuple(str(value) for value in color_scale.domain if value in used)
    sources = {
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
        "notes": SourceInput(notes or ("notes",), typography_role="annotation"),
    }
    if annotation_input is not None:
        sources["annotations"] = annotation_input
    return sources


def _annotation_source_input(view: ViewInput, visual_requests: tuple[VisualRequest, ...],
                             icon_assets: dict[str, Any], theme: Mapping[str, Any]) -> SourceInput | None:
    """Build annotation measurements from the same closed visuals Layout composes."""
    visible = view.visibility.annotations
    mode = visible.get("mode", "none") if isinstance(visible, Mapping) else visible
    if mode == "none":
        return None
    numbered = ((isinstance(visible, Mapping) and visible.get("marker") == "numbered")
                or view.annotation_presentation == "numbered")
    tokens = ThemeTokenView(theme)
    runs = []
    for index, annotation in enumerate(view.annotations):
        annotation_id = str(annotation.get("id", ""))
        prefix = f"{index + 1}. " if numbered else ""
        advances = resolve_label_visual_advances(
            f"annotation-text:{annotation_id}", "annotation", visual_requests=visual_requests,
            icon_assets=icon_assets, theme_tokens=tokens,
        )
        inline_advance = sum((Decimal(str(width + gap)) for _, _, width, gap in advances), Decimal(0))
        runs.append(SourceTextRun(prefix + str(annotation.get("text", "")), "annotation",
                                  f"annotation-text:{annotation_id}", inline_advance))
    return SourceInput(runs=tuple(runs), typography_role="annotation")


def _slot_measurements(root: Mapping[str, Any], measured: Any) -> dict[str, Any]:
    measurements: dict[str, Any] = {}

    def bind(node: Mapping[str, Any]) -> None:
        if node["kind"] == "slot":
            source = node["source"]
            if source in measured.measurements:
                measurements[node["id"]] = measured.measurements[source]
        for child in node.get("children", ()):
            bind(child)

    bind(root)
    return measurements
