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
from chrona.presentation.layout.network_routes import complete_network_routes
from chrona.presentation.layout.sources import MeasuredSources, MeasuredTextRun
from chrona.presentation.layout.canvas_texture import CanvasTexture, complete_canvas_texture
from chrona.presentation.layout.canvas_overlays import CanvasOverlays, complete_canvas_overlays
from chrona.presentation.layout.surface_quality import CollisionDomain, FitWarning, RelationPlacement, TextPlacement, intersects
from chrona.presentation.layout.surface_quality import SlotPlacement, SurfaceLayoutRequest
from chrona.presentation.layout.surface_quality import GroupPlacement
from chrona.presentation.layout.surface_legend import SurfaceLegendBatch
from chrona.presentation.layout.network_group_bands import place_network_bands
from chrona.presentation.layout.network_ink import network_ink_bounds
from chrona.presentation.layout.network_legend import prepare_network_legend, complete_network_legend
from chrona.presentation.layout.slot_heading import (
    complete_slot_headings, content_slot, inline_content_slot, full_slot, inline_full_slot,
)
from chrona.presentation.layout.text import translate_text_block
from chrona.presentation.model.render_progress import RenderProgress
from chrona.presentation.layout.surface_heading import place_surface_headings
from chrona.presentation.layout.surface_deadlines import (
    DeadlineInkStyle, complete_deadline_ink, deadline_ink_style,
)
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject
from chrona.presentation.model.semantic_registry import semantic_binding


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
    is_container: bool = False

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
    shapes: tuple[ShapePlacement, ...] = ()
    groups: tuple[GroupPlacement, ...] = ()
    legend: SurfaceLegendBatch | None = None


def compose_dependency_network_layout(network: Any, *, title_bounds: Rect | None, bounds: Rect,
                                      measured_sources: MeasuredSources,
                                      flow_direction: str,
                                      max_bends: int = 4,
                                      max_detour_ratio: float = 2.0,
                                      canvas_bounds: Rect | None = None,
                                      theme_tokens: Any | None = None,
                                      route_bounds: Rect | None = None,
                                      heading_text: tuple[TextPlacement, ...] | None = None,
                                      progress: RenderProgress | None = None) -> DependencyNetworkLayout:
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
    member_gap = metric.get("network.member.gap", gap)
    title_placement = None
    if heading_text is None:
        if title_bounds is None:
            raise LayoutError("E_LAYOUT_NETWORK_MEASUREMENT", "/layoutManifest/sources/title")
        title_placement = _place_title(_title_measurement(measured_sources), title_bounds)
        heading_text = (title_placement,)
    measured = _node_measurements(nodes, measured_sources)
    deadline_contents = {node.object_id: node.deadline for node in nodes
                         if getattr(node, "deadline", None) is not None}
    deadline_measured = _deadline_measurements(deadline_contents, measured_sources) if deadline_contents else {}
    deadline_style = deadline_ink_style(theme_tokens) if deadline_contents else None
    ranks = _ranks(nodes, edges)
    by_rank: dict[int, list[Any]] = {}
    for node in sorted(nodes, key=lambda item: (ranks[item.object_id], item.order_key, item.object_id)):
        by_rank.setdefault(ranks[node.object_id], []).append(node)
    placed, groups = _place_nodes(by_rank, ranks, measured, bounds, min_inline, min_block, gap, member_gap,
                          flow_direction == "horizontal", deadline_measured, deadline_style,
                          padding_inline=metric.get("network.node.paddingInline"),
                          padding_block=metric.get("network.node.paddingBlock"))
    headers = {group.group_id: group.header_bounds for group in groups}
    text_hosts = [replace(node, bounds=headers[node.object_id]) if node.is_container else node
                  for node in placed]
    if deadline_contents:
        node_text, deadline_text, deadline_shapes = _place_node_contents(
            text_hosts, measured, deadline_contents, deadline_measured, deadline_style)
        text = heading_text + node_text + deadline_text
        deadline_ink = complete_deadline_ink(
            deadline_shapes, deadline_style,
            outline_placement_id=lambda shape: f"deadline-outline:{shape.placement_id}")
        deadline_shapes = (*deadline_ink.outlines, *deadline_shapes)
    else:
        node_text = tuple(_place_node_text(node, measured[node.object_id]) for node in text_hosts)
        text = heading_text + node_text
        deadline_shapes = ()
    _assert_surface_quality(placed, node_text + (deadline_text if deadline_contents else ()))
    requested_canvas = canvas_bounds or (_union(title_bounds, bounds) if title_bounds is not None else bounds)
    canvas = _completed_canvas(requested_canvas, title_bounds, tuple(node.bounds for node in placed),
                               tuple(item.bounds for item in text))
    route_region = _expand_route_bounds(route_bounds, placed) if route_bounds is not None else canvas
    relations, route_warnings = _route_edges(edges, placed, route_region, max_bends, max_detour_ratio,
                                            groups=groups, theme_tokens=theme_tokens, progress=progress)
    group_shapes = _network_group_shapes(groups, theme_tokens)
    occupied = network_ink_bounds(placed, text, (*group_shapes, *deadline_shapes), relations, theme_tokens)
    canvas = _completed_canvas(canvas, None, occupied, ())
    patterns: tuple[PatternedPlacement, ...] = ()
    optional_pattern = getattr(theme_tokens, "optional_pattern", None)
    if callable(optional_pattern):
        token = optional_pattern("network-node")
        if isinstance(token, Mapping) and token.get("kind") == "catalog":
            patterns = tuple(PatternedPlacement(
                node.placement_id, complete_pattern_placement(token, node.bounds))
                for node in placed if not node.is_container)
        for shape in group_shapes:
            token = optional_pattern(semantic_binding(shape.semantic_id).theme_role)
            if isinstance(token, Mapping) and token.get("kind") == "catalog":
                patterns += (PatternedPlacement(
                    shape.placement_id, complete_pattern_placement(token, shape.bounds)),)
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
                                        semantic_id="networkNode") for node in placed if not node.is_container) + group_shapes
    if texture is not None:
        stroke_shapes = (texture.shape, *stroke_shapes)
    strokes = complete_aligned_strokes((), stroke_shapes, (), theme_tokens)
    return DependencyNetworkLayout(tuple(placed), text, relations, canvas, warnings, patterns, texture, strokes,
                                   canvas_overlays=canvas_overlays, shapes=(*group_shapes, *deadline_shapes),
                                   groups=groups)


