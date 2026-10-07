"""Deterministic normal-flow engine for intent-oriented Layout Profile v0.2."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import ROUND_CEILING, Decimal, getcontext, localcontext
from fractions import Fraction
from typing import Any, Callable, Mapping

from chrona.presentation.layout.model import (
    LayoutDecision, LayoutError, LayoutManifest, Measurement, Rect, RegionFrame, ResolvedLayoutProfile, SlotHeading,
)
from chrona.presentation.layout.surface_quality import FitWarning


getcontext().prec = 28
ZERO = Decimal(0)


def _d(value: Any) -> Decimal:
    return Decimal(str(value))


def _distance(profile: ResolvedLayoutProfile, path: str) -> Decimal:
    try:
        return profile.distances[path]
    except KeyError as error:
        raise LayoutError("E_LAYOUT_TOKEN_UNKNOWN", path) from error


def _slot_heading(node: Mapping[str, Any]) -> SlotHeading | None:
    """The slot's declared caption (#1064); its shape was validated with the profile."""
    declared = node.get("heading")
    if declared is None:
        return None
    return SlotHeading(str(declared["text"]), str(declared.get("align", "start")), str(declared.get("block", "top")))


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


def _spec_base(spec: Any, *, axis: str, measurement: Measurement | None, profile: ResolvedLayoutProfile, path: str) -> tuple[Decimal, Decimal | None, Decimal]:
    """Return minimum, preferred/fixed target, and flex weight."""
    if spec == "fill":
        return ZERO, None, Decimal(1)
    if isinstance(spec, dict) and "fr" in spec:
        return ZERO, None, _d(spec["fr"])
    if isinstance(spec, dict) and "fixed" in spec:
        value = spec["fixed"]
        fixed = _d(value) if isinstance(value, (int, float)) else _distance(profile, path + "/fixed")
        return fixed, fixed, ZERO
    if isinstance(spec, dict) and "aspectRatio" in spec:
        return ZERO, None, ZERO
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


def _resolve_flexible_tracks(bases: list[tuple[Decimal, Decimal | None, Decimal]], available: Decimal) -> list[Decimal]:
    """Resolve one axis's tracks from their (minimum, maximum, weight) bases:
    fixed/intrinsic tracks (`weight == 0`) first, then flexible (`fr`/`fill`)
    tracks by CSS Grid's "find the size of an fr" algorithm (#487, ADR-0032).

    A flexible track's `minmax` minimum is a floor its fr share must clear,
    never an amount added underneath it. Each round computes one `fr` unit from
    the space still available to the remaining flexible tracks; any track whose
    minimum exceeds its own share at that `fr`, or whose maximum is smaller than
    that share, is frozen at that bound and removed from the set so the rest
    redistribute what is left, at the next round's recomputed `fr`. This keeps
    the total at `available` — never oversubscribing it — unless every flexible
    track's minimum together already exceeds `available`, in which case each
    keeps its minimum and the caller's existing typed-overflow completion
    applies, as before."""
    sizes: list[Decimal | None] = [None] * len(bases)
    flexible = [index for index, (_, _, weight) in enumerate(bases) if weight > ZERO]
    for index, (minimum, target, weight) in enumerate(bases):
        if weight == ZERO:
            sizes[index] = target if target is not None else minimum
    non_flex_total = sum((sizes[index] for index in range(len(bases)) if sizes[index] is not None), ZERO)
    # A valid profile with too little space still has a finite natural
    # placement.  The caller records its typed overflow and the composition
    # layer expands the completed canvas around the resulting bounds.
    leftover = available - non_flex_total
    while flexible:
        total_weight = sum((bases[index][2] for index in flexible), ZERO)
        fr = leftover / total_weight if leftover > ZERO else ZERO
        violators = [index for index in flexible if bases[index][0] > fr * bases[index][2]]
        if violators:
            for index in violators:
                sizes[index] = bases[index][0]
                leftover -= bases[index][0]
            flexible = [index for index in flexible if index not in violators]
            continue
        clamped = [index for index in flexible
                   if bases[index][1] is not None and bases[index][1] < fr * bases[index][2]]
        if clamped:
            for index in clamped:
                sizes[index] = bases[index][1]
                leftover -= bases[index][1]
            flexible = [index for index in flexible if index not in clamped]
            continue
        for index in flexible:
            sizes[index] = fr * bases[index][2]
        break
    return sizes  # type: ignore[return-value]


