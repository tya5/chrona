"""Typed evidence for a table-timeline host's usable inline capacity."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from math import isfinite
from typing import TYPE_CHECKING

from chrona.presentation.layout.model import LayoutError, LayoutManifest
from chrona.presentation.layout.surface_quality import ScalePlacement

if TYPE_CHECKING:
    from chrona.presentation.layout.sources import MeasuredSources


@dataclass(frozen=True)
class TemporalInlineCapacity:
    """Solved timeline slot width paired with its existing natural source demand."""

    source_id: str
    slot_id: str
    allocated_inline: Decimal
    natural_inline: Decimal

    def __post_init__(self) -> None:
        if (self.source_id != "timeline" or not self.slot_id
                or not self.allocated_inline.is_finite() or self.allocated_inline < 0
                or not self.natural_inline.is_finite() or self.natural_inline <= 0):
            raise LayoutError("E_LAYOUT_TEMPORAL_CAPACITY_INVALID", "/layoutManifest/sources/timeline")

    @classmethod
    def from_manifest(cls, manifest: LayoutManifest, measured_sources: MeasuredSources) -> "TemporalInlineCapacity":
        """Seal the actual timeline slot allocation and its measured natural width."""
        if not isinstance(manifest, LayoutManifest):
            raise LayoutError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
        decision = manifest.source_decisions().get("timeline")
        if decision is None:
            raise LayoutError("E_PRESENTATION_PRIMITIVE_MISSING", "/layoutManifest/sources/timeline")
        try:
            natural = measured_sources.measurements["timeline"].preferred_inline
        except (AttributeError, KeyError, TypeError) as error:
            raise LayoutError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/measurements/timeline") from error
        return cls("timeline", decision.node_id, decision.bounds.inline_size, natural)

    def prototype_scale(
        self,
        window: tuple[date, date],
        *,
        inline_origin: Decimal | float,
        surface_id: str = "table-timeline",
        scale_id: str = "primary",
    ) -> ScalePlacement:
        """Make a measurement-only scale, using natural width only for a zero-width slot."""
        if (len(window) != 2 or type(window[0]) is not date or type(window[1]) is not date
                or window[0] >= window[1]):
            raise LayoutError("E_LAYOUT_TEMPORAL_CAPACITY_INVALID", "/projection/window")
        origin = float(inline_origin)
        width = self.allocated_inline if self.allocated_inline > 0 else self.natural_inline
        width_value = float(width)
        if not isfinite(origin) or not isfinite(width_value) or width_value <= 0:
            raise LayoutError("E_LAYOUT_TEMPORAL_CAPACITY_INVALID", "/layoutManifest/sources/timeline")
        end = origin + width_value
        days = (window[1] - window[0]).days
        return ScalePlacement(surface_id, scale_id, window[0], window[1], origin, end,
                              origin, width_value / days)

    def required_inline(self, left_inset: float, right_inset: float) -> Decimal:
        """Return natural source demand plus resolved point-facet protrusions."""
        if (any(isinstance(value, bool) or not isinstance(value, (int, float))
                or not isfinite(value) or value < 0 for value in (left_inset, right_inset))):
            raise LayoutError("E_LAYOUT_TEMPORAL_CAPACITY_INVALID", "/layout/pointFacets")
        return self.natural_inline + Decimal(str(left_inset)) + Decimal(str(right_inset))

    def require_usable(self, left_inset: float, right_inset: float,
                       *, provisional: ScalePlacement | None = None) -> None:
        """Refuse only a degenerate scale, not a finite positive allocation shortage."""
        required = self.required_inline(left_inset, right_inset)
        # Native callers provide their exact mapping: changing the subtraction
        # order or dropping its origin can change a floating boundary result.
        start = provisional.range_start if provisional is not None else 0.0
        end = provisional.range_end if provisional is not None else float(self.allocated_inline)
        if self.allocated_inline == 0 or end - right_inset <= start + left_inset:
            raise LayoutError(
                "E_LAYOUT_TEMPORAL_INLINE_CAPACITY", "/layoutManifest/sources/timeline", self.slot_id,
                f"slot={self.slot_id}; allocated_inline={self.allocated_inline}; required_inline={required}; "
                f"natural_inline={self.natural_inline}; point_insets={left_inset}+{right_inset}",
            )
