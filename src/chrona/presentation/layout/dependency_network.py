"""Deterministic, measured placement closure for a dependency-network View."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Mapping

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.routing import place_relation_route, relation_route_quality
from chrona.presentation.layout.sources import MeasuredSources, MeasuredTextRun
from chrona.presentation.layout.surface_quality import RelationPlacement, TextPlacement, intersects


@dataclass(frozen=True)
class NetworkNodePlacement:
    object_id: str
    rank: int
    bounds: Rect
    input_port: tuple[float, float]
    output_port: tuple[float, float]
    critical: bool


@dataclass(frozen=True)
class DependencyNetworkLayout:
    """Layout-owned node, text, and relation closure consumed by Scene."""

    nodes: tuple[NetworkNodePlacement, ...]
    text: tuple[TextPlacement, ...]
    relations: tuple[RelationPlacement, ...]


def compose_dependency_network_layout(network: Any, *, bounds: Rect,
                                      measured_sources: MeasuredSources,
                                      writing_mode: str,
                                      max_bends: int = 4,
                                      max_detour_ratio: float = 2.0) -> DependencyNetworkLayout:
    """Place a typed View graph without reading Project, View syntax, or Scene state."""
    nodes, edges = tuple(network.nodes), tuple(network.edges)
    ids = {node.object_id for node in nodes}
    if not nodes or len(ids) != len(nodes) or any(edge.source_id not in ids or edge.target_id not in ids for edge in edges):
        raise LayoutError("E_LAYOUT_NETWORK_GRAPH", "/projection/network")
    if writing_mode not in {"horizontal-tb", "vertical-rl", "vertical-lr"}:
        raise LayoutError("E_LAYOUT_NETWORK_WRITING_MODE", "/layoutManifest/writingMode")
    metric = measured_sources.metric_values
    try:
        min_inline = metric["network.node.minInlineSize"]
        min_block = metric["network.node.minBlockSize"]
        gap = metric["network.rank.gap"]
    except KeyError as error:
        raise LayoutError("E_LAYOUT_METRIC_REQUIRED", "/body/metrics/network") from error
    if min_inline <= 0 or min_block <= 0 or gap < 0:
        raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", "/layoutManifest/network")
    measured = _node_measurements(nodes, measured_sources)
    ranks = _ranks(nodes, edges)
    by_rank: dict[int, list[Any]] = {}
    for node in sorted(nodes, key=lambda item: (ranks[item.object_id], item.order_key, item.object_id)):
        by_rank.setdefault(ranks[node.object_id], []).append(node)
    placed = _place_nodes(by_rank, ranks, measured, bounds, min_inline, min_block, gap,
                          writing_mode == "horizontal-tb")
    text = tuple(_place_node_text(node, measured[node.object_id]) for node in placed)
    _assert_node_quality(placed, text, bounds)
    return DependencyNetworkLayout(tuple(placed), text,
                                   _route_edges(edges, placed, bounds, max_bends, max_detour_ratio))


def _node_measurements(nodes: tuple[Any, ...], measured_sources: MeasuredSources) -> Mapping[str, MeasuredTextRun]:
    found = {item.source_ref: item for item in measured_sources.run_measurements.get("network", ())
             if item.source_ref is not None}
    missing = sorted(node.object_id for node in nodes if node.object_id not in found)
    if missing:
        raise LayoutError("E_LAYOUT_NETWORK_MEASUREMENT", "/measuredSources/network/" + missing[0])
    return found


def _ranks(nodes: tuple[Any, ...], edges: tuple[Any, ...]) -> Mapping[str, int]:
    incoming = {node.object_id: [] for node in nodes}
    outgoing = {node.object_id: [] for node in nodes}
    for edge in edges:
        incoming[edge.target_id].append(edge.source_id)
        outgoing[edge.source_id].append(edge.target_id)
    ready = sorted(node.object_id for node in nodes if not incoming[node.object_id])
    ranks, seen = {node_id: 0 for node_id in ready}, []
    while ready:
        node_id = ready.pop(0)
        seen.append(node_id)
        for target in sorted(outgoing[node_id]):
            ranks[target] = max(ranks.get(target, 0), ranks[node_id] + 1)
            incoming[target].remove(node_id)
            if not incoming[target]:
                ready.append(target)
        ready.sort()
    if len(seen) != len(nodes):
        raise LayoutError("E_LAYOUT_NETWORK_CYCLE", "/projection/network")
    return ranks


def _place_nodes(by_rank: Mapping[int, list[Any]], ranks: Mapping[str, int],
                 measured: Mapping[str, MeasuredTextRun], bounds: Rect,
                 min_inline: Decimal, min_block: Decimal, gap: Decimal,
                 horizontal: bool) -> list[NetworkNodePlacement]:
    dimensions = {node.object_id: (max(min_inline, measured[node.object_id].inline_size),
                                   max(min_block, measured[node.object_id].block_size))
                  for members in by_rank.values() for node in members}
    rank_ids = tuple(sorted(by_rank))
    extent = {rank: max(dimensions[node.object_id][0 if horizontal else 1] for node in members)
              for rank, members in by_rank.items()}
    primary_size = bounds.inline_size if horizontal else bounds.block_size
    if sum(extent.values(), gap * (len(rank_ids) + 1)) > primary_size:
        raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", "/layoutManifest/network")
    starts, cursor = {}, (bounds.inline if horizontal else bounds.block) + gap
    for rank in rank_ids:
        starts[rank] = cursor
        cursor += extent[rank] + gap
    result: list[NetworkNodePlacement] = []
    secondary_origin = bounds.block if horizontal else bounds.inline
    secondary_size = bounds.block_size if horizontal else bounds.inline_size
    for rank in rank_ids:
        members = by_rank[rank]
        cross_total = sum((dimensions[node.object_id][1 if horizontal else 0] for node in members), Decimal(0))
        if cross_total + gap * (len(members) + 1) > secondary_size:
            raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", "/layoutManifest/network")
        cursor = secondary_origin + gap
        for node in members:
            inline_size, block_size = dimensions[node.object_id]
            if horizontal:
                rect = Rect(starts[rank], cursor, inline_size, block_size)
                cursor += block_size + gap
                input_port = (float(rect.inline), float(rect.block + rect.block_size / 2))
                output_port = (float(rect.inline + rect.inline_size), float(rect.block + rect.block_size / 2))
            else:
                rect = Rect(cursor, starts[rank], inline_size, block_size)
                cursor += inline_size + gap
                input_port = (float(rect.inline + rect.inline_size / 2), float(rect.block))
                output_port = (float(rect.inline + rect.inline_size / 2), float(rect.block + rect.block_size))
            result.append(NetworkNodePlacement(node.object_id, ranks[node.object_id], rect,
                                                input_port, output_port, node.critical))
    return result


def _place_node_text(node: NetworkNodePlacement, measured: MeasuredTextRun) -> TextPlacement:
    inline = node.bounds.inline + (node.bounds.inline_size - measured.inline_size) / 2
    baseline = node.bounds.block + (node.bounds.block_size - measured.block_size) / 2 + measured.baseline
    return TextPlacement(
        f"network-label:{node.object_id}", node.object_id, measured.content,
        Rect(inline, baseline - Decimal(str(measured.font_size)), measured.inline_size, measured.block_size),
        measured.typography_role, baseline=(float(inline), float(baseline)), lines=(measured.content,),
        font_family=measured.font_family, font_weight=measured.font_weight,
        font_size=measured.font_size, line_height=measured.line_height,
        font_asset_identity=measured.font_asset_identity, collision_region="network")


def _route_edges(edges: tuple[Any, ...], nodes: list[NetworkNodePlacement], bounds: Rect,
                 max_bends: int, max_detour_ratio: float) -> tuple[RelationPlacement, ...]:
    by_id = {node.object_id: node for node in nodes}
    boxes = {node.object_id: _box(node.bounds) for node in nodes}
    relations = []
    for edge in edges:
        source, target = by_id[edge.source_id], by_id[edge.target_id]
        try:
            points = place_relation_route(source_port=source.output_port, target_port=target.input_port,
                                          obstacles=tuple(box for node_id, box in boxes.items()
                                                          if node_id not in {source.object_id, target.object_id}),
                                          bounds=(float(bounds.inline), float(bounds.block),
                                                  float(bounds.inline + bounds.inline_size),
                                                  float(bounds.block + bounds.block_size)))
        except ValueError as error:
            raise LayoutError("E_LAYOUT_NETWORK_UNROUTABLE", f"/projection/network/edges/{edge.relation_id}") from error
        if not relation_route_quality(points, max_bends=max_bends, max_detour_ratio=max_detour_ratio):
            raise LayoutError("E_LAYOUT_NETWORK_UNROUTABLE", f"/projection/network/edges/{edge.relation_id}")
        relations.append(RelationPlacement(edge.relation_id, f"{edge.source_id}:output", f"{edge.target_id}:input",
                                           tuple(points), semantic_id="dependency-critical" if edge.critical else "dependency"))
    return tuple(relations)


def _assert_node_quality(nodes: list[NetworkNodePlacement], text: tuple[TextPlacement, ...], bounds: Rect) -> None:
    for index, node in enumerate(nodes):
        if not _contains(bounds, node.bounds) or node.input_port == node.output_port:
            raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", "/layoutManifest/network")
        if any(intersects(node.bounds, other.bounds) for other in nodes[index + 1:]):
            raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", "/layoutManifest/network")
    for label, node in zip(text, nodes, strict=True):
        if not _contains(node.bounds, label.bounds) or not _contains(bounds, label.bounds):
            raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", f"/projection/network/nodes/{node.object_id}")


def _contains(outer: Rect, inner: Rect) -> bool:
    return (outer.inline <= inner.inline and outer.block <= inner.block and
            inner.inline + inner.inline_size <= outer.inline + outer.inline_size and
            inner.block + inner.block_size <= outer.block + outer.block_size)


def _box(rect: Rect) -> tuple[float, float, float, float]:
    return (float(rect.inline), float(rect.block),
            float(rect.inline + rect.inline_size), float(rect.block + rect.block_size))
