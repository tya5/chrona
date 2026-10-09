"""Annotation anchor, box, and leader geometry owned by surface Layout."""
from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from typing import Iterable

from chrona.presentation.layout.comparison_marks import ComparisonMark
from chrona.presentation.layout.labels import LabelPlacement, LabelRect, place_label
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.obstacles import ObstacleRect, SurfaceObstacleIndex
from chrona.presentation.layout.routing import route_orthogonal
from chrona.presentation.model.surface_content import AnnotationIntent


def _annotation_error(code: str, owner: str, **operands: object) -> ValueError:
    fields = []
    for name, value in operands.items():
        shown = repr(value).replace("\n", " ").replace("\r", " ")[:96]
        fields.append(f"{name}={shown}")
    return ValueError(f"{code}: {owner} " + ", ".join(fields))


def _anchor_error(annotation: AnnotationIntent, code: str, owner: str, **operands: object) -> LayoutError:
    """Keep anchor diagnostics typed and attached to the declared View pointer."""
    fields = []
    for name, value in operands.items():
        shown = repr(value).replace("\n", " ").replace("\r", " ")[:96]
        fields.append(f"{name}={shown}")
    return LayoutError(code, annotation.anchor_source_ref, detail=f"{owner}: " + ", ".join(fields))


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
                            obstacles: Iterable[LabelRect] | SurfaceObstacleIndex, limit: int,
                            port_ids: tuple[str, ...] = ()) -> tuple[tuple[float, float], ...]:
    """Return a bounded deterministic orthogonal visibility-grid leader route."""
    if limit < 1:
        raise _annotation_error("E_PRESENTATION_ROUTE_LIMIT", "leader route search",
                                state_limit=limit, source=source, target=target)
    index = obstacles if isinstance(obstacles, SurfaceObstacleIndex) else None
    if index is not None:
        return route_orthogonal(source, target, index, limit=limit, port_ids=port_ids)
    boxes = tuple(obstacles)
    xs = sorted({source[0], target[0], *(value for box in boxes for value in (box.x, box.right))})
    ys = sorted({source[1], target[1], *(value for box in boxes for value in (box.y, box.bottom))})
    start, end = (xs.index(source[0]), ys.index(source[1])), (xs.index(target[0]), ys.index(target[1]))
    queue, parents, seen = [(0, start)], {}, {start}; states = 0
    while queue:
        _, node = heappop(queue); states += 1
        if states > limit:
            raise _annotation_error("E_PRESENTATION_ROUTE_LIMIT", "leader route search",
                                    state_limit=limit, examined_states=states,
                                    source=source, target=target)
        if node == end:
            break
        for nxt in ((node[0]-1, node[1]), (node[0]+1, node[1]), (node[0], node[1]-1), (node[0], node[1]+1)):
            if not (0 <= nxt[0] < len(xs) and 0 <= nxt[1] < len(ys)) or nxt in seen:
                continue
            a, b = (xs[node[0]], ys[node[1]]), (xs[nxt[0]], ys[nxt[1]])
            blocked = any(
                (a[1] == b[1] and box.y < a[1] < box.bottom and max(a[0], b[0]) > box.x and min(a[0], b[0]) < box.right)
                or (a[0] == b[0] and box.x < a[0] < box.right and max(a[1], b[1]) > box.y and min(a[1], b[1]) < box.bottom)
                for box in boxes)
            if blocked:
                continue
            seen.add(nxt); parents[nxt] = node
            heappush(queue, (abs(xs[nxt[0]]-target[0]) + abs(ys[nxt[1]]-target[1]), nxt))
    if end not in seen:
        raise _annotation_error("E_PRESENTATION_ROUTE_LIMIT", "leader route search",
                                state_limit=limit, source=source, target=target,
                                obstacle_count=len(boxes))
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
        raise _anchor_error(annotation, "E_PRESENTATION_ANCHOR_UNSUPPORTED", "annotation anchor",
                            annotation_id=annotation.annotation_id,
                            anchor_kind=anchor.get("kind"), expected="object anchor")
    object_id, facet, endpoint = anchor.get("id"), anchor.get("facet"), anchor.get("endpoint")
    if not isinstance(object_id, str) or facet not in {"planned", "actual"} or endpoint not in {"start", "end", "finish", "at", "body"}:
        field = ("id" if not isinstance(object_id, str) else
                 "facet" if facet not in {"planned", "actual"} else "endpoint")
        raise _anchor_error(annotation, "E_PRESENTATION_ANCHOR_MISSING", "annotation anchor fields",
                            annotation_id=annotation.annotation_id, object_id=object_id,
                            facet=facet, endpoint=endpoint, missing_or_invalid=field,
                            expected="id string, facet planned|actual, endpoint start|end|finish|at|body")
    candidates = [mark for mark in marks if mark.source_id == object_id and mark.facet == facet]
    if not candidates:
        raise _anchor_error(annotation, "E_PRESENTATION_ANCHOR_MISSING", "annotation target mark",
                            annotation_id=annotation.annotation_id, object_id=object_id,
                            facet=facet, endpoint=endpoint,
                            reason=f"no completed {facet} mark exists for this object")
    mark = candidates[0]
    if endpoint == "start" and mark.start is None:
        raise _anchor_error(annotation, "E_PRESENTATION_ANCHOR_MISSING", "mark endpoint",
                            annotation_id=annotation.annotation_id, object_id=object_id,
                            facet=facet, endpoint=endpoint, reason="selected mark has no start date")
    if endpoint in {"finish", "end"} and mark.end is None:
        raise _anchor_error(annotation, "E_PRESENTATION_ANCHOR_MISSING", "mark endpoint",
                            annotation_id=annotation.annotation_id, object_id=object_id,
                            facet=facet, endpoint=endpoint, reason="selected mark has no finish date")
    if endpoint == "at" and mark.at is None:
        raise _anchor_error(annotation, "E_PRESENTATION_ANCHOR_MISSING", "mark endpoint",
                            annotation_id=annotation.annotation_id, object_id=object_id,
                            facet=facet, endpoint=endpoint, reason="selected mark has no point date")
    return AnnotationAnchor(annotation.annotation_id, object_id, facet, "finish" if endpoint == "end" else endpoint, mark)  # `end` aliases `finish`: the text is in Scene ids


