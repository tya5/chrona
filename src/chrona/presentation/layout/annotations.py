"""Annotation anchor, box, and leader geometry owned by surface Layout."""
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from typing import Iterable

from chrona.presentation.layout.comparison_marks import ComparisonMark
from chrona.presentation.layout.labels import LabelPlacement, LabelRect, place_label
from chrona.presentation.model.surface_content import AnnotationIntent


@dataclass(frozen=True)
class AnnotationAnchor:
    annotation_id: str
    object_id: str
    facet: str
    endpoint: str
    mark: ComparisonMark


@dataclass(frozen=True)
class AnnotationBox:
    anchor: AnnotationAnchor
    placement: LabelPlacement
    leader_required: bool


def nearest_box_port(box: LabelRect, target: tuple[float, float]) -> tuple[float, float]:
    """Return the nearest edge midpoint with a deterministic tie order."""
    x, y = target
    ports = ((box.x + box.width / 2, box.y), (box.x + box.width / 2, box.bottom),
             (box.right, box.y + box.height / 2), (box.x, box.y + box.height / 2))
    return min(ports, key=lambda port: (abs(port[0] - x) + abs(port[1] - y), ports.index(port)))


def route_annotation_leader(source: tuple[float, float], target: tuple[float, float], *,
                            obstacles: Iterable[LabelRect], limit: int) -> tuple[tuple[float, float], ...]:
    """Return a bounded deterministic orthogonal visibility-grid leader route."""
    if limit < 1:
        raise ValueError("E_PRESENTATION_ROUTE_LIMIT")
    boxes = tuple(obstacles)
    xs = sorted({source[0], target[0], *(value for box in boxes for value in (box.x, box.right))})
    ys = sorted({source[1], target[1], *(value for box in boxes for value in (box.y, box.bottom))})
    start, end = (xs.index(source[0]), ys.index(source[1])), (xs.index(target[0]), ys.index(target[1]))
    queue, parents, seen = [(0, start)], {}, {start}; states = 0
    while queue:
        _, node = heappop(queue); states += 1
        if states > limit:
            raise ValueError("E_PRESENTATION_ROUTE_LIMIT")
        if node == end:
            break
        for nxt in ((node[0]-1, node[1]), (node[0]+1, node[1]), (node[0], node[1]-1), (node[0], node[1]+1)):
            if not (0 <= nxt[0] < len(xs) and 0 <= nxt[1] < len(ys)) or nxt in seen:
                continue
            a, b = (xs[node[0]], ys[node[1]]), (xs[nxt[0]], ys[nxt[1]])
            blocked = any(
                (a[1] == b[1] and box.y < a[1] < box.bottom and max(a[0], b[0]) > box.x and min(a[0], b[0]) < box.right)
                or (a[0] == b[0] and box.x < a[0] < box.right and max(a[1], b[1]) > box.y and min(a[1], b[1]) < box.bottom)
                for box in boxes
            )
            if blocked:
                continue
            seen.add(nxt); parents[nxt] = node
            heappush(queue, (abs(xs[nxt[0]]-target[0]) + abs(ys[nxt[1]]-target[1]), nxt))
    if end not in seen:
        raise ValueError("E_PRESENTATION_ROUTE_LIMIT")
    path, node = [], end
    while node != start:
        path.append((xs[node[0]], ys[node[1]])); node = parents[node]
    points = (source, *reversed(path))
    # Visibility-grid traversal may visit several vertices on one straight
    # segment.  A route-quality bend is a direction change, not a grid vertex.
    compact = [points[0]]
    for point in points[1:]:
        if len(compact) >= 2:
            before, current = compact[-2], compact[-1]
            if ((current[0] - before[0]) * (point[1] - current[1])
                    == (current[1] - before[1]) * (point[0] - current[0])):
                compact[-1] = point
                continue
        compact.append(point)
    return tuple(compact)


