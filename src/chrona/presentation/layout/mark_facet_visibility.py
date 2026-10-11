"""Immutable, date-only window visibility shared by Layout geometry consumers."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from enum import StrEnum
from typing import NoReturn

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.semantic_mark_facets import (
    ItemMarkFacetSelection, LogicalMarkFacet,
)
from chrona.presentation.model.projection import WindowMode


class FacetDisposition(StrEnum):
    CONTAINED = "contained"
    CLIPPED = "clipped"
    OMITTED = "omitted"


@dataclass(frozen=True)
class MarkFacetVisibility:
    source: LogicalMarkFacet
    disposition: FacetDisposition
    visible_start: date | None = None
    visible_finish: date | None = None
    visible_at: date | None = None
    cut_start: bool = False
    cut_finish: bool = False
    start_port_visible: bool = False
    end_port_visible: bool = False


@dataclass(frozen=True)
class ItemMarkVisibility:
    instance_id: str
    source_ref: str
    selection: ItemMarkFacetSelection
    facets: tuple[MarkFacetVisibility, ...]


def admitted_source_selection(visibility: ItemMarkVisibility) -> ItemMarkFacetSelection:
    """Read the shared admission result before measuring visible footprints.

    Keep the original source closure on ``visibility``. This geometric
    consumer view does not select dates again or modify any admitted fact.
    """
    admitted = tuple(facet.source for facet in visibility.facets
                     if facet.disposition != FacetDisposition.OMITTED)
    if admitted == visibility.selection.facets:
        return visibility.selection
    return replace(visibility.selection, facets=admitted)


def complete_item_visibility(
    selection: ItemMarkFacetSelection, *, instance_id: str, source_ref: str,
    window_mode: WindowMode, window_start: date, window_end: date,
) -> ItemMarkVisibility:
    """Retain original facts while completing explicit-window admission and ports.

    A due-end tick has point temporal support even though its completed paint
    uses a span shape. Derived windows deliberately retain the existing path.
    No scale, footprint, Theme, row allocation, or Scene participates here.
    """
    explicit = window_mode == WindowMode.EXPLICIT
    if explicit and (type(window_start) is not date or type(window_end) is not date
                     or window_start >= window_end):
        raise LayoutError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/window")

    def invalid(facet: LogicalMarkFacet, reason: str) -> NoReturn:
        # The immutable result keeps full identity; only diagnostic copy is bounded.
        source = repr(source_ref[:64] + ("…" if len(source_ref) > 64 else ""))
        facet_id = repr(facet.facet[:64])
        raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/items",
                          detail=f"source={source}; facet={facet_id}; "
                                 f"stage=visibility; reason={reason}")

    completed: list[MarkFacetVisibility] = []
    for source in selection.facets:
        anchor = source.at if source.shape == "point" else source.start
        point_like = source.shape == "point" or source.geometry == "end-tick"
        if not explicit:
            completed.append(MarkFacetVisibility(
                source, FacetDisposition.CONTAINED,
                visible_at=anchor if point_like else None,
                visible_start=None if point_like else source.start,
                visible_finish=None if point_like else source.finish,
                start_port_visible=True, end_port_visible=True,
            ))
        elif point_like:
            if type(anchor) is not date:
                invalid(source, "source-date-unavailable")
            admitted = window_start <= anchor < window_end
            completed.append(MarkFacetVisibility(
                source, FacetDisposition.CONTAINED if admitted else FacetDisposition.OMITTED,
                visible_at=anchor if admitted else None,
                start_port_visible=admitted, end_port_visible=admitted,
            ))
        else:
            start, finish = source.start, source.finish
            if type(start) is not date or type(finish) is not date:
                invalid(source, "source-date-unavailable")
            if finish <= start:
                invalid(source, "nonpositive-source-interval")
            visible_start, visible_finish = max(start, window_start), min(finish, window_end)
            if visible_start >= visible_finish:
                completed.append(MarkFacetVisibility(source, FacetDisposition.OMITTED))
                continue
            cut_start, cut_finish = visible_start != start, visible_finish != finish
            completed.append(MarkFacetVisibility(
                source, FacetDisposition.CLIPPED if cut_start or cut_finish
                else FacetDisposition.CONTAINED,
                visible_start=visible_start, visible_finish=visible_finish,
                cut_start=cut_start, cut_finish=cut_finish,
                start_port_visible=window_start <= start < window_end,
                end_port_visible=window_start < finish <= window_end,
            ))
    return ItemMarkVisibility(instance_id, source_ref, selection, tuple(completed))
