"""Deterministic normal-flow engine for intent-oriented Layout Profile v0.2."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from collections import Counter
from decimal import ROUND_CEILING, Decimal, getcontext
from types import MappingProxyType
from typing import Any, Callable, Literal, Mapping

from chrona.presentation.layout.model import (
    CountDependentHeadingFitError, LayoutDecision, LayoutError, LayoutManifest, Measurement, Rect, RegionFrame, ResolvedLayoutProfile, SlotHeading,
    RelationRouteStyle,
    RelationUnroutableMode, PointHostMode,
)
from chrona.presentation.model.wording_tables import is_wording_ref, wording_resolver
from chrona.presentation.layout.surface_quality import FitWarning
from chrona.presentation.layout.tracks import resolve_flexible_tracks as _resolve_flexible_tracks


getcontext().prec = 28
ZERO = Decimal(0)


@dataclass(frozen=True, slots=True)
class SourceInlineBudget:
    """Runtime allocation evidence, never part of a resolved resource identity."""

    slot_id: str
    path: str
    available_inline: Decimal
    ceiling: Decimal
    source_kind: Literal["table", "heading"] = "table"

    @property
    def failure_code(self) -> str:
        return "E_LAYOUT_TEXT_OVERFLOW" if self.source_kind == "heading" else "E_LAYOUT_TABLE_OVERFLOW"


@dataclass(frozen=True, slots=True)
class LayoutSizingContext:
    """Per-solve source closure and ceilings, separate from resource resolution."""

    source_budgets: Mapping[str, SourceInlineBudget]
    measure_source: Callable[[str, Decimal], Measurement] | None = None
    owner_inline_minima: Mapping[str, Decimal] = field(default_factory=dict)
    by_path: Mapping[str, SourceInlineBudget] = field(init=False)

    def __post_init__(self) -> None:
        budgets = dict(self.source_budgets)
        object.__setattr__(self, "source_budgets", MappingProxyType(budgets))
        object.__setattr__(self, "by_path", MappingProxyType({b.path: b for b in budgets.values()}))
        minima = dict(self.owner_inline_minima)
        if any(not isinstance(node_id, str) or not node_id
               or not isinstance(value, Decimal) or not value.is_finite() or value < ZERO
               for node_id, value in minima.items()):
            raise ValueError("owner inline minima require non-empty node ids and finite nonnegative Decimal extents")
        object.__setattr__(self, "owner_inline_minima", MappingProxyType(minima))

    def measurement(self, node: Mapping[str, Any], path: str, inline: Decimal,
                    fallback: Measurement) -> Measurement:
        measured = (self.measure_source(str(node["id"]), inline)
                    if path in self.by_path and self.measure_source is not None else fallback)
        return _with_owner_inline_minimum(measured, self.owner_inline_minima.get(str(node["id"])))

    def close_sources(self, measurements: Mapping[str, Measurement]) -> Mapping[str, Measurement]:
        if self.measure_source is None:
            return measurements
        result = dict(measurements)
        for slot_id, budget in self.source_budgets.items():
            if slot_id not in result:
                raise LayoutError("E_LAYOUT_MEASUREMENT_REQUIRED", budget.path, slot_id)
            result[slot_id] = self.measure_source(slot_id, budget.ceiling)
        return result


def _limit_inline_base(base: tuple[Decimal, Decimal | None, Decimal],
                       budget: SourceInlineBudget, figure_dependencies: frozenset[str] = frozenset()) -> tuple[Decimal, Decimal, Decimal]:
    """Cap a track without converting flexible allocation into a fixed track.

    Intrinsic text floors must already be closed by the source at this budget;
    this function never erases a mandatory or authored minimum.
    """
    minimum, target, weight = base
    if minimum > budget.ceiling:
        if budget.source_kind == "heading" and figure_dependencies:
            raise CountDependentHeadingFitError(budget.path, budget.slot_id,
                "intrinsic text minimum exceeds the declared ceiling", figure_dependencies)
        raise LayoutError(budget.failure_code, budget.path, budget.slot_id,
                          "mandatory or authored inline minimum exceeds the declared ceiling")
    return minimum, min(target, budget.ceiling) if target is not None else budget.ceiling, weight


def validate_source_inline_budgets(expected: Mapping[str, SourceInlineBudget],
                                 actual: Mapping[str, SourceInlineBudget]) -> None:
    """Reject changed or circular budgets while allowing headings narrower than their probe."""
    for slot_id, budget in expected.items():
        final = actual.get(slot_id)
        if final is None:
            raise LayoutError(budget.failure_code, budget.path, slot_id,
                              "budget closure changed its active sources")
        if (final.path != budget.path or final.source_kind != budget.source_kind):
            raise LayoutError(budget.failure_code, budget.path, slot_id,
                              "source inline budget identity changed")
        if budget.source_kind == "heading":
            # The neutral probe is an upper bound for a heading. Sibling floors
            # may consume part of that width in the final track allocation; the
            # heading is remeasured at its actual width before block closure.
            if (final.available_inline > budget.available_inline
                    or final.ceiling > budget.ceiling):
                raise LayoutError(budget.failure_code, budget.path, slot_id,
                                  "heading allocation exceeds its probed ceiling")
        elif final != budget:
            # Tables keep strict probe/final equality, including their share cap.
            raise LayoutError(budget.failure_code, budget.path, slot_id,
                              "source inline budget depends on its intrinsic allocation")
    if actual.keys() != expected.keys():
        slot_id = next(key for key in actual if key not in expected)
        raise LayoutError(actual[slot_id].failure_code, actual[slot_id].path, slot_id,
                          "budget closure changed its active sources")


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _distance(profile: ResolvedLayoutProfile, path: str) -> Decimal:
    try:
        return profile.distances[path]
    except KeyError as error:
        raise LayoutError("E_LAYOUT_TOKEN_UNKNOWN", path) from error


def _slot_heading(node: Mapping[str, Any], profile: ResolvedLayoutProfile | None = None, path: str = "") -> SlotHeading | None:
    """The slot's declared caption (#1064); its shape was validated with the profile."""
    declared = node.get("heading")
    if declared is None:
        return None
    gap = _distance(profile, f"{path}/heading/gap") if profile is not None and "gap" in declared else None
    text = declared.get("text")
    if is_wording_ref(text):  # a render resolves it for its locale first; this stands in for a bare Layout run
        text = wording_resolver("en-US", None).resolve(text)
    return SlotHeading(text, str(declared.get("align", "start")), str(declared.get("block", "top")),
                       gap, template=declared.get("template"))


def _padding(profile: ResolvedLayoutProfile, node: Mapping[str, Any], path: str) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    raw = node.get("padding", 0)
    if isinstance(raw, dict) and "token" not in raw:
        return tuple(_distance(profile, f"{path}/padding/{name}") for name in ("inlineStart", "inlineEnd", "blockStart", "blockEnd"))  # type: ignore[return-value]
    value = _distance(profile, f"{path}/padding")
    return value, value, value, value


# Sources whose composer shrinks its content to the inline size it is given and
# reports every shrink (`W_LAYOUT_TEXT_ELLIPSIZED`). A `content`-sized slot of such
# a source that declares `ellipsize-with-source` is bounded by its container
# instead of growing past it (#497, Specification 33 section 6). A source joins
# this set together with its report, never before.
_SHRINKING_SOURCES = frozenset({"legend"})


def _gap(profile: ResolvedLayoutProfile, node: Mapping[str, Any], path: str) -> Decimal:
    return _distance(profile, f"{path}/gap") if "gap" in node else ZERO


def _slot_measurement(node: Mapping[str, Any], measurements: Mapping[str, Measurement], path: str) -> Measurement:
    try:
        return measurements[str(node["id"])]
    except KeyError as error:
        raise LayoutError("E_LAYOUT_MEASUREMENT_REQUIRED", path, str(node["id"])) from error


def _active_children(node: Mapping[str, Any], measurements: Mapping[str, Measurement]) -> tuple[tuple[int, Mapping[str, Any]], ...]:
    """Keep original profile indices while omitting absent optional sources."""
    return tuple((index, child) for index, child in enumerate(node["children"])
                 if not (child["kind"] == "slot" and child.get("priority") == "optional"
                 and str(child["id"]) not in measurements))


def _block_measurement(measure: Measurement, block: Decimal) -> Measurement:
    return Measurement(measure.min_inline, measure.preferred_inline, measure.max_inline,
                       block, block, block, measure.first_baseline, measure.last_baseline)


def _retain_required_row_blocks(measurements: list[Measurement | None],
                                required: Mapping[int, Decimal]) -> None:
    """A bounded cell's completed line stack cannot be lost to a later cell."""
    for row, block in required.items():
        measured = measurements[row]
        if measured is not None:
            measurements[row] = replace(measured, min_block=max(measured.min_block, block),
                                         preferred_block=max(measured.preferred_block, block),
                                         max_block=max(measured.max_block, block))


def _spec_base(spec: Any, *, axis: str, measurement: Measurement | None,
               profile: ResolvedLayoutProfile, path: str,
               sizing: LayoutSizingContext | None = None) -> tuple[Decimal, Decimal | None, Decimal]:
    base = _unbounded_spec_base(spec, axis=axis, measurement=measurement, profile=profile, path=path)
    budget = sizing.by_path.get(path.removesuffix("/inlineSize")) if sizing and axis == "inline" else None
    dependencies = _intrinsic_floor_dependencies(spec, measurement)
    return _limit_inline_base(base, budget, dependencies) if budget is not None else base


