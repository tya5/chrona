"""Owns named-period band geometry and label requests; reads the View-selected periods, the completed scale and the Theme treatment (#582)."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.labels import LabelRect, LabelRequest
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_base import SurfaceBaseGeometry
from chrona.presentation.layout.surface_geometry import coordinate_for_date, extend_to_plot_edges
from chrona.presentation.layout.surface_quality import CollisionDomain, ShapePlacement
from chrona.presentation.model.projection import ReviewPeriod

# Label placement to the shared label engine's side, about an anchor on the plot edge or the band itself.
_LABEL_SIDE = {"top": "below", "bottom": "above", "inside": "inside"}


@dataclass(frozen=True)
class PeriodBandBatch:
    """Completed band shapes in selection order, the extent of every period that has one, and the diagnostics.

    ``extents`` holds one ``(period, inline start, inline end)`` per period with a drawable extent, whether or
    not the Theme paints a band for it: a label belongs to the extent, not to the paint.
    """

    shapes: tuple[ShapePlacement, ...]
    diagnostics: tuple[str, ...]
    extents: tuple[tuple[ReviewPeriod, float, float], ...] = ()


def compose_period_bands(*, base: SurfaceBaseGeometry, theme_tokens: Any, periods: tuple[ReviewPeriod, ...],
                         window: tuple[Any, Any]) -> PeriodBandBatch:
    """Complete one Rect per drawable selected period across the plot's rows.

    A period is the half-open range ``[start, end)`` clipped to the View window and mapped through the same
    scale that places marks; its block extent is the timeline slot, as the calendar closure's is. A period with
    no extent left after clipping draws nothing and is recorded, never silently dropped. The band is a
    background: it never enters the obstacle index.
    """
    if not periods:
        return PeriodBandBatch((), ())
    window_start, window_end = window
    plot = base.plot
    plot_left, plot_right = float(plot.inline), float(plot.inline + plot.inline_size)
    shapes: list[ShapePlacement] = []
    extents: list[tuple[ReviewPeriod, float, float]] = []
    diagnostics: list[str] = []
    for period in periods:
        # The selected role is required before clipping, as for the unsuffixed role.
        treatment, paint_order = theme_tokens.background(period.band_role)
        # Edge metadata (including required role paint and gap tokens) is a Theme
        # contract and is validated before clipping, even for an off-window period.
        theme_tokens.period_edge_rules(period.band_role)
        start, end = max(period.start, window_start), min(period.end, window_end)
        left = right = 0.0
        if start < end:
            left = max(coordinate_for_date(start, base.scale), plot_left)
            right = min(coordinate_for_date(end, base.scale), plot_right)
        if left < right:
            left, right = extend_to_plot_edges(left, right, scale=base.scale, plot=plot)
        if not left < right:
            diagnostics.append(f"I_LAYOUT_PERIOD_OUTSIDE_WINDOW:{period.period_id}")
            continue
        extents.append((period, left, right))
        bounds = Rect(Decimal(str(left)), plot.block, Decimal(str(right - left)), plot.block_size)
        shapes.extend(compose_period_decoration(
            bounds=bounds, placement_id=f"period-band:{period.period_id}",
            source_ref=period.period_id, visual_role=period.band_role,
            slot_id="timeline", paint_order=paint_order, theme_tokens=theme_tokens))
    return PeriodBandBatch(tuple(shapes), tuple(diagnostics), tuple(extents))


def compose_period_edge_paths(*, bounds: Rect, placement_id: str, source_ref: str,
                              visual_role: str, slot_id: str, paint_order: int,
                              theme_tokens: Any,
                              semantic_id: str = "periodBand") -> tuple[ShapePlacement, ...]:
    """Complete separate, stroke-only paths for a selected period edge treatment.

    The input rectangle is already clipped and Layout-owned. Theme metadata is
    re-read here for reuse by period legend swatches; chart composition also
    validates it before clipping so malformed declarations cannot hide offscreen.
    """
    rules = theme_tokens.period_edge_rules(visual_role)
    if rules is None:
        return ()
    width = rules.stroke_width
    gap = rules.double_rule_gap or Decimal(0)
    left, top = bounds.inline, bounds.block
    right, bottom = left + bounds.inline_size, top + bounds.block_size
    inline_size, block_size = bounds.inline_size, bounds.block_size

    depths = {side: (width if rule == "single" else 2 * width + gap)
              for side, rule in rules.edges}
    required_inline = depths.get("start", Decimal(0)) + depths.get("end", Decimal(0))
    required_block = depths.get("top", Decimal(0)) + depths.get("bottom", Decimal(0))
    tangent_fits = (
        all((block_size if side in {"start", "end"} else inline_size) > width
            for side, _rule in rules.edges)
    )
    if (not tangent_fits or required_inline > inline_size or required_block > block_size):
        raise LayoutError(
            "E_LAYOUT_PERIOD_EDGE_SIZE", f"/body/roles/{visual_role}/edgeRules",
            detail=(f"{placement_id}: clipped={inline_size}x{block_size}; "
                    f"required inward inline={required_inline}, block={required_block}; "
                    f"tangential extent must exceed stroke width {width}"))

    paths: list[ShapePlacement] = []
    for side, rule in rules.edges:
        offsets = (width / 2, 3 * width / 2 + gap) if rule == "double" else (width / 2,)
        for line_index, offset in enumerate(offsets):
            if side == "top":
                y = top + offset
                start, end = left + width / 2, right - width / 2
                bounds_for_path = Rect(start, y, end - start, Decimal(0))
                points = ((float(start), float(y)), (float(end), float(y)))
            elif side == "bottom":
                y = bottom - offset
                start, end = left + width / 2, right - width / 2
                bounds_for_path = Rect(start, y, end - start, Decimal(0))
                points = ((float(start), float(y)), (float(end), float(y)))
            elif side == "start":
                x = left + offset
                start, end = top + width / 2, bottom - width / 2
                bounds_for_path = Rect(x, start, Decimal(0), end - start)
                points = ((float(x), float(start)), (float(x), float(end)))
            else:  # end
                x = right - offset
                start, end = top + width / 2, bottom - width / 2
                bounds_for_path = Rect(x, start, Decimal(0), end - start)
                points = ((float(x), float(start)), (float(x), float(end)))
            paths.append(ShapePlacement(
                f"period-edge:{len(placement_id)}:{placement_id}:{side}:{line_index}",
                source_ref, "Path",
                bounds_for_path, points, slot_id=slot_id, paint_order=paint_order,
                semantic_id=semantic_id, visual_role=visual_role,
                paint_channels="stroke"))
    return tuple(paths)


def compose_period_decoration(*, bounds: Rect, placement_id: str, source_ref: str,
                              visual_role: str, slot_id: str, paint_order: int,
                              theme_tokens: Any,
                              semantic_id: str = "periodBand") -> tuple[ShapePlacement, ...]:
    """Complete the shared period background host and optional edge paths.

    An unruled band preserves its historical single Rect. Ruled fill bands use
    a fill-only host and ruled outlines have paths only; this helper is also the
    source-bound legend swatch completion seam.
    """
    treatment, resolved_order = theme_tokens.background(visual_role)
    rules = theme_tokens.period_edge_rules(visual_role)
    order = paint_order if paint_order is not None else resolved_order
    if treatment == "none":
        return ()
    if rules is None:
        return (ShapePlacement(placement_id, source_ref, "Rect", bounds,
                               slot_id=slot_id, paint_order=order,
                               semantic_id=semantic_id, visual_role=visual_role),)

    host: tuple[ShapePlacement, ...] = ()
    if treatment == "fill":
        host = (ShapePlacement(placement_id, source_ref, "Rect", bounds,
                               slot_id=slot_id, paint_order=order,
                               semantic_id=semantic_id, visual_role=visual_role,
                               paint_channels="fill"),)
    paths = compose_period_edge_paths(
        bounds=bounds, placement_id=placement_id, source_ref=source_ref,
        visual_role=visual_role, slot_id=slot_id, paint_order=order,
        theme_tokens=theme_tokens, semantic_id=semantic_id)
    return (*host, *paths)


def period_label_requests(extents: tuple[tuple[ReviewPeriod, float, float], ...],
                          plot: tuple[float, float, float, float], theme_tokens: Any) -> tuple[LabelRequest, ...]:
    """One label request per labelled period, for the shared label engine.

    ``top`` and ``bottom`` anchor a zero-height strip on the plot edge so the engine's ``below`` and ``above``
    geometry centres the label on the band against that edge; ``inside`` anchors the band itself. The engine
    owns the obstacle search, the chip, and the suppression and overflow records.
    """
    left, top, width, height = plot
    requests = []
    for period, band_left, band_right in extents:
        if period.label_placement is None:
            continue
        if not theme_tokens.has_role(period.label_role):
            raise LayoutError("E_THEME_ROLE_REQUIRED", f"/body/roles/{period.label_role}")
        anchor = LabelRect(band_left, top + (height if period.label_placement == "bottom" else 0.0),
                           band_right - band_left, height if period.label_placement == "inside" else 0.0)
        requests.append(LabelRequest(
            f"period-label:{period.period_id}", period.period_id, period.title, anchor,
            (_LABEL_SIDE[period.label_placement],), period.label_role, period.label_role,
            CollisionDomain("timeline", "overlay"), period.label_overflow,
            bounds=LabelRect(left, top, width, height), semantic_id="periodLabel"))
    return tuple(requests)
