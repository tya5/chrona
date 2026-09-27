"""Layout-owned conversion from a finite seed solve to local lane geometry."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Mapping

from chrona.presentation.layout.lane_preflight import LaneInlineFrame, lane_inline_frame_for_manifest
from chrona.presentation.layout.model import LayoutError, LayoutManifest
from chrona.presentation.layout.presentation import MarkBandFrame
from chrona.presentation.layout.surface_composer import resolve_mark_geometries
from chrona.presentation.layout.surface_quality import ScalePlacement


def lane_seed_mark_band_frame(
    manifest: LayoutManifest, *, window: tuple[date, date],
    metric_values: Mapping[str, Decimal], theme_tokens: Any,
) -> tuple[LaneInlineFrame, MarkBandFrame]:
    """Freeze exactly the inline scale and zero-origin band used by preflight."""
    inline = lane_inline_frame_for_manifest(manifest, window=window)
    block_size = metric_values.get("timeline.mark.blockSize")
    if block_size is None or not block_size.is_finite() or block_size <= 0:
        raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues")
    left = float(inline.timeline_inline)
    width = float(inline.timeline_inline_size)
    scale = ScalePlacement(
        "table-timeline", "primary", window[0], window[1],
        left, left + width, left, float(inline.temporal_scale),
    )
    return inline, MarkBandFrame.zero_origin(
        scale, float(block_size), resolve_mark_geometries(theme_tokens),
    )