def _intrinsic_floor_dependencies(spec: Any, measurement: Measurement | None) -> frozenset[str]:
    """Only a measured text floor is dependent; authored fixed/minimum sizes are not."""
    if measurement is None:
        return frozenset()
    if isinstance(spec, str) and spec in {"content", "min-content", "max-content"}:
        return measurement.figure_dependencies
    if isinstance(spec, dict):
        if "fitContent" in spec:
            return measurement.figure_dependencies
        if "minmax" in spec:
            return _intrinsic_floor_dependencies(spec["minmax"]["min"], measurement)
    return frozenset()


def _unbounded_spec_base(spec: Any, *, axis: str, measurement: Measurement | None, profile: ResolvedLayoutProfile, path: str) -> tuple[Decimal, Decimal | None, Decimal]:
    """Return minimum, preferred/fixed target, and flex weight."""
    if spec == "fill":
        return ZERO, None, Decimal(1)
    if isinstance(spec, dict) and "fr" in spec:
        return ZERO, None, _d(spec["fr"])
    if isinstance(spec, dict) and "fixed" in spec:
        value = spec["fixed"]
        # Aspect-derived track sizes are native Decimal geometry, not tokens.
        fixed = _d(value) if isinstance(value, (int, float, Decimal)) else _distance(profile, path + "/fixed")
        return fixed, fixed, ZERO
    if isinstance(spec, dict) and "aspectRatio" in spec:
        return ZERO, None, ZERO
    if (isinstance(spec, dict) and "minmax" in spec and axis == "inline" and measurement is not None
            and not any((measurement.min_inline, measurement.preferred_inline, measurement.max_inline))
            and spec["minmax"]["min"] == "content"
            and isinstance(spec["minmax"]["max"], dict) and "fr" in spec["minmax"]["max"]):
        # A slot whose source holds nothing has no content to size to and claims no share of the free space:
        # an empty table slot collapses to zero width (#1683).
        return ZERO, ZERO, ZERO
    if isinstance(spec, dict) and "minmax" in spec:
        low, _, _ = _spec_base(spec["minmax"]["min"], axis=axis, measurement=measurement, profile=profile, path=path + "/minmax/min")
        _, high, weight = _spec_base(spec["minmax"]["max"], axis=axis, measurement=measurement, profile=profile, path=path + "/minmax/max")
        return low, high, weight
    if measurement is None:
        raise LayoutError("E_LAYOUT_MEASUREMENT_REQUIRED", path)
    minimum = measurement.min_inline if axis == "inline" else measurement.min_block
    preferred = measurement.preferred_inline if axis == "inline" else measurement.preferred_block
    maximum = measurement.max_inline if axis == "inline" else measurement.max_block
    if spec == "min-content":
        return minimum, minimum, ZERO
    if spec == "max-content":
        return maximum, maximum, ZERO
    if spec == "content":
        return minimum, preferred, ZERO
    if isinstance(spec, dict) and "fitContent" in spec:
        limit = spec["fitContent"]
        bound = _d(limit) if isinstance(limit, (int, float)) else _distance(profile, path + "/fitContent")
        value = min(maximum, max(minimum, min(preferred, bound)))
        return minimum, value, ZERO
    raise LayoutError("E_LAYOUT_SCHEMA", path)


def _allocate(specs: list[Any], available: Decimal, measurements: list[Measurement | None], *, axis: str, profile: ResolvedLayoutProfile, paths: list[str], sizing: LayoutSizingContext | None = None) -> list[Decimal]:
    bases = [_spec_base(spec, axis=axis, measurement=measure, profile=profile, path=path, sizing=sizing) for spec, measure, path in zip(specs, measurements, paths)]
    return _resolve_flexible_tracks(bases, available)


def _measure_node(node: Mapping[str, Any], path: str, measurements: Mapping[str, Measurement],
                  profile: ResolvedLayoutProfile, *,
                  owner_inline_minima: Mapping[str, Decimal] = MappingProxyType({}),
                  exclude_anchored: bool = False) -> Measurement:
    if node["kind"] == "slot":
        measured = _slot_measurement(node, measurements, path)
        floor = owner_inline_minima.get(str(node["id"]))
        return _with_owner_inline_minimum(measured, floor)
    children = [_measure_node(child, f"{path}/children/{index}", measurements, profile,
                              owner_inline_minima=owner_inline_minima,
                              exclude_anchored=exclude_anchored)
                for index, child in _active_children(node, measurements)
                if not (exclude_anchored and node["kind"] == "overlay" and "anchor" in child)]
    i0, i1, b0, b1 = _padding(profile, node, path)
    gap = _gap(profile, node, path)
    count_gap = gap * max(0, len(children) - 1)
    if node["kind"] in {"row", "flow"}:
        minimum_inline = sum((item.min_inline for item in children), ZERO) + count_gap + i0 + i1
        preferred_inline = sum((item.preferred_inline for item in children), ZERO) + count_gap + i0 + i1
        maximum_inline = sum((item.max_inline for item in children), ZERO) + count_gap + i0 + i1
        minimum_block = max((item.min_block for item in children), default=ZERO) + b0 + b1
        preferred_block = max((item.preferred_block for item in children), default=ZERO) + b0 + b1
        maximum_block = max((item.max_block for item in children), default=ZERO) + b0 + b1
    elif node["kind"] == "column":
        minimum_inline = max((item.min_inline for item in children), default=ZERO) + i0 + i1
        preferred_inline = max((item.preferred_inline for item in children), default=ZERO) + i0 + i1
        maximum_inline = max((item.max_inline for item in children), default=ZERO) + i0 + i1
        minimum_block = sum((item.min_block for item in children), ZERO) + count_gap + b0 + b1
        preferred_block = sum((item.preferred_block for item in children), ZERO) + count_gap + b0 + b1
        maximum_block = sum((item.max_block for item in children), ZERO) + count_gap + b0 + b1
    else:  # grid/overlay intrinsic envelope; exact tracks resolve during arrange
        minimum_inline = max((item.min_inline for item in children), default=ZERO) + i0 + i1
        preferred_inline = max((item.preferred_inline for item in children), default=ZERO) + i0 + i1
        maximum_inline = max((item.max_inline for item in children), default=ZERO) + i0 + i1
        minimum_block = max((item.min_block for item in children), default=ZERO) + b0 + b1
        preferred_block = max((item.preferred_block for item in children), default=ZERO) + b0 + b1
        maximum_block = max((item.max_block for item in children), default=ZERO) + b0 + b1
    measured = Measurement(minimum_inline, preferred_inline, maximum_inline,
                           minimum_block, preferred_block, maximum_block)
    return _with_owner_inline_minimum(measured, owner_inline_minima.get(str(node["id"])))


def _with_owner_inline_minimum(measure: Measurement, floor: Decimal | None) -> Measurement:
    """Apply an outer-inline lower bound without rewriting any authored track."""
    if floor is None or floor <= measure.min_inline:
        return measure
    return replace(measure, min_inline=floor,
                   preferred_inline=max(measure.preferred_inline, floor),
                   max_inline=max(measure.max_inline, floor))


def _measure_for_sizing(node: Mapping[str, Any], path: str,
                        measurements: Mapping[str, Measurement],
                        profile: ResolvedLayoutProfile,
                        sizing: LayoutSizingContext | None) -> Measurement:
    return _measure_node(node, path, measurements, profile,
                         owner_inline_minima=(sizing.owner_inline_minima if sizing else MappingProxyType({})))


def measure_required_normal_flow_inline(
        profile: ResolvedLayoutProfile,
        measurements: Mapping[str, Measurement],
        owner_inline_minima: Mapping[str, Decimal] = MappingProxyType({}),
        ) -> Decimal:
    """Close admitted owner floors through the root's normal-flow intrinsic minimum.

    Values are complete outer-inline minima, including the owner's padding.
    Anchored overlay children do not create normal-flow viewport demand; their
    declared/native widths and preferred text widths are not turned into floors.
    The profile's fixed and maximum track declarations remain untouched and are
    still enforced by ordinary arrangement.
    """
    sizing = LayoutSizingContext({}, owner_inline_minima=owner_inline_minima)
    if not sizing.owner_inline_minima:
        return _measure_node(profile.profile["root"], "/root", measurements, profile,
                             exclude_anchored=True).min_inline
    return _measure_node(profile.profile["root"], "/root", measurements, profile,
                         owner_inline_minima=sizing.owner_inline_minima,
                         exclude_anchored=True).min_inline