def _allocate(specs: list[Any], available: Decimal, measurements: list[Measurement | None], *, axis: str, profile: ResolvedLayoutProfile, paths: list[str]) -> list[Decimal]:
    bases = [_spec_base(spec, axis=axis, measurement=measure, profile=profile, path=path) for spec, measure, path in zip(specs, measurements, paths)]
    return _resolve_flexible_tracks(bases, available)


def _measure_node(node: Mapping[str, Any], path: str, measurements: Mapping[str, Measurement], profile: ResolvedLayoutProfile) -> Measurement:
    if node["kind"] == "slot":
        return _slot_measurement(node, measurements, path)
    children = [_measure_node(child, f"{path}/children/{index}", measurements, profile)
                for index, child in _active_children(node, measurements)]
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
    return Measurement(minimum_inline, preferred_inline, maximum_inline, minimum_block, preferred_block, maximum_block)


def _flow_lines(node: Mapping[str, Any], path: str, measurements: Mapping[str, Measurement],
                profile: ResolvedLayoutProfile, inline_size: Decimal,
                height_for: Callable[[Mapping[str, Any], str, Decimal], Decimal]
                ) -> list[list[tuple[int, Mapping[str, Any], Measurement, Decimal, Decimal]]]:
    """Resolve flow wrapping once for both natural measurement and arrangement."""
    gap = _gap(profile, node, path)
    minimum = _distance(profile, path + "/itemMinInlineSize")
    lines: list[list[tuple[int, Mapping[str, Any], Measurement, Decimal, Decimal]]] = [[]]
    used = ZERO
    for index, child in _active_children(node, measurements):
        child_path = f"{path}/children/{index}"
        measured = _measure_node(child, child_path, measurements, profile)
        width = max(minimum, measured.preferred_inline)
        height = height_for(child, child_path, min(inline_size, width))
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
                                      node_path: str = "/root") -> Decimal:
    """Measure natural normal-flow block extent with arrangement's track rules.

    This is a Layout-owned sizing input. It follows the resolved inline extent
    for wrapped flows, uses the same grid track bases as arrangement, and omits
    anchored overlay decoration from the normal-flow envelope.
    """
    def block(node: Mapping[str, Any], path: str, available_inline: Decimal) -> Decimal:
        if node["kind"] == "slot":
            return _slot_measurement(node, measurements, path).preferred_block
        i0, i1, b0, b1 = _padding(profile, node, path)
        inner_inline = max(ZERO, available_inline - i0 - i1)
        gap = _gap(profile, node, path)
        children = _active_children(node, measurements)
        kind = node["kind"]
        if kind == "overlay":
            natural = max((block(child, f"{path}/children/{index}", inner_inline)
                           for index, child in children if "anchor" not in child), default=ZERO)
            return natural + b0 + b1
        if kind == "flow":
            flow = _flow_lines(node, path, measurements, profile, inner_inline,
                               lambda child, child_path, width: block(child, child_path, width))
            return sum((max((item[4] for item in line), default=ZERO) for line in flow), ZERO) + \
                gap * max(0, len(flow) - 1) + b0 + b1
        if kind == "grid":
            columns, rows = node["columnTracks"], node["rowTracks"]
            col_measures: list[Measurement | None] = [None] * len(columns)
            row_measures: list[Measurement | None] = [None] * len(rows)
            child_measures: dict[int, Measurement] = {}
            for index, child in children:
                measured = _measure_node(child, f"{path}/children/{index}", measurements, profile)
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
                                                         child_inline, measurements, profile)
                    row_measures[cell["row"] - 1] = _block_measurement(child_measures[index], natural_block)
            row_bases = [_spec_base(spec, axis="block", measurement=measure, profile=profile,
                                    path=f"{path}/rowTracks/{i}")
                         for i, (spec, measure) in enumerate(zip(rows, row_measures))]
            row_sizes = [target if target is not None else minimum for minimum, target, _ in row_bases]
            return sum(row_sizes, ZERO) + gap * max(0, len(rows) - 1) + b0 + b1
        if kind == "row":
            child_measures = [_measure_node(child, f"{path}/children/{index}", measurements, profile)
                              for index, child in children]
            specs = [child["inlineSize"] for _, child in children]
            sizes = _allocate(specs, inner_inline - gap * max(0, len(children) - 1), child_measures,
                              axis="inline", profile=profile,
                              paths=[f"{path}/children/{index}/inlineSize" for index, _ in children])
            return max((child_block(child, f"{path}/children/{index}", size)
                        for (index, child), size in zip(children, sizes)), default=ZERO) + b0 + b1
        total = b0 + b1 + gap * max(0, len(children) - 1)
        for index, child in children:
            child_path = f"{path}/children/{index}"
            total += child_block(child, child_path, inner_inline)
        return total

    def child_block(node: Mapping[str, Any], path: str, available_inline: Decimal) -> Decimal:
        measured = _measure_node(node, path, measurements, profile)
        required = block(node, path, available_inline)
        if node["kind"] in {"overlay", "grid"}:
            measured = _block_measurement(measured, required)
        minimum, target, _ = _spec_base(node["blockSize"], axis="block", measurement=measured,
                                        profile=profile, path=path + "/blockSize")
        if node["blockSize"] != "content" and target is not None:
            return target
        return max(minimum, required)

    root = profile.profile["root"] if node is None else node
    natural = block(root, node_path, _d(viewport_inline))
    measure = _measure_node(root, node_path, measurements, profile)
    if root["kind"] in {"overlay", "grid"}:
        measure = _block_measurement(measure, natural)
    minimum, target, _ = _spec_base(root["blockSize"], axis="block", measurement=measure,
                                    profile=profile, path=node_path + "/blockSize")
    if root["blockSize"] != "content" and target is not None:
        return target
    return max(minimum, natural)


