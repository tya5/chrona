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
from decimal import Decimal, ROUND_CEILING
from importlib.metadata import version
from pathlib import Path
from typing import Any, Mapping

from chrona.core.diagnostics import Diagnostic
from chrona.usecases.diagnostic_messages import error_message
from chrona.usecases.warning_ledger import RenderWarning, collect_render_warnings
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject, PrimitiveProvenance
from chrona.presentation.scene.viewer_fit import viewer_fit_fallbacks
from chrona.core.ports import RenderArtifact, Renderer, Scheduler
from chrona.extensions.profiles import validate_profiles
from chrona.presentation.layout.engine import (measure_natural_normal_flow_block,
                                               resolve_content_block_extent, solve_layout)
from chrona.presentation.layout.model import LayoutError, LayoutManifest, ResolvedLayoutProfile
from chrona.presentation.layout.group_header_runs import validate_group_header_roles
from chrona.presentation.layout.presentation import validate_label_text_role, validate_table_text_roles
from chrona.presentation.layout.profile import resolve_layout_profile
from chrona.presentation.layout.slot_heading import headed_slot_ids, reserve_slot_heading_blocks
from chrona.presentation.layout.sources import SourceInput, SourceTextRun, measure_sources, resolve_theme_metrics
from chrona.presentation.layout.surface_legend import LegendArrangement, legend_arrangement, legend_source_input
from chrona.presentation.layout.label_visual_measurement import resolve_label_visual_advances
from chrona.presentation.layout.surface_composer import prepare_surface_content, prepare_surface_natural_candidate
from chrona.presentation.layout.surface_content import detail_source_inputs
from chrona.presentation.layout.surface_quality import CapacitySourceEvidence, SurfaceLayoutRequest, VisualRequest
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.closure import ClosureError, RenderClosure
from chrona.presentation.model.font_metrics import FontGlyphSubstitution, FontMetricsError, FontTabularWarning, resolve_font_metrics_catalog
from chrona.presentation.model.font_resources import FontAssetResolver
from chrona.presentation.model.color_separability import ScaleCollision
from chrona.presentation.model.info_diagnostics import PresentationInfo
from chrona.presentation.fonts.system import DraftFontResolution
from chrona.presentation.model.theme_role_consumers import unread_diagnostics as unread_theme_diagnostics
from chrona.presentation.model.theme_tokens import ThemeTokenError, ThemeTokenView, effective_draft_numeric_theme
from chrona.core.attachments import AttachmentWarning, attachment_warnings
from chrona.core.deadlines import deadline_statuses, deadline_warnings
from chrona.core.figures import resolve_figures
from chrona.core.periods import period_range_diagnostics, resolve_periods
from chrona.core.temporal import Calendar
from chrona.presentation.model.color_scale import ColorScaleError, resolve_color_scale
from chrona.presentation.model.axis_color_scale import (
    AxisBandScaleError, resolve_axis_band_scales, validate_axis_band_fill_targets,
)
from chrona.presentation.model.projection import ReviewDeadline, ReviewPeriod, build_review_projection
from chrona.presentation.model.surface_content import HeadingContent, SummaryContent, SurfaceContentInput, TableContent
from chrona.presentation.contracts.resources import ReviewDetailInput, ViewInput, ViewRowMode
from chrona.presentation.review.detail import ReviewDetailError
from chrona.presentation.layout.asof_foot_reserve import BELOW_PLOT, below_plot_reserve
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
    asset_resolver: FontAssetResolver | None = None
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
    contrast_warnings: tuple["SceneContrastWarning", ...] = ()
    info_diagnostics: tuple[PresentationInfo, ...] = ()
    scale_collisions: tuple[ScaleCollision, ...] = ()
    attachment_warnings: tuple[AttachmentWarning, ...] = ()
    deadline_warnings: tuple[Diagnostic, ...] = ()
    warning_records: tuple[RenderWarning, ...] = ()


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
    """Transport detector-owned presentation pointers across the use-case boundary."""
    try:
        return _render_review(request)
    except ColorScaleError as error:
        raise RenderFailed(error.code, error.detail, "presentation", error.source_ref) from error
    except (LayoutError, ThemeTokenError, ScenePaintError) as error:
        message = error_message(error.diagnostic_id, getattr(error, "detail", None))
        node = getattr(error, "node_id", None)  # a Layout finding names the offending token or node here
        raise RenderFailed(error.diagnostic_id, f"{message} ({node})" if node else message,
                           "presentation", error.path or "/") from error


