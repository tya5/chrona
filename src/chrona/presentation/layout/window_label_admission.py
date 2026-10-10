"""Date-only label admission completed once with the source visibility cache."""
from __future__ import annotations

from dataclasses import dataclass
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

    def __post_init__(self) -> None:
        if (self.host_facet not in {"actual", "planned"}
                or type(self.host_outside) is not bool or type(self.delta_outside) is not bool
                or self.delta_anchor_facet not in {None, "actual", "planned"}
                or (self.delta_anchor is not None and type(self.delta_anchor) is not date)
                or (self.delta_anchor is None) != (self.delta_anchor_facet is None)
                or (self.delta_anchor is None and self.delta_outside)):
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/projection/items",
                              detail="stage=label-admission; reason=invalid-original-anchor")


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