def resolve_annotation_anchor(annotation: AnnotationIntent, marks: Iterable[ComparisonMark]) -> AnnotationAnchor:
    """Resolve only the named object target; never substitute an absent actual."""
    anchor = annotation.anchor
    if anchor.get("kind") != "object":
        raise ValueError("E_PRESENTATION_ANCHOR_UNSUPPORTED")
    object_id, facet, endpoint = anchor.get("id"), anchor.get("facet"), anchor.get("endpoint")
    if not isinstance(object_id, str) or facet not in {"planned", "actual"} or endpoint not in {"start", "finish", "at", "body"}:
        raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
    candidates = [mark for mark in marks if mark.source_id == object_id and mark.facet == facet]
    if not candidates:
        raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
    mark = candidates[0]
    if endpoint == "start" and mark.start is None:
        raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
    if endpoint == "finish" and mark.end is None:
        raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
    if endpoint == "at" and mark.at is None:
        raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
    return AnnotationAnchor(annotation.annotation_id, object_id, facet, endpoint, mark)


def project_annotation_box(annotation: AnnotationIntent, resolved: AnnotationAnchor, *, anchor_bounds: LabelRect,
                           text_size: tuple[float, float], candidate_sides: Iterable[str],
                           viewport: LabelRect, obstacles: Iterable[LabelRect], overflow: str,
                           required: bool = True) -> AnnotationBox | None:
    """Place one measured annotation box without assigning renderer semantics."""
    purpose = annotation.purpose
    if purpose not in {"callout", "note", "highlight", "explanatory-arrow"}:
        raise ValueError("E_PRESENTATION_ANCHOR_UNSUPPORTED")
    placement = place_label(anchor_bounds, text_size, candidate_sides, bounds=viewport,
                            obstacles=obstacles, required=required, overflow=overflow)
    if placement is None:
        return None
    alignment = annotation.alignment
    if alignment not in {"start", "center", "end"}:
        raise ValueError("E_PRESENTATION_LABEL_INPUT")
    box = placement.bounds
    if alignment != "center":
        if placement.side in {"above", "below"}:
            x = anchor_bounds.x if alignment == "start" else anchor_bounds.right - box.width
            box = LabelRect(x, box.y, box.width, box.height)
        else:
            y = anchor_bounds.y if alignment == "start" else anchor_bounds.bottom - box.height
            box = LabelRect(box.x, y, box.width, box.height)
        intersects = any(box.x < item.right and item.x < box.right and box.y < item.bottom and item.y < box.bottom for item in obstacles)
        outside_or_colliding = (box.x < viewport.x or box.y < viewport.y
                                 or box.right > viewport.right or box.bottom > viewport.bottom
                                 or intersects)
        if outside_or_colliding and overflow != "visible-overflow":
            return None
        placement = LabelPlacement(placement.side, box,
                                   placement.visible_overflow or outside_or_colliding)
    return AnnotationBox(resolved, placement, purpose in {"callout", "note", "explanatory-arrow"})


def place_annotation_rail(annotation: AnnotationIntent, resolved: AnnotationAnchor, *, anchor_y: float,
                          text_size: tuple[float, float], rail: LabelRect,
                          obstacles: Iterable[LabelRect], overflow: str,
                          required: bool) -> AnnotationBox | None:
    """Place an object-anchored callout in a dedicated annotation rail."""
    width, height = text_size
    if width > rail.width or height > rail.height:
        if overflow != "visible-overflow":
            return None
        box = LabelRect(rail.x, anchor_y - height / 2, width, height)
        return AnnotationBox(resolved, LabelPlacement("rail", box, True), True)
    occupied = tuple(obstacles)
    y = min(max(anchor_y - height / 2, rail.y), rail.bottom - height)
    candidates = [y]
    for index in range(1, int(rail.height // max(1.0, height)) + 1):
        candidates.extend((y + index * height, y - index * height))
    for candidate in candidates:
        box = LabelRect(rail.x, candidate, width, height)
        if rail.y <= box.y and box.bottom <= rail.bottom and not any(
            box.x < item.right and item.x < box.right and box.y < item.bottom and item.y < box.bottom
            for item in occupied
        ):
            return AnnotationBox(resolved, LabelPlacement("rail", box), True)
    if overflow != "visible-overflow":
        return None
    box = LabelRect(rail.x, anchor_y - height / 2, width, height)
    return AnnotationBox(resolved, LabelPlacement("rail", box, True), True)