def admit_v05_detail_content(content: SurfaceContentInput, *, detail: ReviewDetailInput | None,
                             layout_manifest: LayoutManifest) -> SurfaceContentInput:
    """Validate Detail panel availability after solve and return the already-normalized content unchanged."""
    available = {item.source for item in layout_manifest.decisions if item.source}
    required = {item.source for item in layout_manifest.decisions
                if item.source and item.kind == "slot" and item.priority == "required"}
    declared = {
        "group-details": bool(detail and detail.group_details),
        "milestones": bool(detail and detail.milestones),
        "observations": bool(detail and detail.observations is not None),
    }
    for source in ("group-details", "milestones", "observations"):
        if declared[source] and source not in available:
            raise ReviewDetailError(f"E_DETAIL_SLOT_REQUIRED: Detail content source {source!r} requires a declared Layout slot")
        if not declared[source] and source in required:
            raise ReviewDetailError(f"E_LAYOUT_SOURCE_UNAVAILABLE: required Layout source {source!r} has no Detail content declaration")
    return content


def _render_review(request: RenderRequest) -> RenderedReview:
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
    projection, scenario_provenance, attachments, deadlines = _project_review(project, view, render_closure, manifests, request.scheduler)
    color_scale = resolve_color_scale(view.color_encoding, theme["body"].get("colorScales"),
                                      theme["body"].get("categorySlots"),
                                      color_vision=tuple(theme["body"].get("colorVision", ())),
                                      observed=_observed_scale_values(view.color_encoding, projection))
    group_tints, group_tint_collisions = _resolve_group_tints(view, projection, theme)
    if render_closure.actual_set is not None:
        ledger.actual()
    if render_closure.snapshot is not None:
        ledger.snapshot()

    environment = render_closure.context.environment
    asset_root = request.asset_root or snapshot_directory(request.snapshot_root, render_closure.context.identity.revision)
    resolution = request.draft_font_resolution
    if resolution is not None and render_closure.context.identity.revision != "draft":
        raise RenderFailed("E_FONT_SYSTEM_IMMUTABLE", "system font resolution cannot render immutable Context", "presentation")
    if resolution is not None and render_closure.context.target.kind not in {"svg", "png"}:
        raise RenderFailed("E_FONT_SYSTEM_IMMUTABLE", "system font resolution cannot render this target", "presentation")
    if resolution is not None and resolution.tabular_warnings:
        theme = effective_draft_numeric_theme(theme, tuple(item.role for item in resolution.tabular_warnings))
    font_metrics = resolution.metrics if resolution is not None else _font_metrics(
        theme, environment.font_metrics, asset_root, request.asset_resolver)
    _check_summary_figures(render_closure.summary_profile.summary if render_closure.summary_profile else None, projection)
    summary = normalize_summary_content(render_closure.summary_profile.summary if render_closure.summary_profile else None,
                                        projection, render_closure.actual_set.observations_input if render_closure.actual_set else None,
                                        project)
    if render_closure.summary_profile is not None:
        ledger.summary()
    icon_assets = {item.icon_id: item for item in render_closure.icon_assets}
    visual_requests = tuple(_visual_request(visual, projection, index, render_closure)
                            for index, visual in enumerate(render_closure.view.view.visuals))
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
    validate_label_text_role(view.visibility.labels, ThemeTokenView(theme))
    if view.grouping is not None and view.grouping.header is not None:
        validate_group_header_roles(view.grouping.header.role_pointers(), ThemeTokenView(theme))
    selected_content = normalize_v05_surface_content(
        projection, project, view, actual_set=actual_observations,
        detail=render_closure.detail_profile.detail if render_closure.detail_profile else None,
        summary=summary, locale=environment.locale, color_scale=color_scale, table=table_content,
        group_tints=group_tints, annotation_kind_colors=_annotation_kind_colors(theme),
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
    heading_content = (compose_heading(view, project, actual_observations, environment.locale)
                       if view.surface == "table-timeline" else None)
    source_inputs = _source_inputs(project, view, projection, summary,
                                   annotation_input=_annotation_source_input(
                                       view, visual_requests, icon_assets, theme),
                                   table=table_content, content=selected_content,
                                   # A dependency network draws its own title line and ignores `heading` (#991).
                                   heading=(heading_content if view.surface == "table-timeline" else None),
                                   view_heading=heading_content or HeadingContent(
                                       str(project.get("project", {}).get("title", ""))))
    required_metrics = (("timeline.groupHeader.blockSize",)
                        if view.grouping is not None and view.grouping.presentation == "header" else ())
    # The legend slot is measured as the legend Layout will draw: the same entries, the same
    # swatch geometry, and the legend slot's own declared arrangement (#497). That needs the
    # resolved Layout Profile, so it is resolved first (it needs only the source names). A Layout
    # Profile error is still reported after any measurement error, as before.
    layout_error: LayoutError | None = None
    try:
        resolved_layout = resolve_layout_profile(layout, available_sources=set(source_inputs), theme=theme)
    except LayoutError as error:
        resolved_layout, layout_error = None, error
    claimed_sources = (_layout_slot_sources(resolved_layout.profile["root"])
                       if resolved_layout is not None else frozenset())
    if view.surface == "dependency-network" and resolved_layout is not None and "title" not in claimed_sources:
        source_inputs.update(_heading_part_sources(
            compose_heading(view, project, actual_observations, environment.locale)))
    try:
        source_inputs["legend"] = legend_source_input(
            selected_content.legend_entries,
            tokens=ThemeTokenView(theme),
            mark_block_size=float(resolve_theme_metrics(theme)["timeline.mark.blockSize"]),
            font_metrics=font_metrics,
            arrangement=legend_arrangement(resolved_layout) if resolved_layout is not None else LegendArrangement())
        measurement_inputs = {source: value for source, value in source_inputs.items()
                              if (not source.startswith("heading.") or source in claimed_sources)
                              and (source != "title" or "title" in claimed_sources)}
        measured = measure_sources(measurement_inputs, theme, font_metrics=font_metrics,
                                   required_metrics=required_metrics)
        # Omitted content remains available for notices, without demanding unused
        # typography or influencing the legacy aggregate measurements.
        measured = replace(measured, inputs=source_inputs)
    except FontMetricsError as error:
        raise _font_failure(error) from error
    if layout_error is not None:
        raise layout_error
    _check_slot_heading_text(view, resolved_layout)
    # A declared slot heading is part of its content-sized slot's measurement (#1064).
    measured = reserve_slot_heading_blocks(measured, resolved_layout, ThemeTokenView(theme), content=selected_content)
    viewport = {"inlineSize": environment.viewport_inline, "blockSize": environment.viewport_block}
    measurements = _slot_measurements(resolved_layout.profile["root"], measured)
    natural_block_floor = max(1, int(measure_natural_normal_flow_block(
        resolved_layout, viewport_inline=viewport["inlineSize"], measurements=measurements
    ).to_integral_value(rounding=ROUND_CEILING))) if request.draft_auto_block else viewport["blockSize"]
    capacity_short_sources = ()
    # An as-of chip placed `below-plot` (#1063) needs its block under the last row, so the timeline asks for it too.
    foot_reserve = Decimal(str(_below_plot_reserve(view, actual_set=actual_observations, projection=projection,
                                                   theme_tokens=ThemeTokenView(theme))))

    def candidate_request(candidate: LayoutManifest, *, short_sources=()) -> SurfaceLayoutRequest:
        content = admit_v05_detail_content(
            selected_content,
            detail=render_closure.detail_profile.detail if render_closure.detail_profile else None,
            layout_manifest=candidate,
        )
        return SurfaceLayoutRequest(
            projection=projection, presentation_contract=normalize_presentation_input(content),
            surface_content=content, layout_manifest=candidate,
            measured_sources=measured, theme_tokens=ThemeTokenView(theme), font_metrics=font_metrics,
            capabilities={name: True for name in render_closure.context.target.capabilities},
            icon_assets=icon_assets, visual_requests=visual_requests,
            capacity_short_sources=short_sources,
        )

    if view.surface == "table-timeline":
        def candidate_demand(candidate: LayoutManifest) -> Mapping[str, Decimal]:
            natural = prepare_surface_natural_candidate(candidate_request(candidate))
            return {"timeline": natural.required_timeline_block(foot_reserve=foot_reserve)}

        block_resolution = resolve_content_block_extent(
            resolved_layout, viewport_inline=viewport["inlineSize"],
            minimum_block=natural_block_floor if request.draft_auto_block else viewport["blockSize"],
            measurements=measurements,
            required_blocks=candidate_demand,
            content_sized=request.draft_auto_block,
        )
        viewport["blockSize"] = block_resolution.extent
        capacity_short_sources = tuple(CapacitySourceEvidence(
            item.source_id, item.required_block, item.allocated_block)
            for item in block_resolution.short_sources)
    elif request.draft_auto_block:
        raise LayoutError("E_LAYOUT_DRAFT_AUTO_UNSUPPORTED", "/projection/surface",
                          detail=f"surface={view.surface}")
    manifest = solve_layout(
        resolved_layout, viewport_inline=viewport["inlineSize"],
        viewport_block=viewport["blockSize"], measurements=measurements,
        content_sized=request.draft_auto_block,
    )

    fixed_lane_preflight = None
    surface_preparation = None
    if view.surface == "table-timeline":
        natural = prepare_surface_natural_candidate(candidate_request(manifest, short_sources=capacity_short_sources))
        surface_preparation = prepare_surface_content(natural.inline.request, natural=natural)
        surface_content = surface_preparation.inline.request.surface_content
        fixed_lane_preflight = surface_preparation.inline.request.fixed_lane_preflight
    else:
        surface_content = admit_v05_detail_content(
            selected_content,
            detail=render_closure.detail_profile.detail if render_closure.detail_profile else None,
            layout_manifest=manifest,
        )
    if render_closure.detail_profile is not None:
        ledger.detail()
    scene_input = build_scene_input(
        projection=projection, surface_content=surface_content, layout_manifest=manifest,
        resolved_theme=theme, font_metrics=font_metrics, measured_sources=measured,
        capabilities={name: True for name in render_closure.context.target.capabilities},
        visual_profile=visual_profile,
        viewport=(float(viewport["inlineSize"]), float(viewport["blockSize"])),
        icon_assets=icon_assets,
        visual_requests=visual_requests,
        fixed_lane_preflight=fixed_lane_preflight,
        capacity_short_sources=capacity_short_sources,
        surface_preparation=surface_preparation,
    )

    unused = ledger.unused()
    if request.require_all_inputs_read and unused:
        raise RenderFailed("E_CLOSURE_INPUT_UNUSED",
                           "closure inputs loaded but never read: " + ", ".join(unused), "closure")

    try:
        surface = compose_review_surface(scene_input)
    except SceneBuildError as error:
        detail = error.detail or visual_capability_message(error.diagnostic_id)
        raise RenderFailed(error.diagnostic_id, detail,
                           "presentation", error.path) from error
    # A Theme role or binding no document of this closure reads is reported, not silently accepted (#1117).
    unread_roles = unread_theme_diagnostics(
        theme["body"], (view, layout, render_closure.detail_profile.detail if render_closure.detail_profile else None,
                        render_closure.summary_profile.summary if render_closure.summary_profile else None))
    if unread_roles:
        surface = replace(surface, diagnostics=(*surface.diagnostics, *unread_roles))
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
    )
    # Surface diagnostics are already in the preliminary Scene. Append only
    # the post-composition families, preserving duplicates and their order.
    appended = warning_records[sum(item.startswith("W_") for item in surface.diagnostics):]
    scene = replace(scene, diagnostics=(*scene.diagnostics, *(item.identity for item in appended)))
    return RenderedReview(artifact, surface, scene, frozenset(ledger.read), scenario_provenance,
                          glyph_warnings, perceptibility_warnings, contrast_warnings,
                          surface.info_diagnostics, collisions, attachments, deadlines, warning_records)