def _natural_child_block(node: Mapping[str, Any], path: str, available_inline: Decimal,
                         measurements: Mapping[str, Measurement],
                         profile: ResolvedLayoutProfile) -> Decimal:
    return measure_natural_normal_flow_block(
        profile, viewport_inline=available_inline, measurements=measurements,
        node=node, node_path=path,
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


def _cross_position(align: str, start: Decimal, available: Decimal, size: Decimal, safety: str = "strict") -> tuple[Decimal, Decimal]:
    # Sizing is already complete. Alignment must not replace fixed, intrinsic,
    # bounded or aspect-derived dimensions with the container's extent.
    if size > available:
        return start, size
    if align == "center": return start + (available - size) / 2, size
    if align == "end": return start + available - size, size
    return start, size


def _grid_track_inputs(node: Mapping[str, Any], path: str, *, inline_size: Decimal,
                      measurements: Mapping[str, Measurement], profile: ResolvedLayoutProfile,
                      content_sized: bool) -> tuple[list[Decimal], list[Measurement | None]]:
    """Resolve native grid columns and row-track measurements from one inline allocation."""
    columns, rows = node["columnTracks"], node["rowTracks"]
    gap = _gap(profile, node, path)
    active = _active_children(node, measurements)
    column_measures: list[Measurement | None] = [None] * len(columns)
    row_measures: list[Measurement | None] = [None] * len(rows)
    child_measures: dict[int, Measurement] = {}
    for index, child in active:
        measure = _measure_node(child, f"{path}/children/{index}", measurements, profile)
        child_measures[index] = measure
        cell = child["cell"]
        if cell.get("columnSpan", 1) == 1:
            column_measures[cell["column"] - 1] = measure
    column_sizes = _allocate(
        columns, inline_size - gap * (len(columns) - 1), column_measures,
        axis="inline", profile=profile,
        paths=[f"{path}/columnTracks/{index}" for index in range(len(columns))],
    )
    for index, child in active:
        cell = child["cell"]
        if cell.get("rowSpan", 1) != 1:
            continue
        measure = child_measures[index]
        if content_sized:
            column, span = cell["column"] - 1, cell.get("columnSpan", 1)
            child_inline = sum(column_sizes[column:column + span], ZERO) + gap * (span - 1)
            natural_block = _natural_child_block(child, f"{path}/children/{index}", child_inline,
                                                 measurements, profile)
            measure = _block_measurement(measure, natural_block)
        row_measures[cell["row"] - 1] = measure
    return column_sizes, row_measures


class _Arranger:
    def __init__(self, profile: ResolvedLayoutProfile, measurements: Mapping[str, Measurement], *,
                 content_sized: bool = False):
        self.profile, self.measurements = profile, measurements
        self.content_sized = content_sized
        self.decisions: list[LayoutDecision] = []
        self.fit_warnings: list[FitWarning] = []

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
            heading=_slot_heading(node) if is_slot else None,
        ))
        if kind == "slot":
            measure = _slot_measurement(node, self.measurements, path)
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

    def _linear(self, node: Mapping[str, Any], path: str, rect: Rect) -> None:
        inline, block, inline_size, block_size = self._content(node, path, rect)
        row = node["kind"] == "row"; main = inline_size if row else block_size
        cross = block_size if row else inline_size; gap = _gap(self.profile, node, path)
        children = _active_children(node, self.measurements)
        measured = [_measure_node(child, f"{path}/children/{i}", self.measurements, self.profile) for i, child in children]
        specs = [child["inlineSize" if row else "blockSize"] for _, child in children]
        specs = [
            {"fixed": cross * _d(spec["aspectRatio"]) if row else cross / _d(spec["aspectRatio"])}
            if isinstance(spec, dict) and "aspectRatio" in spec else spec
            for spec in specs
        ]
        paths = [f"{path}/children/{i}/{'inlineSize' if row else 'blockSize'}" for i, _ in children]
        sizes = _allocate(specs, main - gap * max(0, len(children)-1), measured, axis="inline" if row else "block", profile=self.profile, paths=paths)
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
                minimum, target, weight = _spec_base(cross_spec, axis="block" if row else "inline", measurement=child_measure, profile=self.profile, path=cross_path)
                cross_used = _cross_size((minimum, target, weight), cross, stretch=align == "stretch")
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
        col_sizes, row_measures = _grid_track_inputs(
            node, path, inline_size=inline_size, measurements=self.measurements,
            profile=self.profile, content_sized=self.content_sized)
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
            self.arrange(child,f"{path}/children/{i}",Rect(col_starts[c],row_starts[r],sum(col_sizes[c:c+cs],ZERO)+gap*(cs-1),sum(row_sizes[r:r+rs],ZERO)+gap*(rs-1)))

    def _flow(self, node: Mapping[str, Any], path: str, rect: Rect) -> None:
        inline, block, inline_size, block_size = self._content(node,path,rect); gap=_gap(self.profile,node,path)
        lines = _flow_lines(node, path, self.measurements, self.profile, inline_size,
                            lambda child, child_path, width:
                            _natural_child_block(child, child_path, width, self.measurements, self.profile)
                            if self.content_sized else
                            _measure_node(child, child_path, self.measurements, self.profile).preferred_block)
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
        indexed = {str(child["id"]): (index, child) for index, child in children}
        bounds: dict[str, Rect] = {}

        def child_size(child: Mapping[str, Any], child_path: str) -> tuple[Decimal, Decimal]:
            measure = _measure_node(child, child_path, self.measurements, self.profile)
            inline_base = _spec_base(child["inlineSize"], axis="inline", measurement=measure, profile=self.profile, path=child_path + "/inlineSize")
            block_base = _spec_base(child["blockSize"], axis="block", measurement=measure, profile=self.profile, path=child_path + "/blockSize")
            place = child.get("place", {})
            used_inline = _cross_size(inline_base, inline_size, stretch=place.get("inline") == "stretch")
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
            measure = _measure_node(indexed[child_id][1], f"{path}/children/{indexed[child_id][0]}", self.measurements, self.profile)
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