def project_annotation_box(annotation: AnnotationIntent, resolved: AnnotationAnchor, *, anchor_bounds: LabelRect,
                           text_size: tuple[float, float], candidate_sides: Iterable[str],
                           viewport: LabelRect, obstacles: Iterable[LabelRect] | SurfaceObstacleIndex, overflow: str,
                           required: bool = True) -> AnnotationBox | None:
    """Place one measured annotation box without assigning renderer semantics."""
    purpose = annotation.purpose
    if purpose not in {"callout", "note", "highlight", "explanatory-arrow"}:
        raise _annotation_error("E_PRESENTATION_ANCHOR_UNSUPPORTED", "annotation purpose",
                                annotation_id=annotation.annotation_id, purpose=purpose)
    placement = place_label(anchor_bounds, text_size, candidate_sides, bounds=viewport,
                            obstacles=obstacles, required=required, overflow=overflow)
    if placement is None:
        return None
    alignment = annotation.alignment
    if alignment not in {"start", "center", "end"}:
        raise _annotation_error("E_PRESENTATION_LABEL_INPUT", "annotation alignment",
                                annotation_id=annotation.annotation_id, alignment=alignment,
                                purpose=purpose)
    box = placement.bounds
    if alignment != "center":
        if placement.side in {"above", "below"}:
            x = anchor_bounds.x if alignment == "start" else anchor_bounds.right - box.width
            box = LabelRect(x, box.y, box.width, box.height)
        else:
            y = anchor_bounds.y if alignment == "start" else anchor_bounds.bottom - box.height
            box = LabelRect(box.x, y, box.width, box.height)
        intersects = (bool(obstacles.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom)))
                      if isinstance(obstacles, SurfaceObstacleIndex)
                      else any(box.x < item.right and item.x < box.right and box.y < item.bottom and item.y < box.bottom
                               for item in obstacles))
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
                          obstacles: Iterable[LabelRect] | SurfaceObstacleIndex, overflow: str,
                          required: bool) -> AnnotationBox | None:
    """Place an object-anchored callout in a dedicated annotation rail."""
    candidates = annotation_rail_candidates(annotation, resolved, anchor_y=anchor_y,
                                            text_size=text_size, rail=rail, obstacles=obstacles)
    if candidates:
        return candidates[0]
    if overflow != "visible-overflow":
        return None
    width, height = text_size
    box = LabelRect(rail.x, anchor_y - height / 2, width, height)
    return AnnotationBox(resolved, LabelPlacement("rail", box, True), True)


def annotation_rail_candidates(annotation: AnnotationIntent, resolved: AnnotationAnchor, *,
                               anchor_y: float, text_size: tuple[float, float], rail: LabelRect,
                               obstacles: Iterable[LabelRect] | SurfaceObstacleIndex,
                               allow_inline_overflow: bool = False) -> tuple[AnnotationBox, ...]:
    """Enumerate finite full-frame rail positions before connector commitment.

    Only visible-overflow completion may allow natural inline overhang. It
    still checks the whole frame against the shared obstacle inventory.
    """
    width, height = text_size
    if (width > rail.width and not allow_inline_overflow) or height > rail.height:
        return ()
    index = obstacles if isinstance(obstacles, SurfaceObstacleIndex) else None
    occupied = () if index is not None else tuple(obstacles)
    aligned = min(max(anchor_y - height / 2, rail.y), rail.bottom - height)
    positions = [aligned]
    for step in range(1, int(rail.height // max(1.0, height)) + 1):
        positions.extend((aligned + step * height, aligned - step * height))
    candidates = []
    for position in positions:
        box = LabelRect(rail.x, position, width, height)
        collides = (bool(index.collisions(ObstacleRect(box.x, box.y, box.right, box.bottom)))
                    if index is not None else any(
                        box.x < item.right and item.x < box.right and box.y < item.bottom and item.y < box.bottom
                        for item in occupied))
        if rail.y <= box.y and box.bottom <= rail.bottom and not collides:
            candidates.append(AnnotationBox(resolved, LabelPlacement("rail", box, width > rail.width), True))
    return tuple(candidates)