def compose_dependency_network_surface(request: SurfaceLayoutRequest) -> DependencyNetworkLayout:
    """Complete native title/network headings and graph geometry from one closed request."""
    manifest = request.layout_manifest
    network = getattr(request.projection, "network", None)
    if manifest is None or network is None:
        raise LayoutError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/network")
    decisions = {item.source: item for item in manifest.decisions
                 if item.kind == "slot" and item.source in {
                     "title", "network", "legend", "heading.title", "heading.kicker", "heading.subtitle"}}
    if "network" not in decisions:
        raise LayoutError(
            "E_PRESENTATION_PRIMITIVE_MISSING", "/layoutManifest/sources/network",
            detail=("surface=dependency-network; missing source='network'; add this slot to a matching "
                    "Layout Profile and select it with --layout <profile>"))
    slots = {source: SlotPlacement(item.node_id, source, item.bounds,
                                   item.priority or "required", item.overflow or "visible-overflow",
                                   direction=item.direction or "block", gap=item.gap,
                                   item_min_inline_size=item.item_min_inline_size, columns=item.columns,
                                   column_distribution=item.column_distribution)
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
    authored_legend = content_slots.get("legend")
    if authored_legend is not None:
        authored_legend = inline_content_slot(authored_legend, headings.reserved_inline("legend"))
    legend_plan = prepare_network_legend(request, network_slot, authored_legend,
                                         heading_block=headings.reserved("legend"))
    network_slot = legend_plan.graph_slot
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
        progress=request.progress,
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
        relations=tuple(replace(item, slot_id=slots["network"].slot_id) for item in placed.relations),
        shapes=tuple(replace(item, slot_id=slots["network"].slot_id) for item in placed.shapes))
    if headings.text:
        placed = replace(placed, text=(*headings.text, *placed.text))
    graph_ink = network_ink_bounds(
        placed.nodes, tuple(item for item in placed.text if item.slot_id == slots["network"].slot_id),
        placed.shapes, placed.relations, request.theme_tokens)
    legend = complete_network_legend(legend_plan, placed.relations, graph_ink)
    if legend is not None:
        if authored_legend is not None:
            delta = legend.slot.bounds.block - authored_legend.bounds.block
            original = slots["legend"]
            legend = replace(legend, slot=inline_full_slot(original,
                full_slot(original, legend.slot, headings.reserved("legend")),
                headings.reserved_inline("legend")))
            placed = replace(placed, text=tuple(
                translate_text_block(item, delta) if item.slot_id == original.slot_id else item
                for item in placed.text))
        legend_ink = network_ink_bounds((), legend.text, legend.shapes, legend.relations, request.theme_tokens)
        completed_canvas = _completed_canvas(placed.canvas_bounds, None, (legend.slot.bounds, *legend_ink), ())
        placed = replace(placed, legend=legend, canvas_bounds=completed_canvas)
        placed = _refresh_canvas_paint(placed, request.theme_tokens)
    warning = canvas_viewport_warning(
        surface_id="dependency-network", declared=request.declared_viewport, actual=placed.canvas_bounds,
        contributors=chain(
            ((slot.slot_id, slot.bounds) for slot in slots.values()),
            ((item.slot_id, item.bounds) for item in (*placed.nodes, *placed.text)),
            ((legend.slot.slot_id, rect) for rect in (legend.slot.bounds, *legend_ink))
            if legend is not None else (),
            ((relation.slot_id, Rect(Decimal(str(inline)), Decimal(str(block)), Decimal(0), Decimal(0)))
             for relation in placed.relations for inline, block in relation.points)))
    return replace(placed, fit_warnings=(*headings.warnings,
                                        *(heading_batch.warnings if heading_batch is not None else ()),
                                        *(legend.warnings if legend is not None else ()),
                                        *placed.fit_warnings),
                   diagnostics=(*headings.diagnostics,
                                *(heading_batch.diagnostics if heading_batch is not None else ()),
                                *(legend.diagnostics if legend is not None else ())),
                   canvas_warning=warning)


