"""Owns axis tiers, labels, targets and calendar intervals; reads closed Layout, Theme and fonts."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from decimal import Decimal
from typing import Any, Callable

from chrona.presentation.layout.axis import (
    axis_intervals, axis_label_fits, format_axis_tier_label, thinning_schedule,
)
from chrona.presentation.layout.labels import LabelRect
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_base import SurfaceBaseGeometry
from chrona.presentation.layout.surface_geometry import (
    BACKGROUND_PAINT_ORDER, GEOMETRY_TOLERANCE, HOSTED_TEXT_PAINT_ORDER,
    bounds_from_rect, coordinate_for_date, extend_to_plot_edges,
)
from chrona.presentation.layout.surface_quality import (
    AxisIntervalOutcome, AxisTierOutcome, CollisionDomain, PlacementDecision, ScalePlacement,
    ShapePlacement, SurfaceLayoutRequest, TextPlacement,
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


def calendar_overlay_intervals(*, closed_days: tuple[date, ...], start: date, end: date,
                                coordinate: Callable[[date, ScalePlacement], float], scale: ScalePlacement
                                ) -> tuple[CalendarOverlayInterval, ...]:
    """Derive ordered closed-date intervals without creating Theme shapes."""
    return tuple(CalendarOverlayInterval(day, coordinate(day, scale),
                                         coordinate(day.fromordinal(day.toordinal() + 1), scale))
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


def _axis_label_inset(theme_tokens: Any, tier: Any, font_size: float) -> float:
    if tier.label is None or tier.label.align != "start":
        return 0.0
    ratio = theme_tokens.optional_number(tier.typography_role or "axis", "labelInset")
    return float(ratio) * font_size if ratio is not None else 0.0


@dataclass(frozen=True)
class _SecondaryPlan:
    """The measured pieces of one tier's secondary label (#493); everything is Theme- and table-derived."""
    intent: Any
    treatment: Any
    metrics: Any
    table: Any
    size: float
    gap: float


def _secondary_plan(tokens: Any, tier: Any, tier_index: int, primary: Any, primary_metrics: Any,
                    font_metrics: Any) -> _SecondaryPlan | None:
    """Resolve a labels tier's secondary text role, table and gap once (#493); None when it declares none."""
    secondary = tier.label.secondary if tier.role == "labels" and tier.label is not None else None
    if secondary is None:
        return None
    treatment = tokens.text_treatment(secondary.typography_role)
    size = float(treatment.font_size)
    ratio = tokens.optional_number(secondary.typography_role, "labelGap")
    if ratio is not None and ratio < 0:
        raise LayoutError("E_PRESENTATION_AXIS_INVALID", f"/view/body/axis/tiers/{tier_index}",
                          detail=f"label-gap:{secondary.typography_role}")
    if ratio is not None:
        gap = float(ratio) * size
    else:
        gap = 0.0 if secondary.placement == "stacked" else _measure(" ", primary, primary_metrics)
    return _SecondaryPlan(secondary, treatment, metric_for_role(tokens, secondary.typography_role, font_metrics),
                          axis_name_table(secondary.name_table_id), size, gap)


def _line_extents(treatment: Any) -> tuple[float, float]:
    """Block extent of one text line above and below its baseline, the convention `place_text` boxes use."""
    size = float(treatment.font_size)
    return size, size * (float(treatment.line_height) - 1)


def _label_block(primary: Any, plan: _SecondaryPlan | None) -> float:
    """Block size the label line(s) of one cell occupy: the primary alone, a stack, or one shared baseline."""
    above, below = _line_extents(primary)
    if plan is None:
        return above + below
    above_s, below_s = _line_extents(plan.treatment)
    if plan.intent.placement == "stacked":
        return above + below + plan.gap + above_s + below_s
    return max(above, above_s) + max(below, below_s)


def _measure(content: str, treatment: Any, metrics: Any) -> float:
    """Width of one axis text in its own role's treatment: the single measurement both texts use."""
    return measure_text_width(content, font_size=float(treatment.font_size), font_metrics=metrics,
                              letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                              numeric_spacing=treatment.numeric_spacing)


