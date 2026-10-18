"""Complete compound-network bands from closed selected containment facts."""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from decimal import Decimal

from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.surface_quality import GroupPlacement
from chrona.presentation.model.projection import DependencyNetworkNode


def place_network_bands(
    nodes: Sequence[DependencyNetworkNode], *, ranks: Mapping[str, int],
    sizes: Mapping[str, tuple[Decimal, Decimal]],
    insets: Mapping[str, tuple[Decimal, Decimal]], bounds: Rect,
    gap: Decimal, horizontal: bool,
) -> tuple[dict[str, Rect], tuple[GroupPlacement, ...]]:
    """Keep unrelated containers disjoint without reranking semantic edges.

    Direct ordinary children share the existing rank-packed band. Nested
    containers receive separate bands; their headers are reserved before
    content. This module knows no Project syntax, font metrics or Scene.
    """
    by_id = {node.object_id: node for node in nodes}
    children: dict[str | None, list[DependencyNetworkNode]] = defaultdict(list)
    for node in nodes:
        parent = node.container_id
        if parent is not None and (parent not in by_id or not by_id[parent].is_container):
            raise LayoutError("E_LAYOUT_NETWORK_GRAPH", "/projection/network",
                              detail="container_id must name a selected group")
        children[parent].append(node)
    for siblings in children.values():
        siblings.sort(key=lambda node: (node.order_key, node.object_id))

    primary, cross = (0, 1) if horizontal else (1, 0)
    rank_extent: dict[int, Decimal] = {}
    for node in nodes:
        if not node.is_container or not children[node.object_id]:
            rank = ranks[node.object_id]
            rank_extent[rank] = max(rank_extent.get(rank, Decimal(0)), sizes[node.object_id][primary])
    starts: dict[int, Decimal] = {}
    cursor = (bounds.inline if horizontal else bounds.block) + gap
    for rank in sorted(rank_extent):
        starts[rank] = cursor
        cursor += rank_extent[rank] + gap

    def ordinary(parent: str | None) -> dict[int, list[DependencyNetworkNode]]:
        result: dict[int, list[DependencyNetworkNode]] = defaultdict(list)
        for node in children[parent]:
            if not node.is_container:
                result[ranks[node.object_id]].append(node)
        return result

    def ordinary_demand(parent: str | None) -> Decimal:
        return max((sum((sizes[node.object_id][cross] for node in siblings), Decimal(0))
                    + gap * (len(siblings) - 1) for siblings in ordinary(parent).values()), default=Decimal(0))

    demands: dict[str, Decimal] = {}

    def content_demand(parent: str | None) -> Decimal:
        parts = [ordinary_demand(parent)]
        parts.extend(group_demand(node) for node in children[parent] if node.is_container)
        occupied = [part for part in parts if part > 0]
        return sum(occupied, Decimal(0)) + gap * max(0, len(occupied) - 1)

    def group_demand(node: DependencyNetworkNode) -> Decimal:
        if node.object_id in demands:
            return demands[node.object_id]
        inline_pad, block_pad = insets[node.object_id]
        content = content_demand(node.object_id) if children[node.object_id] else sizes[node.object_id][cross]
        value = (sizes[node.object_id][1] + 2 * block_pad + content if horizontal
                 else max(sizes[node.object_id][0], content + 2 * inline_pad))
        demands[node.object_id] = value
        return value

    content_demand(None)
    boxes: dict[str, Rect] = {}
    groups: list[GroupPlacement] = []

    def place_children(parent: str | None, cross_start: Decimal, primary_inset: Decimal) -> None:
        for rank, siblings in ordinary(parent).items():
            cursor = cross_start
            for node in siblings:
                width, height = sizes[node.object_id]
                main = starts[rank] + primary_inset
                boxes[node.object_id] = (Rect(main, cursor, width, height) if horizontal
                                         else Rect(cursor, main, width, height))
                cursor += sizes[node.object_id][cross] + gap
        used = ordinary_demand(parent)
        cursor = cross_start + used + (gap if used > 0 else 0)
        for node in children[parent]:
            if not node.is_container:
                continue
            inline_pad, block_pad = insets[node.object_id]
            width, header_height = sizes[node.object_id]
            content = (content_demand(node.object_id) if children[node.object_id]
                       else sizes[node.object_id][cross])
            child_start = cursor + (header_height + block_pad if horizontal else inline_pad)
            child_inset = primary_inset + (inline_pad if horizontal else header_height + block_pad)
            place_children(node.object_id, child_start, child_inset)
            members = [boxes[child.object_id] for child in children[node.object_id]]
            if horizontal:
                left = (min(item.inline for item in members) - inline_pad if members
                        else starts[ranks[node.object_id]] + primary_inset)
                right = max((item.inline + item.inline_size + inline_pad for item in members),
                            default=left + width)
                width = max(width, right - left)
                outer = Rect(left, cursor, width, demands[node.object_id])
                header = Rect(left, cursor, width, header_height)
                area = Rect(left + inline_pad, child_start, width - 2 * inline_pad, content)
            else:
                top = (min(item.block for item in members) - header_height - block_pad if members
                       else starts[ranks[node.object_id]] + primary_inset)
                bottom = max((item.block + item.block_size + block_pad for item in members),
                             default=top + 2 * header_height + 2 * block_pad)
                outer = Rect(cursor, top, demands[node.object_id], bottom - top)
                header = Rect(cursor, top, outer.inline_size, header_height)
                area = Rect(cursor + inline_pad, top + header_height + block_pad,
                            outer.inline_size - 2 * inline_pad, bottom - top - header_height - block_pad)
            boxes[node.object_id] = outer
            groups.append(GroupPlacement(node.object_id, area, header))
            cursor += demands[node.object_id] + gap

    place_children(None, (bounds.block if horizontal else bounds.inline) + gap, Decimal(0))
    if boxes.keys() != by_id.keys():
        raise LayoutError("E_LAYOUT_NETWORK_GRAPH", "/projection/network",
                          detail="selected containment must be acyclic and rooted")
    return boxes, tuple(groups)
