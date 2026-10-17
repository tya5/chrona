"""Render one immutable Render Context closure into a review surface.

This is the whole render use case: it owns the order of the pipeline —
closure, schedule, projection, content, measurement, layout, scene, render —
so that no adapter has to know it. A caller supplies an already-resolved
closure and receives an SVG or a stable diagnostic; nothing here reads
command-line arguments, writes files, or prints.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field, replace
from datetime import date
from importlib.metadata import version
from pathlib import Path
from typing import Any, Mapping

from chrona.usecases.previous_scene import decode_previous_scene

from chrona.core.diagnostics import Diagnostic
from chrona.usecases.diagnostic_messages import error_message
from chrona.usecases.warning_ledger import RenderWarning, collect_render_warnings
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject, PrimitiveProvenance
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
from chrona.presentation.model.font_metrics import FontGlyphSubstitution, FontMetricsError, FontTabularWarning, resolve_font_metrics_catalog
from chrona.presentation.model.font_resources import FontAssetResolver
from chrona.presentation.model.color_separability import ScaleCollision
from chrona.presentation.model.info_diagnostics import PresentationInfo, UnboundSummarySource, FontGlyphFallback, ScaleValuesFolded
from chrona.presentation.model.field_role_view import resolve_field_role_view
from chrona.presentation.contracts.resources import ContractError, ViewAllPeriods, ViewPeriod
from chrona.presentation.model.preset_target import PresetVisualProfileFallback
from chrona.presentation.model.render_progress import RenderProgress
from chrona.presentation.fonts.resolution import resolve_theme_font_stacks
from chrona.presentation.fonts.system import DraftFontResolution
from chrona.presentation.model.theme_role_consumers import unread_diagnostics as unread_theme_diagnostics
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView, effective_draft_numeric_theme
from chrona.core.attachments import AttachmentWarning, attachment_warnings
from chrona.core.deadlines import deadline_statuses, deadline_warnings
from chrona.presentation.count_text import CountTextError
from chrona.core.figures import FigureCounts, FigureResolution, resolve_figures
from chrona.core.periods import period_range_diagnostics, resolve_periods
from chrona.core.temporal import Calendar
from chrona.presentation.model.color_scale import ColorScaleError, resolve_color_scale
from chrona.presentation.model.color_separability import MINIMUM_CATEGORY_DELTA_E, MINIMUM_RESERVED_CHROMA, chroma, delta_e_2000
from chrona.presentation.model.point_paint import resolve_point_paint_role
from chrona.presentation.model.semantic_registry import semantic_binding
from chrona.presentation.model.axis_color_scale import (
    AxisBandScaleError, resolve_axis_band_scales, validate_axis_band_fill_targets,
)
from chrona.presentation.model.projection import ReviewDeadline, ReviewPeriod, build_review_projection
from chrona.presentation.model.actual_variance_paint import resolve_actual_variance_colors
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.contracts.resources import ViewInput
from chrona.presentation.review.detail import ReviewDetailError
from chrona.presentation.review.figure_facts import deferred_layout_figures, projected_counts, projected_last_planned_finish
from chrona.presentation.review.annotation_expansion import AnnotationExpansionError
from chrona.presentation.review.profile_connections import ProfileConnectionError, resolve_profile_connections
from chrona.presentation.annotation_kind_text import AnnotationKindTextError, header_lines, heading_text
from chrona.presentation.figure_text import FigureTextError, FigureTextReadError, resolve_figure_text
from chrona.presentation.review.v05_content import (
    compose_heading, normalize_summary_content, normalize_v05_surface_content, normalize_v05_table_content)
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
    asset_resolver: FontAssetResolver | None = None
    draft_auto_block: bool = False
    draft_font_resolution: DraftFontResolution | None = None
    preset_visual_profile_fallback: PresetVisualProfileFallback | None = None
    progress: RenderProgress | None = field(default=None, compare=False, repr=False)


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
    """One decoration finding that missed its floor or could not be judged, reported and never blocking (#995)."""

    code: str
    finding_code: str
    scene_path: str
    primitive_ids: tuple[str, ...]
    measured_facts: tuple[tuple[str, float | str], ...]
    disposition: str | None
    subjects: tuple[DiagnosticSubject, ...] = ()


class ClosureReadLedger:
    """Records named typed-closure dependencies without generic kind lookup."""

    def __init__(self, closure: RenderClosure):
        self._declared = {item.kind for item in closure.resources}
        if closure.previous_scene_bytes is not None:
            self._declared.add("previous-scene")
        self.read: set[str] = set()

    def required(self) -> None:
        self.read.update({"project", "view", "layout-profile", "theme", "color-scheme"})

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
    except ColorScaleError as error:
        raise RenderFailed(error.code, error.detail, "presentation", error.source_ref) from error
    except AnnotationExpansionError as error:
        raise RenderFailed(error.diagnostic_id, error.detail, "presentation", error.source_ref) from error
    except ProfileConnectionError as error:
        raise RenderFailed(error.code, error.detail, error.component, error.source_ref) from error
    except (LayoutError, ThemeTokenError, ScenePaintError) as error:
        message = error_message(error.diagnostic_id, getattr(error, "detail", None))
        node = getattr(error, "node_id", None)  # a Layout finding names the offending token or node here
        raise RenderFailed(error.diagnostic_id, f"{message} ({node})" if node else message,
                           "presentation", error.path or "/") from error


def _render_review(request: RenderRequest) -> RenderedReview:
    """Render one closure, in the one order the pipeline has."""
    render_closure, ledger = request.closure, ClosureReadLedger(request.closure)
    previous_scene = None
    if render_closure.previous_scene_bytes is not None:
        previous_scene = decode_previous_scene(render_closure.previous_scene_bytes,
            render_closure.project.identity.id,
            current_theme_identity=next((item.content_identity for item in render_closure.resources
                                         if item.kind == "theme"), None))
        ledger.read.add("previous-scene")
    project, view, layout = (render_closure.project.scheduler_input, render_closure.view.view,
                             render_closure.layout_profile.layout_input)
    try:
        view, field_role_info = resolve_field_role_view(view, project)
    except ContractError as error:
        raise RenderFailed(error.diagnostic_id, error.detail, "view", error.source_ref) from error
    profile_connections = resolve_profile_connections(
        view, render_closure.summary_profile.summary if render_closure.summary_profile else None,
        render_closure.detail_profile.detail if render_closure.detail_profile else None,
        project_object_ids=frozenset(project.get("objects", {})))
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
    manifests = {item.package_id: item.profile_input for item in render_closure.profile_packages}
    if manifests:
        ledger.packages()
    if request.progress is not None:
        request.progress.phase("schedule")
    projection, scenario_provenance, attachments, deadlines = _project_review(project, view, render_closure, manifests, request.scheduler)
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
                                      color_vision=tuple(theme["body"].get("colorVision", ())),
                                      observed=_observed_scale_values(view.color_encoding, projection),
                                      reserved=tuple(c for c in legend_colors if chroma(c) >= MINIMUM_RESERVED_CHROMA),
                                      other_color=_other_color(theme, legend_colors))
    group_tints, group_tint_collisions, _group_tint_scale = _resolve_group_tints(view, projection, theme)
    profile_info += tuple(_scale_folded_info(scale) for scale in (color_scale, _group_tint_scale) if scale is not None and scale.folded)
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
                                               asset_resolver=request.asset_resolver)
    if resolution is not None and resolution.tabular_warnings:
        theme = effective_draft_numeric_theme(theme, tuple(item.role for item in resolution.tabular_warnings))
    font_metrics = resolution.metrics if resolution is not None else _font_metrics(
        theme, environment.font_metrics, asset_root, request.asset_resolver)
    _check_summary_figures(profile_connections.summary, projection, view, omitted_metrics=omitted_metrics)
    summary = normalize_summary_content(profile_connections.summary,
                                        projection, render_closure.actual_set.observations_input if render_closure.actual_set else None,
                                        project, omitted_metrics=omitted_metrics,
                                        summary_wording=(view.wording or {}).get("summary", {}))
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
        annotation_kind_also=_annotation_kind_also(theme))
    try:
        validate_axis_band_fill_targets(selected_content.axis_tiers, ThemeTokenView(theme))
        axis_band_scale = resolve_axis_band_scales(
            selected_content.axis_tiers, window=projection.window,
            fiscal_start_month=selected_content.axis_fiscal_start_month,
            scales=theme["body"].get("colorScales", {}), categories=theme["body"].get("categorySlots", {}),
            color_vision=tuple(theme["body"].get("colorVision", ())))
    except AxisBandScaleError as error:
        raise RenderFailed(error.code, error.detail, "presentation", error.path) from error
    selected_content = replace(selected_content, axis_band_paints=axis_band_scale.paints)
    selected_content = _complete_annotation_headers(selected_content, theme, projection, view)
    heading_content = (compose_heading(view, project, actual_observations, environment.locale)
                       if view.surface == "table-timeline" else None)
    try:
        count_input = inspect_count_reads(SurfaceRenderPlanInput(
            previous_route_hints=previous_scene.route_hints if previous_scene is not None else None,
            project=project, view=view, projection=projection, content=selected_content,
            summary=summary, table=table_content, profile=layout, theme=theme,
            font_metrics=font_metrics, heading=heading_content, actual=actual_observations,
            detail=profile_connections.detail,
            viewport_inline=environment.viewport_inline, viewport_block=environment.viewport_block,
            content_sized=request.draft_auto_block, locale=environment.locale,
            capabilities={name: True for name in render_closure.context.target.capabilities},
            icon_assets=icon_assets, visual_requests=visual_requests, progress=request.progress))
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
    scene_input = None
    if plan is not None:
        scene_input = build_surface_input(
            projection=projection, surface_content=plan.content, layout_manifest=plan.manifest,
            resolved_theme=theme, font_metrics=font_metrics, measured_sources=plan.measured,
            capabilities={name: True for name in render_closure.context.target.capabilities},
            visual_profile=visual_profile, viewport=plan.viewport,
            icon_assets=icon_assets, visual_requests=visual_requests,
            fixed_lane_preflight=(plan.preparation.inline.request.fixed_lane_preflight if plan.preparation else None),
            capacity_short_sources=plan.capacity_short_sources, surface_preparation=plan.preparation,
            auto_block_limit=plan.profile.distances.get("/reviewSurface/maxBlockSize"),
            declared_viewport=plan.declared_viewport, progress=request.progress)

    unused = ledger.unused()
    if request.require_all_inputs_read and unused:
        raise RenderFailed("E_CLOSURE_INPUT_UNUSED",
                           "closure inputs loaded but never read: " + ", ".join(unused), "closure")

    try:
        rendered = compose_resolved_review_surface(count_input, visual_profile=visual_profile,
                                                   initial=plan, admitted=scene_input)
        surface, projection, plan = rendered.surface, rendered.projection, rendered.plan
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
        theme["body"], (view, *((render_closure.view.view,) if field_role_info else ()),  # omitted unbound-role columns still read their roles (#1616)
                        layout, render_closure.detail_profile.detail if render_closure.detail_profile else None,
                        render_closure.summary_profile.summary if render_closure.summary_profile else None))
    if unread_roles:
        surface = replace(surface, diagnostics=(*surface.diagnostics, *unread_roles))
    if resolution is not None and resolution.notes:
        surface = replace(surface, diagnostics=(*surface.diagnostics, *resolution.notes))
    glyph_info = tuple(FontGlyphFallback(item.requested_family, item.fallback_family, item.weight,
                                         item.codepoint, item.text)
                       for item in font_metrics.warnings if item.informational)
    if glyph_info:
        surface = replace(surface, info_diagnostics=(*surface.info_diagnostics, *glyph_info))
    try:
        validate_surface_visual_profile(surface, visual_profile)
    except VisualCapabilityError as error:
        raise RenderFailed(error.diagnostic_id, error.message, "presentation", error.path) from error
    collisions = ((color_scale.collisions if color_scale is not None else ())
                  + group_tint_collisions + axis_band_scale.collisions)
    scene = _inspection_scene(render_closure, surface, projection, surface_content,
                              (surface.canvas_bounds[2], surface.canvas_bounds[3]),
                              resolution.tabular_warnings if resolution is not None else (),
                              ())
    perceptibility_warnings = (_scene_perceptibility_warnings(scene, surface.primitive_provenance)
                               if render_closure.context.identity.revision == "draft" else ())
    contrast_warnings = _scene_contrast_warnings(scene, theme, surface.primitive_provenance)
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
    ) for item in substitutions if not item.informational)