def _below_plot_reserve(view: Any, *, actual_set: Any, projection: Any, theme_tokens: Any) -> float:
    """The block extent a `below-plot` as-of chip needs under the plot; 0 without such a marker in the window."""
    marker = next((item for item in view.markers if item.get("kind") == "asOf" and item.get("source") == "actual"
                   and item.get("placement") == BELOW_PLOT and item.get("label")), None)
    body = actual_set.get("body") if actual_set is not None else None
    as_of_value = body.get("asOf") if isinstance(body, dict) else None
    if marker is None or not isinstance(as_of_value, str):
        return 0.0
    start, end = projection.window
    return below_plot_reserve(theme_tokens) if start <= date.fromisoformat(as_of_value) < end else 0.0


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
    ) for item in substitutions)


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
    policy = {**DEFAULT_POLICY, **theme["body"].get("contrastPolicy", {})}
    findings = evaluate_scene_contrast(scene_document(scene), policy=policy)
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
                            ("groundId", finding.ground_id), ("groundKind", finding.ground_kind),
                            ("paintChannel", finding.paint_channel)):
            if value is not None:
                facts.append((name, value))
        warnings.append(SceneContrastWarning(
            finding.code, WARNING_BLOCKING_CODES[finding.code], finding.scene_path,
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


def _resolve_group_tints(view: Any, projection: Any, theme: Mapping[str, Any]
                         ) -> tuple[tuple[tuple[str, str], ...], tuple[Any, ...]]:
    """Resolve the View's per-group tint scale to one colour per group, in display order (#583)."""
    tint = view.grouping.tint if view.grouping is not None else None
    if tint is None:
        return (), ()
    groups = tuple(dict.fromkeys(row.group_id for row in projection.rows if row.group_id))
    scale = resolve_color_scale(
        {"scale": tint.scale, "target": "group", "source": {"field": view.grouping.field},
         "domain": list(tint.domain) if tint.domain is not None else "firstAppearance"},
        theme["body"].get("colorScales"), theme["body"].get("categorySlots"),
        source_ref="/body/grouping/tint",
        color_vision=tuple(theme["body"].get("colorVision", ())), observed=groups)
    if scale is None:
        return (), ()
    return tuple((group, scale.color_for(group, {scale.source_field: group})) for group in groups), scale.collisions


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
    projection = replace(projection, periods=_selected_periods(project, result.placements, view),
                         figures=_resolved_figures(project, result.placements, view, actual),
                         deadlines=_shown_deadlines(project, result.placements, view))
    return projection, tuple(provenance), attachment_warnings(project, result.placements), deadline_warnings(project, result.placements)


def _check_slot_heading_text(view: ViewInput, resolved_layout: ResolvedLayoutProfile) -> None:
    """Admit View copy against the resolved profile, never mutate Layout declarations."""
    if not view.slot_heading_text:
        return
    valid = headed_slot_ids(resolved_layout)
    for node_id in sorted(view.slot_heading_text):
        if node_id not in valid:
            escaped = node_id.replace("~", "~0").replace("/", "~1")
            raise RenderFailed("E_VIEW_SLOT_HEADING_TARGET",
                               f"slotHeadingText target {node_id!r} is not a headed slot; valid headed slots: "
                               + (", ".join(sorted(valid)) or "none"),
                               "view", f"/body/slotHeadingText/{escaped}")


def _check_summary_figures(summary: Any, projection: Any) -> None:
    """A Summary Profile metric naming a figure must name one the View declared, in a format an integer has (#586)."""
    declared = dict(projection.figures)
    for panel in summary.panels if summary is not None else ():
        for metric in panel.metrics:
            source = getattr(metric, "source", None)
            if not isinstance(source, Mapping) or "figure" not in source:
                continue
            path = f"/body/panels/{panel.id}/metrics/{metric.id}"
            if source["figure"] not in declared:
                known = ", ".join(declared) if declared else "none"
                raise RenderFailed("E_VIEW_FIGURE_UNKNOWN",
                                   f"summary metric {metric.id} names figure {source['figure']}, which the View does not declare (declared: {known})",
                                   "presentation", path)
            if metric.format == "date":
                raise RenderFailed("E_PRESENTATION_SUMMARY_FORMAT",
                                   f"summary metric {metric.id} formats figure {source['figure']} as a date, but a figure is a number of days",
                                   "presentation", f"{path}/format")


def _resolved_figures(project: dict[str, Any], placements: dict[str, dict[str, Any]], view: ViewInput,
                      actual: Mapping[str, Any] | None) -> tuple[tuple[str, int], ...]:
    """Every figure the View declares, computed by the Core from the facts gathered here (#586).

    This is the one place the as-of, the placements, the resolved periods and the Project calendars are
    collected; the arithmetic is Core's. A finding on any figure refuses the render with all findings: a
    figure with a missing fact never becomes a blank or a made-up number.
    """
    if not view.figures:
        return ()
    as_of = ((actual or {}).get("body") or {}).get("asOf")
    resolution = resolve_figures(
        view.figures, as_of=date.fromisoformat(as_of) if isinstance(as_of, str) else None, placements=placements,
        periods=resolve_periods(project, placements),
        calendars={key: Calendar.from_mapping(value) for key, value in (project.get("calendars") or {}).items()},
        default_calendar=(project.get("project") or {}).get("calendar"))
    if resolution.diagnostics:
        raise RenderRejected(list(resolution.diagnostics))
    return tuple(resolution.values.items())


def _shown_deadlines(project: dict[str, Any], placements: dict[str, dict[str, Any]], view: ViewInput) -> tuple[ReviewDeadline, ...]:
    """The Project deadlines the View asks to draw, judged by the Core (#822).

    ``slipped`` keeps the objects planned to finish after their deadline, the set `W_DEADLINE` names; ``all`` keeps
    every object that has a deadline. Layout receives the verdict and draws it; it compares no dates.
    """
    if view.deadlines is None:
        return ()
    return tuple(ReviewDeadline(item.object_id, item.deadline, item.finish, item.slipped)
                 for item in deadline_statuses(project, placements) if item.slipped or view.deadlines == "all")


def _selected_periods(project: dict[str, Any], placements: dict[str, dict[str, Any]], view: ViewInput) -> tuple[ReviewPeriod, ...]:
    """The Project periods the View names, as dates, in the View's order (#582).

    A View naming a period the Project does not declare is refused with the declared identifiers, never
    skipped: a silently missing band would read as a period that has no extent.
    """
    if not view.periods:
        return ()
    declared = {item.period_id: item for item in resolve_periods(project, placements)}
    for index, selected in enumerate(view.periods):
        if selected.period_id not in declared:
            known = ", ".join(declared) if declared else "none"
            raise RenderFailed("E_VIEW_PERIOD_UNKNOWN",
                               f"the View selects period {selected.period_id}, which the Project does not declare (declared: {known})",
                               "presentation", f"/body/periods/{index}/id")
    return tuple(ReviewPeriod(item.period_id, selected.label_text or item.title, item.start, item.end,
                              selected.label_placement, selected.label_overflow)
                 for selected, item in ((selected, declared[selected.period_id]) for selected in view.periods))


def _font_metrics(theme: dict[str, Any], font_metrics: dict[str, Any], asset_root: Path,
                  asset_resolver: FontAssetResolver | None = None) -> Any:
    try:
        return resolve_font_metrics_catalog(font_metrics, asset_root=asset_root, asset_resolver=asset_resolver)
    except FontMetricsError as error:
        raise _font_failure(error) from error


def _font_failure(error: FontMetricsError) -> RenderFailed:
    return RenderFailed(error.diagnostic_id, error.detail or "declared font metrics are unavailable",
                        "presentation", "/body/environment/fontMetrics")


def _source_inputs(project: dict[str, Any], view: ViewInput, projection: Any,
                   summary: SummaryContent, annotation_input: SourceInput | None = None, *,
                   content: SurfaceContentInput,
                   table: TableContent | None = None,
                   heading: HeadingContent | None = None,
                   view_heading: HeadingContent | None = None) -> dict[str, SourceInput]:
    """Declare what each slot will hold, for measurement before layout.

    The `legend` entry is a placeholder: Layout measures the legend from the entries it
    draws and the legend slot's own arrangement (`legend_source_input`).
    """
    lane_mode = view.rows.mode is ViewRowMode.LANES
    rows = projection.lane_rows if lane_mode else projection.rows or ()
    row_count = len(rows) or len(projection.items)
    if lane_mode and (not rows or table is None):
        raise LayoutError("E_LAYOUT_LANE_TABLE_ENVELOPE", "/body/rows/laneTable")
    table_lines = (tuple(cell.content for cell in table.cells if cell.column_id == "Lane")
                   if lane_mode and table is not None else
                   tuple(row.label for row in rows) or tuple(item.title for item in projection.items))
    span_days = max(1, (projection.window[1] - projection.window[0]).days)
    network = getattr(projection, "network", None)
    notes = tuple(str(item.get("text", "")) for item in project.get("annotations", {}).values())
    sources = {
        "title": _title_source(project, heading),
        "table": SourceInput(
            table_lines,
            row_count, len(view.table_columns) or 1, table=table),
        "timeline": SourceInput(item_count=row_count, span_days=span_days),
        "timeline-axis": SourceInput(span_days=span_days, typography_role="axis",
                                     axis_tiers=content.axis_tiers),
        "network": SourceInput(
            runs=tuple(SourceTextRun(node.title, "text", node.object_id)
                       for node in network.nodes) if network is not None else (),
            typography_role="text"),
        "summary": _summary_source(summary),
        "legend": SourceInput(("legend",), typography_role="legend"),
        "notes": SourceInput(notes or ("notes",), typography_role="annotation"),
    }
    if view_heading is not None:
        sources.update(_heading_part_sources(view_heading))
    sources.update(detail_source_inputs(content))
    if annotation_input is not None:
        sources["annotations"] = annotation_input
    return sources


def _layout_slot_sources(node: Mapping[str, Any]) -> frozenset[str]:
    own = frozenset((node["source"],)) if node.get("kind") == "slot" else frozenset()
    return own.union(*(_layout_slot_sources(child) for child in node.get("children", ())))


def _heading_part_sources(heading: HeadingContent) -> dict[str, SourceInput]:
    sources = {}
    for part, text, role in (("title", heading.title, "heading"),
                             ("kicker", heading.kicker, "kicker"),
                             ("subtitle", heading.subtitle, "subtitle")):
        source_ref = f"heading.{part}"
        sources[source_ref] = SourceInput(
            lines=(text,) if text else (), typography_role=role,
            runs=(SourceTextRun(text, role, source_ref),) if text else (),
            content_present=bool(text), run_flow="block")
    return sources


def _summary_source(summary: SummaryContent) -> SourceInput:
    """Retain panel grouping only when an arrangement opts into grouped flow."""
    if not any(panel.arrangement == "inline" for panel in summary.panels):
        return SourceInput(runs=tuple(SourceTextRun(run.content, run.typography_role) for run in summary.runs))
    return SourceInput(runs=tuple(SourceTextRun(run.content, run.typography_role, run.placement_id)
                                  for run in summary.runs), summary=summary)


def _title_source(project: dict[str, Any], heading: HeadingContent | None) -> SourceInput:
    """The title slot's content: one `heading` line, plus a `subtitle` line when the View declares one (#991)."""
    title = heading.title if heading is not None else project["project"].get("title", "Chrona")
    subtitle = heading.subtitle if heading is not None else None
    if heading is not None and heading.kicker is not None:
        runs = (SourceTextRun(heading.kicker, "kicker", "kicker"), SourceTextRun(title, "heading", "title"))
        if subtitle is not None:
            runs += (SourceTextRun(subtitle, "subtitle", "subtitle"),)
        return SourceInput(tuple(run.content for run in runs), typography_role="heading", runs=runs,
                           run_flow="block")
    if subtitle is None:
        return SourceInput((title,), typography_role="heading")
    return SourceInput((title, subtitle), typography_role="heading",
                       runs=(SourceTextRun(title, "heading"), SourceTextRun(subtitle, "subtitle")))


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