def _refresh_canvas_paint(placed: DependencyNetworkLayout, tokens: Any) -> DependencyNetworkLayout:
    """Reclose canvas-owned paint after the legend completes natural canvas growth."""
    previous = placed.texture
    texture = complete_canvas_texture(tokens, placed.canvas_bounds)
    patterns = tuple(item for item in placed.patterns if previous is None or item is not previous.pattern)
    strokes = tuple(item for item in placed.aligned_strokes
                    if previous is None or item.primitive_id != previous.shape.placement_id)
    if texture is not None:
        patterns = (texture.pattern, *patterns)
        strokes += complete_aligned_strokes((), (texture.shape,), (), tokens)
    overlays = complete_canvas_overlays(tokens, placed.canvas_bounds)
    return replace(placed, texture=texture, patterns=patterns, aligned_strokes=strokes,
                   canvas_overlays=overlays if overlays.pattern is not None or overlays.radial is not None else None)


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


def _deadline_measurements(contents: Mapping[str, Any], measured_sources: MeasuredSources) -> Mapping[str, MeasuredTextRun]:
    found = {item.source_ref: item for item in measured_sources.run_measurements.get("network-deadlines", ())
             if item.source_ref is not None}
    missing = sorted(object_id for object_id in contents if object_id not in found)
    if missing:
        raise LayoutError("E_LAYOUT_NETWORK_MEASUREMENT", "/measuredSources/network-deadlines/" + missing[0])
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
                 min_inline: Decimal, min_block: Decimal, gap: Decimal, member_gap: Decimal,
                 horizontal: bool, deadline_measured: Mapping[str, MeasuredTextRun] | None = None,
                 deadline_style: DeadlineInkStyle | None = None, *,
                 padding_inline: Decimal | None = None,
                 padding_block: Decimal | None = None) -> tuple[list[NetworkNodePlacement], tuple[GroupPlacement, ...]]:
    dimensions = {node.object_id: _node_content_size(
        measured[node.object_id], (deadline_measured or {}).get(node.object_id), deadline_style,
        min_inline, min_block, padding_inline=padding_inline, padding_block=padding_block)
        for members in by_rank.values() for node in members}
    nodes = tuple(node for rank in sorted(by_rank) for node in by_rank[rank])
    insets = {node.object_id: (
        Decimal(str(measured[node.object_id].font_size)) / 2 if padding_inline is None else padding_inline,
        Decimal(str(measured[node.object_id].font_size)) / 2 if padding_block is None else padding_block)
        for node in nodes}
    boxes, groups = place_network_bands(nodes, ranks=ranks, sizes=dimensions, insets=insets,
                                        bounds=bounds, gap=gap, member_gap=member_gap,
                                        horizontal=horizontal)
    result: list[NetworkNodePlacement] = []
    for node in nodes:
        rect = boxes[node.object_id]
        if horizontal:
            input_port = (float(rect.inline), float(rect.block + rect.block_size / 2))
            output_port = (float(rect.inline + rect.inline_size), float(rect.block + rect.block_size / 2))
        else:
            input_port = (float(rect.inline + rect.inline_size / 2), float(rect.block))
            output_port = (float(rect.inline + rect.inline_size / 2), float(rect.block + rect.block_size))
        result.append(NetworkNodePlacement(node.object_id, ranks[node.object_id], rect,
                                          input_port, output_port, node.critical, is_container=node.is_container))
    return result, groups