def _flow_lines(node: Mapping[str, Any], path: str, measurements: Mapping[str, Measurement],
                profile: ResolvedLayoutProfile, inline_size: Decimal,
                height_for: Callable[[Mapping[str, Any], str, Decimal], Decimal],
                sizing: LayoutSizingContext | None = None,
                ) -> list[list[tuple[int, Mapping[str, Any], Measurement, Decimal, Decimal]]]:
    """Resolve flow wrapping once for both natural measurement and arrangement."""
    gap = _gap(profile, node, path)
    minimum = _distance(profile, path + "/itemMinInlineSize")
    lines: list[list[tuple[int, Mapping[str, Any], Measurement, Decimal, Decimal]]] = [[]]
    used = ZERO
    for index, child in _active_children(node, measurements):
        child_path = f"{path}/children/{index}"
        measured = _measure_for_sizing(child, child_path, measurements, profile, sizing)
        budget = sizing.by_path.get(child_path) if sizing else None
        inline_spec = child["inlineSize"]
        base = _spec_base(inline_spec, axis="inline", measurement=measured,
                          profile=profile, path=child_path + "/inlineSize", sizing=sizing)
        if budget is not None and minimum > budget.ceiling:
            raise LayoutError(budget.failure_code, child_path, str(child["id"]),
                              "Flow item minimum exceeds the declared ceiling")
        width = (base[1] if base[2] == ZERO and base[1] is not None
                 else measured.preferred_inline)
        width = max(minimum, base[0], width)
        fixed_ceiling = (isinstance(inline_spec, dict) and (
            "fixed" in inline_spec or ("minmax" in inline_spec
                and isinstance(inline_spec["minmax"]["max"], dict)
                and "fixed" in inline_spec["minmax"]["max"])))
        if fixed_ceiling and base[1] is not None and width > base[1]:
            raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY", child_path + "/inlineSize",
                              str(child["id"]), "Flow item minimum exceeds its authored inline ceiling")
        if budget is not None:
            width = (base[1] if base[2] == ZERO and base[1] is not None
                     else min(width, budget.ceiling))
            width = max(minimum, base[0], width)
            measured = sizing.measurement(child, child_path, width, measured)
        height = height_for(child, child_path, width)  # the extent it is arranged at: natural sizes are kept (Spec 33 section 13)
        if child["kind"] != "slot":
            measured = _block_measurement(measured, height)
        if budget is not None:
            height = measured.preferred_block
        block_spec = child["blockSize"]
        if not (isinstance(block_spec, dict) and "aspectRatio" in block_spec):
            block_minimum, block_target, block_weight = _spec_base(
                block_spec, axis="block", measurement=measured, profile=profile, path=child_path + "/blockSize")
            height = (block_target if block_spec != "content" and block_weight == ZERO and block_target is not None
                      else max(block_minimum, height))
        if isinstance(child.get("inlineSize"), dict) and "aspectRatio" in child["inlineSize"]:
            width = max(minimum, height * _d(child["inlineSize"]["aspectRatio"]))
        if isinstance(child.get("blockSize"), dict) and "aspectRatio" in child["blockSize"]:
            height = width / _d(child["blockSize"]["aspectRatio"])
        if budget is not None and width > budget.ceiling:
            raise LayoutError(budget.failure_code, child_path, str(child["id"]),
                              "authored aspect size exceeds the declared ceiling")
        needed = width if not lines[-1] else gap + width
        if lines[-1] and used + needed > inline_size:
            lines.append([])
            used = ZERO
            needed = width
        lines[-1].append((index, child, measured, width, height))
        used += needed
    return lines


def measure_natural_normal_flow_block(profile: ResolvedLayoutProfile, *, viewport_inline: int,
                                      measurements: Mapping[str, Measurement],
                                      node: Mapping[str, Any] | None = None,
                                      node_path: str = "/root",
                                      sizing: LayoutSizingContext | None = None) -> Decimal:
    """Measure natural normal-flow block extent with arrangement's track rules.

    This is a Layout-owned sizing input. It follows the resolved inline extent
    for wrapped flows, uses the same grid track bases as arrangement, and omits
    anchored overlay decoration from the normal-flow envelope.
    """
    if sizing:
        measurements = sizing.close_sources(measurements)
    def block(node: Mapping[str, Any], path: str, available_inline: Decimal) -> Decimal:
        if node["kind"] == "slot":
            measured = _slot_measurement(node, measurements, path)
            return (sizing.measurement(node, path, available_inline, measured)
                    if sizing else measured).preferred_block
        i0, i1, b0, b1 = _padding(profile, node, path)
        inner_inline = max(ZERO, available_inline - i0 - i1)
        gap = _gap(profile, node, path)
        children = _active_children(node, measurements)
        kind = node["kind"]
        if kind == "overlay":
            natural = max((child_block(child, f"{path}/children/{index}",
                                      _normal_child_inline(child, f"{path}/children/{index}", inner_inline,
                                          _measure_for_sizing(child, f"{path}/children/{index}", measurements, profile, sizing),
                                          profile, sizing, align=child.get("place", {}).get("inline", "start")))
                           for index, child in children if "anchor" not in child), default=ZERO)
            return natural + b0 + b1
        if kind == "flow":
            flow = _flow_lines(node, path, measurements, profile, inner_inline,
                               lambda child, child_path, width: block(child, child_path, width), sizing)
            return sum((max((item[4] for item in line), default=ZERO) for line in flow), ZERO) + \
                gap * max(0, len(flow) - 1) + b0 + b1
        if kind == "grid":
            columns, rows = node["columnTracks"], node["rowTracks"]
            col_measures: list[Measurement | None] = [None] * len(columns)
            row_measures: list[Measurement | None] = [None] * len(rows)
            child_measures: dict[int, Measurement] = {}
            required_rows: dict[int, Decimal] = {}
            for index, child in children:
                measured = _measure_for_sizing(child, f"{path}/children/{index}", measurements, profile, sizing)
                child_measures[index] = measured
                cell = child["cell"]
                if cell.get("columnSpan", 1) == 1:
                    col_measures[cell["column"] - 1] = measured
            col_sizes = _allocate(columns, inner_inline - gap * max(0, len(columns) - 1),
                                  col_measures, axis="inline", profile=profile,
                                  paths=[f"{path}/columnTracks/{i}" for i in range(len(columns))])
            for index, child in children:
                cell = child["cell"]
                if cell.get("rowSpan", 1) == 1:
                    column, span = cell["column"] - 1, cell.get("columnSpan", 1)
                    child_inline = sum(col_sizes[column:column + span], ZERO) + gap * (span - 1)
                    natural_block = _natural_child_block(child, f"{path}/children/{index}",
                                                         _bounded_child_inline(child, f"{path}/children/{index}",
                                                                              child_inline, child_measures[index],
                                                                              profile, sizing, preserve_cell_extent=True),
                                                         measurements, profile, sizing)
                    row_measures[cell["row"] - 1] = _block_measurement(child_measures[index], natural_block)
                    if sizing and f"{path}/children/{index}" in sizing.by_path:
                        row = cell["row"] - 1
                        required_rows[row] = max(required_rows.get(row, ZERO), natural_block)
            _retain_required_row_blocks(row_measures, required_rows)
            row_bases = [_spec_base(spec, axis="block", measurement=measure, profile=profile,
                                    path=f"{path}/rowTracks/{i}")
                         for i, (spec, measure) in enumerate(zip(rows, row_measures))]
            row_sizes = [target if target is not None else minimum for minimum, target, _ in row_bases]
            return sum(row_sizes, ZERO) + gap * max(0, len(rows) - 1) + b0 + b1
        if kind == "row":
            child_measures = [_measure_for_sizing(child, f"{path}/children/{index}", measurements, profile, sizing)
                              for index, child in children]
            specs = [child["inlineSize"] for _, child in children]
            sizes = _allocate(specs, inner_inline - gap * max(0, len(children) - 1), child_measures,
                              axis="inline", profile=profile,
                              paths=[f"{path}/children/{index}/inlineSize" for index, _ in children], sizing=sizing)
            return max((child_block(child, f"{path}/children/{index}", size)
                        for (index, child), size in zip(children, sizes)), default=ZERO) + b0 + b1
        total = b0 + b1 + gap * max(0, len(children) - 1)
        for index, child in children:
            child_path = f"{path}/children/{index}"
            measured = _measure_for_sizing(child, child_path, measurements, profile, sizing)
            child_inline = _normal_child_inline(child, child_path, inner_inline, measured, profile, sizing,
                align=child.get("place", {}).get("inline", node["alignItems"]))
            total += child_block(child, child_path, child_inline)
        return total

    def child_block(node: Mapping[str, Any], path: str, available_inline: Decimal) -> Decimal:
        measured = _measure_for_sizing(node, path, measurements, profile, sizing)
        if sizing:
            measured = sizing.measurement(node, path, available_inline, measured)
        required = block(node, path, available_inline)
        if node["kind"] != "slot":
            measured = _block_measurement(measured, required)
        minimum, target, _ = _spec_base(node["blockSize"], axis="block", measurement=measured,
                                        profile=profile, path=path + "/blockSize")
        if node["blockSize"] != "content" and target is not None:
            return target
        return max(minimum, required)

    root = profile.profile["root"] if node is None else node
    natural = block(root, node_path, _d(viewport_inline))
    measure = _measure_for_sizing(root, node_path, measurements, profile, sizing)
    if root["kind"] != "slot":
        measure = _block_measurement(measure, natural)
    minimum, target, _ = _spec_base(root["blockSize"], axis="block", measurement=measure,
                                    profile=profile, path=node_path + "/blockSize")
    if root["blockSize"] != "content" and target is not None:
        return target
    return max(minimum, natural)


def _natural_child_block(node: Mapping[str, Any], path: str, available_inline: Decimal,
                         measurements: Mapping[str, Measurement],
                         profile: ResolvedLayoutProfile,
                         sizing: LayoutSizingContext | None = None) -> Decimal:
    return measure_natural_normal_flow_block(
        profile, viewport_inline=available_inline, measurements=measurements,
        node=node, node_path=path, sizing=sizing,
    )


