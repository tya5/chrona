"""Source-proven endpoint absence; never substitute a window-edge port."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from chrona.presentation.layout.mark_facet_visibility import ItemMarkVisibility
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_mark_visibility import ItemMarkVisibilityIndex, MarkOccurrence
from chrona.presentation.model.projection import ReviewProjection, WindowMode


def _outside(visibility: ItemMarkVisibility, endpoint: str) -> bool:
    if endpoint not in {"start", "at", "end", "finish"}:
        raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/relations",
                          detail="stage=relation-admission; reason=invalid-endpoint")
    planned = next((facet for facet in visibility.facets if facet.source.facet == "planned"), None)
    # No planned source facet is not evidence of window omission.
    return planned is not None and not (
        planned.start_port_visible if endpoint in {"start", "at"} else planned.end_port_visible)


@dataclass(frozen=True, slots=True)
class WindowRelationEndpointAbsence:
    """The original endpoint's cached cause, without coordinates or a route."""

    occurrence: MarkOccurrence
    endpoint: str
    visibility: ItemMarkVisibility
    visibility_index: ItemMarkVisibilityIndex = field(repr=False, compare=False)
    reason: str = "outside-window"

    def __post_init__(self) -> None:
        index = self.visibility_index
        valid = (isinstance(index, ItemMarkVisibilityIndex)
                 and isinstance(self.occurrence, MarkOccurrence)
                 and isinstance(self.visibility, ItemMarkVisibility)
                 and index.projection.window_mode == WindowMode.EXPLICIT
                 and self.reason == "outside-window")
        if valid:
            try:
                valid = (index.lookup(self.occurrence, projection=index.projection, as_of=index.as_of)
                         is self.visibility) and _outside(self.visibility, self.endpoint)
            except KeyError:
                valid = False
        if not valid:
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/relations",
                              detail="stage=relation-admission; reason=invalid-source-proof")

    @property
    def source_ref(self) -> str:
        return self.visibility.source_ref


def complete_window_relation_endpoint_absence(
    occurrence: MarkOccurrence, endpoint: str, *, projection: ReviewProjection,
    as_of: date | None, visibility_index: ItemMarkVisibilityIndex,
) -> WindowRelationEndpointAbsence | None:
    """Read the immutable original-port decision, without selecting dates again."""
    visibility_index.require_match(projection, as_of)
    if projection.window_mode != WindowMode.EXPLICIT:
        return None
    try:
        visibility = visibility_index.lookup(occurrence, projection=projection, as_of=as_of)
    except KeyError:
        raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/relations",
                          detail="stage=relation-admission; reason=missing-source-occurrence") from None
    if not _outside(visibility, endpoint):
        return None
    return WindowRelationEndpointAbsence(occurrence, endpoint, visibility, visibility_index)
