"""Deterministic normal-flow engine for intent-oriented Layout Profile v0.2."""
from __future__ import annotations

from decimal import Decimal, getcontext
from typing import Any, Mapping

from chrona.presentation.layout.model import (
    LayoutDecision, LayoutError, LayoutManifest, Measurement, Rect, ResolvedLayoutProfile,
)


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


def _allocate(specs: list[Any], available: Decimal, measurements: list[Measurement | None], *, axis: str, profile: ResolvedLayoutProfile, paths: list[str]) -> list[Decimal]:
    bases = [_spec_base(spec, axis=axis, measurement=measure, profile=profile, path=path) for spec, measure, path in zip(specs, measurements, paths)]
    sizes = [target if target is not None and weight == ZERO else minimum for minimum, target, weight in bases]
    remaining = available - sum(sizes, ZERO)
    if remaining < ZERO:
        raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY")
    flex = sum((weight for _, _, weight in bases), ZERO)
    if flex:
        for index, (_, maximum, weight) in enumerate(bases):
            if weight:
                addition = remaining * weight / flex
                sizes[index] += addition if maximum is None else min(addition, max(ZERO, maximum - sizes[index]))
    return sizes


def _measure_node(node: Mapping[str, Any], path: str, measurements: Mapping[str, Measurement], profile: ResolvedLayoutProfile) -> Measurement:
    if node["kind"] == "slot":
        return _slot_measurement(node, measurements, path)
    children = [_measure_node(child, f"{path}/children/{index}", measurements, profile) for index, child in enumerate(node["children"])]
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
        if safety == "safe": return start, size
        raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW")
    if align == "center": return start + (available - size) / 2, size
    if align == "end": return start + available - size, size
    return start, size