def _scene_perceptibility_warnings(
    scene: InspectionScene, provenance: tuple[PrimitiveProvenance, ...] = (),
) -> tuple[ScenePerceptibilityWarning, ...]:
    """Project only evaluator errors into ordered draft feedback facts."""
    return _warnings_from_findings(evaluate_scene_perceptibility(scene_document(scene)), provenance)


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
    findings = evaluate_scene_contrast(scene_document(scene), policy={**DEFAULT_POLICY, **declared},
                                       exceptions=exceptions)
    blocking = [item for item in findings if item.severity == "error" and item.code in BLOCKING_CODES]
    if blocking:
        first = blocking[0]
        member = policy_member_of(first) or "mark"
        ratio = f", contrast {first.contrast_ratio:.3f} against {first.floor:g}" if first.contrast_ratio is not None else ""
        more = f" and {len(blocking) - 1} more" if len(blocking) > 1 else ""
        raise RenderFailed(first.code, f"{first.primitive_id} ({first.visual_role}){ratio}{more}; the Theme declares "
                           f"contrastPolicy.{member}: error", "presentation", f"/body/contrastPolicy/{member}")
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
    for finding in findings:
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
        warnings.append(SceneContrastWarning(
            finding.code, finding.accepted_code or WARNING_BLOCKING_CODES.get(finding.code, finding.code),
            finding.scene_path,
            (finding.primitive_id,) if finding.primitive_id is not None else (), tuple(facts), finding.disposition,
            _finding_subjects((finding.primitive_id,) if finding.primitive_id is not None else (), provenance)))
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
    groups = tuple(dict.fromkeys(row.group_id for row in projection.rows if row.group_id))
    source_field = view.grouping.field or getattr(view.grouping.by, "value", view.grouping.by)
    scale = resolve_color_scale(
        {"scale": tint.scale, "target": "group", "source": {"field": source_field},
         "domain": list(tint.domain) if tint.domain is not None else "firstAppearance"},
        theme["body"].get("colorScales"), theme["body"].get("categorySlots"),
        source_ref="/body/grouping/tint",
        color_vision=tuple(theme["body"].get("colorVision", ())), observed=groups,
        other_color=_other_color(theme, ()))
    if scale is None:
        return (), (), None
    return tuple((group, scale.color_for(group, {scale.source_field: group})) for group in groups), scale.collisions, scale


