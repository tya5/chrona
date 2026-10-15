"""Resolve point/span hosting from admitted source facts, without row mutation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from chrona.presentation.layout.lane_projection import (
    LaneProjectionInstance, close_lane_projection, lane_instance_owners,
)
from chrona.presentation.layout.mark_facet_visibility import (
    FacetDisposition, ItemMarkVisibility,
)
from chrona.presentation.layout.model import LayoutError, PointHostMode
from chrona.presentation.layout.surface_mark_visibility import (
    ItemMarkVisibilityIndex, MarkOccurrence, MarkOccurrenceKind,
    ensure_item_mark_visibility_index,
)


@dataclass(frozen=True)
class PointHostOccurrence:
    """One source occurrence and its explicit final-row/placement identity."""

    instance: LaneProjectionInstance
    row_id: str
    placement_key: str
    item: Any = field(compare=False, repr=False)
    visibility: ItemMarkVisibility = field(compare=False, repr=False)

    def source_mark_id(self, facet: str) -> str:
        return f"{facet}:{self.visibility.instance_id}"

    def final_mark_id(self, facet: str) -> str:
        return f"{facet}:{self.placement_key}"


@dataclass(frozen=True)
class PointHostRelation:
    """Exact source-facet link, reused by allocation and final composition."""

    point: PointHostOccurrence
    span: PointHostOccurrence
    facet: str


@dataclass(frozen=True)
class PointHostPlan:
    occurrences: tuple[PointHostOccurrence, ...] = ()
    relations: tuple[PointHostRelation, ...] = ()
    visibility_index: ItemMarkVisibilityIndex | None = field(default=None, compare=False, repr=False)


def _occurrences(projection: Any, index: ItemMarkVisibilityIndex,
                 as_of: date | None) -> tuple[PointHostOccurrence, ...]:
    result = []
    if projection.lane_membership is not None:
        closure = close_lane_projection(projection, as_of=as_of)
        owners = lane_instance_owners(projection, closure)
        items = {LaneProjectionInstance(row.row_id, item.item_id or item.object_id,
                                        item.object_id, item.source_kind): item
                 for row in projection.rows for item in row.items}
        for instance in closure.instances:
            item = items[instance]
            row_id, _ = owners[instance]
            occurrence = MarkOccurrence(MarkOccurrenceKind.LANE_SOURCE, instance.row_id,
                instance.item_id, instance.object_id, instance.source_kind)
            result.append(PointHostOccurrence(instance, row_id,
                f"{row_id}:{item.item_id or item.object_id}", item,
                index.lookup(occurrence, projection=projection, as_of=as_of)))
    elif projection.rows:
        for row in projection.rows:
            for item in row.items:
                item_id = item.item_id or item.object_id
                instance = LaneProjectionInstance(row.row_id, item_id, item.object_id, item.source_kind)
                occurrence = MarkOccurrence(MarkOccurrenceKind.ROW, row.row_id,
                    item_id, item.object_id, item.source_kind)
                result.append(PointHostOccurrence(instance, row.row_id,
                    f"{row.row_id}:{item_id}", item,
                    index.lookup(occurrence, projection=projection, as_of=as_of)))
    else:
        folded = {(item.object_id, item.item_id, item.source_kind)
                  for point in projection.folded_points for item in point.all_items}
        for item in projection.items:
            if (item.object_id, item.item_id, item.source_kind) in folded:
                continue
            item_id = item.item_id or item.object_id
            instance = LaneProjectionInstance(item.object_id, item_id, item.object_id, "combined")
            occurrence = MarkOccurrence(MarkOccurrenceKind.AUTO, item.object_id,
                item_id, item.object_id, "combined")
            result.append(PointHostOccurrence(instance, item.object_id, item.object_id, item,
                index.lookup(occurrence, projection=projection, as_of=as_of)))
    return tuple(value for value in result if value.item.temporal_paint)


def resolve_point_host_plan(projection: Any, *, as_of: date | None,
                            mode: PointHostMode | None,
                            visibility_index: ItemMarkVisibilityIndex | None = None) -> PointHostPlan:
    """Select exact hosts once using original dates and existing window admission."""
    if mode is None or projection.surface != "table-timeline":
        return PointHostPlan()
    if mode != PointHostMode.SPAN_WHEN_INSIDE:
        raise LayoutError("E_LAYOUT_SCHEMA", "/reviewSurface/marks/points/host")
    index = ensure_item_mark_visibility_index(projection, as_of=as_of, index=visibility_index)
    occurrences = _occurrences(projection, index, as_of)
    spans: dict[tuple[str, str, str | None, str], list[tuple[PointHostOccurrence, Any]]] = {}
    for occurrence in occurrences:
        for visible in occurrence.visibility.facets:
            source = visible.source
            if (visible.disposition == FacetDisposition.OMITTED
                    or source.shape not in {"span", "open-span"}
                    or source.facet not in {"planned", "actual"}):
                continue
            key = (occurrence.item.object_id, occurrence.instance.source_kind,
                   occurrence.item.scenario_id, source.facet)
            spans.setdefault(key, []).append((occurrence, source))
    relations = []
    for point in occurrences:
        for visible in point.visibility.facets:
            source = visible.source
            if (visible.disposition == FacetDisposition.OMITTED or source.shape != "point"
                    or source.facet not in {"planned", "actual"}):
                continue
            targets = (point.item.declared_attaches_to, point.item.parent_id)
            for target in dict.fromkeys(targets):
                if target is None:
                    continue
                key = (target, point.instance.source_kind, point.item.scenario_id, source.facet)
                eligible = [host for host, span in spans.get(key, ())
                            if span.start <= source.at <= span.finish]
                same_row = [host for host in eligible if host.row_id == point.row_id]
                selected = same_row or eligible
                if len(selected) > 1:
                    names = tuple(host.final_mark_id(source.facet) for host in selected)
                    raise LayoutError("E_LAYOUT_POINT_HOST_AMBIGUOUS", "/projection/items",
                        node_id=point.final_mark_id(source.facet),
                        detail=f"point={point.final_mark_id(source.facet)!r}; candidates={names!r}")
                if selected:
                    relations.append(PointHostRelation(point, selected[0], source.facet))
                    break
    return PointHostPlan(occurrences, tuple(relations), index)