def _distributed_start(kind: str, extra: Decimal, count: int, gap: Decimal) -> tuple[Decimal, Decimal]:
    if extra <= ZERO or count == 0:
        return ZERO, gap
    if kind == "center": return extra / 2, gap
    if kind == "end": return extra, gap
    if kind == "space-between" and count > 1: return ZERO, gap + extra / (count - 1)
    if kind == "space-around":
        unit = extra / count; return unit / 2, gap + unit
    if kind == "space-evenly":
        unit = extra / (count + 1); return unit, gap + unit
    return ZERO, gap


def _cross_size(base: tuple[Decimal, Decimal | None, Decimal], available: Decimal,
                *, stretch: bool) -> Decimal:
    _, target, weight = base
    if weight > ZERO:
        return _resolve_flexible_tracks([base], available)[0] if stretch else available
    return target if target is not None else available


def _bounded_child_inline(node: Mapping[str, Any], path: str, available: Decimal,
                           measured: Measurement, profile: ResolvedLayoutProfile,
                           sizing: LayoutSizingContext | None,
                           block_size: Decimal | None = None, *,
                           preserve_cell_extent: bool = False) -> Decimal:
    """Resolve a capped child inside its independently allocated cross/cell space."""
    if sizing is None or path not in sizing.by_path:
        return available
    base = _spec_base(node["inlineSize"], axis="inline", measurement=measured,
                      profile=profile, path=path + "/inlineSize", sizing=sizing)
    used = _cross_size(base, available, stretch=True)
    spec = node["inlineSize"]
    if isinstance(spec, dict) and "aspectRatio" in spec:
        if block_size is None:
            block_base = _spec_base(node["blockSize"], axis="block", measurement=measured,
                                    profile=profile, path=path + "/blockSize")
            block_size = block_base[1] if block_base[1] is not None else measured.preferred_block
        used = block_size * _d(spec["aspectRatio"])
    if used > sizing.by_path[path].ceiling:
        raise LayoutError(sizing.by_path[path].failure_code, path, str(node["id"]),
                          "authored inline size exceeds the declared ceiling")
    # Full-share text budgets constrain copy without shrinking the existing
    # Grid host. A smaller declared share still constrains the host itself.
    return available if preserve_cell_extent and sizing.by_path[path].ceiling == available else used


def _normal_child_inline(child: Mapping[str, Any], path: str, available: Decimal,
                         measured: Measurement, profile: ResolvedLayoutProfile,
                         sizing: LayoutSizingContext | None, *, align: str) -> Decimal:
    """Share the declared column/overlay child width with natural measurement."""
    if sizing and path in sizing.by_path:
        return _bounded_child_inline(child, path, available, measured, profile, sizing)
    spec = child["inlineSize"]
    if isinstance(spec, dict) and "aspectRatio" in spec:
        block_spec = child["blockSize"]
        if isinstance(block_spec, dict) and "fixed" in block_spec:
            block = _spec_base(block_spec, axis="block", measurement=measured,
                               profile=profile, path=path + "/blockSize")[0]
            return block * _d(spec["aspectRatio"])
        return available
    return _cross_size(_spec_base(spec, axis="inline", measurement=measured,
                                  profile=profile, path=path + "/inlineSize"),
                       available, stretch=align == "stretch")


def _cross_position(align: str, start: Decimal, available: Decimal, size: Decimal, safety: str = "strict") -> tuple[Decimal, Decimal]:
    # Sizing is already complete. Alignment must not replace fixed, intrinsic,
    # bounded or aspect-derived dimensions with the container's extent.
    if size > available:
        return start, size
    if align == "center": return start + (available - size) / 2, size
    if align == "end": return start + available - size, size
    return start, size


