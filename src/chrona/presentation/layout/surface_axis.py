"""Owns axis tiers, labels, targets and calendar intervals; reads closed Layout, Theme and fonts."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any, Callable, Mapping

from chrona.presentation.layout.axis import (
    axis_intervals, axis_label_fits, format_axis_tier_label, thinning_schedule,
)
from chrona.presentation.layout.axis_lanes import (
    SecondaryPlan, axis_tick_requirement, label_block, line_extents, measure_axis_text,
    plan_band_stack, plan_label_lanes, secondary_plan,
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
from chrona.presentation.layout.text import measure_text_width, metric_for_role, place_text
from chrona.presentation.model.semantic_registry import (
    axis_band_semantic_ids, axis_label_semantic_ids, semantic_binding,
)
from chrona.presentation.model.axis_names import axis_name_table


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
                     tier_index: int, declared_lanes: dict[int, tuple[float, float]], axis_size: float,
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


def _band_cell(placement_id: str, x: float, x2: float, block: Decimal, block_size: Decimal, *, semantic_id: str,
               paint_order: int, corner: tuple[str, Decimal] | None, diagnostics: list[str]) -> ShapePlacement:
    """One band cell: a Rect, a rounded Rect, or a chamfered polygon, always inside its own cell rect (#491)."""
    width = max(0.0, x2 - x)
    bounds = Rect(Decimal(str(x)), block, Decimal(str(width)), block_size)
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


def compose_axis(request: SurfaceLayoutRequest, base: SurfaceBaseGeometry) -> SurfaceAxisPlacements:
    """Place all axis tiers against completed scale and return calendar intervals, not shapes."""
    frame = SurfaceAxisFrame(base.scale, base.timeline, base.by_source["timeline-axis"], base.metric_values)
    return complete_axis_plot(prepare_surface_axis(request, frame), base.plot)


def prepare_surface_axis(request: SurfaceLayoutRequest, frame: SurfaceAxisFrame) -> SurfaceAxisPreparation:
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
    lanes = plan_label_lanes(tiers, tokens, font_metrics)
    bands = plan_band_stack(tiers, tokens, lanes)
    declared_lanes, lane_by_unit = lanes.declared, lanes.by_unit

    for tier_index, tier in enumerate(tiers):
        form = tier.label.form if tier.label else None
        name_table = axis_name_table(tier.label.name_table_id) if tier.label else None
        treatment = tokens.text_treatment(tier.typography_role or "axis")
        metrics = metric_for_role(tokens, tier.typography_role or "axis", font_metrics)
        axis_size = float(treatment.font_size)
        plan = secondary_plan(tokens, tier, tier_index, treatment, metrics, font_metrics)
        requested_units = (tuple(candidate for candidate, _ in tier.label.candidate_forms)
                           if tier.unit == "auto" and tier.label else (tier.unit,))
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
        outcomes.append(AxisTierOutcome(
            tier_index, f"/view/body/axis/tiers/{tier_index}", tier.role, requested_units,
            intervals[0].level if intervals else (tier.unit if tier.unit != "auto" else ""), tier.every,
            form, interval_outcomes, name_table.table_id if name_table else None))
        if tier.role == "band":
            if band_ordinal >= len(axis_band_semantic_ids()):
                raise LayoutError("E_PRESENTATION_AXIS_INVALID", f"/view/body/axis/tiers/{tier_index}", detail=f"too many band tiers:{band_ordinal + 1}")
            semantic_id = axis_band_semantic_ids()[band_ordinal]
            if tier.unit in lane_by_unit:
                lane_offset, lane_size = lane_by_unit[tier.unit]
                band_block, band_block_size = axis.bounds.block + Decimal(str(lane_offset)), Decimal(str(lane_size))
            elif band_tier_count == 1:
                band_block, band_block_size = axis.bounds.block, axis.bounds.block_size
            else:
                band_lane_offset, band_lane_size = bands.stacked[tier_index]
                if band_lane_offset + band_lane_size > float(axis.bounds.block_size) + float(GEOMETRY_TOLERANCE):
                    raise LayoutError("E_PRESENTATION_AXIS_OVERFLOW", f"/view/body/axis/tiers/{tier_index}", detail=f"band-lane:{band_ordinal}")
                band_block, band_block_size = axis.bounds.block + Decimal(str(band_lane_offset)), Decimal(str(band_lane_size))
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
                placement_id = f"axis-band-rect:{tier_index}:{interval.index}"
                treatment_bg, paint_order = tokens.background(semantic_binding(semantic_id).scene_role)
                if treatment_bg != "none":
                    band_targets[("axis-band", interval.level, str(interval.index))] = placement_id
                    shapes.append(_band_cell(placement_id, x, x2, band_block, band_block_size, semantic_id=semantic_id,
                                             paint_order=paint_order, corner=corner, diagnostics=diagnostics))
            band_ordinal += 1
        elif tier.role in {"grid-major", "grid-minor"}:
            semantic_id = "axisGrid" if tier.role == "grid-major" else "axisGridMinor"
            tick = _axis_tick_length(tokens, semantic_binding(semantic_id).scene_role, axis.bounds.block_size, tier_index)
            if tick is not None:
                grid_top, grid_size = axis.bounds.block + axis.bounds.block_size - tick, tick
            for interval in intervals:
                x = coordinate_for_date(interval.start, scale)
                if tick is None:
                    shapes.append(AxisPlotGrid(f"axis-grid:{tier_index}:{interval.index}", x, semantic_id))
                    continue
                shapes.append(ShapePlacement(f"axis-grid:{tier_index}:{interval.index}", "timeline-axis", "Path",
                    Rect(Decimal(str(x)), grid_top, Decimal(0), grid_size),
                    ((x, float(grid_top)), (x, float(grid_top + grid_size))),
                    semantic_id=semantic_id, paint_order=BACKGROUND_PAINT_ORDER + 1))
        elif tier.role == "labels" and form is not None:
            if tier.typography_role is None:
                label_semantic_id = axis_label_semantic_ids()[0]
            else:
                label_ordinal += 1
                if label_ordinal >= len(axis_label_semantic_ids()):
                    raise LayoutError("E_PRESENTATION_AXIS_INVALID", f"/view/body/axis/tiers/{tier_index}", detail=f"too many typography-role labels tiers:{label_ordinal}")
                label_semantic_id = axis_label_semantic_ids()[label_ordinal]
            orientation = tier.label.orientation
            widths = tuple(measure_text_width(item.label or "", font_size=axis_size, font_metrics=metrics,
                letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                numeric_spacing=treatment.numeric_spacing) for item in interval_outcomes if item.disposition == "placed")
            lane_size = (axis_size * float(treatment.line_height) + float(GEOMETRY_TOLERANCE)
                         if orientation == "horizontal" else max(widths, default=0.0))
            block = label_block(treatment, plan)
            if plan is not None:
                lane_size = block + float(GEOMETRY_TOLERANCE)
            if tier_index in declared_lanes:
                label_lane_offset, lane_size = declared_lanes[tier_index]
            inset = _axis_label_inset(tokens, tier, axis_size)
            lane_overflow = label_lane_offset + lane_size > float(axis.bounds.block_size)
            if plan is not None and (lane_overflow or (tier_index in declared_lanes
                                                       and block > lane_size + float(GEOMETRY_TOLERANCE))):
                # A secondary the lane or slot cannot hold is a Theme/slot mismatch, not a per-cell condition.
                raise LayoutError("E_PRESENTATION_AXIS_OVERFLOW", f"/view/body/axis/tiers/{tier_index}",
                                  detail=f"secondary-lane:{tier_index}")
            if orientation == "horizontal":
                tier_baseline, _ = _label_baselines(
                    axis_block=float(axis.bounds.block), label_lane_offset=label_lane_offset,
                    lane_size=lane_size, tier_index=tier_index, declared_lanes=declared_lanes,
                    axis_size=axis_size, orientation=orientation, width=0.0, plan=plan,
                    block=block, primary=treatment)
                label_tiers.append(AxisLabelTierGeometry(
                    tier_index,
                    Rect(axis.bounds.inline, axis.bounds.block + Decimal(str(label_lane_offset)),
                         axis.bounds.inline_size, Decimal(str(lane_size))),
                    tier_baseline))
            for interval, outcome in zip(intervals, interval_outcomes, strict=True):
                if outcome.disposition == "thinned":
                    continue
                label_targets[("axis-label", interval.level, str(interval.index))] = outcome.candidate_id
                x, x2 = coordinate_for_date(interval.start, scale), coordinate_for_date(interval.end, scale)
                if interval.index > 0 or x > coordinate_for_date(start, scale) + float(GEOMETRY_TOLERANCE):
                    separator_marks.append((x, *((float(axis.bounds.block) + label_lane_offset,
                        float(axis.bounds.block) + label_lane_offset + lane_size) if tier_index in declared_lanes
                        else (float(axis.bounds.block), float(axis.bounds.block + axis.bounds.block_size)))))
                if tier.label.align == "start" and inset:
                    x += inset
                available = max(0.0, x2 - x)
                label = outcome.label
                if label is None or outcome.disposition != "placed":
                    raise LayoutError("E_PRESENTATION_AXIS_OVERFLOW", f"/view/body/axis/tiers/{tier_index}", detail=outcome.candidate_id)
                width = measure_text_width(label, font_size=axis_size, font_metrics=metrics,
                    letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                    numeric_spacing=treatment.numeric_spacing)
                occupied = width if orientation == "horizontal" else axis_size * float(treatment.line_height)
                secondary_text = outcome.secondary_label if outcome.secondary_disposition == "placed" else None
                gap = plan.gap if plan is not None else 0.0
                secondary_width = measure_axis_text(secondary_text, plan.treatment, plan.metrics) if secondary_text else 0.0
                if secondary_text and plan.intent.placement == "inline":
                    occupied = width + gap + secondary_width
                inline = x if tier.label.align == "start" else x + (available - occupied) / 2
                baseline, secondary_baseline = _label_baselines(
                    axis_block=float(axis.bounds.block), label_lane_offset=label_lane_offset,
                    lane_size=lane_size, tier_index=tier_index, declared_lanes=declared_lanes,
                    axis_size=axis_size, orientation=orientation, width=width, plan=plan,
                    block=block, primary=treatment)
                placed = place_text(placement_id=f"axis-label:{tier_index}:{interval.index}", source_ref="timeline-axis",
                    content=label, inline=inline, baseline_block=baseline,
                    typography_role=tier.typography_role or "axis", theme_tokens=tokens, font_metrics=font_metrics,
                    collision_region="timeline-axis-label", collision_domain=CollisionDomain("timeline-axis", "labels"),
                    source_content=label, available_inline_start=x, available_inline_size=available, orientation=orientation,
                    overflow="visible-overflow" if not outcome.label_fits or lane_overflow else "fit")
                placed = replace(placed, semantic_id=label_semantic_id)
                text.append(placed)
                if secondary_text:
                    secondary_inline = (inline + width + gap if plan.intent.placement == "inline"
                                        else x if tier.label.align == "start"
                                        else x + (available - secondary_width) / 2)
                    text.append(replace(place_text(
                        placement_id=f"axis-label-secondary:{tier_index}:{interval.index}", source_ref="timeline-axis",
                        content=secondary_text, inline=secondary_inline, baseline_block=secondary_baseline,
                        typography_role=plan.intent.typography_role, theme_tokens=tokens, font_metrics=font_metrics,
                        collision_region="timeline-axis-label", collision_domain=CollisionDomain("timeline-axis", "labels"),
                        source_content=secondary_text, available_inline_start=x, available_inline_size=available,
                        orientation=orientation, overflow="fit"), semantic_id=label_semantic_id))
                if not outcome.label_fits or lane_overflow:
                    visible_overflows.append((placed, LabelRect(*bounds_from_rect(axis.bounds))))
            label_lane_offset += lane_size
        else:
            raise LayoutError("E_PRESENTATION_AXIS_INVALID", "/view/body/axis/tiers")

    if tokens.has_role("axis-cell-separator"):
        merged: dict[float, tuple[float, float]] = {}
        for x, top, bottom in separator_marks:
            key = round(x, 6)
            low, high = merged.get(key, (top, bottom))
            merged[key] = (min(low, top), max(high, bottom))
        for index, (x, (top, bottom)) in enumerate(sorted(merged.items())):
            shapes.append(ShapePlacement(f"axis-separator:{index}", "timeline-axis", "Path",
                Rect(Decimal(str(x)), Decimal(str(top)), Decimal(0), Decimal(str(bottom - top))),
                ((x, top), (x, bottom)), semantic_id="axisCellSeparator", paint_order=BACKGROUND_PAINT_ORDER + 2))
    if tokens.has_role("axis-rule"):
        y = float(axis.bounds.block + axis.bounds.block_size)
        left, right = float(timeline.bounds.inline), float(timeline.bounds.inline + timeline.bounds.inline_size)
        shapes.append(ShapePlacement("axis-rule", "timeline-axis", "Path",
            Rect(Decimal(str(left)), Decimal(str(y)), Decimal(str(right - left)), Decimal(0)),
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