def _observed_scale_values(encoding: Any, projection: Any) -> tuple[str, ...]:
    """Source values of the selected primary items, in projection order, for a derived domain."""
    source = encoding.get("source") if isinstance(encoding, Mapping) else None
    field = source.get("field") if isinstance(source, Mapping) else None
    if not isinstance(field, str):
        return ()
    return tuple(str(item.fields[field]) for item in projection.items
                 if item.fields is not None and item.fields.get(field) is not None)


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
    ordering = period_range_diagnostics(project, result.placements)  # only placements can order a referenced period (#582)
    if ordering:
        raise RenderRejected(list(ordering))
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
    projection = build_review_projection(
        project, result.placements, view, actual,
        snapshot_project=snapshot_project,
        snapshot_placements=snapshot_result.placements if snapshot_result is not None else None,
        scenarios=scenarios,
        analysis=result.analysis,
        snapshot_analysis=snapshot_result.analysis if snapshot_result is not None else None,
    )
    global_figures, group_figures = (), ()
    late_ids = {item.figure_id for item in deferred_layout_figures(view.figures)}
    figure_diagnostics = []
    try:
        resolution = _figure_resolution(project, result.placements,
            replace(view, figures=tuple(item for item in view.figures if item.scope == "global"
                                       and item.figure_id not in late_ids)), actual,
            project_last_finish=projected_last_planned_finish(projection.items),
            counts=projected_counts(projection.items, as_of_available=
                                   ((actual or {}).get("body") or {}).get("asOf") is not None))
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
    projection = replace(projection, periods=_selected_periods(project, result.placements, view, dict(global_figures)),
                         figures=global_figures, group_figures=group_figures,
                         unavailable_figures=unavailable_figures,
                         deadlines=_shown_deadlines(project, result.placements, view))
    return projection, tuple(provenance), attachment_warnings(project, result.placements), deadline_warnings(project, result.placements)


