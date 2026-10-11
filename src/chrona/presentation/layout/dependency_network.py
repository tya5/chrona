"""Deterministic, measured placement closure for a dependency-network View."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from itertools import chain
from typing import Any, Mapping

from chrona.presentation.layout.canvas_viewport import CanvasViewportWarning, canvas_viewport_warning
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.pattern_placement import PatternedPlacement, complete_pattern_placement
from chrona.presentation.layout.stroke_alignment import complete_aligned_strokes
from chrona.presentation.layout.surface_quality import AlignedStrokePlacement, ShapePlacement
from chrona.presentation.layout.routing import place_relation_route, relation_route_quality
from chrona.presentation.layout.sources import MeasuredSources, MeasuredTextRun
from chrona.presentation.layout.canvas_texture import CanvasTexture, complete_canvas_texture
from chrona.presentation.layout.canvas_overlays import CanvasOverlays, complete_canvas_overlays
from chrona.presentation.layout.surface_quality import CollisionDomain, FitWarning, RelationPlacement, TextPlacement, intersects
from chrona.presentation.layout.surface_quality import SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.layout.slot_heading import complete_slot_headings, content_slot
from chrona.presentation.layout.surface_heading import place_surface_headings


@dataclass(frozen=True)
class NetworkNodePlacement:
    object_id: str
    rank: int
    bounds: Rect
    input_port: tuple[float, float]
    output_port: tuple[float, float]
    critical: bool
    slot_id: str = "network"
    paint_order: int = 200

    @property
    def placement_id(self) -> str:
        return f"network-node:{self.object_id}"


@dataclass(frozen=True)
class DependencyNetworkLayout:
    """Layout-owned node, text, and relation closure consumed by Scene."""

    nodes: tuple[NetworkNodePlacement, ...]
    text: tuple[TextPlacement, ...]
    relations: tuple[RelationPlacement, ...]
    canvas_bounds: Rect
    fit_warnings: tuple[FitWarning, ...] = ()
    patterns: tuple[PatternedPlacement, ...] = ()
    texture: CanvasTexture | None = None
    aligned_strokes: tuple[AlignedStrokePlacement, ...] = ()
    diagnostics: tuple[str, ...] = ()
    canvas_overlays: CanvasOverlays | None = None
    canvas_warning: CanvasViewportWarning | None = None


def compose_dependency_network_layout(network: Any, *, title_bounds: Rect | None, bounds: Rect,
                                      measured_sources: MeasuredSources,
                                      flow_direction: str,
                                      max_bends: int = 4,
                                      max_detour_ratio: float = 2.0,
                                      canvas_bounds: Rect | None = None,
                                      theme_tokens: Any | None = None,
                                      route_bounds: Rect | None = None,
                                      heading_text: tuple[TextPlacement, ...] | None = None) -> DependencyNetworkLayout:
    """Place a typed View graph without reading Project, View syntax, or Scene state."""
    nodes, edges = tuple(network.nodes), tuple(network.edges)
    ids = {node.object_id for node in nodes}
    if not nodes or len(ids) != len(nodes) or any(edge.source_id not in ids or edge.target_id not in ids for edge in edges):
        raise LayoutError("E_LAYOUT_NETWORK_GRAPH", "/projection/network")
    if flow_direction not in {"horizontal", "vertical-rl", "vertical-lr"}:
        raise LayoutError("E_LAYOUT_NETWORK_FLOW_DIRECTION", "/layoutManifest/dependencyNetworkFlowDirection")
    metric = measured_sources.metric_values
    try:
        min_inline = metric["network.node.minInlineSize"]
        min_block = metric["network.node.minBlockSize"]
        gap = metric["network.rank.gap"]
    except KeyError as error:
        raise LayoutError("E_LAYOUT_METRIC_REQUIRED", "/body/metrics/network") from error
    if min_inline <= 0 or min_block <= 0 or gap < 0:
        raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", "/layoutManifest/network")
    title_placement = None
    if heading_text is None:
        if title_bounds is None:
            raise LayoutError("E_LAYOUT_NETWORK_MEASUREMENT", "/layoutManifest/sources/title")
        title_placement = _place_title(_title_measurement(measured_sources), title_bounds)
        heading_text = (title_placement,)
    measured = _node_measurements(nodes, measured_sources)
    ranks = _ranks(nodes, edges)
    by_rank: dict[int, list[Any]] = {}
    for node in sorted(nodes, key=lambda item: (ranks[item.object_id], item.order_key, item.object_id)):
        by_rank.setdefault(ranks[node.object_id], []).append(node)
    placed = _place_nodes(by_rank, ranks, measured, bounds, min_inline, min_block, gap,
                          flow_direction == "horizontal")
    node_text = tuple(_place_node_text(node, measured[node.object_id]) for node in placed)
    text = heading_text + node_text
    _assert_surface_quality(placed, node_text)
    requested_canvas = canvas_bounds or (_union(title_bounds, bounds) if title_bounds is not None else bounds)
    canvas = _completed_canvas(requested_canvas, title_bounds, tuple(node.bounds for node in placed),
                               tuple(item.bounds for item in text))
    route_region = _expand_route_bounds(route_bounds, placed) if route_bounds is not None else canvas
    relations, route_warnings = _route_edges(edges, placed, route_region, max_bends, max_detour_ratio)
    patterns: tuple[PatternedPlacement, ...] = ()
    optional_pattern = getattr(theme_tokens, "optional_pattern", None)
    if callable(optional_pattern):
        token = optional_pattern("network-node")
        if isinstance(token, Mapping) and token.get("kind") == "catalog":
            patterns = tuple(PatternedPlacement(
                node.placement_id, complete_pattern_placement(token, node.bounds))
                for node in placed)
    texture = complete_canvas_texture(theme_tokens, canvas)
    completed_overlays = complete_canvas_overlays(theme_tokens, canvas)
    canvas_overlays = completed_overlays if (
        completed_overlays.pattern is not None or completed_overlays.radial is not None) else None
    if texture is not None:
        patterns = (texture.pattern, *patterns)
    overflowed = (canvas.inline_size > requested_canvas.inline_size
                  or canvas.block_size > requested_canvas.block_size)
    title_overflow = (title_placement is not None and title_bounds is not None
                      and (title_placement.bounds.inline_size > title_bounds.inline_size
                           or title_placement.bounds.block_size > title_bounds.block_size))
    warnings = tuple(
        item for item in (
            FitWarning("W_LAYOUT_NETWORK_OVERFLOW", "network", "/layoutManifest/network",
                       "network-allocation", "visible-overflow", float(canvas.inline_size),
                       float(canvas.block_size), float(requested_canvas.inline_size), float(requested_canvas.block_size))
            if overflowed else None,
            FitWarning("W_LAYOUT_VISIBLE_OVERFLOW", "title", "title", "network-title",
                       "visible-overflow", float(title_placement.bounds.inline_size),
                       float(title_placement.bounds.block_size), float(title_bounds.inline_size),
                       float(title_bounds.block_size)) if title_overflow else None,
        ) if item is not None
    ) + route_warnings
    stroke_shapes = tuple(ShapePlacement(node.placement_id, node.object_id, "Rect", node.bounds,
                                        semantic_id="networkNode") for node in placed)
    if texture is not None:
        stroke_shapes = (texture.shape, *stroke_shapes)
    strokes = complete_aligned_strokes((), stroke_shapes, (), theme_tokens)
    return DependencyNetworkLayout(tuple(placed), text, relations, canvas, warnings, patterns, texture, strokes,
                                   canvas_overlays=canvas_overlays)


def compose_dependency_network_surface(request: SurfaceLayoutRequest) -> DependencyNetworkLayout:
    """Complete native title/network headings and graph geometry from one closed request."""
    manifest = request.layout_manifest
    network = getattr(request.projection, "network", None)
    if manifest is None or network is None:
        raise LayoutError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/network")
    decisions = {item.source: item for item in manifest.decisions
                 if item.kind == "slot" and item.source in {
                     "title", "network", "heading.title", "heading.kicker", "heading.subtitle"}}
    if "network" not in decisions:
        raise LayoutError("E_PRESENTATION_PRIMITIVE_MISSING", "/layoutManifest/sources/network")
    slots = {source: SlotPlacement(item.node_id, source, item.bounds,
                                   item.priority or "required", item.overflow or "visible-overflow")
             for source, item in decisions.items()}
    headings = complete_slot_headings(request=request, slots=slots, decisions=decisions)
    network_reserve = headings.reserved("network")
    content_slots = {source: content_slot(slot, headings.reserved(source))
                     for source, slot in slots.items()}
    title_slot = content_slots.get("title")
    heading_batch = None
    if title_slot is None:
        heading_batch = place_surface_headings(request, content_slots, request.measured_sources)
    network_slot = content_slot(slots["network"], network_reserve)
    route_bounds = None
    if network_reserve:
        # Routes are contained in the network's content viewport, with its lower edge
        # extended only for naturally overflowing graph nodes. The complete canvas is
        # still allowed to include the caption and therefore remains the Scene canvas.
        route_bounds = Rect(network_slot.bounds.inline, network_slot.bounds.block,
                            network_slot.bounds.inline_size,
                            max(network_slot.bounds.block_size,
                                manifest.viewport.block + manifest.viewport.block_size
                                - network_slot.bounds.block))
    placed = compose_dependency_network_layout(
        network, title_bounds=title_slot.bounds if title_slot is not None else None,
        bounds=network_slot.bounds,
        measured_sources=request.measured_sources,
        flow_direction=manifest.dependency_network_flow_direction,
        max_bends=manifest.relation_max_bends,
        max_detour_ratio=manifest.relation_max_detour_ratio,
        canvas_bounds=manifest.viewport, theme_tokens=request.theme_tokens,
        route_bounds=route_bounds,
        heading_text=tuple(replace(item, semantic_id={
            "title": "titleText", "kicker": "kickerText", "subtitle": "subtitleText"
        }[item.placement_id]) for item in heading_batch.text) if heading_batch is not None else None)
    # Source vocabulary is not slot identity. Close native ownership against the same
    # manifest slots as captions before Scene receives any completed primitive.
    slot_owners = {source: slot.slot_id for source, slot in slots.items()}
    slot_owners.update({slot.slot_id: slot.slot_id for slot in slots.values()})
    placed = replace(placed,
        nodes=tuple(replace(node, slot_id=slots["network"].slot_id) for node in placed.nodes),
        text=tuple(replace(item, slot_id=slot_owners[item.slot_id]) for item in placed.text),
        relations=tuple(replace(item, slot_id=slots["network"].slot_id) for item in placed.relations))
    if headings.text:
        placed = replace(placed, text=(*headings.text, *placed.text))
    warning = canvas_viewport_warning(
        surface_id="dependency-network", declared=request.declared_viewport, actual=placed.canvas_bounds,
        contributors=chain(
            ((slot.slot_id, slot.bounds) for slot in slots.values()),
            ((item.slot_id, item.bounds) for item in (*placed.nodes, *placed.text)),
            ((relation.slot_id, Rect(Decimal(str(inline)), Decimal(str(block)), Decimal(0), Decimal(0)))
             for relation in placed.relations for inline, block in relation.points)))
    return replace(placed, fit_warnings=(*headings.warnings,
                                        *(heading_batch.warnings if heading_batch is not None else ()),
                                        *placed.fit_warnings),
                   diagnostics=(*headings.diagnostics,
                                *(heading_batch.diagnostics if heading_batch is not None else ())),
                   canvas_warning=warning)


def _title_measurement(measured_sources: MeasuredSources) -> MeasuredTextRun:
    title = measured_sources.run_measurements.get("title", ())
    if len(title) != 1:
        raise LayoutError("E_LAYOUT_NETWORK_MEASUREMENT", "/measuredSources/title")
    return title[0]


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
        letter_spacing=measured.letter_spacing, text_transform=measured.text_transform,
        numeric_spacing=measured.numeric_spacing, horizontal_scale=measured.horizontal_scale,
        font_asset_identity=measured.font_asset_identity, collision_region="network",
        collision_domain=CollisionDomain("network", "nodes"), slot_id="network", semantic_id="networkLabel")


def _place_title(measured: MeasuredTextRun, bounds: Rect) -> TextPlacement:
    text_bounds = Rect(bounds.inline, bounds.block, measured.inline_size, measured.block_size)
    return TextPlacement(
        "title", "title", measured.content, text_bounds, measured.typography_role,
        baseline=(float(bounds.inline), float(bounds.block + measured.baseline)), lines=(measured.content,),
        font_family=measured.font_family, font_weight=measured.font_weight,
        font_size=measured.font_size, line_height=measured.line_height,
        letter_spacing=measured.letter_spacing, text_transform=measured.text_transform,
        numeric_spacing=measured.numeric_spacing, horizontal_scale=measured.horizontal_scale,
        font_asset_identity=measured.font_asset_identity, collision_region="network-title",
        collision_domain=CollisionDomain("network-title", "content"), slot_id="title", semantic_id="titleText")


def _route_edges(edges: tuple[Any, ...], nodes: list[NetworkNodePlacement], bounds: Rect,
                 max_bends: int, max_detour_ratio: float) -> tuple[tuple[RelationPlacement, ...], tuple[FitWarning, ...]]:
    by_id = {node.object_id: node for node in nodes}
    boxes = {node.object_id: _box(node.bounds) for node in nodes}
    relations = []
    warnings = []
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
            points = (source.output_port, target.input_port)
            warnings.append(FitWarning("W_LAYOUT_ROUTE_FALLBACK", edge.relation_id,
                                       f"/projection/network/edges/{edge.relation_id}", "relation-route",
                                       "direct-path", 0.0, 0.0, float(bounds.inline_size), float(bounds.block_size)))
        if not relation_route_quality(points, max_bends=max_bends, max_detour_ratio=max_detour_ratio):
            points = (source.output_port, target.input_port)
            warnings.append(FitWarning("W_LAYOUT_ROUTE_FALLBACK", edge.relation_id,
                                       f"/projection/network/edges/{edge.relation_id}", "relation-route",
                                       "direct-path", 0.0, 0.0, float(bounds.inline_size), float(bounds.block_size)))
        relations.append(RelationPlacement(edge.relation_id, f"{edge.source_id}:output", f"{edge.target_id}:input",
                                           tuple(points), semantic_id="dependency-critical" if edge.critical else "dependency",
                                           slot_id="network", paint_order=100))
    return tuple(relations), tuple(warnings)


def _assert_surface_quality(nodes: list[NetworkNodePlacement], text: tuple[TextPlacement, ...]) -> None:
    for index, node in enumerate(nodes):
        if node.input_port == node.output_port:
            raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", "/layoutManifest/network")
        if any(intersects(node.bounds, other.bounds) for other in nodes[index + 1:]):
            raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", "/layoutManifest/network")
    for label, node in zip(text, nodes, strict=True):
        if not _contains(node.bounds, label.bounds):
            raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", f"/projection/network/nodes/{node.object_id}")


def _completed_canvas(requested: Rect, title_bounds: Rect | None, nodes: tuple[Rect, ...], text: tuple[Rect, ...]) -> Rect:
    """Return Layout's natural network extent, anchored at the requested origin."""
    inline_end = requested.inline + requested.inline_size
    block_end = requested.block + requested.block_size
    if title_bounds is not None:
        inline_end = max(inline_end, title_bounds.inline + title_bounds.inline_size)
        block_end = max(block_end, title_bounds.block + title_bounds.block_size)
    for item in nodes + text:
        inline_end = max(inline_end, item.inline + item.inline_size)
        block_end = max(block_end, item.block + item.block_size)
    return Rect(requested.inline, requested.block, inline_end - requested.inline, block_end - requested.block)


