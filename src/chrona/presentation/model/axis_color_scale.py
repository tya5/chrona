"""Resolve explicit Theme colour scales for calendar axis-band intervals.

This module operates on the neutral temporal intervals.  It does not complete
geometry or know how an adapter paints the resulting concrete colours.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
import re
from typing import TYPE_CHECKING

from chrona.presentation.model.color_separability import ScaleCollision, scale_collisions

if TYPE_CHECKING:
    from chrona.presentation.model.surface_content import AxisTier
    from chrona.presentation.model.theme_tokens import ThemeTokenView


_UNIT_ORDER = {"year": 6, "half": 5, "quarter": 4, "month": 3, "week": 2, "day": 1}
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class AxisBandFillSpec:
    """View intent for mapping one axis-band interval to a Theme scale value."""

    scale_id: str
    key: str
    containing_tier: int | None = None


@dataclass(frozen=True)
class AxisBandScaleResolution:
    """Concrete paints keyed by stable axis-band placement id plus #421 findings."""

    paints: tuple[tuple[str, str], ...] = ()
    collisions: tuple[ScaleCollision, ...] = ()


class AxisBandScaleError(ValueError):
    """Stable rejection of an invalid axis-band scale target or mapping."""

    def __init__(self, code: str, detail: str, path: str):
        self.code, self.detail, self.path = code, detail, path
        super().__init__(f"{code}:{path}:{detail}")


def validate_axis_band_fill_targets(tiers: Sequence[AxisTier], tokens: ThemeTokenView) -> None:
    """An opted-in scale must paint an existing visible solid-fill band channel."""
    from chrona.presentation.model.semantic_registry import axis_band_semantic_ids, semantic_binding

    semantic_ids = axis_band_semantic_ids()
    ordinal = 0
    for index, tier in enumerate(tiers):
        if tier.fill_scale is not None:
            path = f"/view/body/axis/tiers/{index}/fillScale"
            if tier.role != "band" or ordinal >= len(semantic_ids):
                raise AxisBandScaleError("E_PRESENTATION_AXIS_SCALE_TARGET", "target has no declared band role", path)
            role = semantic_binding(semantic_ids[ordinal]).scene_role
            if (tokens.background(role)[0] != "fill"
                    or tokens.optional_color(role, "gradientStart") is not None
                    or tokens.optional_color(role, "gradientEnd") is not None
                    or tokens.optional_number(role, "gradientAngle") is not None):
                raise AxisBandScaleError("E_PRESENTATION_AXIS_SCALE_TARGET",
                                         "target requires a visible solid-fill band without a covering gradient", path)
        if tier.role == "band":
            ordinal += 1


