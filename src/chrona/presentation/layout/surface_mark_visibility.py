"""Typed, immutable index of window-completed source mark occurrences."""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Mapping as TypingMapping

from chrona.presentation.layout.lane_projection import (
    LaneProjectionInstance, close_lane_projection, folded_instance_id,
    lane_instance_owners, lane_missing_actual_visible,
)
from chrona.presentation.layout.mark_facet_visibility import (
    ItemMarkVisibility, complete_item_visibility,
)
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.semantic_mark_facets import select_item_mark_facets
from chrona.presentation.model.projection import ReviewProjection

if TYPE_CHECKING:
    from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest


class MarkOccurrenceKind(StrEnum):
    AUTO = "auto"
    ROW = "row"
    LANE_SOURCE = "lane-source"
    LANE_FINAL = "lane-final"
    FOLDED = "folded"


@dataclass(frozen=True, slots=True)
class MarkOccurrence:
    """Discriminated semantic occurrence key, independent of serialized IDs."""

    kind: MarkOccurrenceKind
    container_id: str
    item_id: str
    object_id: str
    source_kind: str


@dataclass(frozen=True)
class ItemMarkVisibilityIndex:
    """Read-only O(1) visibility lookup bound to one projection and as-of value."""

    projection: ReviewProjection = field(repr=False, compare=False)
    as_of: date | None
    entries: TypingMapping[MarkOccurrence, ItemMarkVisibility]

    def __post_init__(self) -> None:
        # Copy before wrapping so a caller retaining the input dict cannot mutate this index.
        object.__setattr__(self, "entries", MappingProxyType(dict(self.entries)))

    def require_match(self, projection: ReviewProjection, as_of: date | None) -> None:
        if projection is not self.projection or as_of != self.as_of:
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window",
                              detail="stage=index; reason=request-mismatch")

    def lookup(self, occurrence: MarkOccurrence, *, projection: ReviewProjection,
               as_of: date | None) -> ItemMarkVisibility:
        self.require_match(projection, as_of)
        return self.entries[occurrence]


def _pointer_part(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _occurrence_visibility(*, item: object, occurrence: MarkOccurrence,
                           instance_id: str, source_ref: str, as_of: date | None,
                           projection: ReviewProjection, emit_missing_actual: bool,
                           emit_diagnostics: bool) -> ItemMarkVisibility:
    selection = select_item_mark_facets(
        item=item, source_kind=occurrence.source_kind, as_of=as_of,
        emit_missing_actual=emit_missing_actual,
        emit_diagnostics=emit_diagnostics,
    )
    start, end = projection.window
    return complete_item_visibility(
        selection, instance_id=instance_id, source_ref=source_ref,
        window_mode=projection.window_mode, window_start=start, window_end=end,
    )


def build_item_mark_visibility_index(
    projection: ReviewProjection, *, as_of: date | None,
) -> ItemMarkVisibilityIndex:
    """Select and complete each source occurrence once, adding typed lane aliases."""
    entries: dict[MarkOccurrence, ItemMarkVisibility] = {}

    def add(occurrence: MarkOccurrence, *, item: object, instance_id: str,
            source_ref: str, emit_missing_actual: bool = True,
            emit_diagnostics: bool = True) -> ItemMarkVisibility:
        if occurrence in entries:
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/items",
                              detail="stage=index; reason=duplicate-occurrence")
        result = _occurrence_visibility(
            item=item, occurrence=occurrence, instance_id=instance_id,
            source_ref=source_ref, as_of=as_of, projection=projection,
            emit_missing_actual=emit_missing_actual,
            emit_diagnostics=emit_diagnostics,
        )
        entries[occurrence] = result
        return result

    if projection.lane_membership is not None:
        closure = close_lane_projection(projection, as_of=as_of)
        owners = lane_instance_owners(projection, closure)
        items = {
            LaneProjectionInstance(row.row_id, item.item_id or item.object_id,
                                   item.object_id, item.source_kind): item
            for row in projection.rows for item in row.items
        }
        for instance in closure.instances:
            item = items[instance]
            source_occurrence = MarkOccurrence(
                MarkOccurrenceKind.LANE_SOURCE, instance.row_id, instance.item_id,
                instance.object_id, instance.source_kind,
            )
            lane_id, member_id = owners[instance]
            final_occurrence = MarkOccurrence(
                MarkOccurrenceKind.LANE_FINAL, lane_id, member_id,
                instance.object_id, instance.source_kind,
            )
            source_ref = (f"/projection/rows/{_pointer_part(instance.row_id)}/items/"
                          f"{_pointer_part(instance.item_id)}")
            visibility = add(
                source_occurrence, item=item, instance_id=instance.placement_key,
                source_ref=source_ref,
                emit_missing_actual=lane_missing_actual_visible(projection),
            )
            if final_occurrence in entries:
                raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/laneRows",
                                  detail="stage=index; reason=duplicate-lane-alias")
            entries[final_occurrence] = visibility
    elif projection.rows:
        for row in projection.rows:
            for item in row.items:
                item_id = item.item_id or item.object_id
                occurrence = MarkOccurrence(
                    MarkOccurrenceKind.ROW, row.row_id, item_id,
                    item.object_id, item.source_kind,
                )
                add(
                    occurrence, item=item, instance_id=f"{row.row_id}:{item_id}",
                    source_ref=(f"/projection/rows/{_pointer_part(row.row_id)}/items/"
                                f"{_pointer_part(item_id)}"),
                )
    else:
        for item in projection.items:
            occurrence = MarkOccurrence(
                MarkOccurrenceKind.AUTO, item.object_id, item.item_id or item.object_id,
                item.object_id, "combined",
            )
            add(occurrence, item=item, instance_id=item.object_id,
                source_ref=f"/projection/items/{_pointer_part(item.object_id)}")

    for folded in projection.folded_points:
        for item in folded.all_items:
            item_id = item.item_id or item.object_id
            occurrence = MarkOccurrence(
                MarkOccurrenceKind.FOLDED, folded.group_id, item_id,
                item.object_id, item.source_kind,
            )
            add(
                occurrence, item=item, instance_id=folded_instance_id(folded, item),
                source_ref=(f"/projection/foldedPoints/{_pointer_part(folded.group_id)}/items/"
                            f"{_pointer_part(item_id)}"),
                emit_missing_actual=False,
                emit_diagnostics=False,
            )

    return ItemMarkVisibilityIndex(projection, as_of, entries)


def ensure_request_mark_visibility_index(request: SurfaceLayoutRequest) -> SurfaceLayoutRequest:
    """Attach one request-lifetime index, or reject a stale cached binding."""
    projection = request.projection
    if projection is None:
        raise LayoutError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection")
    start, end = projection.window
    if not isinstance(start, date) or not isinstance(end, date) or start >= end:
        raise LayoutError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/window")
    as_of = getattr(getattr(request, "surface_content", None), "as_of", None)
    index = request.mark_visibility_index
    if index is None:
        return replace(request, mark_visibility_index=build_item_mark_visibility_index(
            projection, as_of=as_of))
    if not isinstance(index, ItemMarkVisibilityIndex):
        raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/window",
                          detail="stage=index; reason=invalid-request-cache")
    index.require_match(projection, as_of)
    return request