def _expand_route_bounds(requested: Rect, nodes: list[NetworkNodePlacement]) -> Rect:
    """Grow a restricted route viewport for natural node overflow, never upward."""
    inline_end = max(requested.inline + requested.inline_size,
                     *(node.bounds.inline + node.bounds.inline_size for node in nodes))
    block_end = max(requested.block + requested.block_size,
                    *(node.bounds.block + node.bounds.block_size for node in nodes))
    inline_start = min(requested.inline, *(node.bounds.inline for node in nodes))
    return Rect(inline_start, requested.block, inline_end - inline_start,
                block_end - requested.block)


def _union(left: Rect, right: Rect) -> Rect:
    inline = min(left.inline, right.inline)
    block = min(left.block, right.block)
    inline_end = max(left.inline + left.inline_size, right.inline + right.inline_size)
    block_end = max(left.block + left.block_size, right.block + right.block_size)
    return Rect(inline, block, inline_end - inline, block_end - block)


def _contains(outer: Rect, inner: Rect) -> bool:
    return (outer.inline <= inner.inline and outer.block <= inner.block and
            inner.inline + inner.inline_size <= outer.inline + outer.inline_size and
            inner.block + inner.block_size <= outer.block + outer.block_size)


def _box(rect: Rect) -> tuple[float, float, float, float]:
    return (float(rect.inline), float(rect.block),
            float(rect.inline + rect.inline_size), float(rect.block + rect.block_size))