def _complete_annotation_headers(content: SurfaceContentInput, theme: Mapping[str, Any],
                                 projection: Any, view: ViewInput) -> SurfaceContentInput:
    """Compose kind text with explicit View facts before source measurement or Layout."""
    tokens = ThemeTokenView(theme)
    figures = dict(projection.figures)
    scoped = {figure_id for _, values in projection.group_figures for figure_id, _ in values}
    late_ids = {item.figure_id for item in deferred_layout_figures(view.figures)}
    annotations = []
    for annotation in content.annotations:
        token = tokens.annotation_kind(annotation.kind)
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
                      counts: FigureCounts | None = None) -> tuple[tuple[str, int], ...]:
    resolution = _figure_resolution(project, placements, view, actual,
                                   group_first_start=group_first_start, project_last_finish=project_last_finish, counts=counts)
    if resolution.diagnostics:
        raise RenderRejected(list(resolution.diagnostics))
    return tuple(resolution.values.items())


def _figure_resolution(project: dict[str, Any], placements: dict[str, dict[str, Any]], view: ViewInput,
                       actual: Mapping[str, Any] | None, *, group_first_start: date | None = None,
                       project_last_finish: date | None = None,
                       counts: FigureCounts | None = None) -> FigureResolution:
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
        counts=counts, project_last_finish=project_last_finish)


