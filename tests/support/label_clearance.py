"""Measure the gap between completed relation ink and member-name / note-index boxes (#1848 row 02 adoption).

The rule under test is project independent: a relation's stroke and arrowhead keep the shared label gap
(Spec 07 `timeline.mark.labelGap`) from every member-name box and every note index, on whichever side of a
mark they lie. The measurement reads only a completed Scene document, as a reviewer would, so it cannot
share a defect with Layout. Nothing here reads `examples/`.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Any, Mapping

from chrona.presentation.layout.relation_terminals import project_marker_outline
from chrona.presentation.layout.surface_quality import MarkerGeometry, PathCommand
from chrona.presentation.scene.serialization import scene_document

Rect = tuple[float, float, float, float]
Point = tuple[float, float]


@dataclass(frozen=True)
class InkGap:
    relation: str
    ink: str        # "segment", "arrowhead-start" or "arrowhead-end"
    box: str        # "member-label", "label-chip" or "note-index"
    text: str
    gap: float      # painted-ink distance to the box, in px
    label_gap: float

    @property
    def violates(self) -> bool:
        return self.gap < self.label_gap - 1e-6


def _rect(bounds: Mapping[str, float]) -> Rect:
    return (bounds["inline"], bounds["block"],
            bounds["inline"] + bounds["inlineSize"], bounds["block"] + bounds["blockSize"])


def _point_segment(point: Point, start: Point, end: Point) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    length = dx * dx + dy * dy
    t = 0.0 if length == 0 else max(0.0, min(1.0, ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / length))
    return hypot(point[0] - start[0] - t * dx, point[1] - start[1] - t * dy)


def _cross(a: Point, b: Point, c: Point) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def segment_rect_distance(start: Point, end: Point, rect: Rect) -> float:
    """Distance from a segment to a closed rectangle; zero when they touch or overlap."""
    def inside(point: Point) -> bool:
        return rect[0] < point[0] < rect[2] and rect[1] < point[1] < rect[3]
    if inside(start) or inside(end):
        return 0.0
    corners = [(rect[0], rect[1]), (rect[2], rect[1]), (rect[2], rect[3]), (rect[0], rect[3])]
    edges = list(zip(corners, corners[1:] + corners[:1]))
    if any(_cross(start, end, e0) * _cross(start, end, e1) < 0 and _cross(e0, e1, start) * _cross(e0, e1, end) < 0
           for e0, e1 in edges):
        return 0.0
    return min(min(_point_segment(corner, start, end) for corner in corners),
               *(min(_point_segment(start, e0, e1), _point_segment(end, e0, e1)) for e0, e1 in edges))


def _flatten(commands: tuple[PathCommand, ...]) -> list[Point]:
    out: list[Point] = []
    current: Point = (0.0, 0.0)
    for command in commands:
        if command.kind == "quadratic":
            (x1, y1), (x2, y2) = command.points
            for step in range(1, 9):
                t = step / 8
                out.append(((1 - t) ** 2 * current[0] + 2 * (1 - t) * t * x1 + t * t * x2,
                            (1 - t) ** 2 * current[1] + 2 * (1 - t) * t * y1 + t * t * y2))
        else:
            out.append(command.points[-1])
        current = command.points[-1]
    return out


def _marker(document: Mapping[str, Any]) -> MarkerGeometry:
    commands = tuple(PathCommand(item["kind"], tuple(tuple(point) for point in item["points"]))
                     for item in document["outline"])
    stroke = document["paintMode"] == "stroke"
    return MarkerGeometry(commands, document["headLength"], document["headWidth"], document["attachmentOffset"],
                          document["paintMode"], physical_units=True, stroke_width=1.0 if stroke else None)


def label_boxes(scene: Mapping[str, Any]) -> list[tuple[str, str, Rect, float]]:
    """(kind, text, bounds, font size) of every member-name text, label chip and note index."""
    boxes: list[tuple[str, str, Rect, float]] = []
    for primitive in scene["surfaces"][0]["primitives"]:
        if primitive["kind"] == "Text" and primitive["purpose"] in ("member-label", "note-index"):
            boxes.append((primitive["purpose"], primitive["text"], _rect(primitive["bounds"]),
                          float(primitive["textLayout"]["fontSize"])))
        elif primitive["kind"] == "Rect" and primitive["purpose"] == "label-chip":
            boxes.append(("label-chip", primitive.get("sourceRef", ""), _rect(primitive["bounds"]), 15.0))
    return boxes


def ink_gaps(scene: Mapping[str, Any], *, label_gap: float | None = None, within: float = 4.0) -> list[InkGap]:
    """Every (relation ink, label box) pair closer than the label gap plus `within`, minimum per pair.

    `label_gap` is the declared `timeline.mark.labelGap`; unbound it is a quarter of the label font size
    (at least one pixel), the Spec 07 fallback.
    """
    primitives = scene["surfaces"][0]["primitives"]
    boxes = label_boxes(scene)
    best: dict[tuple[str, str, str, str], InkGap] = {}
    for primitive in primitives:
        if primitive["kind"] != "Path" or primitive["purpose"] != "dependency":
            continue
        points = [tuple(point) for point in primitive["points"]]
        width = float(primitive["paint"]["strokeWidth"])
        inks: list[tuple[str, list[tuple[Point, Point]], float]] = [
            ("segment", [(a, b)], width / 2) for a, b in zip(points, points[1:]) if a != b]
        for side, key in (("start", "markerStart"), ("end", "markerEnd")):
            if primitive.get(key):
                marker = primitive[key]
                outline = project_marker_outline(_marker(marker), side=side, points=tuple(points),
                                                 path_commands=(), stroke_width=width)
                polygon = _flatten(outline)
                inks.append((f"arrowhead-{side}", list(zip(polygon, polygon[1:] + polygon[:1])),
                             0.5 if marker["paintMode"] == "stroke" else 0.0))
        for kind, text, rect, font_size in boxes:
            gap = label_gap if label_gap is not None else max(1.0, 0.25 * font_size)
            for ink, edges, radius in inks:
                distance = max(0.0, min(segment_rect_distance(a, b, rect) for a, b in edges) - radius)
                if distance < gap + within:
                    found = InkGap(primitive["sourceRef"], ink, kind, text, round(distance, 3), gap)
                    key = (found.relation, ink, kind, text)
                    if key not in best or found.gap < best[key].gap:
                        best[key] = found
    return sorted(best.values(), key=lambda item: item.gap)


def scene_gaps(rendered: Any, *, label_gap: float | None = None) -> list[InkGap]:
    """`ink_gaps` of a `RenderedReview`."""
    return ink_gaps(scene_document(rendered.scene), label_gap=label_gap)


def violations(gaps: list[InkGap]) -> list[InkGap]:
    return [item for item in gaps if item.violates]
