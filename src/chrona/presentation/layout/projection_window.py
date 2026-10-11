"""Shared validation of completed timeline input before Layout geometry."""
from __future__ import annotations

from datetime import date

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.model.projection import ReviewProjection


def require_positive_projection_window(projection: ReviewProjection | None) -> tuple[date, date]:
    if projection is None:
        raise LayoutError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection",
                          detail="expected a completed timeline projection")
    start, end = projection.window
    if not isinstance(start, date) or not isinstance(end, date) or start >= end:
        ids = tuple(item.object_id for item in projection.items)
        raise LayoutError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/window",
                          detail=f"expected a positive Date window; start={start!r}, end={end!r}; "
                                 f"selected objects={ids!r}")
    return start, end
