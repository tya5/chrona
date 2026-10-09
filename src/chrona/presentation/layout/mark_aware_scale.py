"""Shared date-preserving scale inset from resolved point-mark facets."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import isfinite
from typing import Iterable

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.surface_quality import ScalePlacement


@dataclass(frozen=True)
class PointMarkFootprint:
    """Horizontal visible bounds of one point facet and its date anchor."""

    anchor_date: date
    left: float
    right: float

    def __post_init__(self) -> None:
        if (type(self.anchor_date) is not date
                or any(isinstance(value, bool) or not isinstance(value, (int, float))
                       or not isfinite(value) for value in (self.left, self.right))
                or self.left > self.right):
            raise ValueError(f"E_LAYOUT_MARK_OVERFLOW: point facet anchor_date={self.anchor_date!r}, "
                             f"left={self.left!r}, right={self.right!r}; "
                             "expected an exact date and finite ordered inline bounds")


def inset_scale_for_point_facets(
    provisional: ScalePlacement,
    facets: Iterable[PointMarkFootprint],
) -> ScalePlacement:
    """Reserve resolved edge protrusions while preserving the selected Date domain.

    ``facets`` must have been composed against ``provisional``.  The returned
    scale is the sole completed mapping; an empty facet set preserves the
    original scale object.
    """
    if (not isinstance(provisional, ScalePlacement)
            or type(provisional.domain_start) is not date
            or type(provisional.domain_end) is not date
            or provisional.domain_start >= provisional.domain_end
            or any(not isfinite(value) for value in (
                provisional.range_start, provisional.range_end,
                provisional.origin, provisional.unit_ratio))
            or provisional.range_end <= provisional.range_start
            or provisional.unit_ratio <= 0):
        raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/layoutManifest/sources/timeline")
    resolved = tuple(facets)
    if not resolved:
        return provisional
    left_inset = right_inset = 0.0
    days = (provisional.domain_end - provisional.domain_start).days
    for facet in resolved:
        if not isinstance(facet, PointMarkFootprint):
            raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/layout/pointFacets")
        anchor = provisional.origin + (facet.anchor_date - provisional.domain_start).days * provisional.unit_ratio
        left_inset = max(left_inset, anchor - facet.left)
        right_inset = max(right_inset, facet.right - anchor)
    left_inset = max(0.0, left_inset)
    right_inset = max(0.0, right_inset)
    range_start = provisional.range_start + left_inset
    range_end = provisional.range_end - right_inset
    if range_end <= range_start:
        raise LayoutError("E_LAYOUT_MARK_OVERFLOW", "/layoutManifest/sources/timeline")
    return ScalePlacement(
        provisional.surface_id, provisional.scale_id,
        provisional.domain_start, provisional.domain_end,
        range_start, range_end, range_start,
        (range_end - range_start) / days,
    )
