"""Owns axis tiers, labels, targets and calendar intervals; reads closed Layout, Theme and fonts."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any, Callable, Mapping

from chrona.presentation.axis_intervals import axis_band_placement_id
from chrona.presentation.layout.axis import (
    AxisInterval, axis_intervals, axis_label_fits, format_axis_tier_label, thinning_schedule,
)
from chrona.presentation.layout.axis_lanes import (
    BandLanePlan, LabelLanePlan, SecondaryPlan, axis_tick_requirement, label_block, line_extents,
    measure_axis_text, plan_band_stack, plan_label_lanes, secondary_plan,
)
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_base import SurfaceBaseGeometry
from chrona.presentation.layout.surface_geometry import (
    BACKGROUND_PAINT_ORDER, GEOMETRY_TOLERANCE, HOSTED_TEXT_PAINT_ORDER,
    bounds_from_rect, coordinate_for_date, extend_to_plot_edges,
)
from chrona.presentation.layout.rounded_outline import resolve_corner_radius
from chrona.presentation.layout.surface_quality import (
    AxisIntervalOutcome, AxisTierOutcome, CollisionDomain, PathCommand, PlacementDecision, ScalePlacement,
    ShapePlacement, SlotPlacement, SurfaceLayoutRequest, TextPlacement,
)
from chrona.presentation.layout.text import measured_text_bounds, measure_text_width, metric_for_role, place_text
from chrona.presentation.model.semantic_registry import (
    axis_band_semantic_ids, axis_label_semantic_ids, semantic_binding,
)
from chrona.presentation.model.axis_names import axis_name_table
from chrona.presentation.model.surface_content import AxisTier
from chrona.presentation.model.theme_tokens import TextTreatment


@dataclass(frozen=True)
class CalendarOverlayInterval:
    """One closed-date interval in completed timeline inline coordinates."""
    day: date
    inline_start: float
    inline_end: float
    exception: bool = False  # a day the Project calendar closes by an `exceptions` entry (#991)


@dataclass(frozen=True)
class AxisLabelTierGeometry:
    """Completed geometry for one horizontal labels tier, independent of retained interval text."""

    tier_index: int
    bounds: Rect
    baseline_block: float


def calendar_overlay_intervals(*, closed_days: tuple[date, ...], start: date, end: date,
                                coordinate: Callable[[date, ScalePlacement], float], scale: ScalePlacement,
                                exceptions: frozenset[date] = frozenset()
                                ) -> tuple[CalendarOverlayInterval, ...]:
    """Derive ordered closed-date intervals without creating Theme shapes."""
    return tuple(CalendarOverlayInterval(day, coordinate(day, scale),
                                         coordinate(day.fromordinal(day.toordinal() + 1), scale), day in exceptions)
                 for day in closed_days if start <= day < end)


@dataclass(frozen=True)
class SurfaceAxisPlacements:
    """Ordered axis geometry, text, targeting, diagnostics, and calendar facts."""
    shapes: tuple[ShapePlacement, ...]
    text: tuple[TextPlacement, ...]
    tier_outcomes: tuple[AxisTierOutcome, ...]
    decisions: tuple[PlacementDecision, ...]
    label_targets: dict[tuple[str, str, str], str]
    band_targets: dict[tuple[str, str, str], str]
    diagnostics: tuple[str, ...]
    visible_label_overflows: tuple[tuple[TextPlacement, LabelRect], ...]
    calendar_intervals: tuple[CalendarOverlayInterval, ...]
    label_tiers: tuple[AxisLabelTierGeometry, ...] = ()


@dataclass(frozen=True)
class SurfaceAxisFrame:
    """Axis inputs independent of final shared rows or plot block extent."""
    scale: ScalePlacement
    timeline: SlotPlacement
    axis: SlotPlacement
    metric_values: Mapping[str, Any]


@dataclass(frozen=True)
class AxisPlotGrid:
    """A full-height grid's completed inline coordinate, awaiting the final plot."""
    placement_id: str
    inline: float
    semantic_id: str

    def complete(self, plot: Rect) -> ShapePlacement:
        return ShapePlacement(
            self.placement_id, "timeline-axis", "Path",
            Rect(Decimal(str(self.inline)), plot.block, Decimal(0), plot.block_size),
            ((self.inline, float(plot.block)), (self.inline, float(plot.block + plot.block_size))),
            semantic_id=self.semantic_id, paint_order=BACKGROUND_PAINT_ORDER + 1)


@dataclass(frozen=True)
class SurfaceAxisPreparation:
    """Completed native axis facts and ordered, explicitly deferred plot grids."""
    placements: SurfaceAxisPlacements
    ordered_shapes: tuple[ShapePlacement | AxisPlotGrid, ...]


@dataclass(frozen=True)
class AxisTierMeasurement:
    """Native interval and typography facts for one axis tier, before host-capacity checks."""

    treatment: TextTreatment
    metrics: Any
    secondary: SecondaryPlan | None
    intervals: tuple[AxisInterval, ...]
    tier_outcome: AxisTierOutcome
    diagnostics: tuple[str, ...]
    decisions: tuple[PlacementDecision, ...]

    @property
    def form(self) -> str | None:
        return self.tier_outcome.label_form

    @property
    def outcomes(self) -> tuple[AxisIntervalOutcome, ...]:
        return self.tier_outcome.intervals

    @property
    def axis_size(self) -> float:
        return float(self.treatment.font_size)


@dataclass(frozen=True)
class AxisLabelLaneGeometry:
    """Native label lane for one tier and the next cursor for following label tiers."""

    offset: float
    size: float
    next_offset: float
    block: float


@dataclass(frozen=True)
class AxisCapacityPlan:
    """Host-size-independent facts for the existing candidate-scale axis capacity guards."""

    tick_lengths: tuple[tuple[int, Decimal], ...]
    band_lane_ends: tuple[tuple[int, float], ...]
    secondary_lane_ends: tuple[tuple[int, float], ...]
    declared_secondary_mismatches: tuple[int, ...]

    def fits(self, block: Decimal) -> bool:
        return (all(length <= block for _, length in self.tick_lengths)
                and all(end <= float(block) + float(GEOMETRY_TOLERANCE) for _, end in self.band_lane_ends)
                and all(end <= float(block) for _, end in self.secondary_lane_ends)
                and not self.declared_secondary_mismatches)