class _Arranger:
    def __init__(self, profile: ResolvedLayoutProfile, measurements: Mapping[str, Measurement], *,
                 content_sized: bool = False, collect_inline_budgets: bool = False,
                 sizing: LayoutSizingContext | None = None,
                 heading_slots: frozenset[str] = frozenset(),
                 wrapping_table_slots: frozenset[str] = frozenset()):
        self.profile, self.measurements = profile, measurements
        self.content_sized = content_sized
        self.decisions: list[LayoutDecision] = []
        self.fit_warnings: list[FitWarning] = []
        self.source_inline_budgets: dict[str, SourceInlineBudget] = {}
        self.collect_inline_budgets = collect_inline_budgets or sizing is not None
        self.sizing = sizing
        self.heading_slots = (frozenset(b.slot_id for b in sizing.source_budgets.values()
                                       if b.source_kind == "heading") if sizing else heading_slots)
        self.wrapping_table_slots = (frozenset(b.slot_id for b in sizing.source_budgets.values()
                                              if b.source_kind == "table") if sizing else wrapping_table_slots)

    def _measure(self, node: Mapping[str, Any], path: str) -> Measurement:
        return _measure_for_sizing(node, path, self.measurements, self.profile, self.sizing)

    def _record_inline_budget(self, child: Mapping[str, Any], path: str,
                              available_inline: Decimal) -> None:
        slot_id = str(child["id"])
        heading = slot_id in self.heading_slots
        if not self.collect_inline_budgets or ("maxInlineShare" not in child and not heading
                                              and slot_id not in self.wrapping_table_slots):
            return
        ceiling = available_inline * (Decimal(1) if heading else _d(child.get("maxInlineShare", 1)))
        if not ceiling.is_finite() or ceiling <= ZERO:
            raise LayoutError("E_LAYOUT_TEXT_OVERFLOW" if heading else "E_LAYOUT_TABLE_OVERFLOW", path, slot_id,
                              "no positive independently allocated inline budget")
        self.source_inline_budgets[slot_id] = SourceInlineBudget(
            slot_id, path, available_inline, ceiling, "heading" if heading else "table")

    def _warn(self, node: Mapping[str, Any], path: str, *, required_inline: Decimal,
              required_block: Decimal, available_inline: Decimal, available_block: Decimal) -> None:
        self.fit_warnings.append(FitWarning(
            "W_LAYOUT_VISIBLE_OVERFLOW", str(node["id"]), str(node.get("source") or path),
            "layout-track", "visible-overflow", float(max(ZERO, required_inline)),
            float(max(ZERO, required_block)), float(max(ZERO, available_inline)),
            float(max(ZERO, available_block)),
        ))

    def arrange(self, node: Mapping[str, Any], path: str, rect: Rect, references: tuple[str, ...] = ()) -> None:
        position = len(self.decisions)
        self._arrange_node(node, path, rect, references)
        declared = node.get("frame")
        if declared is None:
            return
        # A region frame is recorded with the arranged subtree and never feeds back into it (#889).
        inset = _distance(self.profile, f"{path}/frame/inset") if "inset" in declared else ZERO
        populated = node["kind"] == "slot" or any(
            item.kind == "slot" and item.bounds.inline_size > ZERO and item.bounds.block_size > ZERO
            for item in self.decisions[position + 1:])
        paint = declared.get("paint")
        self.decisions[position] = replace(self.decisions[position], frame=RegionFrame(inset, populated, paint))

    def _arrange_node(self, node: Mapping[str, Any], path: str, rect: Rect, references: tuple[str, ...] = ()) -> None:
        kind, node_id = str(node["kind"]), str(node["id"])
        is_slot = kind == "slot"
        self.decisions.append(LayoutDecision(
            node_id, kind, rect, node.get("source"), node.get("place", {}), references,
            node.get("priority") if is_slot else None,
            node.get("overflow") if is_slot else None,
            node.get("direction") if is_slot else None,
            (_distance(self.profile, f"{path}/gap") if is_slot and "gap" in node else None),
            (_distance(self.profile, f"{path}/itemMinInlineSize") if is_slot and "itemMinInlineSize" in node else None),
            heading=_slot_heading(node, self.profile, path) if is_slot else None,
            columns=int(node["columns"]) if is_slot and "columns" in node else None,
            column_distribution=str(node.get("columnDistribution", "start")) if is_slot else "start",
        ))
        if kind == "slot":
            measure = _slot_measurement(node, self.measurements, path)
            if self.sizing:
                measure = self.sizing.measurement(node, path, rect.inline_size, measure)
                budget = self.sizing.by_path.get(path)
                if budget and (rect.inline_size > budget.ceiling or rect.inline_size < measure.min_inline):
                    if (budget.source_kind == "heading" and rect.inline_size <= budget.ceiling
                            and measure.figure_dependencies):
                        raise CountDependentHeadingFitError(path, node_id,
                            "completed source does not fit its intrinsic text minimum", measure.figure_dependencies)
                    raise LayoutError(budget.failure_code, path, node_id,
                                      "completed source does not fit its strict inline budget")
            if rect.inline_size < measure.min_inline or rect.block_size < measure.min_block:
                self._warn(node, path, required_inline=measure.min_inline,
                           required_block=measure.min_block, available_inline=rect.inline_size,
                           available_block=rect.block_size)
            return
        if kind == "overlay":
            self._overlay(node, path, rect); return
        if kind == "grid":
            self._grid(node, path, rect); return
        if kind == "flow":
            self._flow(node, path, rect); return
        self._linear(node, path, rect)

    def _content(self, node: Mapping[str, Any], path: str, rect: Rect) -> tuple[Decimal, Decimal, Decimal, Decimal]:
        i0, i1, b0, b1 = _padding(self.profile, node, path)
        inline_size, block_size = rect.inline_size - i0 - i1, rect.block_size - b0 - b1
        if inline_size < ZERO or block_size < ZERO:
            self._warn(node, path, required_inline=i0 + i1, required_block=b0 + b1,
                       available_inline=rect.inline_size, available_block=rect.block_size)
        return rect.inline + i0, rect.block + b0, max(ZERO, inline_size), max(ZERO, block_size)

    def _wrapped_block(self, child: Mapping[str, Any], path: str, measure: Measurement, inline: Decimal) -> Measurement:
        """Close a bounded source or container at its actual arranged inline extent."""
        if self.sizing and path in self.sizing.by_path:
            return self.sizing.measurement(child, path, inline, measure)
        if child["kind"] == "slot":
            return measure
        return _block_measurement(measure, _natural_child_block(child, path, inline, self.measurements, self.profile, self.sizing))

    def _column_child_inline(self, child: Mapping[str, Any], path: str, measure: Measurement,
                             cross: Decimal, node: Mapping[str, Any]) -> Decimal:
        """The inline extent a column gives a child, as `_linear` resolves it for arrangement."""
        align = child.get("place", {}).get("inline", node["alignItems"])
        return _normal_child_inline(child, path, cross, measure, self.profile, self.sizing, align=align)

    def _linear(self, node: Mapping[str, Any], path: str, rect: Rect) -> None:
        inline, block, inline_size, block_size = self._content(node, path, rect)
        row = node["kind"] == "row"; main = inline_size if row else block_size
        cross = block_size if row else inline_size; gap = _gap(self.profile, node, path)
        children = _active_children(node, self.measurements)
        available_inline = inline_size - gap * max(0, len(children) - 1) if row else inline_size
        for index, child in children:
            self._record_inline_budget(child, f"{path}/children/{index}", available_inline)
        measured = [self._measure(child, f"{path}/children/{i}") for i, child in children]
        if not row:
            # A flow child wraps at the inline extent the column gives it, so its block allocation is its line stack
            # there, as arrangement will lay it out (#1219).
            measured = [self._wrapped_block(child, f"{path}/children/{i}", m, self._column_child_inline(child, f"{path}/children/{i}", m, cross, node))
                        for (i, child), m in zip(children, measured)]
        specs = [child["inlineSize" if row else "blockSize"] for _, child in children]
        specs = [
            {"fixed": cross * _d(spec["aspectRatio"]) if row else cross / _d(spec["aspectRatio"])}
            if isinstance(spec, dict) and "aspectRatio" in spec else spec
            for spec in specs
        ]
        paths = [f"{path}/children/{i}/{'inlineSize' if row else 'blockSize'}" for i, _ in children]
        sizes = _allocate(specs, main - gap * max(0, len(children)-1), measured, axis="inline" if row else "block", profile=self.profile, paths=paths, sizing=self.sizing)
        if row:
            # The same for a flow in a row: its block is the line stack at the inline size the row allocated it.
            measured = [self._wrapped_block(child, f"{path}/children/{i}", m, size)
                        for (i, child), m, size in zip(children, measured, sizes)]
        used = sum(sizes, ZERO) + gap * max(0, len(children)-1)
        if used > main:
            self._warn(node, path, required_inline=used if row else cross,
                       required_block=cross if row else used,
                       available_inline=main if row else cross,
                       available_block=cross if row else main)
        cursor_delta, actual_gap = _distributed_start(node["justifyContent"], main-used, len(children), gap)
        cursor = (inline if row else block) + cursor_delta
        baseline = None
        if row and node["alignItems"] in {"first-baseline", "last-baseline"}:
            values = [m.first_baseline if node["alignItems"] == "first-baseline" else m.last_baseline for m in measured]
            if any(value is None for value in values): raise LayoutError("E_LAYOUT_BASELINE_UNAVAILABLE", path, node["id"])
            baseline = max(value for value in values if value is not None)
        for (index, child), child_measure, main_size in zip(children, measured, sizes):
            child_path = f"{path}/children/{index}"
            cross_spec = child["blockSize" if row else "inlineSize"]
            cross_path = child_path + ("/blockSize" if row else "/inlineSize")
            align = child.get("place", {}).get("block" if row else "inline", node["alignItems"])
            if isinstance(cross_spec, dict) and "aspectRatio" in cross_spec:
                ratio = _d(cross_spec["aspectRatio"]); cross_used = main_size / ratio if row else main_size * ratio
            else:
                minimum, target, weight = _spec_base(cross_spec, axis="block" if row else "inline", measurement=child_measure, profile=self.profile, path=cross_path, sizing=self.sizing)
                capped_cross = not row and self.sizing and child_path in self.sizing.by_path
                cross_used = _cross_size((minimum, target, weight), cross, stretch=align == "stretch" or bool(capped_cross))
                if (not row and not weight and cross_spec == "content" and child.get("kind") == "slot"
                        and child.get("source") in _SHRINKING_SOURCES
                        and child.get("overflow") == "ellipsize-with-source"):
                    cross_used = min(cross_used, cross)
            safety = child.get("place", {}).get("safety", "strict")
            cross_start, cross_used = _cross_position(align, block if row else inline, cross, cross_used, safety)
            if cross_used > cross:
                self._warn(child, child_path, required_inline=main_size if row else cross_used,
                           required_block=cross_used if row else main_size,
                           available_inline=main_size if row else cross,
                           available_block=cross if row else main_size)
            if baseline is not None:
                own = child_measure.first_baseline if node["alignItems"] == "first-baseline" else child_measure.last_baseline
                cross_start = block + baseline - own  # type: ignore[operator]
            child_rect = Rect(cursor, cross_start, main_size, cross_used) if row else Rect(cross_start, cursor, cross_used, main_size)
            self.arrange(child, child_path, child_rect); cursor += main_size + actual_gap

    def _grid(self, node: Mapping[str, Any], path: str, rect: Rect) -> None:
        inline, block, inline_size, block_size = self._content(node, path, rect); gap = _gap(self.profile, node, path)
        cols, rows = node["columnTracks"], node["rowTracks"]
        col_measures: list[Measurement | None] = [None] * len(cols); row_measures: list[Measurement | None] = [None] * len(rows)
        child_measures: dict[int, Measurement] = {}
        required_rows: dict[int, Decimal] = {}
        for i, child in _active_children(node, self.measurements):
            measure = self._measure(child, f"{path}/children/{i}"); child_measures[i] = measure; cell=child["cell"]
            if cell.get("columnSpan",1)==1: col_measures[cell["column"]-1]=measure
        col_sizes=_allocate(cols,inline_size-gap*(len(cols)-1),col_measures,axis="inline",profile=self.profile,paths=[f"{path}/columnTracks/{i}" for i in range(len(cols))])
        for i, child in _active_children(node, self.measurements):
            cell = child["cell"]
            if cell.get("rowSpan", 1) != 1:
                continue
            measure = child_measures[i]
            child_path = f"{path}/children/{i}"
            if self.content_sized or child["kind"] != "slot" or (self.sizing and child_path in self.sizing.by_path):
                column, span = cell["column"] - 1, cell.get("columnSpan", 1)
                child_inline = sum(col_sizes[column:column + span], ZERO) + gap * (span - 1)
                child_inline = _bounded_child_inline(child, child_path, child_inline, measure, self.profile, self.sizing,
                                                      preserve_cell_extent=True)
                natural_block = _natural_child_block(child, child_path, child_inline,
                                                     self.measurements, self.profile, self.sizing)
                measure = _block_measurement(measure, natural_block)
                if self.sizing and child_path in self.sizing.by_path:
                    row = cell["row"] - 1
                    required_rows[row] = max(required_rows.get(row, ZERO), natural_block)
            row_measures[cell["row"] - 1] = measure
        _retain_required_row_blocks(row_measures, required_rows)
        row_sizes=_allocate(rows,block_size-gap*(len(rows)-1),row_measures,axis="block",profile=self.profile,paths=[f"{path}/rowTracks/{i}" for i in range(len(rows))])
        required_inline = sum(col_sizes, ZERO) + gap * max(0, len(cols)-1)
        required_block = sum(row_sizes, ZERO) + gap * max(0, len(rows)-1)
        if required_inline > inline_size or required_block > block_size:
            self._warn(node, path, required_inline=required_inline, required_block=required_block,
                       available_inline=inline_size, available_block=block_size)
        col_starts=[]; cursor=inline
        for size in col_sizes: col_starts.append(cursor); cursor+=size+gap
        row_starts=[]; cursor=block
        for size in row_sizes: row_starts.append(cursor); cursor+=size+gap
        for i,child in _active_children(node, self.measurements):
            cell=child["cell"]; c=cell["column"]-1; r=cell["row"]-1; cs=cell.get("columnSpan",1); rs=cell.get("rowSpan",1)
            self._record_inline_budget(child, f"{path}/children/{i}",
                                       sum(col_sizes[c:c+cs], ZERO) + gap * (cs - 1))
            child_path = f"{path}/children/{i}"
            child_inline = sum(col_sizes[c:c+cs], ZERO) + gap * (cs - 1)
            child_block = sum(row_sizes[r:r+rs], ZERO) + gap * (rs - 1)
            child_start = col_starts[c]
            if self.sizing and child_path in self.sizing.by_path:
                used_inline = _bounded_child_inline(child, child_path, child_inline, child_measures[i],
                                                     self.profile, self.sizing, child_block, preserve_cell_extent=True)
                align = child.get("place", {}).get("inline", node["alignItems"])
                child_start, child_inline = _cross_position(align, child_start, child_inline, used_inline)
            self.arrange(child, child_path, Rect(child_start, row_starts[r], child_inline, child_block))

    def _flow(self, node: Mapping[str, Any], path: str, rect: Rect) -> None:
        inline, block, inline_size, block_size = self._content(node,path,rect); gap=_gap(self.profile,node,path)
        for index, child in _active_children(node, self.measurements):
            self._record_inline_budget(child, f"{path}/children/{index}", inline_size)
        lines = _flow_lines(node, path, self.measurements, self.profile, inline_size,
                            lambda child, child_path, width:
                            _natural_child_block(child, child_path, width, self.measurements, self.profile, self.sizing)
                            if self.content_sized or child["kind"] != "slot" else
                            self._measure(child, child_path).preferred_block,
                            self.sizing)
        cursor_b=block
        for line in lines:
            line_height=max((item[4] for item in line),default=ZERO)
            if cursor_b+line_height>block+block_size:
                self._warn(node, path, required_inline=inline_size,
                           required_block=cursor_b + line_height - block,
                           available_inline=inline_size, available_block=block_size)
            total=sum((item[3] for item in line),ZERO)+gap*max(0,len(line)-1)
            delta,actual_gap=_distributed_start(node["justifyContent"],inline_size-total,len(line),gap); cursor_i=inline+delta
            baseline=None
            if node["alignItems"] in {"first-baseline","last-baseline"}:
                values=[item[2].first_baseline if node["alignItems"]=="first-baseline" else item[2].last_baseline for item in line]
                if any(value is None for value in values): raise LayoutError("E_LAYOUT_BASELINE_UNAVAILABLE",path,node["id"])
                baseline=max(value for value in values if value is not None)
            for i,child,measure,width,height in line:
                child_path=f"{path}/children/{i}"; align=child.get("place",{}).get("block",node["alignItems"]); safety=child.get("place",{}).get("safety","strict")
                if align == "stretch":
                    base = _spec_base(child["blockSize"], axis="block", measurement=measure,
                                      profile=self.profile, path=child_path + "/blockSize")
                    if base[2] > ZERO:
                        height = _cross_size(base, line_height, stretch=True)
                child_block,height=_cross_position(align,cursor_b,line_height,height,safety)
                if height > line_height:
                    self._warn(child, child_path, required_inline=width,
                               required_block=height, available_inline=width,
                               available_block=line_height)
                if baseline is not None:
                    own=measure.first_baseline if node["alignItems"]=="first-baseline" else measure.last_baseline; child_block=cursor_b+baseline-own  # type: ignore[operator]
                self.arrange(child,child_path,Rect(cursor_i,child_block,width,height)); cursor_i+=width+actual_gap
            cursor_b+=line_height+gap

    def _overlay(self, node: Mapping[str, Any], path: str, rect: Rect) -> None:
        inline, block, inline_size, block_size = self._content(node, path, rect)
        content = Rect(inline, block, inline_size, block_size)
        children = _active_children(node, self.measurements)
        for index, child in children:
            self._record_inline_budget(child, f"{path}/children/{index}", inline_size)
        indexed = {str(child["id"]): (index, child) for index, child in children}
        bounds: dict[str, Rect] = {}

        def child_size(child: Mapping[str, Any], child_path: str) -> tuple[Decimal, Decimal]:
            measure = self._measure(child, child_path)
            inline_base = _spec_base(child["inlineSize"], axis="inline", measurement=measure, profile=self.profile, path=child_path + "/inlineSize", sizing=self.sizing)
            place = child.get("place", {})
            capped = self.sizing and child_path in self.sizing.by_path
            used_inline = _cross_size(inline_base, inline_size, stretch=place.get("inline") == "stretch" or bool(capped))
            measure = self._wrapped_block(child, child_path, measure, used_inline)
            block_base = _spec_base(child["blockSize"], axis="block", measurement=measure,
                                    profile=self.profile, path=child_path + "/blockSize")
            used_block = _cross_size(block_base, block_size, stretch=place.get("block") == "stretch")
            if isinstance(child["inlineSize"], dict) and "aspectRatio" in child["inlineSize"]:
                used_inline = used_block * _d(child["inlineSize"]["aspectRatio"])
            if isinstance(child["blockSize"], dict) and "aspectRatio" in child["blockSize"]:
                used_block = used_inline / _d(child["blockSize"]["aspectRatio"])
            return used_inline, used_block

        for child_id, (index, child) in indexed.items():
            if "anchor" in child:
                continue
            child_path = f"{path}/children/{index}"
            used_inline, used_block = child_size(child, child_path)
            place = child.get("place", {})
            start_inline, used_inline = _cross_position(place.get("inline", "start"), inline, inline_size, used_inline, place.get("safety", "strict"))
            start_block, used_block = _cross_position(place.get("block", "start"), block, block_size, used_block, place.get("safety", "strict"))
            child_rect = Rect(start_inline, start_block, used_inline, used_block)
            if used_inline > inline_size or used_block > block_size:
                self._warn(child, child_path, required_inline=used_inline,
                           required_block=used_block, available_inline=inline_size,
                           available_block=block_size)
            bounds[child_id] = child_rect
            self.arrange(child, child_path, child_rect)

        guides: dict[str, tuple[str, Decimal]] = {}
        for guide_id, guide in node.get("guides", {}).items():
            axis = guide["axis"]
            origin, extent = (inline, inline_size) if axis == "inline" else (block, block_size)
            at = guide["at"]
            if at == "start": fraction = ZERO
            elif at == "center": fraction = Decimal("0.5")
            elif at == "end": fraction = Decimal(1)
            else:
                numerator, denominator = at.split("/")
                fraction = Decimal(numerator) / Decimal(denominator)
            guides[guide_id] = (axis, origin + extent * fraction)

        barriers = node.get("barriers", {})

        def point(rectangle: Rect, axis: str, name: str, child_id: str | None = None) -> Decimal:
            start = rectangle.inline if axis == "inline" else rectangle.block
            size = rectangle.inline_size if axis == "inline" else rectangle.block_size
            if name == "start": return start
            if name == "center": return start + size / 2
            if name == "end": return start + size
            if axis != "block" or child_id is None:
                raise LayoutError("E_LAYOUT_BASELINE_UNAVAILABLE", path, child_id)
            measure = self._measure(indexed[child_id][1], f"{path}/children/{indexed[child_id][0]}")
            baseline = measure.first_baseline if name == "first-baseline" else measure.last_baseline
            if baseline is None:
                raise LayoutError("E_LAYOUT_BASELINE_UNAVAILABLE", path, child_id)
            return start + baseline

        def barrier_coordinate(barrier_id: str) -> Decimal | None:
            barrier = barriers[barrier_id]
            if any(member not in bounds for member in barrier["members"]):
                return None
            values = [point(bounds[member], barrier["axis"], barrier["edge"], member) for member in barrier["members"]]
            return min(values) if barrier["edge"] == "start" else max(values)

        def target_coordinate(target: Mapping[str, Any], axis: str) -> Decimal | None:
            reference, target_point = target["ref"], target["point"]
            if reference == "parent":
                return point(content, axis, target_point)
            if reference.startswith("node:"):
                target_id = reference[5:]
                return None if target_id not in bounds else point(bounds[target_id], axis, target_point, target_id)
            if reference.startswith("guide:"):
                return guides[reference[6:]][1]
            return barrier_coordinate(reference[8:])

        pending = {child_id for child_id, (_, child) in indexed.items() if "anchor" in child}
        while pending:
            progressed = False
            for child_id in sorted(pending):
                index, child = indexed[child_id]
                child_path = f"{path}/children/{index}"
                anchor = child["anchor"]
                target_inline = target_coordinate(anchor["target"]["inline"], "inline")
                target_block = target_coordinate(anchor["target"]["block"], "block")
                if target_inline is None or target_block is None:
                    continue
                used_inline, used_block = child_size(child, child_path)
                own = Rect(ZERO, ZERO, used_inline, used_block)
                coordinates = {"inline": target_inline, "block": target_block}
                for axis in ("inline", "block"):
                    target = anchor["target"][axis]
                    gap = _distance(self.profile, f"{child_path}/anchor/gap/{axis}") if axis in anchor.get("gap", {}) else ZERO
                    if gap:
                        target_name = target["point"]
                        if target_name == "start": coordinates[axis] -= gap
                        elif target_name == "end": coordinates[axis] += gap
                        elif anchor["self"][axis] == "end": coordinates[axis] -= gap
                        else: coordinates[axis] += gap
                    coordinates[axis] -= point(own, axis, anchor["self"][axis], child_id)
                child_rect = Rect(coordinates["inline"], coordinates["block"], used_inline, used_block)
                safety = child.get("place", {}).get("safety", "strict")
                outside = (child_rect.inline < inline or child_rect.block < block or child_rect.inline + used_inline > inline + inline_size or child_rect.block + used_block > block + block_size)
                if outside:
                    self._warn(child, child_path, required_inline=used_inline,
                               required_block=used_block, available_inline=inline_size,
                               available_block=block_size)
                if outside and safety == "safe":
                    child_rect = Rect(
                        inline if used_inline > inline_size else min(max(child_rect.inline, inline), inline + inline_size - used_inline),
                        block if used_block > block_size else min(max(child_rect.block, block), block + block_size - used_block),
                        used_inline, used_block,
                    )
                references = tuple(anchor["target"][axis]["ref"] for axis in ("inline", "block"))
                bounds[child_id] = child_rect
                self.arrange(child, child_path, child_rect, references)
                pending.remove(child_id)
                progressed = True
                break
            if not progressed:
                raise LayoutError("E_LAYOUT_CONSTRAINT_CYCLE", path, sorted(pending)[0])


