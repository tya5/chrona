"""Complete clipped span ink for marks and summaries without inventing ports."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from math import isfinite

from chrona.presentation.layout.filled_contour import WindowContourError, clip_span_contour
from chrona.presentation.layout.mark_facet_visibility import FacetDisposition, MarkFacetVisibility
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.rounded_outline import rounded_rect_commands
from chrona.presentation.layout.surface_quality import PaintClip, PathCommand, ScalePlacement


@dataclass(frozen=True)
class CompletedWindowSpan:
    bounds: Rect
    contour: tuple[PathCommand, ...]
    source_contour: tuple[PathCommand, ...]
    paint_clip: PaintClip


def window_geometry_error(source_ref: str, visibility: MarkFacetVisibility, reason: str) -> LayoutError:
    source = source_ref[:120] if isinstance(source_ref, str) else "<invalid>"
    facet = visibility.source.facet[:64] if isinstance(visibility.source.facet, str) else "<invalid>"
    return LayoutError("E_LAYOUT_WINDOW_CLIP", "/layout/windowContour", node_id=source,
                       detail=f"source_ref={source!r} facet={facet!r} stage=geometry reason={reason}")


def complete_clipped_span_geometry(
    bounds: Rect, commands: tuple[PathCommand, ...], corner_radius: float,
    visibility: MarkFacetVisibility, scale: ScalePlacement, plot: Rect, *, source_ref: str,
) -> CompletedWindowSpan:
    """Consume cached admission and complete one original span's visible ink."""
    def invalid(reason):
        return window_geometry_error(source_ref, visibility, reason)
    if visibility.disposition != FacetDisposition.CLIPPED:
        raise invalid("invalid-disposition")
    if (visibility.source.shape not in {"span", "open-span"}
            or type(visibility.visible_start) is not date or type(visibility.visible_finish) is not date
            or visibility.visible_start >= visibility.visible_finish):
        raise invalid("unsupported-facet")
    if not isinstance(plot, Rect):
        raise invalid("invalid-plot-or-scale")
    try:
        left, top, plot_width, plot_height = map(float, (
            plot.inline, plot.block, plot.inline_size, plot.block_size))
        x, y, source_width, height = map(float, (
            bounds.inline, bounds.block, bounds.inline_size, bounds.block_size))
        scale_values = tuple(float(value) for value in (
            scale.range_start, scale.range_end, scale.origin, scale.unit_ratio))
        if any(isinstance(value, bool) for value in (
                scale.range_start, scale.range_end, scale.origin, scale.unit_ratio)):
            raise TypeError("boolean scale coordinate")
        x1 = scale.origin + (visibility.visible_start - scale.domain_start).days * scale.unit_ratio
        x2 = scale.origin + (visibility.visible_finish - scale.domain_start).days * scale.unit_ratio
    except Exception as error:
        raise invalid("invalid-plot-or-scale") from error
    right, bottom, width = left + plot_width, top + plot_height, x2 - x1
    if (not all(isfinite(value) for value in (
            x1, x2, y, height, x, source_width, width, left, top, plot_width, plot_height,
            right, bottom, *scale_values))
            or plot_width <= 0 or plot_height <= 0 or scale_values[3] <= 0 or source_width <= 0
            or width <= 0 or height <= 0 or x1 < left or x2 > right or y < top or y + height > bottom):
        raise invalid("host-outside-plot")
    try:
        host = Rect(Decimal(str(x1)), bounds.block, Decimal(str(width)), bounds.block_size)
        original = commands or rounded_rect_commands((x, y, source_width, height), corner_radius)
        contour = clip_span_contour(original, host, cut_start=visibility.cut_start,
                                    cut_finish=visibility.cut_finish, source_ref=source_ref,
                                    facet=visibility.source.facet)
    except WindowContourError:
        raise
    except Exception as error:
        raise invalid("contour-operation-failed") from error
    return CompletedWindowSpan(host, contour, original, PaintClip((left, top, plot_width, plot_height)))