@dataclass(frozen=True)
class SurfaceAxisMeasurement:
    """All candidate-scale axis tier facts and their native host-capacity predicates."""

    tiers: tuple[AxisTierMeasurement, ...]
    label_lanes: tuple[tuple[int, AxisLabelLaneGeometry], ...]
    labels: LabelLanePlan
    bands: BandLanePlan
    capacity: AxisCapacityPlan

    def label_lane(self, tier_index: int) -> AxisLabelLaneGeometry:
        return next(lane for index, lane in self.label_lanes if index == tier_index)


@dataclass(frozen=True)
class AxisVerticalSummary:
    """Vertical extent facts for candidate axis labels and native rectangles."""

    label_tiers: tuple[AxisLabelTierGeometry, ...]
    max_rect_block_end: Decimal | None


@dataclass(frozen=True)
class AxisTextRunGeometry:
    """The exact measured inputs and rectangle used for one native axis text run."""

    content: str
    inline: float
    baseline_block: float
    bounds: Rect


@dataclass(frozen=True)
class AxisLabelTextGeometry:
    """Primary/secondary text runs sharing one interval cell."""

    primary: AxisTextRunGeometry
    secondary: AxisTextRunGeometry | None
    available_inline_start: float
    available_inline_size: float


@dataclass(frozen=True)
class AxisBandLaneGeometry:
    block: Decimal
    block_size: Decimal
    stack_end: float | None


def _axis_text_run_geometry(*, content: str, inline: float, baseline_block: float,
                            treatment: TextTreatment, metrics: Any, orientation: str) -> AxisTextRunGeometry:
    font_size, line_height = float(treatment.font_size), float(treatment.line_height)
    width = measure_text_width(content, font_size=font_size, font_metrics=metrics,
                               letter_spacing=float(treatment.letter_spacing),
                               text_transform=treatment.transform,
                               numeric_spacing=treatment.numeric_spacing)
    height = font_size * line_height
    rotation = {"horizontal": 0, "rotate-cw": 90, "rotate-ccw": -90}[orientation]
    bounds = measured_text_bounds(inline=inline, baseline_block=baseline_block, width=width,
                                  height=height, font_size=font_size, rotation=rotation)
    return AxisTextRunGeometry(content, inline, baseline_block, bounds)


def measure_axis_tier(request: SurfaceLayoutRequest, scale: ScalePlacement, tier_index: int,
                      tier: AxisTier) -> AxisTierMeasurement:
    """Measure native tier choices and labels without admitting them to an axis host."""
    start, end = request.projection.window
    tokens, font_metrics = request.theme_tokens, request.font_metrics
    form = tier.label.form if tier.label else None
    name_table = axis_name_table(tier.label.name_table_id) if tier.label else None
    treatment = tokens.text_treatment(tier.typography_role or "axis")
    metrics = metric_for_role(tokens, tier.typography_role or "axis", font_metrics)
    axis_size = float(treatment.font_size)
    plan = secondary_plan(tokens, tier, tier_index, treatment, metrics, font_metrics)
    requested_units = (tuple(candidate for candidate, _ in tier.label.candidate_forms)
                       if tier.unit == "auto" and tier.label else (tier.unit,))
    diagnostics: list[str] = []
    decisions: list[PlacementDecision] = []
    try:
        if tier.unit == "auto":
            selected = None
            forms = dict(tier.label.candidate_forms) if tier.label else {}
            for candidate in ("day", "week", "month", "quarter", "half", "year"):
                if candidate not in forms:
                    continue
                trial = axis_intervals(start, end, candidate, tick_step=tier.every,
                                       fiscal_start_month=request.surface_content.axis_fiscal_start_month)
                fits = all(axis_label_fits(
                    content=format_axis_tier_label(item, forms[candidate], name_table),
                    available_inline=(item.end - item.start).days * scale.unit_ratio,
                    font_size=axis_size, font_metrics=metrics,
                    letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                    numeric_spacing=treatment.numeric_spacing, orientation=tier.label.orientation,
                    line_height=float(treatment.line_height)) for item in trial)
                if fits or tier.label.overflow == "visible-overflow":
                    selected, form = trial, forms[candidate]
                    break
            if selected is None:
                candidate = next(item for item in ("day", "week", "month", "quarter", "half", "year")
                                 if item in forms)
                selected, form = axis_intervals(start, end, candidate, tick_step=tier.every,
                                                fiscal_start_month=request.surface_content.axis_fiscal_start_month), forms[candidate]
            intervals = selected
        else:
            intervals = axis_intervals(start, end, tier.unit, tick_step=tier.every,
                                       fiscal_start_month=request.surface_content.axis_fiscal_start_month)
    except ValueError as error:
        raise LayoutError(str(error), "/view/body/axis/tiers") from error
    if tier.role == "labels" and form is not None:
        interval_outcomes = tuple(AxisIntervalOutcome(
            f"axis-label:{tier_index}:{item.index}", item.start, item.end,
            item.natural_start, item.natural_end,
            format_axis_tier_label(item, form, name_table),
            axis_label_fits(
                content=format_axis_tier_label(item, form, name_table),
                available_inline=max(0.0, coordinate_for_date(item.end, scale)
                                     - coordinate_for_date(item.start, scale)
                                     - _axis_label_inset(tokens, tier, axis_size)),
                font_size=axis_size, font_metrics=metrics,
                letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                numeric_spacing=treatment.numeric_spacing, orientation=tier.label.orientation,
                line_height=float(treatment.line_height))) for item in intervals)
        fits = tuple(bool(item.label_fits) for item in interval_outcomes)
        if not all(fits) and tier.label.overflow == "thin-with-record":
            try:
                schedule = thinning_schedule(fits)
            except ValueError:
                interval_outcomes = tuple(replace(
                    item, disposition="placed", reason=None if item.label_fits else "visible-overflow")
                    for item in interval_outcomes)
            else:
                retained = set(schedule.retained_positions)
                updated = []
                for position, outcome in enumerate(interval_outcomes):
                    if position in retained:
                        updated.append(replace(outcome, disposition="placed"))
                    else:
                        updated.append(replace(
                            outcome, disposition="thinned", reason="label-does-not-fit"))
                        diagnostics.append(f"W_LAYOUT_AXIS_LABEL_THINNED:{outcome.candidate_id}:label-does-not-fit")
                        decisions.append(PlacementDecision(
                            outcome.candidate_id, f"/view/body/axis/tiers/{tier_index}",
                            ("thin-with-record", "suppress"), "suppress", "suppressed"))
                interval_outcomes = tuple(updated)
                diagnostics.append(f"W_LAYOUT_AXIS_DENSITY:axis-tier:{tier_index}:thinned={len(schedule.thinned_positions)}")
        else:
            interval_outcomes = tuple(replace(
                item, disposition="placed", reason=None if item.label_fits else "visible-overflow")
                for item in interval_outcomes)
    else:
        interval_outcomes = tuple(AxisIntervalOutcome(
            f"axis-tier:{tier_index}:{item.index}", item.start, item.end,
            item.natural_start, item.natural_end) for item in intervals)
    if tier.role == "labels" and form is not None:
        for interval, outcome in zip(intervals, interval_outcomes, strict=True):
            if outcome.disposition == "placed":
                for canonical in name_table.coincident_canonicals(form, interval.natural_start.month):
                    diagnostics.append(f"W_LAYOUT_AXIS_FORM_EQUIVALENT:{outcome.candidate_id}:table={name_table.table_id}:form={form}:canonical={canonical}:month={interval.natural_start.month}")
    if plan is not None and tier.role == "labels" and form is not None:
        interval_outcomes, secondary_diagnostics, secondary_decisions = _secondary_outcomes(
            tier_index=tier_index, plan=plan, intervals=intervals, outcomes=interval_outcomes,
            scale=scale, inset=_axis_label_inset(tokens, tier, axis_size), primary=treatment,
            primary_metrics=metrics)
        diagnostics.extend(secondary_diagnostics)
        decisions.extend(secondary_decisions)
    tier_outcome = AxisTierOutcome(
        tier_index, f"/view/body/axis/tiers/{tier_index}", tier.role, requested_units,
        intervals[0].level if intervals else (tier.unit if tier.unit != "auto" else ""), tier.every,
        form, interval_outcomes, name_table.table_id if name_table else None)
    return AxisTierMeasurement(treatment, metrics, plan, tuple(intervals), tier_outcome,
                               tuple(diagnostics), tuple(decisions))