def resolve_source_inline_budgets(profile: ResolvedLayoutProfile, *,
                                 viewport_inline: int | float | Decimal,
                                 viewport_block: int | float | Decimal,
                                 measurements: Mapping[str, Measurement],
                                 content_sized: bool = False,
                                 heading_slots: frozenset[str] = frozenset(),
                                 wrapping_table_slots: frozenset[str] = frozenset(),
                                 owner_inline_minima: Mapping[str, Decimal] = MappingProxyType({})) -> Mapping[str, SourceInlineBudget]:
    """Probe parent/cell budgets with all selected source demands neutralized.

    The ordinary arranger remains the only implementation of padding, active
    children, flexible tracks, spans and Flow. The source owner then closes
    mandatory and bounded measurements; its final arrangement must reproduce
    these budgets via ``validate_source_inline_budgets``. This probe alone does
    not prove source feasibility or enforce the cap on completed placements.
    """
    capped: list[str] = []
    heading_ancestors: dict[str, tuple[str, ...]] = {}
    nodes: dict[str, tuple[Mapping[str, Any], str]] = {}

    def visit(node: Mapping[str, Any], ancestors: tuple[str, ...] = (), path: str = "/root") -> None:
        node_id = str(node["id"])
        nodes[node_id] = node, path
        if node_id in heading_slots:
            heading_ancestors[node_id] = ancestors
        if "maxInlineShare" in node or node_id in wrapping_table_slots:
            capped.append(str(node["id"]))
        for index, child in _active_children(node, measurements) if "children" in node else ():
            visit(child, (*ancestors, node_id), f"{path}/children/{index}")

    root = profile.profile["root"]
    visit(root)
    if not capped and not heading_ancestors:
        return MappingProxyType({})
    viewport = Rect(ZERO, ZERO, _d(viewport_inline), _d(viewport_block))
    if viewport.inline_size <= ZERO or viewport.block_size <= ZERO:
        raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY", "/viewport")
    neutral = dict(measurements)
    for slot_id in capped:
        try:
            neutral[slot_id] = replace(neutral[slot_id], min_inline=ZERO,
                                       preferred_inline=ZERO, max_inline=ZERO)
        except KeyError as error:
            raise LayoutError("E_LAYOUT_MEASUREMENT_REQUIRED", "/root", slot_id) from error
    # A fitting heading is an ordinary intrinsic demand, not a width-dependent
    # source. Erasing it would collapse a content-sized host containing only
    # that heading. Use the existing arranger's inline evidence to identify
    # actual shortage. Compare native Decimal extents, not rounded reporting
    # warnings, and do not mistake an unrelated sibling's overflow for text
    # shortage at the heading.
    probe_sizing = LayoutSizingContext({}, owner_inline_minima=owner_inline_minima)
    natural = _Arranger(profile, neutral, content_sized=content_sized,
                        sizing=probe_sizing if owner_inline_minima else None)
    natural.arrange(root, "/root", viewport)
    bounds = {decision.node_id: decision.bounds for decision in natural.decisions}

    def heading_needs_closure(slot_id: str, ancestors: tuple[str, ...]) -> bool:
        placed = bounds[slot_id].inline_size
        available = placed
        for ancestor in ancestors:
            node, path = nodes[ancestor]
            i0, i1, _, _ = _padding(profile, node, path)
            inner = max(ZERO, bounds[ancestor].inline_size - i0 - i1)
            if node["kind"] == "row":
                inner -= _gap(profile, node, path) * max(0, len(_active_children(node, measurements)) - 1)
            available = min(available, inner)
        return placed > available or measurements[slot_id].preferred_inline > available

    selected_headings = frozenset(slot_id for slot_id, ancestors in heading_ancestors.items()
                                  if heading_needs_closure(slot_id, ancestors))
    for slot_id in selected_headings:
        neutral[slot_id] = replace(neutral[slot_id], min_inline=ZERO,
                                   preferred_inline=ZERO, max_inline=ZERO)
    arranger = _Arranger(profile, neutral, content_sized=content_sized, collect_inline_budgets=True,
                         heading_slots=selected_headings, wrapping_table_slots=wrapping_table_slots)
    if owner_inline_minima:
        arranger.sizing = probe_sizing
    arranger.arrange(root, "/root", viewport)
    return MappingProxyType(dict(arranger.source_inline_budgets))


