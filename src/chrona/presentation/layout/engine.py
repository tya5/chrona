"""Deterministic normal-flow engine for intent-oriented Layout Profile v0.2."""
from __future__ import annotations

from decimal import ROUND_CEILING, Decimal, getcontext
from typing import Any, Mapping

from chrona.presentation.layout.model import (
    LayoutDecision, LayoutError, LayoutManifest, Measurement, Rect, ResolvedLayoutProfile,
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


def _padding(profile: ResolvedLayoutProfile, node: Mapping[str, Any], path: str) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    raw = node.get("padding", 0)
    if isinstance(raw, dict) and "token" not in raw:
        return tuple(_distance(profile, f"{path}/padding/{name}") for name in ("inlineStart", "inlineEnd", "blockStart", "blockEnd"))  # type: ignore[return-value]
    value = _distance(profile, f"{path}/padding")
    return value, value, value, value


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
    else:  # grid/overlay intrinsic envelope; exact grid tracks resolve during arrange
        minimum_inline = max((item.min_inline for item in children), default=ZERO) + i0 + i1
        preferred_inline = max((item.preferred_inline for item in children), default=ZERO) + i0 + i1
        maximum_inline = max((item.max_inline for item in children), default=ZERO) + i0 + i1
        minimum_block = max((item.min_block for item in children), default=ZERO) + b0 + b1
        preferred_block = max((item.preferred_block for item in children), default=ZERO) + b0 + b1
        maximum_block = max((item.max_block for item in children), default=ZERO) + b0 + b1
    return Measurement(minimum_inline, preferred_inline, maximum_inline, minimum_block, preferred_block, maximum_block)


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


def _cross_position(align: str, start: Decimal, available: Decimal, size: Decimal, safety: str = "strict") -> tuple[Decimal, Decimal]:
    if align == "stretch": return start, available
    if size > available:
        return start, size
    if align == "center": return start + (available - size) / 2, size
    if align == "end": return start + available - size, size
    return start, size


class _Arranger:
    def __init__(self, profile: ResolvedLayoutProfile, measurements: Mapping[str, Measurement]):
        self.profile, self.measurements = profile, measurements
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
        kind, node_id = str(node["kind"]), str(node["id"])
        self.decisions.append(LayoutDecision(node_id, kind, rect, node.get("source"), node.get("place", {}), references,
                                             node.get("priority") if kind == "slot" else None,
                                             node.get("overflow") if kind == "slot" else None))
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
            if isinstance(cross_spec, dict) and "aspectRatio" in cross_spec:
                ratio = _d(cross_spec["aspectRatio"]); cross_used = main_size / ratio if row else main_size * ratio
            else:
                _, target, weight = _spec_base(cross_spec, axis="block" if row else "inline", measurement=child_measure, profile=self.profile, path=cross_path)
                cross_used = cross if weight else (target if target is not None else cross)
            align = child.get("place", {}).get("block" if row else "inline", node["alignItems"])
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
        for i, child in _active_children(node, self.measurements):
            measure = _measure_node(child, f"{path}/children/{i}", self.measurements, self.profile); cell=child["cell"]
            if cell.get("columnSpan",1)==1: col_measures[cell["column"]-1]=measure
            if cell.get("rowSpan",1)==1: row_measures[cell["row"]-1]=measure
        col_sizes=_allocate(cols,inline_size-gap*(len(cols)-1),col_measures,axis="inline",profile=self.profile,paths=[f"{path}/columnTracks/{i}" for i in range(len(cols))])
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
        inline, block, inline_size, block_size = self._content(node,path,rect); gap=_gap(self.profile,node,path); minimum=_distance(self.profile,path+"/itemMinInlineSize")
        lines: list[list[tuple[int, Mapping[str, Any], Measurement, Decimal, Decimal]]] = [[]]
        used=ZERO
        for i,child in _active_children(node, self.measurements):
            child_path=f"{path}/children/{i}"; measure=_measure_node(child,child_path,self.measurements,self.profile)
            inline_spec, block_spec = child["inlineSize"], child["blockSize"]
            width=max(minimum,measure.preferred_inline); height=measure.preferred_block
            if isinstance(inline_spec,dict) and "aspectRatio" in inline_spec: width=max(minimum,height*_d(inline_spec["aspectRatio"]))
            if isinstance(block_spec,dict) and "aspectRatio" in block_spec: height=width/_d(block_spec["aspectRatio"])
            needed=width if not lines[-1] else gap+width
            if lines[-1] and used+needed>inline_size:
                lines.append([]); used=ZERO; needed=width
            lines[-1].append((i,child,measure,width,height)); used+=needed
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
            _, iw, inline_flex = _spec_base(child["inlineSize"], axis="inline", measurement=measure, profile=self.profile, path=child_path + "/inlineSize")
            _, bh, block_flex = _spec_base(child["blockSize"], axis="block", measurement=measure, profile=self.profile, path=child_path + "/blockSize")
            used_inline = inline_size if inline_flex else (iw if iw is not None else inline_size)
            used_block = block_size if block_flex else (bh if bh is not None else block_size)
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


def solve_layout(profile: ResolvedLayoutProfile, *, viewport_inline: int | float | Decimal, viewport_block: int | float | Decimal, measurements: Mapping[str, Measurement]) -> LayoutManifest:
    """Measure and arrange normal-flow and bounded relative layout nodes."""
    viewport = Rect(ZERO, ZERO, _d(viewport_inline), _d(viewport_block))
    if viewport.inline_size <= ZERO or viewport.block_size <= ZERO:
        raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY", "/viewport")
    root = profile.profile["root"]
    _measure_node(root, "/root", measurements, profile)
    arranger = _Arranger(profile, measurements); arranger.arrange(root, "/root", viewport)
    relation_routing = profile.profile.get("relationRouting", {})
    annotation_routing = profile.profile["reviewSurface"]["annotationRouting"]
    return LayoutManifest(
        profile.profile_id, profile.content_hash, str(profile.profile["flowDirection"]),
        str(profile.profile["dependencyNetworkFlowDirection"]), viewport,
        tuple(arranger.decisions),
        relation_max_bends=int(relation_routing.get("maxBends", 4)),
        relation_max_detour_ratio=float(relation_routing.get("maxDetourRatio", 2.0)),
        annotation_max_bends=int(annotation_routing["maxBends"]),
        annotation_max_detour_ratio=float(annotation_routing["maxDetourRatio"]),
        row_distribution=str(profile.profile["reviewSurface"]["rowDistribution"]),
        background_extents=dict(profile.profile["reviewSurface"]["backgroundExtents"]),
        fit_warnings=tuple(arranger.fit_warnings),
    )


def resolve_content_block_extent(profile: ResolvedLayoutProfile, *, viewport_inline: int,
                                 seed_block: int, measurements: Mapping[str, Measurement],
                                 required_blocks: Mapping[str, Decimal]) -> int:
    """Resolve measured content hosts against one coherent finite profile.

    The probe is a normal finite arrangement.  Each declared content
    requirement contributes only its deficit from its allocated slot, so the
    final value preserves profile chrome and the fixed inline extent. Both
    fixed and Draft-auto requests use this same Layout decision; the requested
    block extent is a minimum, not a clipping boundary.
    """
    requested = solve_layout(profile, viewport_inline=viewport_inline,
                             viewport_block=seed_block, measurements=measurements)
    requested_allocated = {item.source: item.bounds.block_size for item in requested.decisions if item.source}
    missing = sorted(set(required_blocks) - set(requested_allocated))
    if missing:
        raise LayoutError("E_LAYOUT_DRAFT_AUTO_UNSUPPORTED", "/layoutManifest/sources/" + missing[0])
    if all(requested_allocated[source] >= required for source, required in required_blocks.items()):
        return seed_block
    # A source's ordinary slot minimum may itself exceed the default Draft
    # canvas (for example, a 100-row table).  Probe at a finite extent that is
    # safely at least one requested content requirement, then measure chrome
    # from that ordinary arrangement.
    probe_block = max(_d(seed_block), max(required_blocks.values(), default=ZERO) + _d(seed_block))
    manifest = solve_layout(profile, viewport_inline=viewport_inline,
                            viewport_block=probe_block, measurements=measurements)
    allocated = {item.source: item.bounds.block_size for item in manifest.decisions if item.source}
    extent = max((_d(seed_block), *(probe_block - allocated[source] + required
                                    for source, required in required_blocks.items())))
    candidate = int(extent.to_integral_value(rounding=ROUND_CEILING))
    if candidate == seed_block:
        return candidate
    # A fixed/max/anchored source may not gain capacity from a taller page.
    # Do not enlarge or translate the entire profile unless the final normal-
    # flow arrangement truly closes every declared content requirement.
    final = solve_layout(profile, viewport_inline=viewport_inline,
                         viewport_block=candidate, measurements=measurements)
    final_allocated = {item.source: item.bounds.block_size for item in final.decisions if item.source}
    if any(final_allocated[source] < required for source, required in required_blocks.items()):
        return seed_block
    return candidate
