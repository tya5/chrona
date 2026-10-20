"""Owns source measurement, allocation and native preparation; reads resolved surface intent and resources."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from decimal import Decimal, ROUND_CEILING
from typing import Any, Mapping

from chrona.presentation.contracts.resources import ReviewDetailInput, ViewInput
from chrona.presentation.heading_text import HeadingTextPrograms
from chrona.presentation.layout.asof_foot_reserve import BELOW_PLOT, below_plot_reserve, measure_as_of_chip
from chrona.presentation.layout.canvas_viewport import DeclaredViewport
from chrona.presentation.layout.engine import measure_natural_normal_flow_block, resolve_content_block_extent, solve_layout
from chrona.presentation.layout.model import LayoutError, LayoutManifest, ResolvedLayoutProfile
from chrona.presentation.layout.profile import resolve_layout_profile
from chrona.presentation.layout.slot_heading import (
    bind_slot_heading_templates, headed_slot_ids, resolve_heading_wording, reserve_slot_heading_blocks)
from chrona.presentation.layout.sources import MeasuredSources, resolve_theme_metrics, measure_sources
from chrona.presentation.layout.source_sizing import SourceSizingSession
from chrona.presentation.layout.source_presence import omit_absent_layout_sources
from chrona.presentation.layout.surface_legend import (
    LegendArrangement, legend_arrangement, legend_source_input, wrapped_legend_line_block)
from chrona.presentation.layout.surface_preparation import SurfacePreRowGeometry, prepare_surface_content, prepare_surface_natural_candidate
from chrona.presentation.layout.surface_mark_visibility import build_item_mark_visibility_index
from chrona.presentation.layout.window_row_admission import (
    complete_window_row_admission, geometry_surface_content, geometry_table,
)
from chrona.presentation.layout.surface_quality import CapacitySourceEvidence, SurfaceLayoutRequest, VisualRequest
from chrona.presentation.layout.temporal_capacity import TemporalInlineCapacity
from chrona.presentation.layout.relation_hint_model import PreviousRouteHints
from chrona.presentation.layout.surface_source_inputs import (
    bind_heading_dependencies, heading_part_sources, network_deadline_source_input,
    surface_source_inputs,
)
from chrona.presentation.layout.style_text import resolve_table_cell_typography
from chrona.presentation.layout.legend_candidates import prepare_realized_legend_candidates
from chrona.presentation.model.font_metrics import FontMetricsError
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.render_progress import RenderProgress
from chrona.presentation.model.surface_content import HeadingContent, SummaryContent, SurfaceContentInput, TableContent
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.model.paint_capabilities import PaintWitnessCapabilities
from chrona.presentation.model.wording_tables import wording_resolver
from chrona.presentation.review.detail import ReviewDetailError
from chrona.presentation.review.v05_content import compose_heading


@dataclass(frozen=True)
class SurfaceRenderPlanInput:
    project: Mapping[str, Any]
    view: ViewInput
    projection: Any
    content: SurfaceContentInput
    summary: SummaryContent
    table: TableContent
    profile: Mapping[str, Any]
    theme: Mapping[str, Any]
    font_metrics: Any
    heading: HeadingContent | HeadingTextPrograms | None
    actual: Mapping[str, Any] | None
    detail: ReviewDetailInput | None
    viewport_inline: int
    viewport_block: int
    content_sized: bool
    locale: str
    capabilities: Mapping[str, bool]
    icon_assets: dict[str, Any]
    visual_requests: tuple[VisualRequest, ...]
    progress: RenderProgress | None = None
    previous_route_hints: PreviousRouteHints | None = None
    paint_capabilities: PaintWitnessCapabilities = field(default_factory=PaintWitnessCapabilities)
    scene_precision: int = 3


@dataclass(frozen=True)
class PreparedSurfaceRenderPlan:
    manifest: LayoutManifest
    profile: ResolvedLayoutProfile
    measured: MeasuredSources
    content: SurfaceContentInput
    preparation: SurfacePreRowGeometry | None
    capacity_short_sources: tuple[CapacitySourceEvidence, ...]
    viewport: tuple[float, float]
    declared_viewport: DeclaredViewport


class SurfacePlanFontError(Exception):
    """Preserve the former measured-source/as-of font transport boundaries."""
    def __init__(self, failure: FontMetricsError):
        super().__init__(str(failure))
        self.failure = failure


class SlotHeadingCopyError(LayoutError):
    """A declared View caption references no headed profile node."""


def prepare_surface_render_plan(value: SurfaceRenderPlanInput) -> PreparedSurfaceRenderPlan:
    """Measure and allocate using the exact existing natural/fixed candidate policy."""
    project, view, projection = value.project, value.view, value.projection
    selected_content, summary, table_content = value.content, value.summary, value.table
    theme, font_metrics, layout = value.theme, value.font_metrics, value.profile
    selected_content = prepare_realized_legend_candidates(
        selected_content, ThemeTokenView(theme),
        mark_block_size=float(resolve_theme_metrics(theme)["timeline.mark.blockSize"]),
        paint_capabilities=value.paint_capabilities)
    selected_content, table_content = resolve_table_cell_typography(
        selected_content, table_content, ThemeTokenView(theme))
    actual_observations, heading_content = value.actual, value.heading
    mark_visibility_index, row_admission = None, None
    if view.surface == "table-timeline" and getattr(projection, "window_outside", "keep") == "omit":
        mark_visibility_index = build_item_mark_visibility_index(projection, as_of=selected_content.as_of)
        row_admission = complete_window_row_admission(projection, mark_visibility_index)
        table_content = geometry_table(table_content, row_admission)
        selected_content = geometry_surface_content(selected_content, row_admission)
    if isinstance(heading_content, HeadingTextPrograms):
        heading_content = HeadingContent(*heading_content.bind(dict(projection.figures), view.figure_formats),
                                         text_wrap=heading_content.text_wrap)
    visual_requests, icon_assets = value.visual_requests, value.icon_assets
    source_inputs = surface_source_inputs(project, view, projection, summary,
        content=selected_content, table=table_content, heading=heading_content,
        view_heading=heading_content or HeadingContent(str(project.get("project", {}).get("title", ""))),
        visual_requests=visual_requests, icon_assets=icon_assets, theme=theme,
        row_admission=row_admission)
    if isinstance(value.heading, HeadingTextPrograms):
        source_inputs = bind_heading_dependencies(source_inputs, value.heading)
    required_metrics = (("timeline.groupHeader.blockSize",)
                        if view.grouping is not None and view.grouping.presentation == "header" else ())
    # The legend slot is measured as the legend Layout will draw: the same entries, the same
    # swatch geometry, and the legend slot's own declared arrangement (#497). That needs the
    # resolved Layout Profile, so it is resolved first (it needs only the source names). A Layout
    # Profile error is still reported after any measurement error, as before.
    layout_error: LayoutError | None = None
    try:
        resolved_layout = resolve_heading_wording(
            resolve_layout_profile(layout, available_sources=set(source_inputs), theme=theme),
            wording_resolver(value.locale, view.wording))
    except LayoutError as error:
        resolved_layout, layout_error = None, error
    claimed_sources = (_layout_slot_sources(resolved_layout.profile["root"])
                       if resolved_layout is not None else frozenset())
    if uses_independent_view_heading(view.surface, resolved_layout):
        # The use case supplies the shared composed heading. Keep this fallback
        # for direct plan callers, which may construct the plan without one.
        if value.heading is None:
            network_heading = compose_heading(view, project, actual_observations, value.locale)
            if isinstance(network_heading, HeadingTextPrograms):
                network_heading = HeadingContent(*network_heading.bind(dict(projection.figures), view.figure_formats),
                                                 text_wrap=network_heading.text_wrap)
            source_inputs.update(heading_part_sources(network_heading))
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
        if view.surface == "dependency-network":
            # This run group is internal measurement input, not a Layout Profile
            # source. It is added only after source admission has completed.
            measurement_inputs["network-deadlines"] = network_deadline_source_input(projection, theme)
        measured = measure_sources(measurement_inputs, theme, font_metrics=font_metrics,
                                   required_metrics=required_metrics)
        # Omitted content remains available for notices, without demanding unused
        # typography or influencing the legacy aggregate measurements.
        measured = replace(measured, inputs=source_inputs)
    except FontMetricsError as error:
        raise SurfacePlanFontError(error) from error
    if layout_error is not None:
        raise layout_error
    _check_slot_heading_text(view, resolved_layout)
    absent_sources = set()
    if summary.absent:
        absent_sources.add("summary")
    if not source_inputs["annotations"].content_present:
        absent_sources.add("annotations")
    if not selected_content.legend_entries:
        absent_sources.add("legend")
    if not selected_content.notes:
        absent_sources.add("notes")  # an empty notes source reserves no block and no gap (#1649)
    selected_content = bind_slot_heading_templates(resolved_layout, content=selected_content, view=view,
                                                  figures=dict(projection.figures), measured=measured)
    resolved_layout = omit_absent_layout_sources(resolved_layout, frozenset(absent_sources))
    # A declared slot heading is part of its content-sized slot's measurement (#1064).
    measured_before_headings = measured
    measured = reserve_slot_heading_blocks(measured, resolved_layout, ThemeTokenView(theme), content=selected_content,
                                           font_metrics=font_metrics)
    viewport = {"inlineSize": value.viewport_inline, "blockSize": value.viewport_block}
    declared_viewport = DeclaredViewport(
        Decimal(value.viewport_inline),
        None if value.content_sized else Decimal(value.viewport_block))
    measurements = _slot_measurements(resolved_layout.profile["root"], measured)
    source_sizing = SourceSizingSession(resolved_layout, measured, theme=theme,
                                       font_metrics=font_metrics, content=selected_content)

    def sizing_context(block: int | Decimal):
        return source_sizing.context(viewport_inline=viewport["inlineSize"], viewport_block=block,
                                     measurements=measurements, content_sized=value.content_sized)

    natural_block_floor = max(1, int(measure_natural_normal_flow_block(
        resolved_layout, viewport_inline=viewport["inlineSize"], measurements=measurements,
        sizing=sizing_context(viewport["blockSize"]) if source_sizing.active else None,
    ).to_integral_value(rounding=ROUND_CEILING))) if value.content_sized else viewport["blockSize"]
    completion_floor = natural_block_floor if value.content_sized else viewport["blockSize"]
    completed = _complete_wrapped_legend(
        resolved_layout, measured_before_headings, measured, viewport_inline=viewport["inlineSize"],
        floor=completion_floor, measurements=measurements,
        sizing=sizing_context(completion_floor) if source_sizing.active else None,
        content_sized=value.content_sized)
    if completed is not None:
        # Complete the source measurement at the width allocated by the provisional solve. The
        # fixed outer canvas remains fixed; only content-sized allocation follows the completed rows.
        measured = reserve_slot_heading_blocks(completed, resolved_layout, ThemeTokenView(theme),
                                               content=selected_content, font_metrics=font_metrics)
        measurements = _slot_measurements(resolved_layout.profile["root"], measured)
        source_sizing = SourceSizingSession(resolved_layout, measured, theme=theme,
                                           font_metrics=font_metrics, content=selected_content)
        if value.content_sized:
            natural_block_floor = max(1, int(measure_natural_normal_flow_block(
                resolved_layout, viewport_inline=viewport["inlineSize"], measurements=measurements,
                sizing=sizing_context(viewport["blockSize"]) if source_sizing.active else None,
            ).to_integral_value(rounding=ROUND_CEILING)))
    capacity_short_sources = ()
    # An as-of chip placed `below-plot` (#1063) needs its block under the last row, so the timeline asks for it too.
    try:
        as_of_chip_measurement = measure_as_of_chip(selected_content, window=projection.window,
            theme_tokens=ThemeTokenView(theme), font_metrics=font_metrics,
            visual_requests=visual_requests, icon_assets=icon_assets,
            scene_precision=value.scene_precision)
    except FontMetricsError as error:
        raise SurfacePlanFontError(error) from error
    foot_reserve = Decimal(str(_below_plot_reserve(view, actual_set=actual_observations, projection=projection,
        theme_tokens=ThemeTokenView(theme), chip_measurement=as_of_chip_measurement)))

    def candidate_request(candidate: LayoutManifest, *, short_sources=()) -> SurfaceLayoutRequest:
        content = admit_detail_content(
            selected_content,
            detail=value.detail,
            layout_manifest=candidate,
        )
        measured = source_sizing.close_manifest(candidate)
        return SurfaceLayoutRequest(
            projection=projection, presentation_contract=normalize_presentation_input(content),
            surface_content=content, layout_manifest=candidate,
            measured_sources=measured,
            temporal_capacity=(TemporalInlineCapacity.from_manifest(candidate, measured)
                               if view.surface == "table-timeline" else None),
            theme_tokens=ThemeTokenView(theme), font_metrics=font_metrics,
            capabilities=dict(value.capabilities),
            paint_capabilities=value.paint_capabilities,
            icon_assets=icon_assets, visual_requests=visual_requests,
            capacity_short_sources=short_sources,
            as_of_chip_measurement=as_of_chip_measurement,
            declared_viewport=declared_viewport,
            auto_block_limit=resolved_layout.distances.get("/reviewSurface/maxBlockSize"),
            progress=value.progress,
            previous_route_hints=value.previous_route_hints,
            mark_visibility_index=mark_visibility_index,
            row_admission=row_admission,
            scene_precision=value.scene_precision,
        )

    if view.surface == "table-timeline":
        def candidate_demand(candidate: LayoutManifest) -> Mapping[str, Decimal]:
            natural = prepare_surface_natural_candidate(candidate_request(candidate))
            return {"timeline": natural.required_timeline_block(foot_reserve=foot_reserve)}

        block_resolution = resolve_content_block_extent(
            resolved_layout, viewport_inline=viewport["inlineSize"],
            minimum_block=natural_block_floor if value.content_sized else viewport["blockSize"],
            measurements=measurements,
            required_blocks=candidate_demand,
            content_sized=value.content_sized,
            sizing=sizing_context if source_sizing.active else None,
        )
        viewport["blockSize"] = block_resolution.extent
        capacity_short_sources = tuple(CapacitySourceEvidence(
            item.source_id, item.required_block, item.allocated_block)
            for item in block_resolution.short_sources)
    elif value.content_sized:
        raise LayoutError("E_LAYOUT_DRAFT_AUTO_UNSUPPORTED", "/projection/surface",
                          detail=(f"surface={view.surface}; choose a fixed WIDTHxHEIGHT viewport "
                                  "(for example, --viewport 1600x900); auto height is supported only "
                                  "for table-timeline"))
    manifest = solve_layout(
        resolved_layout, viewport_inline=viewport["inlineSize"],
        viewport_block=viewport["blockSize"], measurements=measurements,
        content_sized=value.content_sized,
        sizing=sizing_context(viewport["blockSize"]) if source_sizing.active else None,
    )
    measured = source_sizing.close_manifest(manifest)

    fixed_lane_preflight = None
    surface_preparation = None
    if view.surface == "table-timeline":
        natural = prepare_surface_natural_candidate(candidate_request(manifest, short_sources=capacity_short_sources))
        surface_preparation = prepare_surface_content(natural.inline.request, natural=natural)
        surface_content = surface_preparation.inline.request.surface_content
        fixed_lane_preflight = surface_preparation.inline.request.fixed_lane_preflight
    else:
        surface_content = admit_detail_content(
            selected_content,
            detail=value.detail,
            layout_manifest=manifest,
        )
    return PreparedSurfaceRenderPlan(manifest, resolved_layout, measured, surface_content,
        surface_preparation, capacity_short_sources,
        (float(viewport["inlineSize"]), float(viewport["blockSize"])), declared_viewport)


def admit_detail_content(content: SurfaceContentInput, *, detail: ReviewDetailInput | None,
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

def _below_plot_reserve(view: Any, *, actual_set: Any, projection: Any, theme_tokens: Any,
                        chip_measurement: Any = None) -> float:
    """The block extent a `below-plot` as-of chip needs under the plot; 0 without such a marker in the window."""
    marker = next((item for item in view.markers if item.get("kind") == "asOf" and item.get("source") == "actual"
                   and item.get("placement") == BELOW_PLOT and item.get("label")), None)
    body = actual_set.get("body") if actual_set is not None else None
    as_of_value = body.get("asOf") if isinstance(body, dict) else None
    if marker is None or not isinstance(as_of_value, str):
        return 0.0
    start, end = projection.window
    return (below_plot_reserve(theme_tokens, chip_measurement=chip_measurement)
            if start <= date.fromisoformat(as_of_value) < end else 0.0)

def _layout_slot_sources(node: Mapping[str, Any]) -> frozenset[str]:
    own = frozenset((node["source"],)) if node.get("kind") == "slot" else frozenset()
    return own.union(*(_layout_slot_sources(child) for child in node.get("children", ())))


def uses_independent_view_heading(surface: str, profile: ResolvedLayoutProfile | None) -> bool:
    """Whether the selected native surface allocates the View heading as named parts."""
    return (surface == "dependency-network" and profile is not None
            and "title" not in _layout_slot_sources(profile.profile["root"]))

def _complete_wrapped_legend(resolved_layout: ResolvedLayoutProfile, unheaded: MeasuredSources,
                           measured: MeasuredSources, *, viewport_inline: int, floor: int,
                           measurements: Mapping[str, Any], sizing: Any,
                           content_sized: bool) -> MeasuredSources | None:
    """Return the sources with a `line` legend measured at its resolved inline size, or None to keep the stack.

    Which inline size the legend slot gets is known only after a solve, so the conservative stack (every entry on
    its own row) is solved once to find it; a legend whose width is not known keeps the conservative height
    (#497, #1273, #1649). The narrowed block is exactly the rows `place_legend` draws at that width.
    """
    legend = unheaded.inputs.get("legend")
    node = _legend_slot(resolved_layout.profile["root"])
    if legend is None or node is None or legend.run_flow != "line" or not legend.runs:
        return None
    try:
        manifest = solve_layout(resolved_layout, viewport_inline=viewport_inline, viewport_block=floor,
                                measurements=measurements, content_sized=content_sized, sizing=sizing)
    except LayoutError:
        return None
    decision = next((item for item in manifest.decisions if item.node_id == node["id"]), None)
    sizes = tuple(run.inline_size for run in unheaded.run_measurements.get("legend", ()))
    if decision is None or len(sizes) != len(legend.runs) or "legend" not in measured.measurements:
        return None
    caption_inline = measured.measurements["legend"].preferred_inline - unheaded.measurements["legend"].preferred_inline
    block = wrapped_legend_line_block(
        sizes, gap=legend.run_gap, row_block=legend.row_block,
        item_min_inline=legend_arrangement(resolved_layout).item_min_inline_size,
        available_inline=decision.bounds.inline_size - caption_inline)
    current = unheaded.measurements["legend"]
    if block == current.preferred_block:
        return None
    completed = replace(current, preferred_block=block, max_block=block * 2)
    return replace(unheaded, measurements={**unheaded.measurements, "legend": completed})


def _legend_slot(node: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if node.get("kind") == "slot":
        return node if node.get("source") == "legend" else None
    for child in node.get("children", ()):
        found = _legend_slot(child)
        if found is not None:
            return found
    return None


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

def _check_slot_heading_text(view: ViewInput, resolved_layout: ResolvedLayoutProfile) -> None:
    if not view.slot_heading_text:
        return
    valid = headed_slot_ids(resolved_layout)
    for node_id in sorted(view.slot_heading_text):
        if node_id not in valid:
            escaped = node_id.replace("~", "~0").replace("/", "~1")
            raise SlotHeadingCopyError("E_VIEW_SLOT_HEADING_TARGET",
                f"/body/slotHeadingText/{escaped}",
                detail=f"slotHeadingText target {node_id!r} is not a headed slot; valid headed slots: "
                       + (", ".join(sorted(valid)) or "none"))
