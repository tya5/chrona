"""Lower completed Scene paint to vector SVG constructs understood by svglib.

This is PDF syntax adaptation, not placement: terminal transforms and repeat
cells are the same completed-data operations used by existing Scene adapters.
The public SVG and PNG routes never call this module.
"""
from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lxml.etree import _Element as Element

from chrona.presentation.renderers.pattern_repeat import repeat_cells
from chrona.presentation.scene.model import ScenePrimitive, SceneSurface, completed_marker_outline

PDF_PAINT_GRAMMAR = "pdf-scene-paint-v1"
_NS = "{http://www.w3.org/2000/svg}"
_EFFECTS = frozenset({"opacity", "filter", "clip-path", "mask", "transform"})


def _number(value: float) -> str:
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _invalid(detail: str) -> ValueError:
    return ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: PDF vector lowering: {detail}")


def _path_data(commands: tuple) -> str:
    glyphs = {"move": "M", "line": "L", "quadratic": "Q"}
    return "".join(glyphs[command.kind] + " ".join(
        _number(value) for point in command.points for value in point) for command in commands)


def _child(parent: Element, tag: str, attributes: dict[str, str]) -> Element:
    element = parent.makeelement(_NS + tag, attributes)
    parent.append(element)
    return element


def _replace(parent: Element, old: Element, new: Element) -> None:
    index = list(parent).index(old)
    parent.remove(old)
    parent.insert(index, new)


def _lower_markers(element: Element, node: ScenePrimitive) -> Element:
    # Keep primitive-wide effects around both the route and its terminal paint.
    group = element.makeelement(_NS + "g", {key: element.attrib.pop(key)
                                           for key in tuple(element.attrib) if key in _EFFECTS})
    route = deepcopy(element)
    group.append(route)
    for side, marker in (("start", node.marker_start), ("end", node.marker_end)):
        route.attrib.pop("marker-" + side, None)
        if marker is None:
            continue
        if node.paint is None or node.paint.stroke is None:
            raise _invalid(f"marker on {node.scene_id!r} has no completed stroke pigment")
        points, commands = node.points, node.path_commands
        if node.paint.wobble is not None and node.paint.wobble.outline:
            # SVG paints the completed wobble rather than the nominal route.
            # Start/end markers belong to the entire path, not each sub-path.
            points = node.paint.wobble.outline[0 if side == "start" else -1]
            commands = ()
        outline = completed_marker_outline(marker, side=side, points=points,
                                           path_commands=commands,
                                           stroke_width=node.paint.stroke_width)
        attributes = {"d": _path_data(outline), "data-pdf-marker": side}
        if marker.paint_mode == "fill":
            attributes.update(fill=node.paint.stroke, stroke="none")
        else:
            width = marker.stroke_width if marker.physical_units else node.paint.stroke_width
            if width is None:
                raise _invalid(f"stroked marker on {node.scene_id!r} has no completed width")
            attributes.update(fill="none", stroke=node.paint.stroke,
                              **{"stroke-width": _number(width), "stroke-linecap": "butt",
                                 "stroke-linejoin": "miter", "stroke-miterlimit": "4"})
        _child(group, "path", attributes)
    return group


