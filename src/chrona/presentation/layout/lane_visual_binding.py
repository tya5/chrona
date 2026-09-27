"""Bind object-level View visuals to exact lane projection instances."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from chrona.presentation.layout.lane_projection import LaneProjectionClosure, LaneProjectionInstance
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_quality import VisualRequest
from chrona.presentation.model.projection import ReviewProjection


def bind_lane_visual_requests(
    projection: ReviewProjection,
    closure: LaneProjectionClosure,
    requests: Iterable[VisualRequest],
) -> tuple[dict[LaneProjectionInstance, tuple[VisualRequest, ...]],
           dict[tuple[LaneProjectionInstance, str], VisualRequest]]:
    """Fan object selectors out to their selected lane occurrences.

    Plot-label visuals bind once to each countable per-row occurrence (the
    same representative the lane mapper labels), including attached points.
    Mark selectors match semantic roles; their typed request keys use each
    expected mark's emission purpose, which may differ for comparison marks.
    Comparison roles share the public ``planned`` selector. Serialized
    placement IDs are never parsed.
    """
    representatives: dict[str, list[LaneProjectionInstance]] = defaultdict(list)
    for row in projection.rows:
        groups: dict[str, list[LaneProjectionInstance]] = defaultdict(list)
        for instance in closure.instances:
            if instance.row_id == row.row_id:
                groups[instance.object_id].append(instance)
        for object_id, variants in groups.items():
            representative = _representative(variants, row.table_subject_id)
            representatives[object_id].append(representative)

    label_requests: dict[LaneProjectionInstance, list[VisualRequest]] = defaultdict(list)
    mark_requests: dict[tuple[LaneProjectionInstance, str], VisualRequest] = {}
    label_sides: set[tuple[LaneProjectionInstance, str]] = set()
    for request in requests:
        selector = dict(request.selector)
        if request.target_kind == "plot-label":
            object_id = selector.get("id")
            matches = representatives.get(object_id or "", ())
            if not object_id or not matches:
                raise LayoutError("E_LAYOUT_VISUAL_TARGET", request.source_ref)
            for instance in matches:
                side_key = (instance, request.side)
                if side_key in label_sides:
                    raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", request.source_ref)
                label_sides.add(side_key)
                label_requests[instance].append(request)
        elif request.target_kind == "mark":
            object_id, facet = selector.get("object"), selector.get("facet")
            roles = _semantic_roles(facet)
            if not object_id or not roles:
                raise LayoutError("E_LAYOUT_VISUAL_TARGET", request.source_ref)
            matches = tuple((expected.instance, expected.purpose)
                            for expected in closure.expected_marks
                            if expected.instance.object_id == object_id
                            and expected.role in roles)
            if not matches:
                raise LayoutError("E_LAYOUT_VISUAL_TARGET", request.source_ref)
            for instance, purpose in matches:
                key = (instance, purpose)
                if key in mark_requests:
                    raise LayoutError("E_LAYOUT_VISUAL_DUPLICATE", request.source_ref)
                mark_requests[key] = request
    return ({instance: tuple(values) for instance, values in label_requests.items()}, mark_requests)


def _semantic_roles(facet: str | None) -> tuple[str, ...]:
    if facet == "planned":
        return ("planned", "snapshot", "scenario")
    if facet == "actual":
        return ("actual",)
    return ()


def _representative(variants: list[LaneProjectionInstance],
                    table_subject_id: str) -> LaneProjectionInstance:
    preferred = tuple(instance for instance in variants if instance.item_id == table_subject_id)
    if len(preferred) == 1:
        return preferred[0]
    primary = tuple(instance for instance in variants
                    if instance.source_kind in {"primary", "combined"})
    if len(primary) == 1:
        return primary[0]
    return variants[0]
