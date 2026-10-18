"""Measured intrinsic/authored legend closure for dependency-network surfaces."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from typing import Any, Callable, Mapping

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.network_ink import relation_paint_bounds
from chrona.presentation.layout.sources import measure_sources
from chrona.presentation.layout.surface_legend import (
    LegendArrangement, SurfaceLegendBatch, SurfaceLegendContext,
    legend_item_gap, legend_source_input, place_legend,
)
from chrona.presentation.layout.surface_quality import RelationPlacement, SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.layout.text import metric_for_role
from chrona.presentation.model.surface_content import SurfaceLegendEntry


_INTRINSIC_SLOT_ID = "network-intrinsic-legend"


@dataclass(frozen=True)
class NetworkLegendPlan:
    """Prepared graph allocation and its one authored or intrinsic legend child."""

    request: SurfaceLayoutRequest
    graph_slot: SlotPlacement
    legend_slot: SlotPlacement | None
    intrinsic: bool
    block_gap: Decimal
    heading_block: Decimal
    metric_values: Mapping[str, Any]
    metric_for: Callable[[str], Any]


def prepare_network_legend(request: SurfaceLayoutRequest, network_slot: SlotPlacement,
                           authored_legend_slot: SlotPlacement | None, *,
                           heading_block: Decimal = Decimal(0)) -> NetworkLegendPlan:
    """Reserve a measured intrinsic critical key or retain the one authored legend slot.

    The normalized content is authoritative: this function neither discovers a
    critical edge nor synthesizes a key. Without an authored slot, unrelated
    Detail candidates are excluded from the intrinsic band.
    """
    content = request.surface_content
    entries = tuple(content.legend_entries)
    critical_entries = tuple(entry for entry in entries if entry.role == "critical-edge")
    if authored_legend_slot is not None:
        candidates = entries
        legend_slot = authored_legend_slot if candidates else None
        intrinsic = False
        graph_slot = network_slot
        block_gap = Decimal(str(legend_item_gap(
            authored_legend_slot.gap,
            float(request.theme_tokens.text_treatment("legend").font_size),
        )))
    elif critical_entries:
        candidates = critical_entries
        intrinsic = True
        metric_values = request.measured_sources.metric_values
        arrangement = LegendArrangement(direction="inline")
        source = legend_source_input(
            candidates, tokens=request.theme_tokens,
            # Critical-edge entries are line swatches, so mark geometry does
            # not participate in their measurement.
            mark_block_size=0.0,
            font_metrics=request.font_metrics, arrangement=arrangement)
        measured = measure_sources(
            {"legend": source}, request.theme_tokens.resolved_theme,
            font_metrics=request.font_metrics, resolved_metrics=metric_values,
        ).measurements["legend"]
        band_block = measured.preferred_block
        block_gap = Decimal(str(legend_item_gap(None, float(request.theme_tokens.text_treatment("legend").font_size))))
        graph_block = max(Decimal(0), network_slot.bounds.block_size - band_block - block_gap)
        legend_block = network_slot.bounds.block + graph_block + block_gap
        graph_slot = replace(network_slot, bounds=Rect(
            network_slot.bounds.inline, network_slot.bounds.block,
            network_slot.bounds.inline_size, graph_block))
        used_ids = {item.node_id for item in request.layout_manifest.decisions}
        slot_id, suffix = _INTRINSIC_SLOT_ID, 2
        while slot_id in used_ids:
            slot_id = f"{_INTRINSIC_SLOT_ID}-{suffix}"
            suffix += 1
        legend_slot = SlotPlacement(
            slot_id, "legend",
            Rect(network_slot.bounds.inline, legend_block,
                 network_slot.bounds.inline_size, band_block),
            direction="inline",
        )
    else:
        candidates = ()
        intrinsic = False
        graph_slot = network_slot
        legend_slot = None
        block_gap = Decimal(0)

    filtered = replace(content, legend_entries=candidates)
    planned_request = replace(request, surface_content=filtered)
    return NetworkLegendPlan(
        planned_request, graph_slot, legend_slot, intrinsic,
        block_gap, heading_block if authored_legend_slot is not None else Decimal(0),
        request.measured_sources.metric_values,
        lambda role: metric_for_role(request.theme_tokens, role, request.font_metrics),
    )


def complete_network_legend(plan: NetworkLegendPlan, relations: tuple[RelationPlacement, ...],
                            occupied_rects: tuple[Rect, ...]) -> SurfaceLegendBatch | None:
    """Place one legend after routing, moving it only when actual graph ink overlaps it."""
    slot = plan.legend_slot
    if slot is None:
        return None
    has_visible_critical_edge = any(
        relation.semantic_id == "criticalEdge" and not relation.suppressed
        and any(start != end for start, end in zip(relation.points, relation.points[1:]))
        for relation in relations)
    entries = tuple(plan.request.surface_content.legend_entries)
    if plan.intrinsic and not has_visible_critical_edge:
        return None
    if not has_visible_critical_edge:
        entries = tuple(entry for entry in entries if entry.role != "critical-edge")
        if not entries:
            return None
    if entries != plan.request.surface_content.legend_entries:
        request = replace(plan.request,
                          surface_content=replace(plan.request.surface_content, legend_entries=entries))
    else:
        request = plan.request

    collision_band = slot.bounds
    if not plan.intrinsic and plan.heading_block:
        collision_band = Rect(
            slot.bounds.inline, slot.bounds.block - plan.heading_block,
            slot.bounds.inline_size, slot.bounds.block_size + plan.heading_block,
        )
    overlapping = tuple(rect for rect in occupied_rects if _overlaps(collision_band, rect))
    if overlapping:
        # Flow below the grown graph, not merely the first intersecting node:
        # moving past that node must not land on a later row or route.
        block = max(rect.block + rect.block_size for rect in occupied_rects)
        slot = replace(slot, bounds=Rect(
            slot.bounds.inline, block + plan.block_gap + plan.heading_block,
            slot.bounds.inline_size, slot.bounds.block_size))

    batch = place_legend(SurfaceLegendContext(request, slot, plan.metric_values, plan.metric_for))
    return replace(batch, relations=tuple(replace(relation,
        paint_bounds=relation_paint_bounds(relation, request.theme_tokens)) for relation in batch.relations))


def _overlaps(left: Rect, right: Rect) -> bool:
    return (left.inline < right.inline + right.inline_size
            and right.inline < left.inline + left.inline_size
            and left.block < right.block + right.block_size
            and right.block < left.block + left.block_size)