def axis_label_lane_geometry(*, tier_index: int, tier: AxisTier, measured: AxisTierMeasurement,
                             declared_lanes: Mapping[int, tuple[float, float]],
                             running_offset: float) -> AxisLabelLaneGeometry:
    """Resolve the native lane size and cursor from one tier's measured labels."""
    treatment, metrics, plan = measured.treatment, measured.metrics, measured.secondary
    widths = tuple(measure_text_width(item.label or "", font_size=measured.axis_size, font_metrics=metrics,
        letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
        numeric_spacing=treatment.numeric_spacing)
        for item in measured.outcomes if item.disposition == "placed")
    lane_size = (measured.axis_size * float(treatment.line_height) + float(GEOMETRY_TOLERANCE)
                 if tier.label.orientation == "horizontal" else max(widths, default=0.0))
    block = label_block(treatment, plan)
    if plan is not None:
        lane_size = block + float(GEOMETRY_TOLERANCE)
    offset = running_offset
    if tier_index in declared_lanes:
        offset, lane_size = declared_lanes[tier_index]
    return AxisLabelLaneGeometry(offset, lane_size, offset + lane_size, block)


def measure_surface_axis(request: SurfaceLayoutRequest, scale: ScalePlacement) -> SurfaceAxisMeasurement:
    """Measure candidate-scale axis lanes and native host-capacity predicates once."""
    if request.theme_tokens is None or request.font_metrics is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    tokens, font_metrics = request.theme_tokens, request.font_metrics
    tiers = request.surface_content.axis_tiers
    labels = plan_label_lanes(tiers, tokens, font_metrics)
    bands = plan_band_stack(tiers, tokens, labels)
    tier_measurements = tuple(measure_axis_tier(request, scale, index, tier)
                              for index, tier in enumerate(tiers))
    band_count = sum(tier.role == "band" for tier in tiers)
    label_lanes: list[tuple[int, AxisLabelLaneGeometry]] = []
    tick_lengths: list[tuple[int, Decimal]] = []
    band_ends: list[tuple[int, float]] = []
    secondary_ends: list[tuple[int, float]] = []
    declared_secondary_mismatches: list[int] = []
    label_cursor = 0.0
    for tier_index, (tier, measured) in enumerate(zip(tiers, tier_measurements, strict=True)):
        if tier.role == "labels" and measured.form is not None:
            lane = axis_label_lane_geometry(tier_index=tier_index, tier=tier, measured=measured,
                                            declared_lanes=labels.declared, running_offset=label_cursor)
            label_lanes.append((tier_index, lane))
            label_cursor = lane.next_offset
            if measured.secondary is not None:
                secondary_ends.append((tier_index, lane.offset + lane.size))
                if tier_index in labels.declared and lane.block > lane.size + float(GEOMETRY_TOLERANCE):
                    declared_secondary_mismatches.append(tier_index)
        if tier.role == "band" and band_count > 1 and tier.unit not in labels.by_unit:
            offset, size = bands.stacked[tier_index]
            band_ends.append((tier_index, offset + size))
        if tier.role in {"grid-major", "grid-minor"}:
            semantic_id = "axisGrid" if tier.role == "grid-major" else "axisGridMinor"
            tick = axis_tick_requirement(tokens, semantic_binding(semantic_id).scene_role, tier_index)
            if tick is not None:
                tick_lengths.append((tier_index, tick))
    capacity = AxisCapacityPlan(tuple(tick_lengths), tuple(band_ends), tuple(secondary_ends),
                                tuple(declared_secondary_mismatches))
    return SurfaceAxisMeasurement(tier_measurements, tuple(label_lanes), labels, bands, capacity)


