"""Deterministic placement closure for a typed dependency-network projection."""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.routing import place_relation_route, relation_route_quality
from chrona.presentation.layout.surface_quality import RelationPlacement


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
    nodes: tuple[NetworkNodePlacement, ...]
    relations: tuple[RelationPlacement, ...]


def compose_dependency_network_layout(network: Any, *, bounds: Rect, node_inline: Decimal,
                                      node_block: Decimal, max_bends: int = 4,
                                      max_detour_ratio: float = 2.0) -> DependencyNetworkLayout:
    """Rank and route a closed View graph; Project and Scheduler never enter here."""
    nodes = tuple(network.nodes)
    ids = {node.object_id for node in nodes}
    edges = tuple(network.edges)
    if len(ids) != len(nodes) or any(edge.source_id not in ids or edge.target_id not in ids for edge in edges):
        raise LayoutError("E_LAYOUT_NETWORK_GRAPH", "/projection/network")
    incoming = {node.object_id: [] for node in nodes}
    outgoing = {node.object_id: [] for node in nodes}
    for edge in edges:
        incoming[edge.target_id].append(edge.source_id)
        outgoing[edge.source_id].append(edge.target_id)
    ready = sorted((node.object_id for node in nodes if not incoming[node.object_id]))
    ranks, seen = {node_id: 0 for node_id in ready}, []
    while ready:
        node_id = ready.pop(0); seen.append(node_id)
        for target in sorted(outgoing[node_id]):
            ranks[target] = max(ranks.get(target, 0), ranks[node_id] + 1)
            incoming[target].remove(node_id)
            if not incoming[target]:
                ready.append(target)
        ready.sort()
    if len(seen) != len(nodes):
        raise LayoutError("E_LAYOUT_NETWORK_CYCLE", "/projection/network")
    ordered = sorted(nodes, key=lambda node: (ranks[node.object_id], node.order_key, node.object_id))
    by_rank: dict[int, list[Any]] = {}
    for node in ordered:
        by_rank.setdefault(ranks[node.object_id], []).append(node)
    rank_count = max(ranks.values(), default=0) + 1
    inline_gap = (bounds.inline_size - node_inline * rank_count) / Decimal(max(1, rank_count + 1))
    if inline_gap <= 0 or node_block <= 0 or node_inline <= 0:
        raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", "/layoutManifest/network")
    placements = []
    for rank, members in sorted(by_rank.items()):
        total = node_block * len(members)
        block_gap = (bounds.block_size - total) / Decimal(max(1, len(members) + 1))
        if block_gap <= 0:
            raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", "/layoutManifest/network")
        for index, node in enumerate(members, 1):
            rect = Rect(bounds.inline + inline_gap * (rank + 1) + node_inline * rank,
                        bounds.block + block_gap * index + node_block * (index - 1), node_inline, node_block)
            center = float(rect.block + rect.block_size / 2)
            placements.append(NetworkNodePlacement(node.object_id, rank, rect,
                (float(rect.inline), center), (float(rect.inline + rect.inline_size), center), node.critical))
    by_id = {node.object_id: node for node in placements}
    obstacles = tuple((float(node.bounds.inline), float(node.bounds.block), float(node.bounds.inline + node.bounds.inline_size),
                       float(node.bounds.block + node.bounds.block_size)) for node in placements)
    relations = []
    for edge in edges:
        source, target = by_id[edge.source_id], by_id[edge.target_id]
        try:
            points = place_relation_route(source_port=source.output_port, target_port=target.input_port,
                                          obstacles=tuple(box for box in obstacles if box not in {
                                              (float(source.bounds.inline), float(source.bounds.block), float(source.bounds.inline + source.bounds.inline_size), float(source.bounds.block + source.bounds.block_size)),
                                              (float(target.bounds.inline), float(target.bounds.block), float(target.bounds.inline + target.bounds.inline_size), float(target.bounds.block + target.bounds.block_size))}),
                                          bounds=(float(bounds.inline), float(bounds.block), float(bounds.inline + bounds.inline_size), float(bounds.block + bounds.block_size)))
        except ValueError as error:
            raise LayoutError("E_LAYOUT_NETWORK_UNROUTABLE", f"/projection/network/edges/{edge.relation_id}") from error
        if not relation_route_quality(points, max_bends=max_bends, max_detour_ratio=max_detour_ratio):
            raise LayoutError("E_LAYOUT_NETWORK_UNROUTABLE", f"/projection/network/edges/{edge.relation_id}")
        relations.append(RelationPlacement(edge.relation_id, f"{edge.source_id}:output", f"{edge.target_id}:input", points,
                                           semantic_id="dependency-critical" if edge.critical else "dependency"))
    return DependencyNetworkLayout(tuple(placements), tuple(relations))