class _Arranger:
    def __init__(self, profile: ResolvedLayoutProfile, measurements: Mapping[str, Measurement]):
        self.profile, self.measurements = profile, measurements
        self.decisions: list[LayoutDecision] = []

    def arrange(self, node: Mapping[str, Any], path: str, rect: Rect) -> None:
        kind, node_id = str(node["kind"]), str(node["id"])
        self.decisions.append(LayoutDecision(node_id, kind, rect, node.get("source"), node.get("place", {})))
        if kind == "slot":
            measure = _slot_measurement(node, self.measurements, path)
            if node["overflow"] == "diagnose" and (rect.inline_size < measure.min_inline or rect.block_size < measure.min_block):
                raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW", path, node_id)
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
        return rect.inline + i0, rect.block + b0, rect.inline_size - i0 - i1, rect.block_size - b0 - b1

    def _linear(self, node: Mapping[str, Any], path: str, rect: Rect) -> None:
        inline, block, inline_size, block_size = self._content(node, path, rect)
        row = node["kind"] == "row"; main = inline_size if row else block_size
        cross = block_size if row else inline_size; gap = _gap(self.profile, node, path)
        children = list(node["children"])
        measured = [_measure_node(child, f"{path}/children/{i}", self.measurements, self.profile) for i, child in enumerate(children)]
        specs = [child["inlineSize" if row else "blockSize"] for child in children]
        specs = [
            {"fixed": cross * _d(spec["aspectRatio"]) if row else cross / _d(spec["aspectRatio"])}
            if isinstance(spec, dict) and "aspectRatio" in spec else spec
            for spec in specs
        ]
        paths = [f"{path}/children/{i}/{'inlineSize' if row else 'blockSize'}" for i in range(len(children))]
        sizes = _allocate(specs, main - gap * max(0, len(children)-1), measured, axis="inline" if row else "block", profile=self.profile, paths=paths)
        used = sum(sizes, ZERO) + gap * max(0, len(children)-1)
        cursor_delta, actual_gap = _distributed_start(node["justifyContent"], main-used, len(children), gap)
        cursor = (inline if row else block) + cursor_delta
        baseline = None
        if row and node["alignItems"] in {"first-baseline", "last-baseline"}:
            values = [m.first_baseline if node["alignItems"] == "first-baseline" else m.last_baseline for m in measured]
            if any(value is None for value in values): raise LayoutError("E_LAYOUT_BASELINE_UNAVAILABLE", path, node["id"])
            baseline = max(value for value in values if value is not None)
        for index, (child, child_measure, main_size) in enumerate(zip(children, measured, sizes)):
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
            if baseline is not None:
                own = child_measure.first_baseline if node["alignItems"] == "first-baseline" else child_measure.last_baseline
                cross_start = block + baseline - own  # type: ignore[operator]
            child_rect = Rect(cursor, cross_start, main_size, cross_used) if row else Rect(cross_start, cursor, cross_used, main_size)
            self.arrange(child, child_path, child_rect); cursor += main_size + actual_gap

    def _grid(self, node: Mapping[str, Any], path: str, rect: Rect) -> None:
        inline, block, inline_size, block_size = self._content(node, path, rect); gap = _gap(self.profile, node, path)
        cols, rows = node["columnTracks"], node["rowTracks"]
        col_measures: list[Measurement | None] = [None] * len(cols); row_measures: list[Measurement | None] = [None] * len(rows)
        for i, child in enumerate(node["children"]):
            measure = _measure_node(child, f"{path}/children/{i}", self.measurements, self.profile); cell=child["cell"]
            if cell.get("columnSpan",1)==1: col_measures[cell["column"]-1]=measure
            if cell.get("rowSpan",1)==1: row_measures[cell["row"]-1]=measure
        col_sizes=_allocate(cols,inline_size-gap*(len(cols)-1),col_measures,axis="inline",profile=self.profile,paths=[f"{path}/columnTracks/{i}" for i in range(len(cols))])
        row_sizes=_allocate(rows,block_size-gap*(len(rows)-1),row_measures,axis="block",profile=self.profile,paths=[f"{path}/rowTracks/{i}" for i in range(len(rows))])
        col_starts=[]; cursor=inline
        for size in col_sizes: col_starts.append(cursor); cursor+=size+gap
        row_starts=[]; cursor=block
        for size in row_sizes: row_starts.append(cursor); cursor+=size+gap
        for i,child in enumerate(node["children"]):
            cell=child["cell"]; c=cell["column"]-1; r=cell["row"]-1; cs=cell.get("columnSpan",1); rs=cell.get("rowSpan",1)
            self.arrange(child,f"{path}/children/{i}",Rect(col_starts[c],row_starts[r],sum(col_sizes[c:c+cs],ZERO)+gap*(cs-1),sum(row_sizes[r:r+rs],ZERO)+gap*(rs-1)))

    def _flow(self, node: Mapping[str, Any], path: str, rect: Rect) -> None:
        inline, block, inline_size, block_size = self._content(node,path,rect); gap=_gap(self.profile,node,path); minimum=_distance(self.profile,path+"/itemMinInlineSize")
        lines: list[list[tuple[int, Mapping[str, Any], Measurement, Decimal, Decimal]]] = [[]]
        used=ZERO
        for i,child in enumerate(node["children"]):
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
            if cursor_b+line_height>block+block_size: raise LayoutError("E_LAYOUT_REQUIRED_OVERFLOW",path,node["id"])
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
                if baseline is not None:
                    own=measure.first_baseline if node["alignItems"]=="first-baseline" else measure.last_baseline; child_block=cursor_b+baseline-own  # type: ignore[operator]
                self.arrange(child,child_path,Rect(cursor_i,child_block,width,height)); cursor_i+=width+actual_gap
            cursor_b+=line_height+gap

    def _overlay(self, node: Mapping[str, Any], path: str, rect: Rect) -> None:
        inline, block, inline_size, block_size=self._content(node,path,rect)
        for i,child in enumerate(node["children"]):
            if "anchor" in child: continue
            child_path=f"{path}/children/{i}"; measure=_measure_node(child,child_path,self.measurements,self.profile); place=child.get("place",{})
            _, iw, fw=_spec_base(child["inlineSize"],axis="inline",measurement=measure,profile=self.profile,path=child_path+"/inlineSize")
            _, bh, fb=_spec_base(child["blockSize"],axis="block",measurement=measure,profile=self.profile,path=child_path+"/blockSize")
            ci=inline_size if fw else (iw or inline_size); cb=block_size if fb else (bh or block_size)
            si,ci=_cross_position(place.get("inline","start"),inline,inline_size,ci,place.get("safety","strict")); sb,cb=_cross_position(place.get("block","start"),block,block_size,cb,place.get("safety","strict"))
            self.arrange(child,child_path,Rect(si,sb,ci,cb))


def solve_layout(profile: ResolvedLayoutProfile, *, viewport_inline: int | float | Decimal, viewport_block: int | float | Decimal, measurements: Mapping[str, Measurement]) -> LayoutManifest:
    """Measure and arrange normal-flow nodes; relative overlay children are I24-3."""
    viewport = Rect(ZERO, ZERO, _d(viewport_inline), _d(viewport_block))
    if viewport.inline_size <= ZERO or viewport.block_size <= ZERO:
        raise LayoutError("E_LAYOUT_CONSTRAINT_CONTRADICTORY", "/viewport")
    root = profile.profile["root"]
    _measure_node(root, "/root", measurements, profile)
    arranger = _Arranger(profile, measurements); arranger.arrange(root, "/root", viewport)
    return LayoutManifest(profile.profile_id, profile.content_hash, str(profile.profile["writingMode"]), viewport, tuple(arranger.decisions))