def _lower_pattern(element: Element, node: ScenePrimitive,
                   tile: Element, definitions: Element, index: int) -> Element:
    pattern = node.pattern
    assert pattern is not None
    # The host contour and each tile are separate clips, exactly as SVG pattern
    # viewport clipping followed by the filled host contour. Keep a legacy host
    # outline outside the fill clip, with the original stroke attributes.
    host_clip_id, tile_clip_id = f"pdf-pattern-host-{index}", f"pdf-pattern-tile-{index}"
    host_clip = _child(definitions, "clipPath", {"id": host_clip_id, "clipPathUnits": "userSpaceOnUse"})
    contour = {key: element.attrib[key] for key in ("x", "y", "width", "height", "rx", "ry")
               if key in element.attrib}
    _child(host_clip, "rect", contour)
    tile_clip = _child(definitions, "clipPath", {"id": tile_clip_id, "clipPathUnits": "userSpaceOnUse"})
    _child(tile_clip, "rect", {
        "x": "0", "y": "0", "width": _number(pattern.tile_inline_size),
        "height": _number(pattern.tile_block_size)})
    effects = {key: value for key, value in element.attrib.items() if key in _EFFECTS}
    group = element.makeelement(_NS + "g", effects)
    fill = _child(group, "g", {"clip-path": f"url(#{host_clip_id})"})
    for x, y in repeat_cells(node):
        cell = _child(fill, "g", {
            "transform": f"translate({_number(x)} {_number(y)}) rotate({_number(pattern.angle_degrees)})"})
        clipped = _child(cell, "g", {"clip-path": f"url(#{tile_clip_id})"})
        clipped.extend(deepcopy(child) for child in tile)
    if element.get("stroke", "none") != "none":
        outline = deepcopy(element)
        outline.set("fill", "none")
        for key in _EFFECTS:
            outline.attrib.pop(key, None)
        group.append(outline)
    return group


def lower_pdf_svg(surface: SceneSurface, svg: bytes) -> bytes:
    """Materialize markers and patterned Rects without changing completed facts.

    Unknown pattern host forms are a counted refusal before conversion. Keeping
    an unsupported ``url(#pattern)`` would let svglib silently lose its paint.
    """
    unsupported = [node.scene_id for node in surface.primitives
                   if node.pattern is not None and node.kind != "Rect"]
    if unsupported:
        raise ValueError("E_VISUAL_CAPABILITY_UNSUPPORTED: PDF pattern hosts must be Rect; "
                         f"count={len(unsupported)} primitiveIds={unsupported!r}")
    relevant = {node.scene_id: node for node in surface.primitives
                if node.pattern is not None or node.marker_start is not None or node.marker_end is not None}
    if not relevant:
        return svg
    # Preserve the default SVG namespace: svglib indexes <defs> through that
    # binding. Rewriting it to ns0 silently loses even existing host clips.
    try:
        from lxml import etree
    except ImportError as error:
        raise ValueError("E_RENDER_RASTERIZER_UNAVAILABLE: PDF vector lowering requires lxml") from error
    root = etree.fromstring(svg)
    parents = {child: parent for parent in root.iter() for child in parent}
    definitions = root.find(_NS + "defs")
    if definitions is None:
        raise _invalid("completed marker/pattern definitions are missing")
    tiles = {item.get("id"): item for item in definitions if item.tag == _NS + "pattern"}
    marker_hits: set[str] = set()
    pattern_hits: set[str] = set()
    for element in tuple(root.iter()):
        owner = element
        while owner is not None and owner.get("data-scene-id") not in relevant:
            owner = parents.get(owner)
        if owner is None:
            continue
        node = relevant[owner.get("data-scene-id")]
        if element.tag == _NS + "path" and (element.get("marker-start") or element.get("marker-end")):
            _replace(parents[element], element, _lower_markers(element, node))
            marker_hits.add(node.scene_id)
        fill = element.get("fill", "")
        if fill.startswith("url(#") and fill[5:-1] in tiles:
            if element.tag != _NS + "rect" or node.pattern is None:
                raise _invalid(f"pattern host {node.scene_id!r} has no completed Rect contour")
            _replace(parents[element], element, _lower_pattern(
                element, node, tiles[fill[5:-1]], definitions, len(pattern_hits)))
            pattern_hits.add(node.scene_id)
    missing = [node.scene_id for node in relevant.values()
               if ((node.pattern is not None and node.scene_id not in pattern_hits)
                   or ((node.marker_start is not None or node.marker_end is not None)
                       and node.scene_id not in marker_hits))]
    if missing:
        raise _invalid(f"completed paint did not reach vector conversion: primitiveIds={missing!r}")
    return etree.tostring(root, encoding="utf-8")