def solve_layout(profile: ResolvedLayoutProfile, *, viewport_inline: int | float | Decimal, viewport_block: int | float | Decimal, measurements: Mapping[str, Measurement], content_sized: bool = False) -> LayoutManifest:
    """Measure and arrange normal-flow and bounded relative layout nodes."""
    viewport = Rect(ZERO, ZERO, _d(viewport_inline), _d(viewport_block))
    if viewport.inline_size <= ZERO or viewport.block_size <= ZERO:
        raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY", "/viewport")
    root = profile.profile["root"]
    _measure_node(root, "/root", measurements, profile)
    arranger = _Arranger(profile, measurements, content_sized=content_sized); arranger.arrange(root, "/root", viewport)
    relation_routing = profile.profile.get("relationRouting", {})
    annotation_routing = profile.profile["reviewSurface"]["annotationRouting"]
    return LayoutManifest(
        profile.profile_id, profile.content_hash, str(profile.profile["flowDirection"]),
        str(profile.profile["dependencyNetworkFlowDirection"]), viewport,
        tuple(arranger.decisions),
        relation_max_bends=int(relation_routing.get("maxBends", 4)),
        relation_max_detour_ratio=float(relation_routing.get("maxDetourRatio", 2.0)),
        relation_entry=str(relation_routing.get("entry", "side-when-free")),
        annotation_max_bends=int(annotation_routing["maxBends"]),
        annotation_max_detour_ratio=float(annotation_routing["maxDetourRatio"]),
        row_distribution=str(profile.profile["reviewSurface"]["rowDistribution"]),
        background_extents=dict(profile.profile["reviewSurface"]["backgroundExtents"]),
        member_names=dict(profile.profile["reviewSurface"].get("memberNames", {})),
        fit_warnings=tuple(arranger.fit_warnings),
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
            raise ValueError("E_LAYOUT_CONTENT_SHORTFALL_INVALID")


@dataclass(frozen=True)
class ContentBlockResolution:
    """Chosen viewport extent plus exact required-source profile shortfalls."""

    extent: int
    short_sources: tuple[ShortContentSource, ...] = ()

    def __post_init__(self) -> None:
        if self.extent <= 0 or tuple(sorted(self.short_sources, key=lambda item: item.source_id)) != self.short_sources:
            raise ValueError("E_LAYOUT_CONTENT_RESOLUTION_INVALID")
        if len({item.source_id for item in self.short_sources}) != len(self.short_sources):
            raise ValueError("E_LAYOUT_CONTENT_RESOLUTION_INVALID")


def _track_unit_for_requirement(bases: list[tuple[Decimal, Decimal | None, Decimal]],
                                indices: tuple[int, ...], required: Decimal,
                                gap: Decimal) -> Fraction | None:
    """Return a sufficient common fr unit for one selected track span, or prove it capped."""
    track_required = max(Fraction(0), Fraction(required) - Fraction(gap) * max(0, len(indices) - 1))
    fixed = Fraction(0)
    minimum = Fraction(0)
    capacity = Fraction(0)
    unbounded = False
    events: dict[Fraction, list[tuple[str, Fraction]]] = {}
    for index in indices:
        raw_low, raw_high, raw_weight = bases[index]
        low, weight = Fraction(raw_low), Fraction(raw_weight)
        high = None if raw_high is None else Fraction(raw_high)
        if weight <= ZERO:
            amount = high if high is not None else low
            fixed += amount
            capacity += amount
            continue
        minimum += low
        capacity += high if high is not None else low
        if high is None:
            unbounded = True
        elif high < low:
            return None
        threshold = low / weight
        if high is None or high > low:
            events.setdefault(threshold, []).append(("start", weight))
        if high is not None and high > low:
            events.setdefault(high / weight, []).append(("stop", weight))
    if not unbounded and capacity < track_required:
        return None
    value = fixed + minimum
    if value >= track_required:
        return Fraction(0)
    active = Fraction(0)
    cursor = Fraction(0)
    for point in sorted(events):
        if point > cursor and active > ZERO:
            next_value = value + active * (point - cursor)
            if next_value >= track_required:
                return cursor + (track_required - value) / active
            value = next_value
        cursor = point
        for kind, weight in events[point]:
            if kind == "stop":
                active -= weight
        for kind, weight in events[point]:
            if kind == "start":
                active += weight
    if active > ZERO:
        return cursor + (track_required - value) / active
    # A finite maximum can still satisfy a multi-track span after every track caps.
    if not unbounded and value >= track_required:
        return cursor
    return None


def _block_track_extent_witness(*, bases: list[tuple[Decimal, Decimal | None, Decimal]],
                                constraints: tuple[tuple[tuple[int, ...], Decimal], ...],
                                gap: Decimal, padding: Decimal, current: Decimal) -> Decimal | None:
    """Give a conservative finite container extent for selected direct block tracks."""
    unit = Fraction(0)
    for indices, required in constraints:
        selected = _track_unit_for_requirement(bases, indices, required, gap)
        if selected is None:
            return None
        unit = max(unit, selected)
    if not constraints:
        return current
    fixed = sum((Fraction(high if high is not None else low)
                 for low, high, weight in bases if weight <= ZERO), Fraction(0))
    flex_minima = sum((Fraction(low) for low, _high, weight in bases if weight > ZERO), Fraction(0))
    total_weight = sum((Fraction(weight) for _low, _high, weight in bases if weight > ZERO), Fraction(0))
    tracks = fixed + flex_minima + total_weight * unit + Fraction(gap) * max(0, len(bases) - 1)
    extent = max(Fraction(current), tracks + Fraction(padding))
    # Preserve an upper bound when converting the exact capacity inverse back
    # to the native allocator's Decimal representation.
    with localcontext() as context:
        context.rounding = ROUND_CEILING
        return Decimal(extent.numerator) / Decimal(extent.denominator)


def _content_block_capacity_witness(profile: ResolvedLayoutProfile, *, manifest: LayoutManifest,
                                    measurements: Mapping[str, Measurement],
                                    required_blocks: Mapping[str, Decimal],
                                    content_sized: bool = False) -> Decimal | None:
    """Conservatively propagate constant source block needs back through the native allocator tree.

    This is an upper-bound witness only. Callers must solve the unchanged profile at the returned
    extent and verify every requested source allocation before treating it as a fitting bound.
    """
    if not required_blocks:
        return manifest.viewport.block_size
    decisions = {item.node_id: item for item in manifest.decisions}
    slots_by_source: dict[str, str] = {}

    def index_nodes(node: Mapping[str, Any]) -> None:
        node_id = str(node["id"])
        if node["kind"] == "slot":
            source = str(node["source"])
            if source in slots_by_source:
                slots_by_source[source] = ""
            else:
                slots_by_source[source] = node_id
        for child in node.get("children", ()):
            index_nodes(child)

    root = profile.profile["root"]
    index_nodes(root)
    if any(source not in slots_by_source or not slots_by_source[source]
           or slots_by_source[source] not in decisions for source in required_blocks):
        return None
    demand_by_node = {slots_by_source[source]: _d(required)
                      for source, required in required_blocks.items()}

    def measured(node: Mapping[str, Any], path: str) -> Measurement:
        return _measure_node(node, path, measurements, profile)

    def current_size(node: Mapping[str, Any]) -> Decimal | None:
        decision = decisions.get(str(node["id"]))
        return decision.bounds.block_size if decision is not None else None

    def visit(node: Mapping[str, Any], path: str) -> Decimal | None:
        node_id = str(node["id"])
        current = current_size(node)
        if current is None:
            return None
        if node["kind"] == "slot":
            required = demand_by_node.get(node_id)
            return max(current, required) if required is not None else ZERO
        children = _active_children(node, measurements)
        child_needs: dict[int, Decimal] = {}
        for index, child in children:
            need = visit(child, f"{path}/children/{index}")
            if need is None:
                return None
            if need > ZERO:
                child_needs[index] = need
        if not child_needs:
            return ZERO
        kind = node["kind"]
        i0, i1, b0, b1 = _padding(profile, node, path)
        block_padding = b0 + b1
        if kind == "column":
            bases = []
            constraints = []
            for offset, (index, child) in enumerate(children):
                child_path = f"{path}/children/{index}"
                child_measure = measured(child, child_path)
                spec = child["blockSize"]
                if isinstance(spec, dict) and "aspectRatio" in spec:
                    parent_decision = decisions[node_id]
                    i0_parent, i1_parent, _b0, _b1 = _padding(profile, node, path)
                    cross = max(ZERO, parent_decision.bounds.inline_size - i0_parent - i1_parent)
                    spec = {"fixed": cross / _d(spec["aspectRatio"])}
                bases.append(_spec_base(spec, axis="block", measurement=child_measure,
                                        profile=profile, path=child_path + "/blockSize"))
                if index in child_needs:
                    constraints.append(((offset,), child_needs[index]))
            target = _block_track_extent_witness(
                bases=bases, constraints=tuple(constraints), gap=_gap(profile, node, path),
                padding=block_padding, current=max(ZERO, current - block_padding))
            return None if target is None else max(current, target)
        if kind == "grid":
            rows = node["rowTracks"]
            indexed_children = dict(children)
            col_sizes, row_measures = _grid_track_inputs(
                node, path,
                inline_size=max(ZERO, decisions[node_id].bounds.inline_size - i0 - i1),
                measurements=measurements, profile=profile, content_sized=content_sized)
            bases = [_spec_base(spec, axis="block", measurement=row_measures[index], profile=profile,
                                path=f"{path}/rowTracks/{index}")
                     for index, spec in enumerate(rows)]
            constraints = []
            for index in child_needs:
                child = indexed_children[index]
                cell = child["cell"]
                start = cell["row"] - 1
                span = cell.get("rowSpan", 1)
                constraints.append((tuple(range(start, start + span)), child_needs[index]))
            target = _block_track_extent_witness(
                bases=bases, constraints=tuple(constraints), gap=_gap(profile, node, path),
                padding=block_padding, current=max(ZERO, current - block_padding))
            return None if target is None else max(current, target)
        if kind in {"row", "overlay"}:
            inner = max(ZERO, current - block_padding)
            needed = inner
            active_by_index = dict(children)
            for index, required in child_needs.items():
                child = active_by_index[index]
                child_path = f"{path}/children/{index}"
                child_decision = decisions.get(str(child["id"]))
                if child_decision is None:
                    return None
                if child["kind"] == "slot" and child_decision.bounds.block_size >= required:
                    continue
                spec = child["blockSize"]
                measure = measured(child, child_path)
                base = _spec_base(spec, axis="block", measurement=measure, profile=profile,
                                  path=child_path + "/blockSize")
                if isinstance(spec, dict) and "aspectRatio" in spec:
                    capacity = child_decision.bounds.inline_size / _d(spec["aspectRatio"])
                    if required > capacity:
                        return None
                    continue
                if base[2] <= ZERO:
                    capacity = base[1] if base[1] is not None else base[0]
                    if required > capacity:
                        return None
                    continue
                default_align = node["alignItems"] if kind == "row" else "start"
                align = child.get("place", {}).get("block", default_align)
                if base[1] is not None and align == "stretch" and required > base[1]:
                    return None
                needed = max(needed, required, base[0])
            return max(current, needed + block_padding)
        if kind == "flow":
            active_by_index = dict(children)
            for index, required in child_needs.items():
                child = active_by_index[index]
                child_bounds = current_size(child)
                if child_bounds is None or required > child_bounds:
                    return None
            return current
        return None

    return visit(root, "/root")


def resolve_content_block_extent(profile: ResolvedLayoutProfile, *, viewport_inline: int,
                                 minimum_block: int, measurements: Mapping[str, Measurement],
                                 required_blocks: Mapping[str, Decimal],
                                 content_sized: bool = False) -> ContentBlockResolution:
    """Verify a native allocation-capacity witness, then choose its least integral extent.

    The requested extent remains the finite minimum (or the caller's measured
    auto floor). A speculative witness never becomes output unless the unchanged
    whole profile satisfies every source and, for auto, normal-flow content.
    Shortage evidence always describes the manifest at the returned extent.
    """
    if minimum_block <= 0:
        raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY", "/viewport")

    def arrange(extent: int) -> LayoutManifest:
        return solve_layout(profile, viewport_inline=viewport_inline,
                            viewport_block=extent, measurements=measurements,
                            content_sized=content_sized)

    def allocations(manifest: LayoutManifest) -> dict[str, Decimal]:
        return {item.source: item.bounds.block_size for item in manifest.decisions if item.source}

    def satisfies(manifest: LayoutManifest) -> bool:
        allocated = allocations(manifest)
        return (all(allocated[source] >= required for source, required in required_blocks.items())
                and (not content_sized or not _unresolved_normal_flow_warnings(profile, manifest)))

    requested = arrange(minimum_block)
    requested_allocated = allocations(requested)
    missing = sorted(set(required_blocks) - set(requested_allocated))
    if missing:
        raise LayoutError("E_LAYOUT_DRAFT_AUTO_UNSUPPORTED", "/layoutManifest/sources/" + missing[0])
    if satisfies(requested):
        return ContentBlockResolution(minimum_block)

    witness = _content_block_capacity_witness(
        profile, manifest=requested, measurements=measurements,
        required_blocks=required_blocks, content_sized=content_sized,
    )
    # A strict integral upper witness avoids a native Decimal fr division
    # landing just below an exact capacity boundary. Bisection still tests
    # that boundary and returns it whenever the unchanged allocator fits.
    high = minimum_block if witness is None else max(minimum_block, int(witness) + 1)
    if high == minimum_block or not satisfies(arrange(high)):
        return ContentBlockResolution(minimum_block, tuple(
            ShortContentSource(source, required_blocks[source], requested_allocated[source])
            for source in sorted(required_blocks)
            if requested_allocated[source] < required_blocks[source]
        ))

    # Only this verified fitting interval may drive the least-integral search.
    low = minimum_block
    while high - low > 1:
        middle = (low + high) // 2
        if satisfies(arrange(middle)):
            high = middle
        else:
            low = middle
    return ContentBlockResolution(high)