def solve_layout(profile: ResolvedLayoutProfile, *, viewport_inline: int | float | Decimal, viewport_block: int | float | Decimal, measurements: Mapping[str, Measurement], content_sized: bool = False, sizing: LayoutSizingContext | None = None) -> LayoutManifest:
    """Measure and arrange normal-flow and bounded relative layout nodes."""
    viewport = Rect(ZERO, ZERO, _d(viewport_inline), _d(viewport_block))
    if viewport.inline_size <= ZERO or viewport.block_size <= ZERO:
        raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY", "/viewport")
    root = profile.profile["root"]
    if sizing:
        measurements = sizing.close_sources(measurements)
    _measure_for_sizing(root, "/root", measurements, profile, sizing)
    arranger = _Arranger(profile, measurements, content_sized=content_sized, sizing=sizing)
    arranger.arrange(root, "/root", viewport)
    if sizing:
        validate_source_inline_budgets(sizing.source_budgets, arranger.source_inline_budgets)
    relation_routing = profile.profile.get("relationRouting", {})
    annotation_routing = profile.profile["reviewSurface"]["annotationRouting"]
    return LayoutManifest(
        profile.profile_id, profile.content_hash, str(profile.profile["flowDirection"]),
        str(profile.profile["dependencyNetworkFlowDirection"]), viewport,
        tuple(arranger.decisions),
        relation_max_bends=int(relation_routing.get("maxBends", 4)),
        relation_max_detour_ratio=float(relation_routing.get("maxDetourRatio", 2.0)),
        relation_entry=str(relation_routing.get("entry", "side-when-free")),
        relation_search=str(relation_routing.get("search", "first-fit")),
        relation_unroutable=RelationUnroutableMode(relation_routing.get("unroutable", "relax")),
        relation_search_budget=(int(relation_routing["searchBudget"])
                                if "searchBudget" in relation_routing else None),
        relation_style=RelationRouteStyle(relation_routing.get("style", "orthogonal")),
        annotation_max_bends=int(annotation_routing["maxBends"]),
        annotation_max_detour_ratio=float(annotation_routing["maxDetourRatio"]),
        row_distribution=str(profile.profile["reviewSurface"]["rowDistribution"]),
        background_extents=dict(profile.profile["reviewSurface"]["backgroundExtents"]),
        member_names=dict(profile.profile["reviewSurface"].get("memberNames", {})),
        fit_warnings=tuple(arranger.fit_warnings),
        point_host_mode=(PointHostMode(profile.profile["reviewSurface"]["marks"]["points"]["host"])
                         if profile.profile["reviewSurface"].get("marks", {}).get("points", {}).get("host") is not None
                         else None),
    )


def _unresolved_normal_flow_warnings(profile: ResolvedLayoutProfile,
                                     manifest: LayoutManifest) -> tuple[FitWarning, ...]:
    """Return growable normal-flow overflows; anchored/capped fallback is valid."""
    nodes: dict[str, tuple[Mapping[str, Any], bool, bool]] = {}

    def visit(node: Mapping[str, Any], anchored: bool = False, capped_ancestor: bool = False) -> None:
        nodes[str(node["id"])] = (node, anchored, capped_ancestor)
        node_capped = capped(node)
        for child in node.get("children", ()):
            cell = child.get("cell", {})
            span = cell.get("rowSpan", 1)
            grid_span_fallback = node["kind"] == "grid" and span > 1
            grid_track_fallback = (
                node["kind"] == "grid" and span == 1
                and bounded_track(node["rowTracks"][cell["row"] - 1])
            )
            visit(child, anchored or (node["kind"] == "overlay" and "anchor" in child),
                  capped_ancestor or node_capped or grid_span_fallback or grid_track_fallback)

    def bounded_track(spec: Any) -> bool:
        if isinstance(spec, str):
            return spec in {"min-content", "max-content"}
        if not isinstance(spec, dict):
            return False
        if "fixed" in spec or "fitContent" in spec:
            return True
        if "minmax" in spec:
            return bounded_track(spec["minmax"]["max"])
        return False

    def capped(node: Mapping[str, Any]) -> bool:
        spec = node.get("blockSize")
        if bounded_track(spec):
            return True
        if node["kind"] == "grid":
            tracks = node.get("rowTracks", ())
            return bool(tracks) and all(bounded_track(track) for track in tracks)
        return False

    visit(profile.profile["root"])

    result = []
    for warning in manifest.fit_warnings:
        if warning.required_block <= warning.available_block:
            continue
        entry = nodes.get(warning.placement_id)
        if entry is None:
            continue
        node, anchored, capped_ancestor = entry
        if anchored or capped_ancestor or capped(node):
            continue
        result.append(warning)
    return tuple(result)