def _network_group_shapes(groups: tuple[GroupPlacement, ...], theme_tokens: Any) -> tuple[ShapePlacement, ...]:
    if theme_tokens is None:
        return ()
    shapes = []
    for group in groups:
        subject = DiagnosticSubject.project_object(group.group_id)
        for semantic, role, bounds in (("groupBand", "group-band", group.content_bounds),
                                       ("groupHeaderBand", "group-header-band", group.header_bounds)):
            treatment, order = theme_tokens.background(role)
            if treatment != "none":
                shapes.append(ShapePlacement(f"network-{semantic}:{group.group_id}", group.group_id, "Rect",
                    bounds, slot_id="network", semantic_id=semantic, paint_order=order, subjects=(subject,)))
    return tuple(shapes)


def _deadline_footer_size(measured: MeasuredTextRun, style: DeadlineInkStyle | None) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return footer inline/block demand, glyph side, and the measured text gap."""
    if style is None or style.stroke_width <= 0:
        _, _, text_height = _text_vertical_envelope(measured)
        return measured.inline_size, text_height, Decimal(0), Decimal(0)
    side = style.reach * measured.block_size
    margin = Decimal(str(style.margin))
    painted_side = side + 2 * margin
    gap = Decimal(str(measured.font_size))
    _, _, text_height = _text_vertical_envelope(measured)
    return painted_side + gap + measured.inline_size, max(painted_side, text_height), side, gap


def _node_content_size(title: MeasuredTextRun, footer: MeasuredTextRun | None,
                       style: DeadlineInkStyle | None, min_inline: Decimal,
                       min_block: Decimal, *, padding_inline: Decimal | None = None,
                       padding_block: Decimal | None = None) -> tuple[Decimal, Decimal]:
    default_padding = Decimal(str(title.font_size)) / 2
    inline_inset = default_padding if padding_inline is None else padding_inline
    block_inset = default_padding if padding_block is None else padding_block
    footer_inline, footer_block = Decimal(0), Decimal(0)
    if footer is not None:
        footer_inline, footer_block, _, _ = _deadline_footer_size(footer, style)
    _, _, title_height = _text_vertical_envelope(title)
    return (max(min_inline, max(title.inline_size, footer_inline) + 2 * inline_inset),
            max(min_block, title_height + footer_block + 2 * block_inset))


def _text_vertical_envelope(measured: MeasuredTextRun) -> tuple[Decimal, Decimal, Decimal]:
    """Return measured Text bounds relative to the line origin, including baseline bearings."""
    top = measured.baseline - Decimal(str(measured.font_size))
    bottom = top + measured.block_size
    envelope_top = min(Decimal(0), top)
    envelope_bottom = max(measured.block_size, bottom)
    return envelope_top, envelope_bottom, envelope_bottom - envelope_top


def _place_node_contents(nodes: list[NetworkNodePlacement], titles: Mapping[str, MeasuredTextRun],
                          contents: Mapping[str, Any], footers: Mapping[str, MeasuredTextRun],
                          style: DeadlineInkStyle | None) -> tuple[tuple[TextPlacement, ...],
                                                                  tuple[TextPlacement, ...],
                                                                  tuple[ShapePlacement, ...]]:
    title_text: list[TextPlacement] = []
    footer_text: list[TextPlacement] = []
    shapes: list[ShapePlacement] = []
    for node in nodes:
        title = titles[node.object_id]
        footer = footers.get(node.object_id)
        if footer is None:
            title_text.append(_place_node_text(node, title))
            continue
        footer_inline, footer_block, side, gap = _deadline_footer_size(footer, style)
        title_top, _, title_block = _text_vertical_envelope(title)
        footer_top, _, _ = _text_vertical_envelope(footer)
        content_block = title_block + footer_block
        block_start = node.bounds.block + (node.bounds.block_size - content_block) / 2
        title_inline = node.bounds.inline + (node.bounds.inline_size - title.inline_size) / 2
        title_text.append(_place_node_text_at(node, title, title_inline, block_start - title_top))

        footer_inline_start = node.bounds.inline + (node.bounds.inline_size - footer_inline) / 2
        glyph_margin = Decimal(str(style.margin)) if style is not None and style.stroke_width > 0 else Decimal(0)
        row_block = block_start + title_block
        if side > 0:
            x = footer_inline_start + glyph_margin
            y = row_block + (footer_block - side - 2 * glyph_margin) / 2 + glyph_margin
            bottom = y + side
            paint_order = 210 + (style.paint_order if style is not None else 0)
            subject = DiagnosticSubject.project_object(node.object_id, titles[node.object_id].content)
            shapes.append(ShapePlacement(
                f"deadline-network-tick:{node.object_id}", node.object_id, "Path",
                Rect(x, y, Decimal(0), side),
                ((float(x), float(y)), (float(x), float(bottom))),
                slot_id=node.slot_id, paint_order=paint_order, semantic_id="deadlineMark", subjects=(subject,)))
            if contents[node.object_id].slipped:
                shapes.append(ShapePlacement(
                    f"deadline-network-slip:{node.object_id}", node.object_id, "Path",
                    Rect(x, bottom, side, Decimal(0)),
                    ((float(x), float(bottom)), (float(x + side), float(bottom))),
                    slot_id=node.slot_id, paint_order=paint_order, semantic_id="deadlineMark", subjects=(subject,)))
        text_x = footer_inline_start + (side + 2 * glyph_margin + gap if side > 0 else Decimal(0))
        footer_baseline = row_block - footer_top + footer.baseline
        text_y = footer_baseline - Decimal(str(footer.font_size))
        subject = DiagnosticSubject.project_object(node.object_id, titles[node.object_id].content)
        footer_text.append(TextPlacement(
            f"deadline-network-label:{node.object_id}", node.object_id, footer.content,
            Rect(text_x, text_y, footer.inline_size, footer.block_size), footer.typography_role,
            baseline=(float(text_x), float(footer_baseline)), lines=(footer.content,),
            font_family=footer.font_family, font_weight=footer.font_weight,
            font_size=footer.font_size, line_height=footer.line_height,
            letter_spacing=footer.letter_spacing, text_transform=footer.text_transform,
            numeric_spacing=footer.numeric_spacing, horizontal_scale=footer.horizontal_scale,
            font_asset_identity=footer.font_asset_identity, runs=footer.fallback_runs,
            collision_region="network", collision_domain=CollisionDomain("network", "nodes"),
            slot_id=node.slot_id, semantic_id="deadlineCaption", subjects=(subject,)))
    return tuple(title_text), tuple(footer_text), tuple(shapes)


def _place_node_text_at(node: NetworkNodePlacement, measured: MeasuredTextRun,
                        inline: Decimal, block: Decimal) -> TextPlacement:
    baseline = block + measured.baseline
    return replace(_place_node_text(node, measured),
                   bounds=Rect(inline, baseline - Decimal(str(measured.font_size)),
                               measured.inline_size, measured.block_size),
                   baseline=(float(inline), float(baseline)))


def _place_node_text(node: NetworkNodePlacement, measured: MeasuredTextRun) -> TextPlacement:
    inline = node.bounds.inline + (node.bounds.inline_size - measured.inline_size) / 2
    envelope_top, _, envelope_height = _text_vertical_envelope(measured)
    baseline = (node.bounds.block + (node.bounds.block_size - envelope_height) / 2
                - envelope_top + measured.baseline)
    return TextPlacement(
        f"network-label:{node.object_id}", node.object_id, measured.content,
        Rect(inline, baseline - Decimal(str(measured.font_size)), measured.inline_size, measured.block_size),
        measured.typography_role, baseline=(float(inline), float(baseline)), lines=(measured.content,),
        font_family=measured.font_family, font_weight=measured.font_weight,
        font_size=measured.font_size, line_height=measured.line_height,
        letter_spacing=measured.letter_spacing, text_transform=measured.text_transform,
        numeric_spacing=measured.numeric_spacing, horizontal_scale=measured.horizontal_scale,
        font_asset_identity=measured.font_asset_identity, runs=measured.fallback_runs, collision_region="network",
        collision_domain=CollisionDomain("network", "nodes"), slot_id="network",
        semantic_id="groupHeader" if node.is_container else "networkLabel")


def _place_title(measured: MeasuredTextRun, bounds: Rect) -> TextPlacement:
    text_bounds = Rect(bounds.inline, bounds.block, measured.inline_size, measured.block_size)
    return TextPlacement(
        "title", "title", measured.content, text_bounds, measured.typography_role,
        baseline=(float(bounds.inline), float(bounds.block + measured.baseline)), lines=(measured.content,),
        font_family=measured.font_family, font_weight=measured.font_weight,
        font_size=measured.font_size, line_height=measured.line_height,
        letter_spacing=measured.letter_spacing, text_transform=measured.text_transform,
        numeric_spacing=measured.numeric_spacing, horizontal_scale=measured.horizontal_scale,
        font_asset_identity=measured.font_asset_identity, runs=measured.fallback_runs, collision_region="network-title",
        collision_domain=CollisionDomain("network-title", "content"), slot_id="title", semantic_id="titleText")


def _route_edges(edges: tuple[Any, ...], nodes: list[NetworkNodePlacement], bounds: Rect,
                 max_bends: int, max_detour_ratio: float, *,
                 groups: tuple[GroupPlacement, ...] = (),
                 theme_tokens: Any | None = None,
                 progress: RenderProgress | None = None) -> tuple[tuple[RelationPlacement, ...], tuple[FitWarning, ...]]:
    obstacles = {node.object_id: node.bounds for node in nodes if not node.is_container}
    obstacles.update({group.group_id: group.header_bounds for group in groups})
    return complete_network_routes(
        edges, ports={node.object_id: (node.input_port, node.output_port) for node in nodes},
        obstacles=obstacles,
        subjects={node.object_id: DiagnosticSubject.project_object(node.object_id) for node in nodes},
        bounds=bounds, max_bends=max_bends, max_detour_ratio=max_detour_ratio,
        theme_tokens=theme_tokens, progress=progress)


def _assert_surface_quality(nodes: list[NetworkNodePlacement], text: tuple[TextPlacement, ...]) -> None:
    for index, node in enumerate(nodes):
        if node.input_port == node.output_port:
            raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", "/layoutManifest/network")
        if not node.is_container and any(intersects(node.bounds, other.bounds)
                                        for other in nodes[index + 1:] if not other.is_container):
            raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", "/layoutManifest/network")
    by_id = {node.object_id: node for node in nodes}
    for label in text:
        node = by_id.get(label.source_ref)
        if node is not None and not _contains(node.bounds, label.bounds):
            raise LayoutError("E_LAYOUT_NETWORK_OVERFLOW", f"/projection/network/nodes/{node.object_id}")


def _completed_canvas(requested: Rect, title_bounds: Rect | None, nodes: tuple[Rect, ...], text: tuple[Rect, ...]) -> Rect:
    """Contain the requested viewport and completed ink, including outward strokes."""
    inline_start, block_start = requested.inline, requested.block
    inline_end = requested.inline + requested.inline_size
    block_end = requested.block + requested.block_size
    if title_bounds is not None:
        inline_end = max(inline_end, title_bounds.inline + title_bounds.inline_size)
        block_end = max(block_end, title_bounds.block + title_bounds.block_size)
    for item in nodes + text:
        inline_start = min(inline_start, item.inline)
        block_start = min(block_start, item.block)
        inline_end = max(inline_end, item.inline + item.inline_size)
        block_end = max(block_end, item.block + item.block_size)
    return Rect(inline_start, block_start, inline_end - inline_start, block_end - block_start)


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