def summarize_surface_axis_vertical(request: SurfaceLayoutRequest, frame: SurfaceAxisFrame,
                                   measured: SurfaceAxisMeasurement) -> AxisVerticalSummary:
    """Return candidate label lanes and the furthest native Rect end without placement or host guards."""
    tokens, axis, scale = request.theme_tokens, frame.axis, frame.scale
    tiers = request.surface_content.axis_tiers
    band_count = sum(tier.role == "band" for tier in tiers)
    band_ordinal = label_ordinal = 0
    label_tiers: list[AxisLabelTierGeometry] = []
    ends: list[Decimal] = []
    separator_marks: list[tuple[float, float, float]] = []
    start, _end = request.projection.window
    for tier_index, (tier, tier_measurement) in enumerate(zip(tiers, measured.tiers, strict=True)):
        if tier.role == "band":
            semantic_id = _axis_band_semantic_id(tier_index, band_ordinal)
            band_ordinal += 1
            if tier_measurement.intervals:
                role = semantic_binding(semantic_id).scene_role
                background, _paint_order = tokens.background(role)
            else:
                background = "none"
            if background != "none":
                lane = _axis_band_lane_geometry(axis=axis.bounds, tier_index=tier_index, tier=tier,
                                                band_count=band_count, labels=measured.labels,
                                                bands=measured.bands)
                rect = _axis_band_cell_bounds(0.0, 0.0, lane.block, lane.block_size)
                ends.append(rect.block + rect.block_size)
        elif tier.role in {"grid-major", "grid-minor"}:
            tick = dict(measured.capacity.tick_lengths).get(tier_index)
            if tick is not None:
                for interval in tier_measurement.intervals:
                    x = coordinate_for_date(interval.start, scale)
                    rect = _axis_tick_bounds(axis.bounds, x, tick)
                    ends.append(rect.block + rect.block_size)
        elif tier.role == "labels" and tier_measurement.form is not None:
            _semantic_id, label_ordinal = _axis_label_semantic_id(tier_index, tier, label_ordinal)
            lane = measured.label_lane(tier_index)
            if tier.label.orientation == "horizontal":
                label_tiers.append(_axis_label_tier_geometry(
                    axis=axis, tier_index=tier_index, tier=tier, measurement=tier_measurement,
                    lane=lane, declared_lanes=measured.labels.declared))
            for interval, outcome in zip(tier_measurement.intervals, tier_measurement.outcomes, strict=True):
                if outcome.disposition == "thinned":
                    continue
                x = coordinate_for_date(interval.start, scale)
                if interval.index > 0 or x > coordinate_for_date(start, scale) + float(GEOMETRY_TOLERANCE):
                    separator_marks.append((x, *((float(axis.bounds.block) + lane.offset,
                        float(axis.bounds.block) + lane.offset + lane.size)
                        if tier_index in measured.labels.declared
                        else (float(axis.bounds.block), float(axis.bounds.block + axis.bounds.block_size)))))
                geometry = _axis_label_text_geometry(
                    theme_tokens=tokens, tier_index=tier_index, tier=tier, interval=interval,
                    outcome=outcome, measurement=tier_measurement, scale=scale, axis=axis,
                    lane=lane, declared_lanes=measured.labels.declared)
                ends.append(geometry.primary.bounds.block + geometry.primary.bounds.block_size)
                if geometry.secondary is not None:
                    ends.append(geometry.secondary.bounds.block + geometry.secondary.bounds.block_size)
        else:
            raise LayoutError("E_PRESENTATION_AXIS_INVALID", "/view/body/axis/tiers")
    if tokens.has_role("axis-cell-separator"):
        ends.extend(bounds.block + bounds.block_size for _, bounds in _axis_separator_bounds(separator_marks))
    if tokens.has_role("axis-rule"):
        rect = _axis_rule_bounds(frame.timeline.bounds, axis.bounds)
        ends.append(rect.block + rect.block_size)
    return AxisVerticalSummary(tuple(label_tiers), max(ends) if ends else None)


def complete_axis_plot(prepared: SurfaceAxisPreparation, plot: Rect) -> SurfaceAxisPlacements:
    """Close only plot-dependent grid endpoints, retaining native shape order."""
    return replace(prepared.placements, shapes=tuple(
        shape.complete(plot) if isinstance(shape, AxisPlotGrid) else shape
        for shape in prepared.ordered_shapes))


def _axis_label_inset(theme_tokens: Any, tier: Any, font_size: float) -> float:
    if tier.label is None or tier.label.align != "start":
        return 0.0
    ratio = theme_tokens.optional_number(tier.typography_role or "axis", "labelInset")
    return float(ratio) * font_size if ratio is not None else 0.0


def _label_baselines(*, axis_block: float, label_lane_offset: float, lane_size: float,
                     tier_index: int, declared_lanes: Mapping[int, tuple[float, float]], axis_size: float,
                     orientation: str, width: float, plan: SecondaryPlan | None,
                     block: float, primary: Any) -> tuple[float, float]:
    """Use the same measured lane geometry for label text and exported tier baselines."""
    if tier_index in declared_lanes:
        line_block = axis_size * float(primary.line_height)
        baseline = axis_block + label_lane_offset + (lane_size - line_block) / 2 + axis_size
    else:
        baseline = axis_block + label_lane_offset + (
            axis_size if orientation == "horizontal" else (0 if orientation == "rotate-cw" else width))
    secondary_baseline = baseline
    if plan is not None:
        line_top = axis_block + label_lane_offset + (
            (lane_size - block) / 2 if tier_index in declared_lanes else 0.0)
        above, below = line_extents(primary)
        above_secondary, _ = line_extents(plan.treatment)
        if plan.intent.placement == "stacked":
            baseline = line_top + above
            secondary_baseline = line_top + above + below + plan.gap + above_secondary
        else:
            baseline = secondary_baseline = line_top + max(above, above_secondary)
    return baseline, secondary_baseline