@dataclass(frozen=True)
class ShortContentSource:
    """A required content source that remains short in the final profile solve."""

    source_id: str
    required_block: Decimal
    allocated_block: Decimal

    def __post_init__(self) -> None:
        if (not self.source_id or not self.required_block.is_finite()
                or not self.allocated_block.is_finite()
                or self.allocated_block >= self.required_block):
            raise ValueError(
                f"E_LAYOUT_CONTENT_SHORTFALL_INVALID: source_id={repr(self.source_id[:160]) if isinstance(self.source_id, str) else type(self.source_id).__name__}, "
                f"required_block={self.required_block!r}, allocated_block={self.allocated_block!r}; "
                "expected a non-empty source with finite required and allocated blocks, allocated below required"
            )


@dataclass(frozen=True)
class ContentBlockResolution:
    """Chosen viewport extent plus exact required-source profile shortfalls."""

    extent: int
    short_sources: tuple[ShortContentSource, ...] = ()

    def __post_init__(self) -> None:
        if self.extent <= 0 or tuple(sorted(self.short_sources, key=lambda item: item.source_id)) != self.short_sources:
            source_ids = tuple(item.source_id[:160] for item in self.short_sources[:8])
            raise ValueError(
                f"E_LAYOUT_CONTENT_RESOLUTION_INVALID: extent={self.extent!r}, source_ids={source_ids!r}, source_count={len(self.short_sources)}; "
                "expected a positive extent and short sources ordered by source_id"
            )
        if len({item.source_id for item in self.short_sources}) != len(self.short_sources):
            counts = Counter(item.source_id for item in self.short_sources)
            duplicates = tuple(source_id[:160] for source_id, count in counts.items() if count > 1)[:8]
            raise ValueError(
                f"E_LAYOUT_CONTENT_RESOLUTION_INVALID: extent={self.extent!r}, duplicate_source_ids={duplicates!r}, source_count={len(self.short_sources)}; "
                "expected each short source_id to occur once"
            )


def _block_extent_feeds_inline(profile: ResolvedLayoutProfile) -> bool:
    """True when a node's inline extent is derived from its block extent (an inline `aspectRatio`).

    Without that coupling every allocation is a non-decreasing function of the block extent, so "the required slot
    fits" is monotone and the first fitting extent follows from the deficit of one probe. With it, a taller
    extent can widen an aspect-ratio flow so that its items wrap into fewer lines and a slot shrinks: the fit
    predicate is not monotone and only the first fitting integral extent is the least one (#1214, Spec 33 13.1).
    """
    def visit(node: Mapping[str, Any]) -> bool:
        spec = node.get("inlineSize")
        if isinstance(spec, dict) and "aspectRatio" in spec:
            return True
        return any(visit(child) for child in node.get("children", ()))
    return visit(profile.profile["root"])


def _first_fitting_extent(fits: Callable[[int], bool], minimum_block: int, known_fit: int) -> int:
    """The least integral extent from the requested minimum up to a verified fitting extent that itself fits.

    The scan is bounded by `known_fit`, an extent already verified against the complete native manifest, so
    it needs no retry cap; each candidate is judged by its own complete native arrangement.
    """
    for extent in range(max(1, minimum_block), known_fit):
        if fits(extent):
            return extent
    return known_fit


def resolve_content_block_extent(profile: ResolvedLayoutProfile, *, viewport_inline: int,
                                 minimum_block: int, measurements: Mapping[str, Measurement],
                                 required_blocks: Mapping[str, Decimal] | Callable[[LayoutManifest], Mapping[str, Decimal]],
                                 content_sized: bool = False,
                                 sizing: LayoutSizingContext | Callable[[Decimal], LayoutSizingContext] | None = None) -> ContentBlockResolution:
    """Resolve measured content hosts against one coherent finite profile.

    The probe is a normal finite arrangement.  Each declared content
    requirement contributes only its deficit from its allocated slot, so the
    final value preserves profile chrome and the fixed inline extent. Both
    fixed and Draft-auto requests use this same Layout decision; the requested
    block extent is a minimum, not a clipping boundary. Draft auto supplies
    its positive one-unit sizing floor here; finite requests supply their
    requested extent. The synthetic Context seed is not inferred here.
    """
    if minimum_block <= 0:
        raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY", "/viewport")

    def solve_at(block: int | Decimal) -> LayoutManifest:
        # A block-to-inline coupling may legally change an independent parent
        # budget between trials. Build a fresh source closure for that trial;
        # never reuse the initial viewport's ceiling or relax final validation.
        context = sizing(_d(block)) if callable(sizing) else sizing
        return solve_layout(profile, viewport_inline=viewport_inline, viewport_block=block,
                             measurements=measurements, content_sized=content_sized, sizing=context)

    def allocations(manifest: LayoutManifest) -> dict[str, Decimal]:
        return {item.source: item.bounds.block_size for item in manifest.decisions if item.source}

    def requirements(manifest: LayoutManifest) -> Mapping[str, Decimal]:
        required = required_blocks(manifest) if callable(required_blocks) else required_blocks
        missing = sorted(set(required) - set(allocations(manifest)))
        if missing:
            raise LayoutError("E_LAYOUT_DRAFT_AUTO_UNSUPPORTED", "/layoutManifest/sources/" + missing[0])
        return required

    requested = solve_at(minimum_block)
    requested_allocated = allocations(requested)
    requested_required = requirements(requested)
    if (all(requested_allocated[source] >= required for source, required in requested_required.items())
            and (not content_sized or not _unresolved_normal_flow_warnings(profile, requested))):
        return ContentBlockResolution(minimum_block)
    if not content_sized:
        # Finite Draft and immutable requests preserve #468's requested
        # minimum and source-deficit reallocation behavior exactly.
        probe_block = max(_d(minimum_block), max(requested_required.values(), default=ZERO) + _d(minimum_block))
        manifest = solve_at(probe_block)
        allocated = allocations(manifest)
        probe_required = requirements(manifest)
        extent = max((_d(minimum_block), *(probe_block - allocated[source] + required
                                           for source, required in probe_required.items())))
        candidate = int(extent.to_integral_value(rounding=ROUND_CEILING))
        final = solve_at(candidate)
        final_allocated = allocations(final)
        final_required = requirements(final)
        short_sources = tuple(
            ShortContentSource(source, final_required[source], final_allocated[source])
            for source in sorted(final_required)
            if final_allocated[source] < final_required[source]
        )
        if _block_extent_feeds_inline(profile):
            # A coupled profile: an earlier extent than the deficit probe's may already fit (#1214).
            def finite_fits(extent: int) -> bool:
                trial = solve_at(extent)
                trial_allocated = allocations(trial)
                return all(trial_allocated[source] >= required for source, required in requirements(trial).items())
            earliest = _first_fitting_extent(finite_fits, int(minimum_block), candidate)
            if earliest != candidate or not short_sources:
                return ContentBlockResolution(earliest)
        if short_sources:
            short_sources = tuple(
                ShortContentSource(source, requested_required[source], requested_allocated[source])
                for source in sorted(requested_required)
                if requested_allocated[source] < requested_required[source]
            )
            return ContentBlockResolution(minimum_block, short_sources)
        return ContentBlockResolution(candidate)

    # The intrinsic whole-profile measurement supplies the auto floor. Add
    # declared content needs on top, then verify the final complete manifest.
    probe_block = max(_d(minimum_block), max(requested_required.values(), default=ZERO) + _d(minimum_block))
    manifest = solve_at(probe_block)
    allocated = allocations(manifest)
    probe_required = requirements(manifest)
    probe_satisfied = (all(allocated[source] >= required for source, required in probe_required.items())
                       and not _unresolved_normal_flow_warnings(profile, manifest))
    coupled = _block_extent_feeds_inline(profile)

    def requested_fallback() -> ContentBlockResolution:
        short_sources = tuple(
            ShortContentSource(source, requested_required[source], requested_allocated[source])
            for source in sorted(requested_required)
            if requested_allocated[source] < requested_required[source]
        )
        return ContentBlockResolution(minimum_block, short_sources)

    if not probe_satisfied and not coupled:
        return requested_fallback()
    extent = max((_d(minimum_block), *(probe_block - allocated[source] + required
                                    for source, required in probe_required.items())))
    candidate = int(extent.to_integral_value(rounding=ROUND_CEILING))

    def satisfies(extent: int) -> bool:
        manifest = solve_at(extent)
        source_allocated = allocations(manifest)
        candidate_required = requirements(manifest)
        return (all(source_allocated[source] >= required for source, required in candidate_required.items())
                and not _unresolved_normal_flow_warnings(profile, manifest))

    if coupled:
        # A failed probe can precede a fitting wrap branch. Verify its native
        # deficit candidate before falling back; never scan to an unverified
        # bound or interpret a failed candidate as a global infeasibility proof.
        if satisfies(candidate):
            known_fit = candidate
        elif probe_satisfied and satisfies(int(probe_block)):
            known_fit = int(probe_block)
        else:
            return requested_fallback()
        return ContentBlockResolution(_first_fitting_extent(satisfies, int(minimum_block), known_fit))

    # Retain the published uncoupled Draft-auto search, evaluating every
    # candidate's own demand.
    low, high = minimum_block - 1, max(candidate, int(probe_block))
    if callable(required_blocks) and not satisfies(high):
        return requested_fallback()
    while high - low > 1:
        middle = (low + high) // 2
        if satisfies(middle):
            high = middle
        else:
            low = middle
    return ContentBlockResolution(high)