def _resolved_group_figures(project: dict[str, Any], placements: dict[str, dict[str, Any]], view: ViewInput,
                            actual: Mapping[str, Any] | None, projection: Any
                            ) -> tuple[tuple[str, tuple[tuple[str, int], ...]], ...]:
    """Gather selected Primary dates per semantic group; Core only receives neutral dates."""
    specs = tuple(item for item in view.figures if item.scope == "group")
    if not specs:
        return ()
    group_ids = tuple(dict.fromkeys(row.group_id for row in projection.rows if row.group_id))
    if not group_ids:
        raise RenderRejected([Diagnostic("E_FIGURE_GROUP_UNAVAILABLE",
                                         f"Figure {item.figure_id} requires a current group, but the View projects none",
                                         f"{item.path}/scope") for item in specs])
    scoped_view = replace(view, figures=specs)
    values = []
    diagnostics = []
    for group_id in group_ids:
        member_ids = {item.object_id for row in projection.rows if row.group_id == group_id
                      for item in row.items if item.source_kind in {"primary", "combined"}}
        members = tuple(item for item in projection.items
                        if item.source_kind == "primary" and item.object_id in member_ids)
        starts = tuple(item.planned.get("start", item.planned.get("at")) for item in members)
        dates = tuple(item for item in starts if isinstance(item, date))
        try:
            resolved = _resolved_figures(project, placements, scoped_view, actual,
                                         group_first_start=min(dates) if dates else None,
                                         project_last_finish=projected_last_planned_finish(projection.items),
                                         counts=projected_counts(members, as_of_available=
                                             ((actual or {}).get("body") or {}).get("asOf") is not None))
            values.append((group_id, resolved))
        except RenderRejected as error:
            diagnostics.extend(replace(item, message=f"Group {group_id}: {item.message}")
                               for item in error.diagnostics)
    if diagnostics:
        raise RenderRejected(diagnostics)
    return tuple(values)


def _shown_deadlines(project: dict[str, Any], placements: dict[str, dict[str, Any]], view: ViewInput) -> tuple[ReviewDeadline, ...]:
    """The Project deadlines the View asks to draw, judged by the Core (#822).

    ``slipped`` keeps the objects planned to finish after their deadline, the set `W_DEADLINE` names; ``all`` keeps
    every object that has a deadline. Layout receives the verdict and draws it; it compares no dates.
    """
    if view.deadlines is None:
        return ()
    shown = []
    for item in deadline_statuses(project, placements):
        if not item.slipped and view.deadlines.show != "all":
            continue
        caption = None
        if item.slipped and view.deadlines.caption is not None:
            try:
                caption = view.deadlines.caption.bind(item.days_late)
            except CountTextError as error:
                raise RenderFailed(error.code, error.detail, "view", "/body/deadlines/caption/format") from error
        shown.append(ReviewDeadline(item.object_id, item.deadline, item.finish, item.slipped,
                                    item.days_late, caption))
    return tuple(shown)


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
