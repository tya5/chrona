"""Conservative Layout-owned reconstruction and reanchoring of prior routes."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from math import hypot

from chrona.presentation.layout.model import Rect
from chrona.presentation.layout.ports import ConnectorEgress, connector_egress_candidates
from chrona.presentation.layout.relation_terminals import complete_centred_terminals
from chrona.presentation.layout.routing import route_self_overlaps
from chrona.presentation.layout.relation_shapes import first_fit_port_pairs

TOLERANCE = 1e-6


@dataclass(frozen=True)
class HintCandidate:
    pair: tuple
    middle: tuple


@dataclass(frozen=True)
class HintProposal:
    disposition: str
    reason: str
    candidates: tuple[HintCandidate, ...] = ()


def _equal(left, right):
    return len(left) == len(right) and all(abs(a - b) <= TOLERANCE
        for first, second in zip(left, right) for a, b in zip(first, second))


def _side(points, *, source):
    origin, neighbor = (points[0], points[1]) if source else (points[-1], points[-2])
    dx, dy = neighbor[0] - origin[0], neighbor[1] - origin[1]
    if abs(dx) <= TOLERANCE and abs(dy) > TOLERANCE:
        return "below" if dy > 0 else "above"
    if abs(dy) <= TOLERANCE and abs(dx) > TOLERANCE:
        return "end" if dx > 0 else "start"
    return None


def _old_mark(current, old):
    # Unknown primitive families cannot prove old temporal port geometry.
    if (old.source_ref != current.source_ref
            or current.mark_shape == "point" and old.kind != "Symbol"
            or current.mark_shape != "point" and old.kind != "Rect"):
        return None
    x, y, width, height = old.bounds
    bounds = Rect(*(Decimal(str(value)) for value in old.bounds))
    return replace(current, bounds=bounds, start_port=(x, y + height / 2),
                   end_port=(x + width, y + height / 2))


def _marker_compatible(old, current):
    if old is None or current is None:
        return old is None and current is None
    outline = tuple((command.kind, command.points) for command in current.outline)
    return (old.outline == outline and old.head_length == current.head_length
            and old.head_width == current.head_width and old.paint_mode == current.paint_mode)


def _unpainted_port(prior, *, source, marker):
    origin, neighbor = (prior.points[0], prior.points[1]) if source else (prior.points[-1], prior.points[-2])
    length = hypot(neighbor[0] - origin[0], neighbor[1] - origin[1])
    if length <= TOLERANCE:
        return None
    old = prior.marker_start if source else prior.marker_end
    shift = 0.0
    if marker is not None and marker.centred:
        shift = (old.head_length / 2 - old.attachment_offset if source else
                 old.attachment_offset - old.head_length / 2)
        if len(prior.points) > 2:
            # Multi-leg trimming ignores attachment offsets and clamps at half
            # the original leg; the remaining drawn leg proves that clamp.
            shift = min(old.head_length / 2, length)
    return (origin[0] - (neighbor[0] - origin[0]) * shift / length,
            origin[1] - (neighbor[1] - origin[1]) * shift / length)


def _on_segment(point, left, right):
    if abs(left[0] - right[0]) <= TOLERANCE:
        return abs(point[0] - left[0]) <= TOLERANCE and min(left[1], right[1]) - TOLERANCE <= point[1] <= max(left[1], right[1]) + TOLERANCE
    if abs(left[1] - right[1]) <= TOLERANCE:
        return abs(point[1] - left[1]) <= TOLERANCE and min(left[0], right[0]) - TOLERANCE <= point[0] <= max(left[0], right[0]) + TOLERANCE
    return False


def _after(points, exposed):
    for index, (left, right) in enumerate(zip(points, points[1:])):
        if _on_segment(exposed, left, right):
            return (exposed, *(point for point in points[index + 1:] if point != exposed))
    return None


def _reanchor(points, source, target):
    first_delta = (source[0] - points[0][0], source[1] - points[0][1])
    last_delta = (target[0] - points[-1][0], target[1] - points[-1][1])
    if _equal((first_delta,), (last_delta,)):
        return tuple((x + first_delta[0], y + first_delta[1]) for x, y in points)
    result = list(points)
    result[0], result[-1] = source, target
    if len(points) == 2:
        return tuple(result) if _side(result, source=True) == _side(points, source=True) else None
    if abs(points[1][0] - points[0][0]) <= TOLERANCE:
        result[1] = (source[0], result[1][1])
    else:
        result[1] = (result[1][0], source[1])
    if abs(points[-2][0] - points[-1][0]) <= TOLERANCE:
        result[-2] = (target[0], result[-2][1])
    else:
        result[-2] = (result[-2][0], target[1])
    return tuple(result)


def propose_hint(hints, *, surface_id, source_ref, source_id, target_id,
                 source_mark, target_mark, source_endpoint, target_endpoint,
                 source_siblings, target_siblings, port_pairs, marker_start, marker_end, stroke_width):
    """Return one proposal, never an acceptance verdict or a route search."""
    if not hints.has_endpoint_identity:
        return HintProposal("unusable", "missing-endpoint-identity")
    surfaces = tuple(item for item in hints.surfaces if item.surface_id == surface_id)
    if len(surfaces) != 1:
        return HintProposal("absent" if not surfaces else "unusable", "surface-identity")
    surface = surfaces[0]
    matches = tuple(item for item in surface.relations if (item.source_ref, item.from_instance_id,
        item.to_instance_id) == (source_ref, source_id, target_id))
    if len(matches) != 1:
        return HintProposal("absent" if not matches else "unusable", "relation-identity")
    prior = matches[0]
    if len(prior.points) < 2 or any(_side((a, b), source=True) is None for a, b in zip(prior.points, prior.points[1:])):
        return HintProposal("unusable", "unsupported-shape")
    if not _marker_compatible(prior.marker_start, marker_start) or not _marker_compatible(prior.marker_end, marker_end):
        return HintProposal("unusable", "terminal-semantics")
    old_by_id = {item.placement_id: item for item in surface.marks}
    if len(old_by_id) != len(surface.marks):
        return HintProposal("unusable", "ambiguous-mark-identity")
    candidates = []
    for current, endpoint, siblings, toward, source in (
        (source_mark, source_endpoint, source_siblings, prior.points[-1], True),
        (target_mark, target_endpoint, target_siblings, prior.points[0], False)):
        if current is None:
            if not hints.terminal_provenance_compatible:
                return HintProposal("unusable", "unpainted-terminal-provenance")
            point = _unpainted_port(prior, source=source, marker=marker_start if source else marker_end)
            sides = {pair[0 if source else 1].side for pair in port_pairs}
            if point is None or len(sides) != 1:
                return HintProposal("unusable", "ambiguous-unpainted-port")
            candidates.append((ConnectorEgress(next(iter(sides)), point, point, ()),))
            continue
        old = old_by_id.get(current.placement_id)
        restored = _old_mark(current, old) if old is not None else None
        if restored is None:
            return HintProposal("unusable", "host-geometry")
        restored_siblings = tuple(mark for sibling in siblings
            if (old_sibling := old_by_id.get(sibling.placement_id)) is not None
            and (mark := _old_mark(sibling, old_sibling)) is not None)
        candidates.append(connector_egress_candidates(restored, endpoint, toward, restored_siblings))
    source_boundary = source_mark is not None and (source_mark.mark_shape == "point" or source_endpoint in {"at", "body"})
    target_boundary = target_mark is not None and (target_mark.mark_shape == "point" or target_endpoint in {"at", "body"})
    reconstructed = {}
    for left in candidates[0]:
        for right in candidates[1]:
            semantic = (left.semantic_port, *prior.points[1:-1], right.semantic_port)
            drawn, _, _ = complete_centred_terminals(semantic, marker_start, marker_end, stroke_width)
            if _equal(drawn, prior.points):
                key = (left.semantic_port, right.semantic_port,
                       left.side if source_boundary else None, right.side if target_boundary else None)
                reconstructed.setdefault(key, (left, right, semantic))
    if len(reconstructed) != 1:
        return HintProposal("unusable", "ambiguous-port-inverse")
    old_source, old_target, semantic = next(iter(reconstructed.values()))
    choices = []
    reason = "unadmitted-boundary"
    for pair in first_fit_port_pairs(port_pairs):
        if ((source_boundary and pair[0].side != old_source.side)
                or (target_boundary and pair[1].side != old_target.side)):
            continue
        anchored = _reanchor(semantic, pair[0].semantic_port, pair[1].semantic_port)
        if (anchored is None or route_self_overlaps(anchored)
                or any(_side((a, b), source=True) is None for a, b in zip(anchored, anchored[1:]))
                or _side(anchored, source=True) != _side(semantic, source=True)
                or _side(anchored, source=False) != _side(semantic, source=False)):
            reason = "shape-degenerated"
            continue
        middle = _after(anchored, pair[0].exposed_port)
        middle = _after(tuple(reversed(middle)), pair[1].exposed_port) if middle else None
        if middle is None:
            reason = "changed-egress-corridor"
            continue
        candidate = HintCandidate(pair, tuple(reversed(middle)))
        if candidate not in choices:
            choices.append(candidate)
    return (HintProposal("proposed", "reanchored", tuple(choices)) if choices
            else HintProposal("invalidated", reason))