def _axis_label_text_geometry(*, theme_tokens: Any, tier_index: int, tier: AxisTier, interval: AxisInterval,
                              outcome: AxisIntervalOutcome, measurement: AxisTierMeasurement,
                              scale: ScalePlacement, axis: SlotPlacement,
                              lane: AxisLabelLaneGeometry, declared_lanes: Mapping[int, tuple[float, float]]
                              ) -> AxisLabelTextGeometry:
    if outcome.label is None or outcome.disposition != "placed":
        raise LayoutError("E_PRESENTATION_AXIS_OVERFLOW", f"/view/body/axis/tiers/{tier_index}",
                          detail=outcome.candidate_id)
    treatment, metrics, plan = measurement.treatment, measurement.metrics, measurement.secondary
    orientation = tier.label.orientation
    inset = _axis_label_inset(theme_tokens, tier, measurement.axis_size)
    x, x2 = coordinate_for_date(interval.start, scale), coordinate_for_date(interval.end, scale)
    if tier.label.align == "start" and inset:
        x += inset
    available = max(0.0, x2 - x)
    primary_width = measure_text_width(outcome.label, font_size=measurement.axis_size, font_metrics=metrics,
        letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
        numeric_spacing=treatment.numeric_spacing)
    secondary_text = (outcome.secondary_label
                      if outcome.secondary_disposition == "placed" and plan is not None else None)
    gap = plan.gap if plan is not None else 0.0
    secondary_width = measure_axis_text(secondary_text, plan.treatment, plan.metrics) if secondary_text else 0.0
    occupied = primary_width if orientation == "horizontal" else measurement.axis_size * float(treatment.line_height)
    if secondary_text and plan.intent.placement == "inline":
        occupied = primary_width + gap + secondary_width
    primary_inline = x if tier.label.align == "start" else x + (available - occupied) / 2
    primary_baseline, secondary_baseline = _label_baselines(
        axis_block=float(axis.bounds.block), label_lane_offset=lane.offset,
        lane_size=lane.size, tier_index=tier_index, declared_lanes=declared_lanes,
        axis_size=measurement.axis_size, orientation=orientation, width=primary_width, plan=plan,
        block=lane.block, primary=treatment)
    primary = _axis_text_run_geometry(content=outcome.label, inline=primary_inline,
        baseline_block=primary_baseline, treatment=treatment, metrics=metrics, orientation=orientation)
    secondary = None
    if secondary_text and plan is not None:
        secondary_inline = (primary_inline + primary_width + gap if plan.intent.placement == "inline"
                            else x if tier.label.align == "start"
                            else x + (available - secondary_width) / 2)
        secondary = _axis_text_run_geometry(content=secondary_text, inline=secondary_inline,
            baseline_block=secondary_baseline, treatment=plan.treatment, metrics=plan.metrics,
            orientation=orientation)
    return AxisLabelTextGeometry(primary, secondary, x, available)


def _axis_label_tier_geometry(*, axis: SlotPlacement, tier_index: int, tier: AxisTier,
                              measurement: AxisTierMeasurement, lane: AxisLabelLaneGeometry,
                              declared_lanes: Mapping[int, tuple[float, float]]) -> AxisLabelTierGeometry:
    baseline, _ = _label_baselines(
        axis_block=float(axis.bounds.block), label_lane_offset=lane.offset, lane_size=lane.size,
        tier_index=tier_index, declared_lanes=declared_lanes, axis_size=measurement.axis_size,
        orientation=tier.label.orientation, width=0.0, plan=measurement.secondary,
        block=lane.block, primary=measurement.treatment)
    return AxisLabelTierGeometry(
        tier_index,
        Rect(axis.bounds.inline, axis.bounds.block + Decimal(str(lane.offset)),
             axis.bounds.inline_size, Decimal(str(lane.size))),
        baseline)


def _axis_band_semantic_id(tier_index: int, band_ordinal: int) -> str:
    semantic_ids = axis_band_semantic_ids()
    if band_ordinal >= len(semantic_ids):
        raise LayoutError("E_PRESENTATION_AXIS_INVALID", f"/view/body/axis/tiers/{tier_index}",
                          detail=f"too many band tiers:{band_ordinal + 1}")
    return semantic_ids[band_ordinal]


def _axis_label_semantic_id(tier_index: int, tier: AxisTier, label_ordinal: int) -> tuple[str, int]:
    if tier.typography_role is None:
        return axis_label_semantic_ids()[0], label_ordinal
    next_ordinal = label_ordinal + 1
    semantic_ids = axis_label_semantic_ids()
    if next_ordinal >= len(semantic_ids):
        raise LayoutError("E_PRESENTATION_AXIS_INVALID", f"/view/body/axis/tiers/{tier_index}",
                          detail=f"too many typography-role labels tiers:{next_ordinal}")
    return semantic_ids[next_ordinal], next_ordinal


def _secondary_outcomes(*, tier_index: int, plan: SecondaryPlan, intervals: Any, outcomes: tuple[AxisIntervalOutcome, ...],
                        scale: ScalePlacement, inset: float, primary: Any, primary_metrics: Any
                        ) -> tuple[tuple[AxisIntervalOutcome, ...], list[str], list[PlacementDecision]]:
    """Decide each cell's secondary label from measured fit (#493); it never alters the primary's outcome."""
    gap = plan.gap
    diagnostics: list[str] = []
    decisions: list[PlacementDecision] = []
    updated: list[AxisIntervalOutcome] = []
    for interval, outcome in zip(intervals, outcomes, strict=True):
        if outcome.disposition != "placed" or outcome.label is None:
            updated.append(outcome)
            continue
        content = format_axis_tier_label(interval, plan.intent.form, plan.table)
        available = max(0.0, coordinate_for_date(interval.end, scale) - coordinate_for_date(interval.start, scale) - inset)
        secondary_width = measure_axis_text(content, plan.treatment, plan.metrics)
        required = (secondary_width if plan.intent.placement == "stacked"
                    else measure_axis_text(outcome.label, primary, primary_metrics) + gap + secondary_width)
        if not outcome.label_fits:
            reason: str | None = "primary-does-not-fit"
        else:
            reason = None if required <= available else "does-not-fit"
        secondary_id = f"axis-label-secondary:{tier_index}:{interval.index}"
        if reason is None:
            updated.append(replace(outcome, secondary_label=content, secondary_disposition="placed"))
            for canonical in plan.table.coincident_canonicals(plan.intent.form, interval.natural_start.month):
                diagnostics.append(f"W_LAYOUT_AXIS_FORM_EQUIVALENT:{secondary_id}:table={plan.table.table_id}:form={plan.intent.form}:canonical={canonical}:month={interval.natural_start.month}")
            continue
        updated.append(replace(outcome, secondary_label=content, secondary_disposition="omitted", secondary_reason=reason))
        diagnostics.append(f"W_LAYOUT_AXIS_SECONDARY_OMITTED:{outcome.candidate_id}:{reason}")
        decisions.append(PlacementDecision(secondary_id, f"/view/body/axis/tiers/{tier_index}",
                                           ("secondary", "suppress"), "suppress", "suppressed"))
    return tuple(updated), diagnostics, decisions


