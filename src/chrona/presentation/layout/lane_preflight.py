"""Fixed-membership lane frame inputs shared by Layout's lane preflight."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from chrona.presentation.layout.model import LayoutError, LayoutManifest


@dataclass(frozen=True)
class LaneInlineFrame:
    """Solved inline geometry used to compose fixed-membership lane marks."""

    table_inline: Decimal
    table_inline_size: Decimal
    timeline_inline: Decimal
    timeline_inline_size: Decimal
    temporal_scale: Decimal

    def __post_init__(self) -> None:
        values = (self.table_inline, self.table_inline_size, self.timeline_inline,
                  self.timeline_inline_size, self.temporal_scale)
        if (any(not value.is_finite() for value in values)
                or self.table_inline_size <= 0 or self.timeline_inline_size <= 0
                or self.temporal_scale <= 0):
            raise LayoutError("E_LAYOUT_LANE_SEED_INVALID", "/layoutManifest")


def lane_inline_frame_for_manifest(
    manifest: LayoutManifest, *, window: tuple[date, date],
) -> LaneInlineFrame:
    """Read the exact lane-driving table/timeline inline frame from one solve."""
    if (not isinstance(manifest, LayoutManifest) or len(window) != 2
            or any(type(value) is not date for value in window)
            or window[0] >= window[1]):
        raise LayoutError("E_LAYOUT_LANE_SEED_INVALID", "/layoutManifest")
    sources = {name: tuple(item for item in manifest.decisions if item.source == name)
               for name in ("table", "timeline")}
    if any(len(items) != 1 for items in sources.values()):
        raise LayoutError("E_LAYOUT_LANE_SEED_INVALID", "/layoutManifest")
    table = sources["table"][0].bounds
    timeline = sources["timeline"][0].bounds
    ratio = float(timeline.inline_size) / max(1, (window[1] - window[0]).days)
    return LaneInlineFrame(table.inline, table.inline_size,
                           timeline.inline, timeline.inline_size, Decimal(str(ratio)))