def resolve_axis_band_scales(
    tiers: Sequence[AxisTier], *, window: tuple[date, date], fiscal_start_month: int,
    scales: Mapping[str, object], categories: Mapping[str, object], color_vision: tuple[str, ...] = (),
) -> AxisBandScaleResolution:
    """Resolve every opted-in band interval from exact Scheme-slot mappings.

    The interval module is imported lazily so a View without ``fillScale`` is a
    true no-op and does not validate or inspect dates, Theme, or Scheme data.
    """
    specs = tuple(getattr(tier, "fill_scale", None) for tier in tiers)
    if not any(spec is not None for spec in specs):
        return AxisBandScaleResolution()

    from chrona.presentation.axis_intervals import axis_band_placement_id, axis_intervals

    interval_sets = tuple(
        axis_intervals(window[0], window[1], tier.unit, tick_step=tier.every,
                       fiscal_start_month=fiscal_start_month)
        if getattr(tier, "unit", None) in _UNIT_ORDER and getattr(tier, "role", None) == "band"
        else ()
        for tier in tiers
    )
    paints: list[tuple[str, str]] = []
    collisions: list[ScaleCollision] = []
    for tier_index, (tier, spec) in enumerate(zip(tiers, specs, strict=True)):
        if spec is None:
            continue
        pointer = f"/view/body/axis/tiers/{tier_index}/fillScale"
        if getattr(tier, "role", None) != "band" or getattr(tier, "unit", None) not in _UNIT_ORDER:
            raise AxisBandScaleError("E_PRESENTATION_AXIS_SCALE_TARGET", "target must be a fixed-unit band tier", pointer)
        if not isinstance(spec, AxisBandFillSpec) or not isinstance(spec.scale_id, str) or not spec.scale_id:
            raise AxisBandScaleError("E_PRESENTATION_AXIS_SCALE_TARGET", "invalid fillScale", pointer)
        if spec.key not in {"alternating", "interval"}:
            raise AxisBandScaleError("E_PRESENTATION_AXIS_SCALE_TARGET", "key must be alternating or interval", pointer + "/key")

        source_tier_index = tier_index
        if spec.containing_tier is not None:
            parent_index = spec.containing_tier
            parent_pointer = pointer + "/containingTier"
            if isinstance(parent_index, bool) or not isinstance(parent_index, int) or not 0 <= parent_index < len(tiers):
                raise AxisBandScaleError("E_PRESENTATION_AXIS_SCALE_PARENT", "containingTier is not a declared tier", parent_pointer)
            parent = tiers[parent_index]
            if (parent_index == tier_index or getattr(parent, "role", None) != "band"
                    or getattr(parent, "unit", None) not in _UNIT_ORDER
                    or _UNIT_ORDER[parent.unit] <= _UNIT_ORDER[tier.unit]):
                raise AxisBandScaleError("E_PRESENTATION_AXIS_SCALE_PARENT", "containingTier must name a strictly coarser fixed-unit band", parent_pointer)
            source_tier_index = parent_index

        source_intervals = interval_sets[source_tier_index]
        if not source_intervals:
            raise AxisBandScaleError("E_PRESENTATION_AXIS_SCALE_PARENT", "source tier has no selected intervals", pointer)
        domain = (("0", "1") if spec.key == "alternating"
                  else tuple(str(item.index) for item in source_intervals))
        if not domain:
            raise AxisBandScaleError("E_PRESENTATION_SCALE_MAPPING", "empty interval domain", pointer)
        declared = scales.get(spec.scale_id) if isinstance(scales, Mapping) else None
        slots = declared.get("slots") if isinstance(declared, Mapping) else None
        if (not isinstance(declared, Mapping) or "palette" in declared or not isinstance(slots, Mapping)
                or set(slots) != set(domain) or not isinstance(categories, Mapping)):
            raise AxisBandScaleError("E_PRESENTATION_SCALE_MAPPING", f"{spec.scale_id}: exact slots required for {domain}", pointer)
        resolved: list[tuple[str, str]] = []
        for value in domain:
            slot = slots[value]
            color = categories.get(slot) if isinstance(slot, str) else None
            if not isinstance(color, str) or _HEX.fullmatch(color) is None:
                raise AxisBandScaleError("E_PRESENTATION_SCALE_MAPPING", f"{spec.scale_id}:{value}: unknown Scheme category", pointer)
            resolved.append((value, color))
        collisions.extend(scale_collisions(spec.scale_id, tuple(resolved), color_vision))
        color_by_value = dict(resolved)

        for interval in interval_sets[tier_index]:
            if spec.containing_tier is None:
                key = str(interval.index % 2) if spec.key == "alternating" else str(interval.index)
            else:
                containing = tuple(
                    candidate for candidate in source_intervals
                    if candidate.natural_start <= interval.natural_start
                    and candidate.natural_end >= interval.natural_end
                )
                if len(containing) != 1:
                    raise AxisBandScaleError(
                        "E_PRESENTATION_AXIS_SCALE_PARENT",
                        f"child natural interval {interval.natural_start}..{interval.natural_end} has {len(containing)} selected containers",
                        pointer + "/containingTier",
                    )
                key = str(containing[0].index % 2) if spec.key == "alternating" else str(containing[0].index)
            if key not in color_by_value:
                raise AxisBandScaleError("E_PRESENTATION_SCALE_MAPPING", f"source value {key!r} is outside {domain}", pointer)
            paints.append((axis_band_placement_id(tier_index, interval.index), color_by_value[key]))

    return AxisBandScaleResolution(tuple(paints), tuple(dict.fromkeys(collisions)))
