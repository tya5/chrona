"""Axis label lanes: the block extent each labels tier occupies, shared by placement and measurement (#1150)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_geometry import GEOMETRY_TOLERANCE
from chrona.presentation.layout.text import measure_text_width, metric_for_role
from chrona.presentation.model.axis_names import axis_name_table


@dataclass(frozen=True)
class SecondaryPlan:
    """The measured pieces of one tier's secondary label (#493); everything is Theme- and table-derived."""
    intent: Any
    treatment: Any
    metrics: Any
    table: Any
    size: float
    gap: float


def secondary_plan(tokens: Any, tier: Any, tier_index: int, primary: Any, primary_metrics: Any,
                    font_metrics: Any) -> SecondaryPlan | None:
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
        gap = 0.0 if secondary.placement == "stacked" else measure_axis_text(" ", primary, primary_metrics)
    return SecondaryPlan(secondary, treatment, metric_for_role(tokens, secondary.typography_role, font_metrics),
                          axis_name_table(secondary.name_table_id), size, gap)


def line_extents(treatment: Any) -> tuple[float, float]:
    """Block extent of one text line above and below its baseline, the convention `place_text` boxes use."""
    size = float(treatment.font_size)
    return size, size * (float(treatment.line_height) - 1)


def label_block(primary: Any, plan: SecondaryPlan | None) -> float:
    """Block size the label line(s) of one cell occupy: the primary alone, a stack, or one shared baseline."""
    above, below = line_extents(primary)
    if plan is None:
        return above + below
    above_s, below_s = line_extents(plan.treatment)
    if plan.intent.placement == "stacked":
        return above + below + plan.gap + above_s + below_s
    return max(above, above_s) + max(below, below_s)


def measure_axis_text(content: str, treatment: Any, metrics: Any) -> float:
    """Width of one axis text in its own role's treatment: the single measurement both texts use."""
    return measure_text_width(content, font_size=float(treatment.font_size), font_metrics=metrics,
                              letter_spacing=float(treatment.letter_spacing), text_transform=treatment.transform,
                              numeric_spacing=treatment.numeric_spacing)


@dataclass(frozen=True)
class LabelLanePlan:
    """Where each labels tier's lane starts and how tall it is; `total` is the sum of every lane."""

    declared: dict[int, tuple[float, float]]
    by_unit: dict[str, tuple[float, float]]
    total: float


def plan_label_lanes(tiers: Any, tokens: Any, font_metrics: Any) -> LabelLanePlan:
    """Stack the labels tiers' lanes: a declared `laneBlockSize` for a horizontal tier, else its label block."""
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
            first_plan = (secondary_plan(tokens, tier, tier_index, treatment,
                                         metric_for_role(tokens, role, font_metrics), font_metrics)
                          if tier.label.secondary is not None else None)
            lane_cursor += ((label_block(treatment, first_plan) if first_plan is not None
                             else float(treatment.font_size * treatment.line_height))
                            + float(GEOMETRY_TOLERANCE))
    return LabelLanePlan(declared_lanes, lane_by_unit, lane_cursor)


def derived_axis_block_size(tiers: Any, tokens: Any, font_metrics: Any) -> Decimal | None:
    """The axis block size a Theme may leave unbound: the sum of the axis lanes (#1150).

    Labels tiers stack their lanes, and a band tier stacks its own lane only when several band tiers
    share the axis and none shares a declared label lane (a single band spans the axis; grid tiers
    take no lane); the two stacks overlay each other, so the axis holds the taller. A rotated label
    tier sizes its lane from the interval widths, which are not known before placement, so a set that
    has one returns None and the metric stays required, as before.
    """
    if not tiers or any(tier.role == "labels" and (tier.label is None or tier.label.orientation != "horizontal")
                        for tier in tiers):
        return None
    labels = plan_label_lanes(tiers, tokens, font_metrics)
    bands = [tier for tier in tiers if tier.role == "band"]
    band_stack = 0.0
    if len(bands) > 1:
        for tier in bands:
            if tier.unit not in labels.by_unit:
                treatment = tokens.text_treatment(tier.typography_role or "axis")
                band_stack += float(treatment.font_size) * float(treatment.line_height) + float(GEOMETRY_TOLERANCE)
    total = max(labels.total, band_stack)
    return Decimal(str(total)) if total > 0 else None