def _secondary_outcomes(*, tier_index: int, plan: _SecondaryPlan, intervals: Any, outcomes: tuple[AxisIntervalOutcome, ...],
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
        secondary_width = _measure(content, plan.treatment, plan.metrics)
        required = (secondary_width if plan.intent.placement == "stacked"
                    else _measure(outcome.label, primary, primary_metrics) + gap + secondary_width)
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


def _axis_tick_length(theme_tokens: Any, role: str, slot_block_size: Decimal, tier_index: int) -> Decimal | None:
    """The Theme-declared tick length of a grid role (#492), or None for the full-height line."""
    declared = theme_tokens.optional_number(role, "tickLength")
    if declared is None:
        return None
    source = f"/view/body/axis/tiers/{tier_index}"
    if not declared > 0:
        raise LayoutError("E_PRESENTATION_AXIS_INVALID", source, detail=f"tick-length:{role}")
    if declared > slot_block_size:
        raise LayoutError("E_PRESENTATION_AXIS_OVERFLOW", source, detail=f"tick-length:{role}")
    return declared


def compose_axis(request: SurfaceLayoutRequest, base: SurfaceBaseGeometry) -> SurfaceAxisPlacements:
    """Place all axis tiers against completed scale and return calendar intervals, not shapes."""
    if request.theme_tokens is None or request.font_metrics is None:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    start, end = request.projection.window
    scale, timeline = base.scale, base.timeline
    axis = base.by_source["timeline-axis"]
    tokens, font_metrics = request.theme_tokens, request.font_metrics
    shapes: list[ShapePlacement] = []
    text: list[TextPlacement] = []
    outcomes: list[AxisTierOutcome] = []
    decisions: list[PlacementDecision] = []
    label_targets: dict[tuple[str, str, str], str] = {}
    band_targets: dict[tuple[str, str, str], str] = {}
    diagnostics: list[str] = []
    visible_overflows: list[tuple[TextPlacement, LabelRect]] = []
    separator_marks: list[tuple[float, float, float]] = []
    label_lane_offset = band_lane_offset = 0.0
    band_ordinal = label_ordinal = 0
    tiers = request.surface_content.axis_tiers
    band_tier_count = sum(item.role == "band" for item in tiers)
    declared_lanes: dict[int, tuple[float, float]] = {}
    lane_by_unit: dict[str, tuple[float, float]] = {}
    lane_cursor = 0.0
    for tier_index, tier in enumerate(tiers):
        if tier.role != "labels" or tier.label is None:
            continue
        role = tier.typography_role or "axis"
        declared = tokens.optional_number(role, "laneBlockSize")
        treatment = tokens.text_treatment(role)
        if declared is not None and float(declared) > 0 and tier.label.orientation == "horizontal":
            declared_lanes[tier_index] = (lane_cursor, float(declared))
            lane_by_unit.setdefault(tier.unit, (lane_cursor, float(declared)))
            lane_cursor += float(declared)
        else:
            first_plan = _secondary_plan(tokens, tier, tier_index, treatment,
                                         metric_for_role(tokens, role, font_metrics), font_metrics)
            lane_cursor += ((_label_block(treatment, first_plan) if first_plan is not None
                             else float(treatment.font_size * treatment.line_height))
                            + float(GEOMETRY_TOLERANCE))

    for tier_index, tier in enumerate(tiers):
        form = tier.label.form if tier.label else None
        name_table = axis_name_table(tier.label.name_table_id) if tier.label else None
        treatment = tokens.text_treatment(tier.typography_role or "axis")
        metrics = metric_for_role(tokens, tier.typography_role or "axis", font_metrics)
        axis_size = float(treatment.font_size)
        plan = _secondary_plan(tokens, tier, tier_index, treatment, metrics, font_metrics)
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
                band_lane_size = axis_size * float(treatment.line_height) + float(GEOMETRY_TOLERANCE)
                if band_lane_offset + band_lane_size > float(axis.bounds.block_size) + float(GEOMETRY_TOLERANCE):
                    raise LayoutError("E_PRESENTATION_AXIS_OVERFLOW", f"/view/body/axis/tiers/{tier_index}", detail=f"band-lane:{band_ordinal}")
                band_block, band_block_size = axis.bounds.block + Decimal(str(band_lane_offset)), Decimal(str(band_lane_size))
            gap = float(tokens.optional_number(semantic_binding(semantic_id).scene_role, "cellGap") or 0)
            for interval in intervals:
                raw, raw2 = coordinate_for_date(interval.start, scale), coordinate_for_date(interval.end, scale)
                x, x2 = raw, raw2
                if gap:
                    x, x2 = x + gap / 2, max(x + gap / 2, x2 - gap / 2)
                # A cell at the window edge reaches the plot edge (#880); the cell gap lies between cells, so the
                # outer edge of that cell takes no gap and ends where the axis rule ends.
                edge, edge2 = extend_to_plot_edges(raw, raw2, scale=scale, plot=base.plot)
                x, x2 = (edge if edge != raw else x), (edge2 if edge2 != raw2 else x2)
                placement_id = f"axis-band-rect:{tier_index}:{interval.index}"
                treatment_bg, paint_order = tokens.background(semantic_binding(semantic_id).scene_role)
                if treatment_bg != "none":
                    band_targets[("axis-band", interval.level, str(interval.index))] = placement_id
                    shapes.append(ShapePlacement(placement_id, "timeline-axis", "Rect",
                        Rect(Decimal(str(x)), band_block, Decimal(str(max(0.0, x2 - x))), band_block_size),
                        semantic_id=semantic_id, paint_order=paint_order))
            if band_tier_count > 1 and tier.unit not in lane_by_unit:
                band_lane_offset += band_lane_size
            band_ordinal += 1
        elif tier.role in {"grid-major", "grid-minor"}:
            semantic_id = "axisGrid" if tier.role == "grid-major" else "axisGridMinor"
            tick = _axis_tick_length(tokens, semantic_binding(semantic_id).scene_role, axis.bounds.block_size, tier_index)
            if tick is None:
                grid_top, grid_size = base.plot.block, base.plot.block_size
            else:
                grid_top, grid_size = axis.bounds.block + axis.bounds.block_size - tick, tick
            for interval in intervals:
                x = coordinate_for_date(interval.start, scale)
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
            block = _label_block(treatment, plan)
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
                secondary_width = _measure(secondary_text, plan.treatment, plan.metrics) if secondary_text else 0.0
                if secondary_text and plan.intent.placement == "inline":
                    occupied = width + gap + secondary_width
                inline = x if tier.label.align == "start" else x + (available - occupied) / 2
                if tier_index in declared_lanes:
                    line_block = axis_size * float(treatment.line_height)
                    baseline = float(axis.bounds.block) + label_lane_offset + (lane_size - line_block) / 2 + axis_size
                else:
                    baseline = float(axis.bounds.block) + label_lane_offset + (axis_size if orientation == "horizontal" else (0 if orientation == "rotate-cw" else width))
                secondary_baseline = baseline
                if plan is not None:
                    line_top = float(axis.bounds.block) + label_lane_offset + (
                        (lane_size - block) / 2 if tier_index in declared_lanes else 0.0)
                    above, below = _line_extents(treatment)
                    above_secondary, _ = _line_extents(plan.treatment)
                    if plan.intent.placement == "stacked":
                        baseline = line_top + above
                        secondary_baseline = line_top + above + below + plan.gap + above_secondary
                    else:
                        baseline = secondary_baseline = line_top + max(above, above_secondary)
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
    bands = tuple(item for item in shapes if item.semantic_id in axis_band_semantic_ids())
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
    minimum = base.metric_values.get("timeline.calendarClosed.minimumDayWidth")
    closed = contract.time.calendar_closed
    if minimum is not None and scale.unit_ratio < float(minimum):
        closed = contract.time.calendar_exceptions
    calendar = calendar_overlay_intervals(
        closed_days=tuple(closed), start=start, end=end, coordinate=coordinate_for_date, scale=scale)
    return SurfaceAxisPlacements(tuple(shapes), tuple(text), tuple(outcomes), tuple(decisions),
        label_targets, band_targets, tuple(diagnostics), tuple(visible_overflows), calendar)