def _cell_corner(theme_tokens: Any, role: str, tier_index: int) -> tuple[str, Any, Any | None] | None:
    """The Theme-declared band-cell corner, with a physical radius overriding its legacy ratio."""
    radius = theme_tokens.optional_number(role, "cellCornerRadius")
    chamfer = theme_tokens.optional_number(role, "cellCornerChamfer")
    physical_radius = theme_tokens.optional_token(role, "cornerRadius", "radius")
    source = f"/view/body/axis/tiers/{tier_index}"
    if physical_radius is not None:
        if chamfer is not None:
            raise LayoutError("E_PRESENTATION_AXIS_INVALID", source, detail=f"cell-corner-both:{tier_index}")
        return "radius", None, physical_radius
    if radius is None and chamfer is None:
        return None
    if radius is not None and chamfer is not None:
        raise LayoutError("E_PRESENTATION_AXIS_INVALID", source, detail=f"cell-corner-both:{tier_index}")
    shape, ratio = ("radius", radius) if radius is not None else ("chamfer", chamfer)
    if not 0 < ratio <= Decimal("0.5"):
        raise LayoutError("E_PRESENTATION_AXIS_INVALID", source, detail=f"cell-corner:{tier_index}")
    if shape == "chamfer" and theme_tokens.optional_pattern(role) is not None:
        raise LayoutError("E_PRESENTATION_AXIS_INVALID", source, detail=f"cell-chamfer-pattern:{tier_index}")
    return shape, ratio, None


def _axis_band_cell_bounds(x: float, x2: float, block: Decimal, block_size: Decimal) -> Rect:
    return Rect(Decimal(str(x)), block, Decimal(str(max(0.0, x2 - x))), block_size)


def _axis_band_lane_geometry(*, axis: Rect, tier_index: int, tier: AxisTier, band_count: int,
                              labels: LabelLanePlan, bands: BandLanePlan) -> AxisBandLaneGeometry:
    if tier.unit in labels.by_unit:
        offset, size = labels.by_unit[tier.unit]
        return AxisBandLaneGeometry(axis.block + Decimal(str(offset)), Decimal(str(size)), None)
    if band_count == 1:
        return AxisBandLaneGeometry(axis.block, axis.block_size, None)
    offset, size = bands.stacked[tier_index]
    return AxisBandLaneGeometry(axis.block + Decimal(str(offset)), Decimal(str(size)), offset + size)


def _band_cell(placement_id: str, x: float, x2: float, block: Decimal, block_size: Decimal, *, semantic_id: str,
               paint_order: int, corner: tuple[str, Decimal] | None, diagnostics: list[str]) -> ShapePlacement:
    """One band cell: a Rect, a rounded Rect, or a chamfered polygon, always inside its own cell rect (#491)."""
    bounds = _axis_band_cell_bounds(x, x2, block, block_size)
    width = float(bounds.inline_size)
    if corner is None:
        return ShapePlacement(placement_id, "timeline-axis", "Rect", bounds, semantic_id=semantic_id, paint_order=paint_order)
    shape, ratio, physical_radius = corner
    if physical_radius is not None:
        requested = (float(physical_radius) if isinstance(physical_radius, (int, float))
                     and not isinstance(physical_radius, bool) else min(width, float(block_size)) / 2)
        applied = resolve_corner_radius(physical_radius, width=width, height=float(block_size), legacy_radius=0.0)
    else:
        requested = float(ratio * block_size)
        applied = min(requested, width / 2)
    if applied < requested:
        diagnostics.append(f"W_LAYOUT_AXIS_CELL_CORNER_REDUCED:{placement_id}")
    if shape == "radius":
        return ShapePlacement(placement_id, "timeline-axis", "Rect", bounds, semantic_id=semantic_id,
                              paint_order=paint_order, corner_radius=applied)
    top, bottom = float(block), float(block + block_size)
    left, right = x, x + width
    points = ((left + applied, top), (right - applied, top), (right, top + applied), (right, bottom - applied),
              (right - applied, bottom), (left + applied, bottom), (left, bottom - applied), (left, top + applied))
    commands = (PathCommand("move", (points[0],)), *(PathCommand("line", (point,)) for point in points[1:]),
                PathCommand("line", (points[0],)))
    return ShapePlacement(placement_id, "timeline-axis", "Chamfer", bounds, semantic_id=semantic_id,
                          paint_order=paint_order, path_commands=commands)


def _axis_tick_length(theme_tokens: Any, role: str, slot_block_size: Decimal, tier_index: int) -> Decimal | None:
    """The Theme-declared tick length of a grid role (#492), or None for the full-height line."""
    declared = axis_tick_requirement(theme_tokens, role, tier_index)
    if declared is None:
        return None
    source = f"/view/body/axis/tiers/{tier_index}"
    if declared > slot_block_size:
        raise LayoutError("E_PRESENTATION_AXIS_OVERFLOW", source, detail=f"tick-length:{role}")
    return declared


def _axis_tick_bounds(axis: Rect, inline: float, tick: Decimal) -> Rect:
    top = axis.block + axis.block_size - tick
    return Rect(Decimal(str(inline)), top, Decimal(0), tick)


def _axis_separator_bounds(marks: list[tuple[float, float, float]]) -> tuple[tuple[float, Rect], ...]:
    merged: dict[float, tuple[float, float]] = {}
    for x, top, bottom in marks:
        key = round(x, 6)
        low, high = merged.get(key, (top, bottom))
        merged[key] = (min(low, top), max(high, bottom))
    return tuple((x, Rect(Decimal(str(x)), Decimal(str(top)), Decimal(0), Decimal(str(bottom - top))))
                 for x, (top, bottom) in sorted(merged.items()))


