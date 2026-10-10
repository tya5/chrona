"""Date-only label admission completed once with the source visibility cache."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from chrona.presentation.layout.mark_facet_visibility import FacetDisposition, ItemMarkVisibility
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.model.projection import WindowMode


@dataclass(frozen=True, slots=True)
class WindowLabelAdmission:
    """Original label-host and delta-anchor facts; no coordinates or measurements."""

    host_facet: str
    host_outside: bool
    delta_anchor_facet: str | None
    delta_anchor: date | None
    delta_outside: bool

    def admit_components(self, components: tuple[tuple[str, str], ...], *,
                         semantic_id: str = "memberLabel") -> tuple[str, ...]:
        if semantic_id == "memberLabel" and self.host_outside:
            return ()
        return tuple(value for kind, value in components
                     if kind != "finishDelta" or not self.delta_outside)

    def __post_init__(self) -> None:
        if (self.host_facet not in {"actual", "planned"}
                or type(self.host_outside) is not bool or type(self.delta_outside) is not bool
                or self.delta_anchor_facet not in {None, "actual", "planned"}
                or (self.delta_anchor is not None and type(self.delta_anchor) is not date)
                or (self.delta_anchor is None) != (self.delta_anchor_facet is None)
                or (self.delta_anchor is None and self.delta_outside)):
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/items",
                              detail="stage=label-admission; reason=invalid-original-anchor")


@dataclass(frozen=True, slots=True)
class WindowLabelAbsence:
    """A source-keyed temporal label suppression with no spatial operands."""

    placement_id: str
    source_ref: str
    occurrence: Any
    semantic_id: str
    admission: WindowLabelAdmission
    components: tuple[tuple[str, str], ...]
    lane_row_id: str | None = None
    lane_member_id: str | None = None
    reason: str = "outside-window"
    visibility_index: Any = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        from chrona.presentation.layout.surface_mark_visibility import MarkOccurrence, MarkOccurrenceKind
        if (not isinstance(self.occurrence, MarkOccurrence)
                or not isinstance(self.placement_id, str) or not self.placement_id
                or self.source_ref != self.occurrence.object_id
                or self.semantic_id not in {"memberLabel", "finishDelta"}
                or not isinstance(self.admission, WindowLabelAdmission)
                or not isinstance(self.components, tuple) or not self.components
                or any(not isinstance(component, tuple) or len(component) != 2
                       or component[0] not in {"title", "attached", "finishDelta"}
                       or not isinstance(component[1], str) for component in self.components)
                or (self.lane_row_id is None) != (self.lane_member_id is None)
                or self.reason != "outside-window"):
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/items",
                              detail="stage=label-absence; reason=invalid-source-account")
        if self.occurrence.kind == MarkOccurrenceKind.AUTO:
            instance = self.occurrence.object_id
        elif self.occurrence.kind == MarkOccurrenceKind.FOLDED:
            instance = f"group-header:{self.occurrence.container_id}:{self.occurrence.item_id}"
        elif self.occurrence.kind in {MarkOccurrenceKind.ROW, MarkOccurrenceKind.LANE_FINAL}:
            instance = f"{self.occurrence.container_id}:{self.occurrence.item_id}"
        else:
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", self.placement_id,
                              detail="stage=label-absence; reason=invalid-occurrence")
        prefix = "member-label" if self.semantic_id == "memberLabel" else "variance"
        if self.placement_id != f"{prefix}:{instance}":
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", self.placement_id,
                              detail="stage=label-absence; reason=invalid-label-identity")
        omitted = (self.semantic_id == "memberLabel" and self.admission.host_outside) or (
            self.admission.delta_outside and all(kind == "finishDelta" for kind, _ in self.components))
        if not omitted:
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", self.placement_id,
                              detail="stage=label-absence; reason=visible-label")
        self.validate_cache(self.visibility_index)

    @property
    def diagnostic(self) -> str:
        return f"W_LAYOUT_LABEL_SUPPRESSED:{self.placement_id}"

    def validate_cache(self, index: Any) -> None:
        from chrona.presentation.layout.surface_mark_visibility import ItemMarkVisibilityIndex
        if not isinstance(index, ItemMarkVisibilityIndex):
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", self.placement_id,
                              detail="stage=label-absence; reason=missing-source-account")
        if index.lookup_label(self.occurrence, projection=index.projection,
                              as_of=index.as_of) is not self.admission:
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", self.placement_id,
                              detail="stage=label-absence; reason=borrowed-source-account")


def complete_window_label_admission(item: Any, visibility: ItemMarkVisibility, *,
                                    window_mode: WindowMode,
                                    window: tuple[date, date]) -> WindowLabelAdmission:
    host_facet = "actual" if visibility.selection.source_kind == "actual" else "planned"
    host = next((facet for facet in visibility.facets if facet.source.facet == host_facet), None)
    actual_finish = (item.actual or {}).get("finish")
    anchor = actual_finish if isinstance(actual_finish, date) else item.planned.get(
        "end", item.planned.get("at"))
    anchor_facet = "actual" if isinstance(actual_finish, date) else "planned"
    if not isinstance(anchor, date):
        anchor, anchor_facet = None, None
    explicit = window_mode == WindowMode.EXPLICIT
    # A source-selected absence (for example invalid open Actual) is not a
    # temporal omission and retains its existing strict host validation.
    host_outside = bool(explicit and host is not None and host.disposition == FacetDisposition.OMITTED)
    point = item.source_type == "point"
    anchor_inside = anchor is not None and (
        window[0] <= anchor < window[1] if point else window[0] < anchor <= window[1])
    return WindowLabelAdmission(host_facet, host_outside, anchor_facet, anchor,
                                bool(explicit and anchor is not None and not anchor_inside))
