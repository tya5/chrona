"""Render one immutable Render Context closure into a review surface.

This is the whole render use case: it owns the order of the pipeline —
closure, schedule, projection, content, measurement, layout, scene, render —
so that no adapter has to know it. A caller supplies an already-resolved
closure and receives an SVG or a stable diagnostic; nothing here reads
command-line arguments, writes files, or prints.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field, replace
from datetime import date
from importlib.metadata import version
from pathlib import Path
from typing import Any, Mapping

from chrona.usecases.previous_scene import decode_previous_scene
from chrona.usecases.contrast_grouping import group_contrast_findings

from chrona.core.diagnostics import Diagnostic
from chrona.usecases.diagnostic_messages import encoding_contrast_detail, error_message
from chrona.usecases.warning_ledger import RenderWarning, collect_render_warnings
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, DiagnosticSubject, PrimitiveProvenance
from chrona.presentation.scene.viewer_fit import viewer_fit_fallbacks
from chrona.core.ports import RenderArtifact, Renderer, Scheduler
from chrona.extensions.profiles import validate_profiles
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_count_closure import inspect_count_reads
from chrona.presentation.layout.surface_render_plan import (
    SurfaceRenderPlanInput, SlotHeadingCopyError, SurfacePlanFontError, prepare_surface_render_plan,
)
from chrona.presentation.layout.group_header_runs import validate_group_header_roles
from chrona.presentation.layout.presentation import (
    validate_label_text_role, validate_lane_table_text_roles, validate_table_text_roles)
from chrona.presentation.layout.surface_quality import VisualRequest
from chrona.presentation.model.closure import ClosureError, RenderClosure
from chrona.presentation.model.font_metrics import FontGlyphSubstitution, FontMetricsError, group_glyph_substitutions, FontTabularWarning, resolve_font_metrics_catalog
from chrona.presentation.model.font_resources import FontAssetResolver
from chrona.presentation.model.color_separability import SIMULATED_VISIONS, ScaleCollision
from chrona.presentation.model.info_diagnostics import (
    PresentationInfo, UnboundSummarySource, FontGlyphFallback, ScaleValuesFolded,
    ForecastInfo, FieldGroupingSummariesOmitted, BaselineObjectsRemoved, RoutingCostAdvisory,
    AnnotationNotDrawn, LegendRoleUnkeyed,
)
from chrona.presentation.model.legend_role_coverage import unkeyed_band_and_fill_roles
from chrona.usecases.forecast_schedule import forecast_schedule
from chrona.usecases.profile_field_bindings import resolve_source_field_bindings
from chrona.presentation.model.field_role_view import resolve_field_role_view
from chrona.presentation.contracts.resources import ContractError, ViewAllPeriods, ViewPeriod
from chrona.presentation.model.preset_target import PresetVisualProfileFallback
from chrona.presentation.model.render_progress import RenderAdvisoryEvent, RenderEvent, RenderProgress
from chrona.presentation.fonts.resolution import resolve_theme_font_stacks
from chrona.presentation.fonts.system import DraftFontResolution
from chrona.presentation.model.theme_role_consumers import unread_diagnostics as unread_theme_diagnostics
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView, effective_draft_numeric_theme
from chrona.presentation.model.theme_paint import ThemePaintError
from chrona.core.attachments import AttachmentWarning, attachment_warnings
from chrona.core.deadlines import DeadlineStatus, deadline_statuses, deadline_warnings_from_statuses
from chrona.presentation.count_text import CountTextError
from chrona.core.figures import FigureCounts, FigureResolution, resolve_figures
from chrona.core.periods import period_range_diagnostics, resolve_periods
from chrona.core.temporal import Calendar
from chrona.presentation.model.color_scale import ColorScaleError, resolve_color_scale, scale_text
from chrona.presentation.model.color_separability import MINIMUM_CATEGORY_DELTA_E, MINIMUM_RESERVED_CHROMA, chroma, delta_e_2000
from chrona.presentation.model.point_paint import resolve_point_paint_role
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.style import EncodingWitness
from chrona.presentation.model.axis_color_scale import (
    AxisBandScaleError, resolve_axis_band_scales, validate_axis_band_fill_targets,
)
from chrona.presentation.model.projection import (
    NetworkDeadlineContent, NetworkLabelSourceError, ViewWindowError, ReviewDeadline, ReviewPeriod, build_review_projection, forecast_deadline_placements,
)
from chrona.presentation.model.actual_variance_paint import resolve_actual_variance_colors
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.model.style_rules import StyleEvaluationError
from chrona.presentation.contracts.resources import ViewInput
from chrona.presentation.review.detail import ReviewDetailError
from chrona.presentation.review.figure_facts import (deferred_layout_figures, filtered_figure_counts, projected_counts,
                                                     projected_last_planned_finish)
from chrona.presentation.review.annotation_expansion import (
    AnnotationExpansionError, undrawn_project_annotations,
)
from chrona.presentation.model.wording_tables import wording_resolver
from chrona.presentation.review.profile_connections import ProfileConnectionError, resolve_profile_connections
from chrona.presentation.annotation_kind_text import AnnotationKindTextError, header_lines, heading_text
from chrona.presentation.figure_text import FigureTextError, FigureTextReadError, resolve_figure_text
from chrona.presentation.review.v05_content import (
    compose_heading, missing_heading_fact_warnings, normalize_summary_content,
    normalize_v05_surface_content, normalize_v05_table_content)
from chrona.presentation.style import bind_style_rules
from chrona.presentation.scene.model import (
    ContentFamilyCounts, InspectionScene, SceneManifest, SceneProvenance,
    SceneSurface,
)
from chrona.presentation.scene.contrast_policy import (
    BLOCKING_CODES, DEFAULT_POLICY, WARNING_BLOCKING_CODES, SceneContrastFinding, evaluate_scene_contrast,
    policy_member_of)
from chrona.presentation.scene.perceptibility import ScenePerceptibilityFinding, evaluate_scene_perceptibility
from chrona.presentation.scene.paint import ScenePaintError
from chrona.presentation.scene.serialization import scene_document
from chrona.presentation.scene.v05_builder import SceneBuildError
from chrona.presentation.surface_pipeline import build_surface_input, compose_resolved_review_surface
from chrona.presentation.scene.visual_capabilities import (
    VisualCapabilityError,
    resolve_visual_profile,
    validate_surface_visual_profile,
    visual_capability_message,
    paint_witness_capabilities,
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

    def __init__(self, code: str, message: str, component: str, source_ref: str = "/",
                 *, details: Mapping[str, Any] | None = None):
        super().__init__(code)
        self.code = code
        self.message = message
        self.component = component
        self.source_ref = source_ref
        self.details = dict(details) if details is not None else None


@dataclass(frozen=True)
class RenderRequest:
    """One resolved closure and the store it was read from."""

    closure: RenderClosure
    snapshot_root: Path
    scheduler: Scheduler
    renderer: Renderer | None = None
    require_all_inputs_read: bool = False
    asset_root: Path | None = None
    asset_resolver: FontAssetResolver | None = None
    draft_auto_block: bool = False
    draft_font_resolution: DraftFontResolution | None = None
    preset_visual_profile_fallback: PresetVisualProfileFallback | None = None
    progress: RenderProgress | None = field(default=None, compare=False, repr=False)
    # Extension diagnostics a draft caller resolved beside the Project file (no Store); Context renders leave it empty.
    extension_diagnostics: tuple[Diagnostic, ...] = ()
    # Draft renders have no Store closure: manifests resolved beside the Project file, one set per source Project.
    # They apply only where the closure holds no profile package, so they can never shadow a pinned one.
    extension_manifests: Mapping[str, Any] = field(default_factory=dict, compare=False, repr=False)
    snapshot_extension_manifests: Mapping[str, Any] = field(default_factory=dict, compare=False, repr=False)


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
    contrast_warnings: tuple["SceneContrastWarning", ...] = ()
    info_diagnostics: tuple[PresentationInfo, ...] = ()
    scale_collisions: tuple[ScaleCollision, ...] = ()
    attachment_warnings: tuple[AttachmentWarning, ...] = ()
    deadline_warnings: tuple[Diagnostic, ...] = ()
    warning_records: tuple[RenderWarning, ...] = ()
    preset_visual_profile_fallback: PresetVisualProfileFallback | None = None


@dataclass(frozen=True)
class FontGlyphWarning:
    """One target-honest draft font substitution warning."""

    requested_family: str
    fallback_family: str
    weight: int
    codepoint: int
    text: str
    drawn: bool | None = None
    script: str = "other"
    count: int = 1


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
    subjects: tuple[DiagnosticSubject, ...] = ()


@dataclass(frozen=True)
class SceneContrastWarning:
    """One contrast finding below its floor or not judgeable, with optional encoding provenance."""

    code: str
    finding_code: str
    scene_path: str
    primitive_ids: tuple[str, ...]
    measured_facts: tuple[tuple[str, float | str], ...]
    disposition: str | None
    subjects: tuple[DiagnosticSubject, ...] = ()
    encoding: EncodingWitness | None = None
    encoding_pair: tuple[tuple[str, str | float], ...] = ()
    ground_ids: tuple[str, ...] = ()


class ClosureReadLedger:
    """Records named typed-closure dependencies without generic kind lookup."""

    def __init__(self, closure: RenderClosure):
        self._declared = {item.kind for item in closure.resources}
        if closure.previous_scene_bytes is not None:
            self._declared.add("previous-scene")
        self.read: set[str] = set()

    def required(self) -> None:
        self.read.update({"project", "view", "layout-profile", "theme", "color-scheme", "semantic-vocabulary"})

    def actual(self) -> None:
        self.read.add("actual-set")

    def snapshot(self) -> None:
        self.read.update({"snapshot-ref", "snapshot-project"})

    def snapshot_project(self) -> None:
        self.read.add("snapshot-project")

    def detail(self) -> None:
        self.read.add("review-detail-profile")

    def summary(self) -> None:
        self.read.add("summary-profile")

    def style(self) -> None:
        self.read.add("style")

    def packages(self) -> None:
        self.read.add("profile-package")

    def icons(self) -> None:
        self.read.add("icon-catalog")

    def unused(self) -> tuple[str, ...]:
        return tuple(sorted(self._declared - self.read - _IMPLICITLY_READ))


def render_review(request: RenderRequest) -> RenderedReview:
    """Transport detector-owned presentation pointers across the use-case boundary."""
    try:
        return _render_review(request)
    except ViewWindowError as error:
        raise RenderFailed(error.code, error.detail, "view", error.source_ref) from error
    except NetworkLabelSourceError as error:
        subject = DiagnosticSubject.project_object(error.object_id, error.title)
        raise RenderFailed(error.code, error.detail, "view", error.source_ref, details={
            "objectId": error.object_id,
            "actualType": error.value_type,
            "sourceSubjects": [{"sourceRef": subject.source_ref, "title": subject.title}],
        }) from error
    except ColorScaleError as error:
        raise RenderFailed(error.code, error.detail, "presentation", error.source_ref) from error
    except StyleEvaluationError as error:
        raise RenderFailed(
            error.diagnostic_id, error.detail, "presentation", error.source_ref,
            details={"ruleIds": list(error.rule_ids),
                     **({"subject": asdict(error.subject)} if error.subject is not None else {})},
        ) from error
    except AnnotationExpansionError as error:
        raise RenderFailed(error.diagnostic_id, error.detail, "presentation", error.source_ref) from error
    except ProfileConnectionError as error:
        raise RenderFailed(error.code, error.detail, error.component, error.source_ref) from error
    except (LayoutError, ThemeTokenError, ThemePaintError, ScenePaintError) as error:
        message = error_message(error.diagnostic_id, getattr(error, "detail", None))
        node = getattr(error, "node_id", None)  # a Layout finding names the offending token or node here
        raise RenderFailed(error.diagnostic_id, f"{message} ({node})" if node else message,
                           "presentation", error.path or "/") from error


def _layout_has_source(node: object, source: str) -> bool:
    if not isinstance(node, Mapping):
        return False
    if node.get("kind") == "slot" and node.get("source") == source:
        return True
    children = node.get("children")
    return isinstance(children, list) and any(_layout_has_source(child, source) for child in children)


def _undrawn_annotation_warnings(view: Any, project: Mapping[str, Any], projection: Any,
                                 plan: Any) -> tuple[AnnotationNotDrawn, ...]:
    """Name each Project annotation on a drawn target that no binding or notes slot draws (#1870)."""
    visible = view.visibility.annotations
    mode = visible.get("mode", "none") if isinstance(visible, Mapping) else visible
    notes = project.get("annotations", {})
    if mode == "none" or not isinstance(notes, Mapping) or not notes:
        return ()
    if _layout_has_source(plan.profile.profile.get("root"), "notes"):
        return ()  # the notes slot draws every note a binding left over
    unplaced = (key for key, _ in plan.content.notes)
    return tuple(AnnotationNotDrawn(*item)
                 for item in undrawn_project_annotations(notes, projection, unplaced))


def _render_review(request: RenderRequest) -> RenderedReview:
    """Render one closure, in the one order the pipeline has."""
    render_closure, ledger = request.closure, ClosureReadLedger(request.closure)
    try:
        render_closure.require_semantic_vocabulary()
    except ClosureError as error:
        raise RenderFailed(error.diagnostic_id, error.detail, "presentation", error.source_ref) from error
    previous_scene = None
    if render_closure.previous_scene_bytes is not None:
        previous_scene = decode_previous_scene(render_closure.previous_scene_bytes,
            render_closure.project.identity.id,
            current_theme_identity=next((item.content_identity for item in render_closure.resources
                                         if item.kind == "theme"), None))
        ledger.read.add("previous-scene")
    project, view, layout = (render_closure.project.scheduler_input, render_closure.view.view,
                             render_closure.layout_profile.layout_input)
    authored_view = view
    try:
        view, field_role_info = resolve_field_role_view(view, project)
    except ContractError as error:
        raise RenderFailed(error.diagnostic_id, error.detail, "view", error.source_ref) from error
    profile_connections = resolve_profile_connections(
        view, render_closure.summary_profile.summary if render_closure.summary_profile else None,
        render_closure.detail_profile.detail if render_closure.detail_profile else None,
        project_object_ids=frozenset(project.get("objects", {})),
        locale=render_closure.context.environment.locale)
    view = profile_connections.view
    omitted_metrics = frozenset((item.panel_index, item.metric_index)
                               for item in profile_connections.omissions)
    profile_info = field_role_info + tuple(UnboundSummarySource(item.panel_id, item.metric_id,
                                              item.source_kind, item.source_name)
                         for item in profile_connections.omissions)
    theme = render_closure.resolved_theme.resolved_input
    try:
        visual_profile = resolve_visual_profile(render_closure.context.target.visual_profile,
                                                render_closure.context.target.kind)
    except VisualCapabilityError as error:
        raise RenderFailed(error.diagnostic_id, error.message, "presentation", error.path) from error
    ledger.required()
    packages = render_closure.profile_packages
    manifests = ({item.package_id: item.profile_input
                  for item in render_closure.profile_packages_for(render_closure.project)} if packages
                 else dict(request.extension_manifests))
    if packages:
        ledger.packages()
    if request.progress is not None:
        request.progress.phase("schedule")
    projection, scenario_provenance, attachments, deadlines = _project_review(project, view, render_closure, manifests, request.scheduler, request.extension_diagnostics,
                                                                              request.snapshot_extension_manifests)
    profile_info += tuple(ForecastInfo(item) for item in projection.forecast_findings)
    if projection.removed_objects:
        profile_info += (BaselineObjectsRemoved(projection.removed_objects),)
    if projection.omitted_group_summary_count:
        profile_info += (FieldGroupingSummariesOmitted(projection.omitted_group_summary_count),)
    unavailable = {item.details["figure"]: item.id for item in projection.unavailable_figures}
    unavailable_metrics = []
    if profile_connections.summary is not None:
        for panel_index, panel in enumerate(profile_connections.summary.panels):
            for metric_index, metric in enumerate(panel.metrics):
                source = getattr(metric, "source", None)
                if isinstance(source, Mapping) and source.get("figure") in unavailable:
                    unavailable_metrics.append((panel_index, metric_index))
                    profile_info += (UnboundSummarySource(panel.id, metric.id, "slot", source["figure"],
                                                         reason=unavailable[source["figure"]]),)
    omitted_metrics = omitted_metrics | frozenset(unavailable_metrics)
    if request.progress is not None:
        request.progress.phase("layout")
    legend_colors = _legend_colors(theme, profile_connections.detail)
    color_scale = resolve_color_scale(view.color_encoding, theme["body"].get("colorScales"),
                                      theme["body"].get("categorySlots"),
                                      observed=_observed_scale_values(view.color_encoding, projection),
                                      reserved=tuple(c for c in legend_colors if chroma(c) >= MINIMUM_RESERVED_CHROMA),
                                      other_color=_other_color(theme, legend_colors))
    group_tints, group_tint_collisions, _group_tint_scale = _resolve_group_tints(view, projection, theme)
    if render_closure.actual_set is not None:
        ledger.actual()
    if render_closure.snapshot is not None:
        ledger.snapshot()
    elif render_closure.snapshot_project is not None:
        ledger.snapshot_project()

    environment = render_closure.context.environment
    asset_root = request.asset_root or snapshot_directory(request.snapshot_root, render_closure.context.identity.revision)
    resolution = request.draft_font_resolution
    if resolution is None:
        # Installed fonts are a normal source on every path (#1281): a role whose font stack is not one declared exact
        # face resolves to an installed face or the packaged Noto Sans; declared faces keep precedence.
        resolution = resolve_theme_font_stacks(theme, environment.font_metrics, asset_root=asset_root,
                                               asset_resolver=request.asset_resolver,
                                               font_files_required=render_closure.context.target.kind != "svg")
    if resolution is not None and resolution.tabular_warnings:
        theme = effective_draft_numeric_theme(theme, tuple(item.role for item in resolution.tabular_warnings))
    font_metrics = resolution.metrics if resolution is not None else _font_metrics(
        theme, environment.font_metrics, asset_root, request.asset_resolver)
    _check_summary_figures(profile_connections.summary, projection, view, omitted_metrics=omitted_metrics)
    summary = normalize_summary_content(profile_connections.summary,
                                        projection, render_closure.actual_set.observations_input if render_closure.actual_set else None,
                                        project, omitted_metrics=omitted_metrics,
                                        summary_wording=(view.wording or {}).get("summary", {}),
                                        unknown_text=wording_resolver(environment.locale, view.wording).text("missing.unknown"),
                                        resolver=wording_resolver(environment.locale, view.wording))
    summary = replace(summary, absent=bool(omitted_metrics) and not summary.panels)
    if render_closure.summary_profile is not None:
        ledger.summary()
    icon_assets = {item.icon_id: item for item in render_closure.icon_assets}
    visual_requests = tuple(_visual_request(visual, projection, index, render_closure)
                            for index, visual in enumerate(view.visuals))
    theme_assets = render_closure.resolved_theme
    if visual_requests or icon_assets or theme_assets.catalog_glyphs or theme_assets.catalog_patterns:
        # A Theme-only annotationContainer.image binding (#465) selects a
        # catalog entry no View visual names; icon_assets is non-empty
        # exactly when the pinned iconCatalogs closure actually supplied
        # something to read, whichever selected it. A Theme glyph or pattern
        # (a canvas texture, #587) reads its catalogue without any icon asset:
        # the resolved Theme carries only the entries it references.
        ledger.icons()
    actual_observations = render_closure.actual_set.observations_input if render_closure.actual_set else None
    table_content = normalize_v05_table_content(projection, project, view, actual_set=actual_observations,
                                                locale=environment.locale)
    validate_table_text_roles(view.table_columns, ThemeTokenView(theme))
    validate_lane_table_text_roles(view.rows.lane_table, ThemeTokenView(theme))
    validate_label_text_role(view.visibility.labels, ThemeTokenView(theme))
    if view.grouping is not None and view.grouping.header is not None:
        validate_group_header_roles(view.grouping.header.role_pointers(), ThemeTokenView(theme))
    selected_content = normalize_v05_surface_content(
        projection, project, view, actual_set=actual_observations,
        detail=profile_connections.detail,
        summary=summary, locale=environment.locale, color_scale=color_scale, table=table_content,
        group_tints=group_tints, annotation_kind_colors=_annotation_kind_colors(theme),
        actual_variance_colors=resolve_actual_variance_colors(ThemeTokenView(theme)),
        dependency_critical_role_available=ThemeTokenView(theme).has_role("dependency-critical"),
        annotation_kind_also=_annotation_kind_also(theme), theme=theme,
        gate_declared=ThemeTokenView(theme).has_role("gate"),
        style_rules=(bind_style_rules(render_closure.style.identity.id, render_closure.style.rules)
                     if render_closure.style is not None else ()),
        view_id=render_closure.view.identity.id,
        scale_reserved=tuple(c for c in legend_colors if chroma(c) >= MINIMUM_RESERVED_CHROMA),
        scale_other_color=_other_color(theme, legend_colors))
    if render_closure.style is not None:
        ledger.style()
    # A Style domain union replaces the provisional View map of that name;
    # diagnostics describe the completed map once, not both generations.
    if color_scale is not None:
        color_scale = next((scale for scale in selected_content.style_fills.scales
                            if scale.scale_id == color_scale.scale_id), color_scale)
    style_scales = tuple(scale for scale in selected_content.style_fills.scales
                         if scale is not color_scale)
    profile_info += tuple(_scale_folded_info(scale) for scale in (color_scale, _group_tint_scale, *style_scales)
                          if scale is not None and scale.folded)
    try:
        validate_axis_band_fill_targets(selected_content.axis_tiers, ThemeTokenView(theme))
        axis_band_scale = resolve_axis_band_scales(
            selected_content.axis_tiers, window=projection.window,
            fiscal_start_month=selected_content.axis_fiscal_start_month,
            scales=theme["body"].get("colorScales", {}), categories=theme["body"].get("categorySlots", {}))
    except AxisBandScaleError as error:
        raise RenderFailed(error.code, error.detail, "presentation", error.path) from error
    selected_content = replace(selected_content, axis_band_paints=axis_band_scale.paints)
    selected_content = _complete_annotation_headers(selected_content, theme, projection, view, wording_resolver(environment.locale, view.wording))
    routing_advisory: RoutingCostAdvisory | None = None

    def observe_layout_work(event: RenderEvent) -> None:
        nonlocal routing_advisory
        if isinstance(event, RenderAdvisoryEvent):
            if routing_advisory is not None:
                return
            routing_advisory = event.advisory
        if request.progress is not None:
            request.progress.emit(event)

    # Retain typed Layout work facts independently of the optional UI sink.
    # Count trials buffer ordinary progress but forward attempted-work advisories.
    layout_progress = RenderProgress(observe_layout_work)
    # Both native surfaces use the same composed View heading. A network's
    # whole-title slot is the heading host; profiles without that slot admit
    # the same named heading parts as before.
    snapshot_present = render_closure.snapshot is not None or render_closure.snapshot_project is not None
    heading_content = compose_heading(view, project, actual_observations, environment.locale,
                                      snapshot_present=snapshot_present)
    try:
        count_input = inspect_count_reads(SurfaceRenderPlanInput(
            previous_route_hints=previous_scene.route_hints if previous_scene is not None else None,
            project=project, view=view, projection=projection, content=selected_content,
            summary=summary, table=table_content, profile=layout, theme=theme,
            font_metrics=font_metrics, heading=heading_content, actual=actual_observations,
            detail=profile_connections.detail,
            viewport_inline=environment.viewport_inline, viewport_block=environment.viewport_block,
            content_sized=request.draft_auto_block, locale=environment.locale,
            scene_precision=environment.scene_precision, snapshot_present=snapshot_present,
            paint_capabilities=paint_witness_capabilities(visual_profile),
            capabilities={name: True for name in render_closure.context.target.capabilities},
            icon_assets=icon_assets, visual_requests=visual_requests, progress=layout_progress))
        plan = prepare_surface_render_plan(count_input.value) if not count_input.active else None
    except SurfacePlanFontError as error:
        raise _font_failure(error.failure) from error.failure
    except FontMetricsError as error:
        raise _font_failure(error) from error
    except SlotHeadingCopyError as error:
        raise RenderFailed(error.diagnostic_id, error.detail, "view", error.path) from error
    except FigureTextReadError as error:
        raise RenderFailed(error.failure.code, error.failure.detail, error.component, error.path) from error
    if render_closure.detail_profile is not None:
        ledger.detail()
    try:
        scene_input = None
        if plan is not None:
            scene_input = build_surface_input(
                projection=projection, surface_content=plan.content, layout_manifest=plan.manifest,
                resolved_theme=theme, font_metrics=font_metrics, measured_sources=plan.measured,
                capabilities={name: True for name in render_closure.context.target.capabilities},
                visual_profile=visual_profile, viewport=plan.viewport,
                icon_assets=icon_assets, visual_requests=visual_requests,
                fixed_lane_preflight=(plan.preparation.inline.request.fixed_lane_preflight
                                      if plan.preparation else None),
                capacity_short_sources=plan.capacity_short_sources, surface_preparation=plan.preparation,
                auto_block_limit=plan.profile.distances.get("/reviewSurface/maxBlockSize"),
                declared_viewport=plan.declared_viewport, progress=layout_progress)

        unused = ledger.unused()
        if request.require_all_inputs_read and unused:
            raise RenderFailed("E_CLOSURE_INPUT_UNUSED",
                               "closure inputs loaded but never read: " + ", ".join(unused), "closure")

        rendered = compose_resolved_review_surface(count_input, visual_profile=visual_profile,
                                                   initial=plan, admitted=scene_input)
        surface, projection, plan = rendered.surface, rendered.projection, rendered.plan
        if (view.surface == "table-timeline" or view.surface == "dependency-network"):
            profile_info += missing_heading_fact_warnings(view, project, actual_observations,
                                                          snapshot_present=snapshot_present)
        if view.surface == "table-timeline":
            profile_info += _undrawn_annotation_warnings(view, project, projection, plan)
        profile_info += tuple(LegendRoleUnkeyed(role, purpose)
                              for purpose, role in unkeyed_band_and_fill_roles(surface.primitives))
        if routing_advisory is not None:
            profile_info += (routing_advisory,)
        if profile_info:
            surface = replace(surface,
                info_diagnostics=(*surface.info_diagnostics, *(item for item in profile_info if not item.code.startswith("W_"))),
                diagnostics=(*surface.diagnostics, *(item.scene_diagnostic() for item in profile_info if item.code.startswith("W_"))))
        surface_content = plan.content
    except FontMetricsError as error:
        raise _font_failure(error) from error
    except SurfacePlanFontError as error:
        raise _font_failure(error.failure) from error.failure
    except SlotHeadingCopyError as error:
        raise RenderFailed(error.diagnostic_id, error.detail, "view", error.path) from error
    except FigureTextReadError as error:
        raise RenderFailed(error.failure.code, error.failure.detail, error.component, error.path) from error
    except SceneBuildError as error:
        detail = error.detail or visual_capability_message(error.diagnostic_id)
        raise RenderFailed(error.diagnostic_id, detail,
                           "presentation", error.path) from error
    # A Theme role or binding no document of this closure reads is reported, not silently accepted (#1117).
    unread_roles = unread_theme_diagnostics(
        theme["body"], (view, *((authored_view,) if view is not authored_view else ()),  # omitted unbound-role columns still read their roles (#1616)
                        layout, render_closure.detail_profile.detail if render_closure.detail_profile else None,
                        render_closure.summary_profile.summary if render_closure.summary_profile else None,
                        render_closure.style.rules if render_closure.style is not None else (),
                        selected_content.style_intents.intents))
    if unread_roles:
        surface = replace(surface, diagnostics=(*surface.diagnostics, *unread_roles))
    if resolution is not None and resolution.notes:
        surface = replace(surface, diagnostics=(*surface.diagnostics, *resolution.notes))
    glyph_info = tuple(FontGlyphFallback(item.requested_family, item.fallback_family, item.weight,
                                         item.codepoint, item.text, item.script, item.count)
                       for item in group_glyph_substitutions(item for item in font_metrics.warnings if item.informational))
    if glyph_info:
        surface = replace(surface, info_diagnostics=(*surface.info_diagnostics, *glyph_info))
    try:
        validate_surface_visual_profile(surface, visual_profile)
    except VisualCapabilityError as error:
        raise RenderFailed(error.diagnostic_id, error.message, "presentation", error.path) from error
    collisions = ((color_scale.collisions if color_scale is not None else ())
                  + tuple(collision for scale in style_scales for collision in scale.collisions)
                  + group_tint_collisions + axis_band_scale.collisions)
    scene = _inspection_scene(render_closure, surface, projection, surface_content,
                              (surface.canvas_bounds[2], surface.canvas_bounds[3]),
                              resolution.tabular_warnings if resolution is not None else (),
                              ())
    perceptibility_warnings = (_scene_perceptibility_warnings(scene, surface.primitive_provenance)
                               if render_closure.context.identity.revision == "draft" else ())
    contrast_warnings = _scene_contrast_warnings(scene, theme, surface.primitive_provenance)
    _enforce_color_vision_claims(theme, collisions, surface.diagnostic_provenance)
    _enforce_print_claim(render_closure.color_scheme.scheme_input, surface.diagnostic_provenance)
    renderer = request.renderer or renderer_for(
        {"kind": render_closure.context.target.kind, "capabilities": list(render_closure.context.target.capabilities)},
        environment.renderer_environment(),
        asset_root=asset_root,
        font_files=resolution.font_files if resolution is not None else None,
        asset_resolver=request.asset_resolver,
    )
    if request.progress is not None:
        request.progress.phase("output")
    try:
        artifact = renderer.render(surface)
    except FontMetricsError as error:
        raise _font_failure(error) from error
    if artifact.target_kind != render_closure.context.target.kind:
        raise RenderFailed("E_PRESENTATION_TARGET", "renderer target does not match Context target", "renderer")
    if surface.canvas_bounds is None:
        raise RenderFailed("E_PRESENTATION_RENDER_INPUT", "completed Scene surface has no canvas bounds", "presentation")
    glyph_warnings = _font_warnings(font_metrics.warnings, artifact.target_kind)
    warning_records = collect_render_warnings(
        surface_diagnostics=(*surface.diagnostics, *viewer_fit_fallbacks(surface, artifact.target_kind)),
        tabular_warnings=scene.font_warnings,
        glyph_warnings=glyph_warnings, fit_warnings=surface.fit_warnings,
        perceptibility_warnings=perceptibility_warnings, scale_collisions=collisions,
        attachment_warnings=attachments, deadline_warnings=deadlines,
        forecast_warnings=projection.forecast_warnings,
        contrast_warnings=contrast_warnings,
        surface_provenance=surface.diagnostic_provenance,
        canvas_warning=surface.canvas_warning,
        auto_block_warning=surface.auto_block_warning,
    )
    # Surface diagnostics are already in the preliminary Scene. Append only
    # the post-composition families, preserving duplicates and their order.
    appended = warning_records[sum(item.startswith("W_") for item in surface.diagnostics):]
    scene = replace(scene, diagnostics=(*scene.diagnostics, *(item.identity for item in appended)))
    return RenderedReview(artifact, surface, scene, frozenset(ledger.read), scenario_provenance,
                          glyph_warnings, perceptibility_warnings, contrast_warnings,
                          surface.info_diagnostics, collisions, attachments, deadlines, warning_records,
                          preset_visual_profile_fallback=request.preset_visual_profile_fallback)


def _inspection_scene(closure: RenderClosure, surface: SceneSurface, projection: Any,
                      content: Any, viewport: tuple[float, float],
                      tabular_warnings: tuple[FontTabularWarning, ...] = (),
                      collisions: tuple[ScaleCollision, ...] = ()) -> InspectionScene:
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
    return InspectionScene(provenance, viewport, tuple(sorted(capabilities)), (surface,), manifest,
                           (*surface.diagnostics, *(item.scene_diagnostic() for item in surface.info_diagnostics),
                            *(item.scene_diagnostic() for item in collisions)),
                           tabular_warnings)


def _font_warnings(substitutions: tuple[FontGlyphSubstitution, ...], target_kind: str) -> tuple[FontGlyphWarning, ...]:
    """Project metric substitutions once the completed output target is known."""
    drawn = False if target_kind in {"png", "pdf"} else None
    return tuple(FontGlyphWarning(
        item.requested_family, item.fallback_family, item.weight, item.codepoint, item.text, drawn,
        item.script, item.count,
    ) for item in group_glyph_substitutions(item for item in substitutions if not item.informational))


def _scene_perceptibility_warnings(
    scene: InspectionScene, provenance: tuple[PrimitiveProvenance, ...] = (),
) -> tuple[ScenePerceptibilityWarning, ...]:
    """Project only evaluator errors into ordered draft feedback facts."""
    return _warnings_from_findings(evaluate_scene_perceptibility(scene_document(scene)), provenance)


def _enforce_color_vision_claims(
    theme: Mapping[str, Any], collisions: tuple[ScaleCollision, ...],
    provenance: tuple[DiagnosticProvenance, ...],
) -> None:
    """Enforce only Scheme claims; measurement and default warnings stay independent."""
    claims = frozenset(ThemeTokenView(theme).color_vision) & frozenset(SIMULATED_VISIONS)
    _enforce_separability_claims({vision: vision for vision in claims}, collisions, provenance,
                               "/body/suitability/colorVision", "suitability.colorVision includes")


def _enforce_print_claim(
    scheme: Mapping[str, Any], provenance: tuple[DiagnosticProvenance, ...],
) -> None:
    """Print claims govern completed legend ink, never categorical scale domains."""
    claim = scheme["body"]["suitability"]["print"]
    claims = {"grayscale": claim} if claim in {"print-friendly", "photocopy-friendly"} else {}
    _enforce_separability_claims(claims, (), provenance,
                               "/body/suitability/print", "suitability.print is")


def _enforce_separability_claims(
    claims: Mapping[str, str], collisions: tuple[ScaleCollision, ...],
    provenance: tuple[DiagnosticProvenance, ...], source_ref: str, claim_description: str,
) -> None:
    """Apply declared severities to measured facts without reinterpreting geometry."""
    if not claims:
        return
    failures = []
    for item in collisions:
        if item.vision in claims:
            failures.append(("E_PRESENTATION_SCALE_NOT_SEPARABLE", {
                "vision": item.vision, "deltaE": item.delta_e,
                "minimumDeltaE": MINIMUM_CATEGORY_DELTA_E, "claim": claims[item.vision],
                "scaleId": item.scale_id, "first": item.first, "second": item.second,
            }))
    for item in provenance:
        finding = item.color_pair
        if finding is not None and finding.vision in claims:
            failures.append(("E_LEGEND_COLOR_NOT_SEPARABLE", {
                "vision": finding.vision, "deltaE": finding.delta_e,
                "minimumDeltaE": MINIMUM_CATEGORY_DELTA_E, "claim": claims[finding.vision],
                "sourceSubjects": [{"sourceRef": subject.source_ref,
                    **({"title": subject.title} if subject.title is not None else {})}
                    for subject in item.subjects],
            }))
    if failures:
        code, details = failures[0]
        pair = (f"scale {details['scaleId']}: {details['first']} / {details['second']}"
                if "scaleId" in details else " / ".join(
                    subject.get("title", subject["sourceRef"]) for subject in details["sourceSubjects"]))
        more = f" and {len(failures) - 1} more" if len(failures) > 1 else ""
        raise RenderFailed(code,
            f"{pair}: colour difference {details['deltaE']!r} below {MINIMUM_CATEGORY_DELTA_E:g} "
            f"under {details['vision']}{more}; the Scheme claims {claim_description} {details['claim']}",
            "presentation", source_ref, details=details)


def _scene_contrast_warnings(
    scene: InspectionScene, theme: Mapping[str, Any], provenance: tuple[PrimitiveProvenance, ...] = (),
) -> tuple[SceneContrastWarning, ...]:
    """Report the contrast findings under the Theme's `contrastPolicy` (#995, #1126).

    Contrast constraints are an opt-in design option: a class the Theme does not declare is `warning` (a typed
    warning, never an error of the render), `none` reports nothing, and `error` fails the render with the first
    finding's blocking code before any adapter output. Structural findings (a malformed paint) are not governed.
    """
    declared = dict(theme["body"].get("contrastPolicy", {}))
    exceptions = declared.pop("exceptions", ())
    # Ground participation is already completed onto the cone in Scene. It
    # is not a severity class or a runtime-only observation override.
    declared.pop("asOfConeGround", None)
    findings = evaluate_scene_contrast(scene_document(scene), policy={**DEFAULT_POLICY, **declared},
                                       exceptions=exceptions)
    blocking = [item for item in findings if item.severity == "error" and item.code in BLOCKING_CODES]
    if blocking:
        first = blocking[0]
        member = policy_member_of(first) or "mark"
        ratio = f", contrast {first.contrast_ratio:.3f} against {first.floor:g}" if first.contrast_ratio is not None else ""
        more = f" and {len(blocking) - 1} more" if len(blocking) > 1 else ""
        details = None
        if first.encoding is not None:
            detail = encoding_contrast_detail({
                "encoding": first.encoding.as_mapping(), "contrastRatio": first.contrast_ratio,
                "floor": first.floor, "groundId": first.ground_id, "groundKind": first.ground_kind,
            })
            message = f"{first.primitive_id} ({first.visual_role}): {detail}{more}; the Theme declares "
            details = {"encoding": first.encoding.as_mapping(), "contrastRatio": first.contrast_ratio,
                       "floor": first.floor, "groundId": first.ground_id,
                       "paintChannel": first.paint_channel}
        else:
            message = f"{first.primitive_id} ({first.visual_role}){ratio}{more}; the Theme declares "
        raise RenderFailed(first.code, message + f"contrastPolicy.{member}: error", "presentation",
                           f"/body/contrastPolicy/{member}", details=details)
    return _contrast_warnings_from_findings(findings, provenance)


def _finding_subjects(
    primitive_ids: tuple[str, ...], provenance: tuple[PrimitiveProvenance, ...],
) -> tuple[DiagnosticSubject, ...]:
    """Join exact producer identities, preserving finding and subject order."""
    by_id: dict[str, list[DiagnosticSubject]] = {}
    for item in provenance:
        by_id.setdefault(item.primitive_id, []).extend(item.subjects)
    return tuple(dict.fromkeys(subject for identity in primitive_ids for subject in by_id.get(identity, ())))


def _contrast_warnings_from_findings(
    findings: tuple[SceneContrastFinding, ...], provenance: tuple[PrimitiveProvenance, ...] = (),
) -> tuple[SceneContrastWarning, ...]:
    warnings = []
    for group in group_contrast_findings(findings):
        finding = group[0]
        if finding.severity != "warning":
            continue
        facts: list[tuple[str, float | str]] = []
        for name, value in (("contrastRatio", finding.contrast_ratio), ("floor", finding.floor),
                            ("exceptionMinimum", finding.exception_minimum),
                            ("exceptionReason", finding.exception_reason),
                            ("groundId", finding.ground_id), ("groundKind", finding.ground_kind),
                            ("paintChannel", finding.paint_channel)):
            if value is not None:
                facts.append((name, value))
        if finding.encoding is not None:
            facts.extend((name, value) for name, value in (
                ("scaleId", finding.encoding.scale_id), ("field", finding.encoding.field),
                ("value", finding.encoding.value)))
        primitive_ids = tuple(dict.fromkeys(item.primitive_id for item in group if item.primitive_id is not None))
        pair = tuple(finding.encoding_pair.as_mapping().items()) if (
            finding.code == "W_SCENE_ENCODING_CONTRAST" and finding.encoding_pair is not None) else ()
        ground_ids = tuple(dict.fromkeys(item.ground_id for item in group if item.ground_id is not None))
        if pair:
            facts.extend((name, value) for name, value in pair if name not in {"contrastRatio", "floor"})
        warnings.append(SceneContrastWarning(
            finding.code, finding.accepted_code or WARNING_BLOCKING_CODES.get(finding.code, finding.code),
            finding.scene_path,
            primitive_ids, tuple(facts), finding.disposition,
            _finding_subjects(primitive_ids, provenance), finding.encoding, pair, ground_ids))
    return tuple(warnings)


def _warnings_from_findings(
    findings: tuple[ScenePerceptibilityFinding, ...], provenance: tuple[PrimitiveProvenance, ...] = (),
) -> tuple[ScenePerceptibilityWarning, ...]:
    return tuple(ScenePerceptibilityWarning(
        "W_" + finding.code.removeprefix("E_"), finding.code, finding.scene_path,
        finding.primitive_ids, finding.slot_id, finding.measured_facts, finding.disposition,
        _finding_subjects(finding.primitive_ids, provenance),
    ) for finding in findings if finding.severity == "error")


def _annotation_kind_colors(theme: Mapping[str, Any]) -> dict[str, str]:
    """The resolved colour of each Theme-declared annotation kind that has one (#584)."""
    kinds = theme["body"].get("annotationKinds", {})
    return {str(kind): str(entry["color"]) for kind, entry in kinds.items() if "color" in entry}


def _annotation_kind_also(theme: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    """The extra elements (header, leader) each kind colour also paints (#991)."""
    kinds = theme["body"].get("annotationKinds", {})
    return {str(kind): tuple(str(item) for item in entry["colorAlso"]) for kind, entry in kinds.items() if entry.get("colorAlso")}


def _other_color(theme: Mapping[str, Any], legend_colors: tuple[str, ...]) -> str | None:
    """The first neutral candidate no non-category legend entry already uses, so "Other" is its own colour (#1628)."""
    candidates = theme["body"].get("otherColors") or ()
    for candidate in candidates:
        if all(delta_e_2000(candidate, used) >= MINIMUM_CATEGORY_DELTA_E for used in legend_colors):
            return candidate
    return candidates[-1] if candidates else None


def _tint_other_color(theme: Mapping[str, Any], *, scale_id: str) -> str | None:
    """Folded group tints take a light neutral ground that keeps header text readable, apart from the scale's own tints (#1628)."""
    body = theme["body"]
    slots = (body.get("colorScales", {}).get(scale_id) or {}).get("palette") or ()
    used = tuple(body["categorySlots"][slot] for slot in slots if slot in body.get("categorySlots", {}))
    candidates = body.get("tintOtherColors") or ()
    for candidate in candidates:
        if all(delta_e_2000(candidate, colour) >= MINIMUM_CATEGORY_DELTA_E for colour in used):
            return candidate
    return candidates[-1] if candidates else _other_color(theme, ())


def _legend_colors(theme: Mapping[str, Any], detail: Any) -> tuple[str, ...]:
    """Colours of the Detail legend's non-category entries (Planned, Milestone, Dependency, Today ...).

    A categorical scale must not reuse their hue, nor may its "Other" share one (#1628).
    """
    if detail is None:
        return ()
    body = theme["body"]
    roles, values = body.get("roles", {}), body.get("values", {})
    colours: list[str] = []
    for entry in detail.legend:
        role = entry.role
        if role in ("asOf", "deadlineMark"):
            role = semantic_binding(role).scene_role
        else:
            role = resolve_point_paint_role(role, gate_declared="gate" in roles, legend=True)
        binding = roles.get(role, {})
        for channel in ("fill", "stroke"):
            token = values.get(binding.get(channel)) if isinstance(binding.get(channel), str) else None
            colour = token.get("value") if isinstance(token, Mapping) and token.get("type") == "color" else None
            if isinstance(colour, str) and colour not in colours:
                colours.append(colour)
                break
    return tuple(colours)


def _scale_folded_info(scale: Any) -> ScaleValuesFolded:
    return ScaleValuesFolded(scale.scale_id, scale.source_field, scale.palette_size, scale.folded)


def _resolve_group_tints(view: Any, projection: Any, theme: Mapping[str, Any]
                         ) -> tuple[tuple[tuple[str, str], ...], tuple[Any, ...], Any]:
    """Resolve the View's per-group tint scale to one colour per group, in display order (#583)."""
    tint = view.grouping.tint if view.grouping is not None else None
    if tint is None:
        return (), (), None
    groups = projection.group_ids
    source_field = view.grouping.field or getattr(view.grouping.by, "value", view.grouping.by)
    scale = resolve_color_scale(
        {"scale": tint.scale, "target": "group", "source": {"field": source_field},
         "domain": list(tint.domain) if tint.domain is not None else "firstAppearance"},
        theme["body"].get("colorScales"), theme["body"].get("categorySlots"),
        source_ref="/body/grouping/tint",
        observed=groups,
        other_color=_tint_other_color(theme, scale_id=tint.scale))
    if scale is None:
        return (), (), None
    return tuple((group, scale.color_for(group, {scale.source_field: group})) for group in groups), scale.collisions, scale


def _observed_scale_values(encoding: Any, projection: Any) -> tuple[str, ...]:
    """Source values of the selected primary items, in projection order, for a derived domain."""
    source = encoding.get("source") if isinstance(encoding, Mapping) else None
    if not isinstance(source, Mapping):
        return ()
    values: list[str] = []
    for item in projection.items:
        result = item.field_bindings.read_result(item.fields, source, object_id=item.object_id)
        if result.value is not None:
            values.append(scale_text(result.value) or str(result.value))
    return tuple(values)


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
                    manifests: dict[str, dict[str, Any]], scheduler: Scheduler,
                    extra_diagnostics: tuple[Diagnostic, ...] = (),
                    draft_snapshot_manifests: Mapping[str, Any] | None = None) -> Any:
    """Schedule the Project, and its Snapshot when one is bound, then project the review."""
    result = scheduler.schedule(project, extension_diagnostics=[*extra_diagnostics, *validate_profiles(project, manifests)])
    if not result.ok:
        raise RenderRejected(result.diagnostics)
    field_bindings, descriptor_diagnostics = resolve_source_field_bindings(project, manifests)
    if descriptor_diagnostics:
        raise RenderRejected(list(descriptor_diagnostics))
    ordering = period_range_diagnostics(project, result.placements)  # only placements can order a referenced period (#582)
    if ordering:
        raise RenderRejected(list(ordering))
    actual = closure.actual_set.observations_input if closure.actual_set is not None else None
    forecast = forecast_schedule(project, result, actual, scheduler) if getattr(closure.context, "forecast", False) else None
    if forecast is not None:
        if not forecast.ok:
            raise RenderRejected(forecast.diagnostics)
        _require_forecast_presentation(view, closure.layout_profile.layout_input)
    snapshot_project = closure.snapshot_project.scheduler_input if closure.snapshot_project is not None else None
    snapshot_manifests = ({item.package_id: item.profile_input
                          for item in closure.profile_packages_for(closure.snapshot_project)}
                         if snapshot_project is not None and closure.profile_packages
                         else dict(draft_snapshot_manifests or {}))
    snapshot_result = (scheduler.schedule(snapshot_project,
                                         extension_diagnostics=validate_profiles(snapshot_project, snapshot_manifests))
                       if snapshot_project is not None else None)
    if snapshot_result is not None and not snapshot_result.ok:
        raise RenderRejected(snapshot_result.diagnostics)
    snapshot_field_bindings = None
    if snapshot_project is not None:
        snapshot_field_bindings, descriptor_diagnostics = resolve_source_field_bindings(
            snapshot_project, snapshot_manifests)
        if descriptor_diagnostics:
            raise RenderRejected(list(descriptor_diagnostics))
    scenario_ids = ({view.comparison.scenario_id} if view.comparison.baseline == "scenario" else set())
    scenario_ids.update(item.scenario_id for row in view.rows.items for item in row.items if item.source_kind == "scenario")
    if None in scenario_ids:
        raise RenderFailed("E_SCENARIO_REQUIRED", "Scenario source requires a scenario id", "view")
    scenarios = {}
    scenario_field_bindings = {}
    provenance = []
    for scenario_id in sorted(scenario_ids):
        try:
            resolved = resolve_scenario(project, scenario_id)
            scenario_project = resolved.project
        except ScenarioError as error:
            raise RenderFailed(error.diagnostic.id, error.diagnostic.message, "scenario") from error
        scenario_result = scheduler.schedule(scenario_project,
                                             extension_diagnostics=validate_profiles(scenario_project, manifests))
        if not scenario_result.ok:
            raise RenderRejected(scenario_result.diagnostics)
        source_bindings, descriptor_diagnostics = resolve_source_field_bindings(scenario_project, manifests)
        if descriptor_diagnostics:
            raise RenderRejected(list(descriptor_diagnostics))
        scenario_field_bindings[scenario_id] = source_bindings
        scenarios[scenario_id] = (scenario_project, scenario_result.placements)
        provenance.append(resolved.provenance)
    projection = build_review_projection(
        project, result.placements, view, actual,
        snapshot_project=snapshot_project,
        snapshot_placements=snapshot_result.placements if snapshot_result is not None else None,
        scenarios=scenarios,
        analysis=result.analysis,
        snapshot_analysis=snapshot_result.analysis if snapshot_result is not None else None,
        forecast=forecast,
        field_bindings=field_bindings,
        snapshot_field_bindings=snapshot_field_bindings,
        scenario_field_bindings=scenario_field_bindings,
        wording=wording_resolver(closure.context.environment.locale, view.wording),
    )
    if forecast is not None:
        _require_forecast_occurrence_coverage(view, projection)
    global_figures, group_figures = (), ()
    late_ids = {item.figure_id for item in deferred_layout_figures(view.figures)}
    figure_diagnostics = []
    try:
        resolution = _figure_resolution(project, result.placements,
            replace(view, figures=tuple(item for item in view.figures if item.scope == "global"
                                       and item.figure_id not in late_ids)), actual,
            project_last_finish=projected_last_planned_finish(projection.items),
            counts=projected_counts(projection.items, as_of_available=
                                   ((actual or {}).get("body") or {}).get("asOf") is not None),
            filtered_counts=filtered_figure_counts(view.figures, projection.items, grouping=view.grouping,
                                                   as_of_available=((actual or {}).get("body") or {}).get("asOf") is not None))
        global_figures = tuple(resolution.values.items())
        binding_ids = {item.figure.figure_id for item in view.profile_bindings if item.figure is not None}
        unavailable_figures = tuple(item for item in resolution.diagnostics
            if item.details.get("figure") in binding_ids
            and item.id in {"E_FIGURE_ASOF_MISSING", "E_FIGURE_PROJECT_FINISH_MISSING"})
        figure_diagnostics.extend(item for item in resolution.diagnostics if item not in unavailable_figures)
    except RenderRejected as error:
        figure_diagnostics.extend(error.diagnostics)
    try:
        group_figures = _resolved_group_figures(project, result.placements, view, actual, projection)
    except RenderRejected as error:
        figure_diagnostics.extend(error.diagnostics)
    if figure_diagnostics:
        raise RenderRejected(figure_diagnostics)
    finish_overrides = forecast_deadline_placements(projection) if forecast is not None else None
    deadline_results = deadline_statuses(project, result.placements, finish_overrides)
    shown_deadlines = _shown_deadlines(project, deadline_results, view)
    network = _network_deadline_projection(projection.network, shown_deadlines)
    projection = replace(projection, periods=_selected_periods(project, result.placements, view, dict(global_figures)),
                         figures=global_figures, group_figures=group_figures,
                         unavailable_figures=unavailable_figures,
                         deadlines=shown_deadlines, network=network)
    return (projection, tuple(provenance), attachment_warnings(project, result.placements),
            deadline_warnings_from_statuses(deadline_results, forecast_mode=forecast is not None))


def _require_forecast_presentation(view: ViewInput, layout: Mapping[str, Any]) -> None:
    """Check declared capabilities, never invent a View selection or Layout slot."""
    missing = []
    if view.surface != "table-timeline":
        missing.append("table-timeline surface")
    labels = view.visibility.labels
    plot_delta = (isinstance(labels, Mapping) and labels.get("placement") in {"plot", "both"}
                  and "finishDelta" in labels.get("content", ()))
    table_delta = (view.rows.mode != "lanes" and any(
        isinstance(column.source, Mapping) and
        (column.source.get("facet") == "finishDelta" or column.source.get("comparisonFacet") == "finishDelta")
        for column in view.table_columns))
    if not (plot_delta or table_delta):
        missing.append("per-item finishDelta channel")
    pending = [layout.get("root", {})]
    legend = False
    while pending:
        node = pending.pop()
        legend |= node.get("kind") == "slot" and node.get("source") == "legend"
        pending.extend(node.get("children", ()))
    if not legend:
        missing.append("legend slot")
    if missing:
        raise RenderFailed("E_FORECAST_PRESENTATION_REQUIRED",
                           "Forecast requires " + ", ".join(missing) +
                           "; choose a capable View/Layout (for example technical-print or target-b)",
                           "presentation", "/body/forecast")


def _require_forecast_occurrence_coverage(view: ViewInput, projection: Any) -> None:
    """A declared cell covers its exact subject, never every item in the row."""
    labels = view.visibility.labels
    if (isinstance(labels, Mapping) and labels.get("placement") in {"plot", "both"}
            and "finishDelta" in labels.get("content", ())):
        return
    for row in projection.rows:
        for item in row.items:
            if (item.forecast is not None and item.temporal_paint
                    and (item.item_id or item.object_id) != row.table_subject_id):
                occurrence = f"{row.row_id}:{item.item_id or item.object_id}"
                raise RenderFailed("E_FORECAST_PRESENTATION_REQUIRED",
                    f"Forecast occurrence {occurrence!r} has no delta cell; declare a plot finishDelta channel",
                    "presentation", "/body/rows")
    for folded in projection.folded_points:
        for item in folded.all_items:
            if item.forecast is not None and item.temporal_paint:
                occurrence = f"group-header:{folded.group_id}:{item.item_id or item.object_id}"
                raise RenderFailed("E_FORECAST_PRESENTATION_REQUIRED",
                    f"Folded forecast occurrence {occurrence!r} has no table cell; declare a plot finishDelta channel",
                    "presentation", "/body/rows/points")


def _complete_annotation_headers(content: SurfaceContentInput, theme: Mapping[str, Any],
                                 projection: Any, view: ViewInput, resolver: Any = None) -> SurfaceContentInput:
    """Compose kind text with explicit View facts before source measurement or Layout."""
    tokens = ThemeTokenView(theme)
    figures = dict(projection.figures)
    scoped = {figure_id for _, values in projection.group_figures for figure_id, _ in values}
    late_ids = {item.figure_id for item in deferred_layout_figures(view.figures)}
    annotations = []
    for annotation in content.annotations:
        token = tokens.annotation_kind(annotation.kind, resolver)
        if token is None:
            annotations.append(annotation)
            continue
        escaped_kind = annotation.kind.replace("~", "~0").replace("/", "~1")
        for field, parts in (("title", token.header.parts), ("heading", token.header.heading_parts)):
            for kind, value in parts:
                if kind != "field" or not value.startswith("figure:"):
                    continue
                figure_id = value[len("figure:"):]
                if figure_id in late_ids:
                    raise RenderFailed("E_FIGURE_LAYOUT_SCOPE", "placedNotes is unavailable before completed Layout",
                                       "presentation", f"/body/annotationKinds/{escaped_kind}/{field}")
                if figure_id not in figures:
                    code = "E_FIGURE_SCOPE_UNAVAILABLE" if figure_id in scoped else "E_VIEW_FIGURE_UNKNOWN"
                    raise RenderFailed(code, f"annotation kind {annotation.kind} {field} cannot read global figure "
                                       f"{figure_id}; declared global figures: {', '.join(figures) or 'none'}",
                                       "presentation", f"/body/annotationKinds/{escaped_kind}/{field}")
        try:
            annotations.append(replace(annotation,
                kind_header_lines=header_lines(token.header, subject=annotation.subject,
                                               subject_id=annotation.subject_id, figures=figures),
                kind_heading_text=heading_text(token.header, subject=annotation.subject,
                                                subject_id=annotation.subject_id, figures=figures)))
        except AnnotationKindTextError as error:
            raise RenderFailed(error.code, error.detail, "presentation",
                               f"/body/annotationKinds/{escaped_kind}") from error
    return replace(content, annotations=tuple(annotations))


def _check_summary_figures(summary: Any, projection: Any, view: ViewInput, *,
                          omitted_metrics: frozenset[tuple[int, int]] = frozenset()) -> None:
    """A Summary Profile metric naming a figure must name one the View declared, in a format an integer has (#586)."""
    declared = dict(projection.figures)
    kinds = {item.figure_id: item.kind for item in view.figures}
    late_ids = {item.figure_id for item in deferred_layout_figures(view.figures)}
    for panel_index, panel in enumerate(summary.panels if summary is not None else ()):
        for metric_index, metric in enumerate(panel.metrics):
            if (panel_index, metric_index) in omitted_metrics:
                continue
            source = getattr(metric, "source", None)
            if not isinstance(source, Mapping) or "figure" not in source:
                continue
            path = f"/body/panels/{panel.id}/metrics/{metric.id}"
            if source["figure"] in late_ids:
                raise RenderFailed("E_FIGURE_LAYOUT_SCOPE", "placedNotes is unavailable to Summary metrics",
                                   "presentation", f"/body/panels/{panel_index}/metrics/{metric_index}/source/figure")
            if source["figure"] not in declared:
                scoped = {figure_id for _, values in projection.group_figures for figure_id, _ in values}
                if source["figure"] in scoped:
                    raise RenderFailed("E_FIGURE_SCOPE_UNAVAILABLE",
                                       f"summary metric {metric.id} names group-scoped figure {source['figure']} without a current group",
                                       "presentation", path)
                known = ", ".join(declared) if declared else "none"
                raise RenderFailed("E_VIEW_FIGURE_UNKNOWN",
                                   f"summary metric {metric.id} names figure {source['figure']}, which the View does not declare (declared: {known})",
                                   "presentation", path)
            if metric.format == "date" or (metric.format == "signedDays" and kinds.get(source["figure"]) == "count"):
                raise RenderFailed("E_PRESENTATION_SUMMARY_FORMAT",
                                   f"summary metric {metric.id} cannot format {kinds.get(source['figure'])} figure "
                                   f"{source['figure']} as {metric.format}",
                                   "presentation", f"{path}/format")


def _resolved_figures(project: dict[str, Any], placements: dict[str, dict[str, Any]], view: ViewInput,
                      actual: Mapping[str, Any] | None, *,
                      group_first_start: date | None = None,
                      project_last_finish: date | None = None,
                      counts: FigureCounts | None = None,
                      filtered_counts: Mapping[str, FigureCounts] | None = None) -> tuple[tuple[str, int], ...]:
    resolution = _figure_resolution(project, placements, view, actual,
                                   group_first_start=group_first_start, project_last_finish=project_last_finish,
                                   counts=counts, filtered_counts=filtered_counts)
    if resolution.diagnostics:
        raise RenderRejected(list(resolution.diagnostics))
    return tuple(resolution.values.items())


def _figure_resolution(project: dict[str, Any], placements: dict[str, dict[str, Any]], view: ViewInput,
                       actual: Mapping[str, Any] | None, *, group_first_start: date | None = None,
                       project_last_finish: date | None = None,
                       counts: FigureCounts | None = None,
                       filtered_counts: Mapping[str, FigureCounts] | None = None) -> FigureResolution:
    """Every figure the View declares, computed by the Core from the facts gathered here (#586).

    This is the one place the as-of, the placements, the resolved periods and the Project calendars are
    collected; the arithmetic is Core's. A finding yields no number; the caller
    distinguishes strict consumers from unavailable Summary connections.
    """
    if not view.figures:
        return FigureResolution({}, ())
    as_of = ((actual or {}).get("body") or {}).get("asOf")
    return resolve_figures(
        view.figures, as_of=date.fromisoformat(as_of) if isinstance(as_of, str) else None, placements=placements,
        periods=resolve_periods(project, placements),
        calendars={key: Calendar.from_mapping(value) for key, value in (project.get("calendars") or {}).items()},
        default_calendar=(project.get("project") or {}).get("calendar"), group_first_start=group_first_start,
        counts=counts, project_last_finish=project_last_finish, filtered_counts=filtered_counts)


def _resolved_group_figures(project: dict[str, Any], placements: dict[str, dict[str, Any]], view: ViewInput,
                            actual: Mapping[str, Any] | None, projection: Any
                            ) -> tuple[tuple[str, tuple[tuple[str, int], ...]], ...]:
    """Gather selected Primary dates per semantic group; Core only receives neutral dates."""
    specs = tuple(item for item in view.figures if item.scope == "group")
    if not specs:
        return ()
    group_ids = projection.group_ids
    if not group_ids:
        raise RenderRejected([Diagnostic("E_FIGURE_GROUP_UNAVAILABLE",
                                         f"Figure {item.figure_id} requires a current group, but the View projects none",
                                         f"{item.path}/scope") for item in specs])
    scoped_view = replace(view, figures=specs)
    values = []
    diagnostics = []
    for group_id in group_ids:
        member_ids = {item.object_id for item in projection.group_member_items(group_id)
                      if item.source_kind in {"primary", "combined"}}
        members = tuple(item for item in projection.items
                        if item.source_kind == "primary" and item.object_id in member_ids)
        starts = tuple(item.planned.get("start", item.planned.get("at")) for item in members)
        dates = tuple(item for item in starts if isinstance(item, date))
        try:
            resolved = _resolved_figures(project, placements, scoped_view, actual,
                                         group_first_start=min(dates) if dates else None,
                                         project_last_finish=projected_last_planned_finish(projection.items),
                                         counts=projected_counts(members, as_of_available=
                                             ((actual or {}).get("body") or {}).get("asOf") is not None),
                                         filtered_counts=filtered_figure_counts(
                                             specs, members, grouping=view.grouping, as_of_available=
                                             ((actual or {}).get("body") or {}).get("asOf") is not None))
            values.append((group_id, resolved))
        except RenderRejected as error:
            diagnostics.extend(replace(item, message=f"Group {group_id}: {item.message}")
                               for item in error.diagnostics)
    if diagnostics:
        raise RenderRejected(diagnostics)
    return tuple(values)


def _shown_deadlines(project: dict[str, Any], statuses: tuple[DeadlineStatus, ...], view: ViewInput) -> tuple[ReviewDeadline, ...]:
    """The Project deadlines the View asks to draw, using Core's selected finish basis (#822).

    ``slipped`` keeps the objects whose selected planned/forecast finish is after deadline; ``all`` keeps every object
    that has a deadline. Layout receives the verdict and draws it; it compares no dates.
    """
    if view.deadlines is None:
        return ()
    overrides = dict(view.deadlines.overrides)
    objects = project.get("objects", {})
    for object_id in overrides:
        if object_id not in objects:
            known = ", ".join(objects) if objects else "none"
            raise RenderFailed("E_VIEW_DEADLINE_OBJECT_UNKNOWN",
                               f"deadline override names object {object_id}, which the Project does not declare (declared: {known})",
                               "view", f"/body/deadlines/overrides/{object_id}")
    shown = []
    for item in statuses:
        show = overrides.get(item.object_id, view.deadlines.show)
        if show == "hidden" or (not item.slipped and show != "all"):
            continue
        caption = None
        if item.slipped and view.deadlines.caption is not None:
            try:
                caption = view.deadlines.caption.bind(item.days_late)
            except CountTextError as error:
                raise RenderFailed(error.code, error.detail, "view", "/body/deadlines/caption/format") from error
        shown.append(ReviewDeadline(item.object_id, item.deadline, item.deadline_boundary,
                                    item.finish_boundary, item.slipped, item.days_late, caption))
    return tuple(shown)


def _network_deadline_projection(network: Any, deadlines: tuple[ReviewDeadline, ...]) -> Any:
    """Attach only selected primary-node deadline copy before Layout sees the projection."""
    if network is None or not deadlines:
        return network
    by_object = {item.object_id: item for item in deadlines}
    nodes = tuple(
        replace(node, deadline=(NetworkDeadlineContent(
            item.object_id,
            item.deadline.isoformat() + (f" {item.caption}" if item.slipped and item.caption else ""),
            item.slipped,
        ) if node.source_kind == "primary" and (item := by_object.get(node.object_id)) is not None else None))
        for node in network.nodes
    )
    return replace(network, nodes=nodes)


def _selected_periods(project: dict[str, Any], placements: dict[str, dict[str, Any]], view: ViewInput,
                      figures: Mapping[str, int] | None = None) -> tuple[ReviewPeriod, ...]:
    """The Project periods the View names, as dates, in the View's order (#582).

    A View naming a period the Project does not declare is refused with the declared identifiers, never
    skipped: a silently missing band would read as a period that has no extent.
    """
    if not view.periods:
        return ()
    declared = {item.period_id: item for item in resolve_periods(project, placements)}
    selected_periods = (tuple(ViewPeriod(period_id, view.periods.label) for period_id in declared)
                        if isinstance(view.periods, ViewAllPeriods) else view.periods)
    for index, selected in enumerate(selected_periods):
        if selected.period_id not in declared:
            known = ", ".join(declared) if declared else "none"
            raise RenderFailed("E_VIEW_PERIOD_UNKNOWN",
                               f"the View selects period {selected.period_id}, which the Project does not declare (declared: {known})",
                               "presentation", f"/body/periods/{index}/id")
    def caption(selected: Any, item: Any, index: int) -> str:
        if selected.label is None or selected.label.template is None:
            return selected.label.text if selected.label is not None and selected.label.text is not None else item.title
        try:
            return resolve_figure_text(selected.label.template, figures or {}, strict=True)
        except FigureTextError as error:
            path = ("/body/periods/label/template" if isinstance(view.periods, ViewAllPeriods)
                    else f"/body/periods/{index}/label/template")
            raise RenderFailed(error.code, error.detail, "presentation", path) from error
    return tuple(ReviewPeriod(item.period_id, caption(selected, item, index), item.start, item.end,
                              selected.label.placement if selected.label else None,
                              selected.label.overflow if selected.label else "visible-overflow", selected.variant)
                 for index, (selected, item) in enumerate((selected, declared[selected.period_id]) for selected in selected_periods))


def _font_metrics(theme: dict[str, Any], font_metrics: dict[str, Any], asset_root: Path,
                  asset_resolver: FontAssetResolver | None = None) -> Any:
    try:
        return resolve_font_metrics_catalog(font_metrics, asset_root=asset_root, asset_resolver=asset_resolver)
    except FontMetricsError as error:
        raise _font_failure(error) from error


def _font_failure(error: FontMetricsError) -> RenderFailed:
    return RenderFailed(error.diagnostic_id, error.detail or "declared font metrics are unavailable",
                        "presentation", "/body/environment/fontMetrics")