def _axis_rule_bounds(timeline: Rect, axis: Rect) -> Rect:
    y = float(axis.block + axis.block_size)
    left, right = float(timeline.inline), float(timeline.inline + timeline.inline_size)
    return Rect(Decimal(str(left)), Decimal(str(y)), Decimal(str(right - left)), Decimal(0))


def compose_axis(request: SurfaceLayoutRequest, base: SurfaceBaseGeometry) -> SurfaceAxisPlacements:
    """Place all axis tiers against completed scale and return calendar intervals, not shapes."""
    frame = SurfaceAxisFrame(base.scale, base.timeline, base.by_source["timeline-axis"], base.metric_values)
    return complete_axis_plot(prepare_surface_axis(request, frame), base.plot)


def prepare_surface_axis(request: SurfaceLayoutRequest, frame: SurfaceAxisFrame, *,
                         measured: SurfaceAxisMeasurement | None = None) -> SurfaceAxisPreparation:
    """Complete native axis text/bands once, before final shared rows are placed."""
    if request.theme_tokens is None or request.font_metrics is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    start, end = request.projection.window
    scale, timeline, axis = frame.scale, frame.timeline, frame.axis
    tokens, font_metrics = request.theme_tokens, request.font_metrics
    shapes: list[ShapePlacement | AxisPlotGrid] = []
    text: list[TextPlacement] = []
    outcomes: list[AxisTierOutcome] = []
    decisions: list[PlacementDecision] = []
    label_targets: dict[tuple[str, str, str], str] = {}
    band_targets: dict[tuple[str, str, str], str] = {}
    diagnostics: list[str] = []
    visible_overflows: list[tuple[TextPlacement, LabelRect]] = []
    label_tiers: list[AxisLabelTierGeometry] = []
    separator_marks: list[tuple[float, float, float]] = []
    label_lane_offset = 0.0
    band_ordinal = label_ordinal = 0
    tiers = request.surface_content.axis_tiers
    band_tier_count = sum(item.role == "band" for item in tiers)
    if measured is None:
        lanes = plan_label_lanes(tiers, tokens, font_metrics)
        bands = plan_band_stack(tiers, tokens, lanes)
    else:
        lanes, bands = measured.labels, measured.bands
    declared_lanes, lane_by_unit = lanes.declared, lanes.by_unit

    for tier_index, tier in enumerate(tiers):
        tier_measurement = (measure_axis_tier(request, scale, tier_index, tier)
                            if measured is None else measured.tiers[tier_index])
        form = tier_measurement.form
        treatment, metrics = tier_measurement.treatment, tier_measurement.metrics
        axis_size, plan = tier_measurement.axis_size, tier_measurement.secondary
        intervals, interval_outcomes = tier_measurement.intervals, tier_measurement.outcomes
        diagnostics.extend(tier_measurement.diagnostics)
        decisions.extend(tier_measurement.decisions)
        outcomes.append(tier_measurement.tier_outcome)
        if tier.role == "band":
            semantic_id = _axis_band_semantic_id(tier_index, band_ordinal)
            lane = _axis_band_lane_geometry(axis=axis.bounds, tier_index=tier_index, tier=tier,
                                            band_count=band_tier_count, labels=lanes, bands=bands)
            if lane.stack_end is not None and lane.stack_end > float(axis.bounds.block_size) + float(GEOMETRY_TOLERANCE):
                raise LayoutError("E_PRESENTATION_AXIS_OVERFLOW", f"/view/body/axis/tiers/{tier_index}", detail=f"band-lane:{band_ordinal}")
            band_block, band_block_size = lane.block, lane.block_size
            gap = float(tokens.optional_number(semantic_binding(semantic_id).scene_role, "cellGap") or 0)
            corner = _cell_corner(tokens, semantic_binding(semantic_id).scene_role, tier_index)
            for interval in intervals:
                raw, raw2 = coordinate_for_date(interval.start, scale), coordinate_for_date(interval.end, scale)
                x, x2 = raw, raw2
                if gap:
                    x, x2 = x + gap / 2, max(x + gap / 2, x2 - gap / 2)
                # A cell at the window edge reaches the plot edge (#880); the cell gap lies between cells, so the
                # outer edge of that cell takes no gap and ends where the axis rule ends.
                edge, edge2 = extend_to_plot_edges(raw, raw2, scale=scale, plot=timeline.bounds)
                x, x2 = (edge if edge != raw else x), (edge2 if edge2 != raw2 else x2)
                placement_id = axis_band_placement_id(tier_index, interval.index)
                treatment_bg, paint_order = tokens.background(semantic_binding(semantic_id).scene_role)
                if treatment_bg != "none":
                    band_targets[("axis-band", interval.level, str(interval.index))] = placement_id
                    shapes.append(_band_cell(placement_id, x, x2, band_block, band_block_size, semantic_id=semantic_id,
                                             paint_order=paint_order, corner=corner, diagnostics=diagnostics))
            band_ordinal += 1
        elif tier.role in {"grid-major", "grid-minor"}:
            semantic_id = "axisGrid" if tier.role == "grid-major" else "axisGridMinor"
            tick = _axis_tick_length(tokens, semantic_binding(semantic_id).scene_role, axis.bounds.block_size, tier_index)
            for interval in intervals:
                x = coordinate_for_date(interval.start, scale)
                if tick is None:
                    shapes.append(AxisPlotGrid(f"axis-grid:{tier_index}:{interval.index}", x, semantic_id))
                    continue
                bounds = _axis_tick_bounds(axis.bounds, x, tick)
                shapes.append(ShapePlacement(f"axis-grid:{tier_index}:{interval.index}", "timeline-axis", "Path",
                    bounds,
                    ((x, float(bounds.block)), (x, float(bounds.block + bounds.block_size))),
                    semantic_id=semantic_id, paint_order=BACKGROUND_PAINT_ORDER + 1))
        elif tier.role == "labels" and form is not None:
            label_semantic_id, label_ordinal = _axis_label_semantic_id(tier_index, tier, label_ordinal)
            orientation = tier.label.orientation
            lane = (axis_label_lane_geometry(tier_index=tier_index, tier=tier, measured=tier_measurement,
                                             declared_lanes=declared_lanes, running_offset=label_lane_offset)
                    if measured is None else measured.label_lane(tier_index))
            label_lane_offset, lane_size, block = lane.offset, lane.size, lane.block
            lane_overflow = label_lane_offset + lane_size > float(axis.bounds.block_size)
            if plan is not None and (lane_overflow or (tier_index in declared_lanes
                                                       and block > lane_size + float(GEOMETRY_TOLERANCE))):
                # A secondary the lane or slot cannot hold is a Theme/slot mismatch, not a per-cell condition.
                raise LayoutError("E_PRESENTATION_AXIS_OVERFLOW", f"/view/body/axis/tiers/{tier_index}",
                                  detail=f"secondary-lane:{tier_index}")
            if orientation == "horizontal":
                label_tiers.append(_axis_label_tier_geometry(
                    axis=axis, tier_index=tier_index, tier=tier, measurement=tier_measurement,
                    lane=lane, declared_lanes=declared_lanes))
            for interval, outcome in zip(intervals, interval_outcomes, strict=True):
                if outcome.disposition == "thinned":
                    continue
                label_targets[("axis-label", interval.level, str(interval.index))] = outcome.candidate_id
                x, x2 = coordinate_for_date(interval.start, scale), coordinate_for_date(interval.end, scale)
                if interval.index > 0 or x > coordinate_for_date(start, scale) + float(GEOMETRY_TOLERANCE):
                    separator_marks.append((x, *((float(axis.bounds.block) + label_lane_offset,
                        float(axis.bounds.block) + label_lane_offset + lane_size) if tier_index in declared_lanes
                        else (float(axis.bounds.block), float(axis.bounds.block + axis.bounds.block_size)))))
                geometry = _axis_label_text_geometry(
                    theme_tokens=tokens, tier_index=tier_index, tier=tier, interval=interval,
                    outcome=outcome, measurement=tier_measurement, scale=scale, axis=axis,
                    lane=lane, declared_lanes=declared_lanes)
                primary = geometry.primary
                placed = place_text(placement_id=f"axis-label:{tier_index}:{interval.index}", source_ref="timeline-axis",
                    content=primary.content, inline=primary.inline, baseline_block=primary.baseline_block,
                    typography_role=tier.typography_role or "axis", theme_tokens=tokens, font_metrics=font_metrics,
                    collision_region="timeline-axis-label", collision_domain=CollisionDomain("timeline-axis", "labels"),
                    source_content=primary.content, available_inline_start=geometry.available_inline_start,
                    available_inline_size=geometry.available_inline_size, orientation=orientation,
                    overflow="visible-overflow" if not outcome.label_fits or lane_overflow else "fit")
                placed = replace(placed, semantic_id=label_semantic_id)
                text.append(placed)
                if geometry.secondary is not None:
                    secondary = geometry.secondary
                    text.append(replace(place_text(
                        placement_id=f"axis-label-secondary:{tier_index}:{interval.index}", source_ref="timeline-axis",
                        content=secondary.content, inline=secondary.inline,
                        baseline_block=secondary.baseline_block,
                        typography_role=plan.intent.typography_role, theme_tokens=tokens, font_metrics=font_metrics,
                        collision_region="timeline-axis-label", collision_domain=CollisionDomain("timeline-axis", "labels"),
                        source_content=secondary.content, available_inline_start=geometry.available_inline_start,
                        available_inline_size=geometry.available_inline_size,
                        orientation=orientation, overflow="fit"), semantic_id=label_semantic_id))
                if not outcome.label_fits or lane_overflow:
                    visible_overflows.append((placed, LabelRect(*bounds_from_rect(axis.bounds))))
            label_lane_offset = lane.next_offset
        else:
            raise LayoutError("E_PRESENTATION_AXIS_INVALID", "/view/body/axis/tiers")

    if tokens.has_role("axis-cell-separator"):
        for index, (x, bounds) in enumerate(_axis_separator_bounds(separator_marks)):
            shapes.append(ShapePlacement(f"axis-separator:{index}", "timeline-axis", "Path",
                bounds,
                ((x, float(bounds.block)), (x, float(bounds.block + bounds.block_size))),
                semantic_id="axisCellSeparator", paint_order=BACKGROUND_PAINT_ORDER + 2))
    if tokens.has_role("axis-rule"):
        bounds = _axis_rule_bounds(timeline.bounds, axis.bounds)
        y, left = float(bounds.block), float(bounds.inline)
        right = float(bounds.inline + bounds.inline_size)
        shapes.append(ShapePlacement("axis-rule", "timeline-axis", "Path",
            bounds,
            ((left, y), (right, y)), semantic_id="axisRule", paint_order=BACKGROUND_PAINT_ORDER + 2))
    bands = tuple(item for item in shapes if isinstance(item, ShapePlacement)
                  and item.semantic_id in axis_band_semantic_ids())
    def host(item: TextPlacement) -> str | None:
        centre = item.bounds.inline + item.bounds.inline_size / 2
        lane_centre = item.bounds.block + item.bounds.block_size / 2
        candidates = tuple(band for band in bands
            if band.bounds.inline <= centre <= band.bounds.inline + band.bounds.inline_size
            and band.bounds.block <= lane_centre <= band.bounds.block + band.bounds.block_size)
        return min(candidates, key=lambda band: band.placement_id).placement_id if candidates else None
    text = [replace(item, host_placement_id=host(item), paint_order=HOSTED_TEXT_PAINT_ORDER)
            if item.semantic_id in axis_label_semantic_ids() else item for item in text]
    contract = request.presentation_contract
    minimum = frame.metric_values.get("timeline.calendarClosed.minimumDayWidth")
    closed = contract.time.calendar_closed
    if minimum is not None and scale.unit_ratio < float(minimum):
        closed = contract.time.calendar_exceptions
    calendar = calendar_overlay_intervals(
        closed_days=tuple(closed), start=start, end=end, coordinate=coordinate_for_date, scale=scale,
        exceptions=frozenset(contract.time.calendar_exceptions))
    placements = SurfaceAxisPlacements(tuple(shape for shape in shapes if isinstance(shape, ShapePlacement)),
        tuple(text), tuple(outcomes), tuple(decisions),
        label_targets, band_targets, tuple(diagnostics), tuple(visible_overflows), calendar,
        tuple(label_tiers))
    return SurfaceAxisPreparation(placements, tuple(shapes))
