"""Prove final mark/visual footprints equal the immutable preflight partition."""
from __future__ import annotations

from collections import defaultdict

from chrona.presentation.layout.lane_mark_facets import _mark_facets, _overlay_compound_facets, _with_mark_visuals
from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment
from chrona.presentation.layout.point_host_allocation import _translate
from chrona.presentation.layout.surface_geometry import GEOMETRY_TOLERANCE


def validate_point_host_frames(preflight, marks, icons, shapes, tracks, theme):
    """Use explicit source identities and facet order, never parse placement IDs."""
    allocation, plan = preflight.point_host_allocation, preflight.point_host_plan
    if allocation is None or plan is None:
        return
    frames = {frame.facet_id: frame for frame in allocation.frames}
    occurrences = {occurrence.instance: occurrence for occurrence in plan.occurrences}
    mark_by_id = {mark.placement_id: mark for mark in marks}
    track_by_id = {track.instance_id: track for track in tracks}
    icon_by_host, progress_by_host = defaultdict(list), defaultdict(list)
    for icon in icons:
        if icon.host_placement_id is not None:
            icon_by_host[icon.host_placement_id].append(icon)
    for shape in shapes:
        if shape.host_placement_id is not None and shape.semantic_id == "progressFill":
            progress_by_host[shape.host_placement_id].append(shape)
    verified = set()
    for unit in allocation.semantic_units:
        occurrence = occurrences[unit.projection_instance_id]
        for role in ("planned", "actual", "snapshot", "scenario", "missing-actual"):
            source_id, final_id = occurrence.source_mark_id(role), occurrence.final_mark_id(role)
            expected = [facet for facet in unit.facets if facet.mark_id == source_id]
            if not expected:
                continue
            mark = mark_by_id.get(final_id)
            if mark is None:
                _failure(source_id, "missing final mark")
            facets = _overlay_compound_facets(_mark_facets(
                occurrence.item, occurrence.instance, mark, theme))
            actual = _with_mark_visuals(occurrence.item, occurrence.instance, mark, facets,
                icon_by_host.get(final_id, ()), progress_by_host.get(final_id, ()), theme)
            if len(actual) != len(expected):
                _failure(source_id, "final facet count differs from source partition")
            for before, after in zip(expected, actual, strict=True):
                frame = frames[before.facet_id]
                owner = occurrences[frame.allocation_instance]
                track = track_by_id.get(owner.placement_key)
                if track is None:
                    _failure(before.facet_id, "missing physical allocation track")
                footprint = _translate(before.footprint, frame.block_offset + track.block)
                if before.purpose != after.purpose or not _equal(footprint, after.visible_footprint):
                    _failure(before.facet_id, "final footprint differs from allocated source frame")
                if before.facet_id in verified:
                    _failure(before.facet_id, "duplicate final facet")
                verified.add(before.facet_id)
    if verified != set(frames):
        _failure("/projection/items", "incomplete final physical facet partition")


def _equal(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, ObstacleRect):
        a, b = (left.left, left.top, left.right, left.bottom), (right.left, right.top, right.right, right.bottom)
    elif isinstance(left, ObstacleSegment):
        a, b = (*left.start, *left.end, left.stroke_width), (*right.start, *right.end, right.stroke_width)
    else:
        return False
    return all(abs(x - y) <= GEOMETRY_TOLERANCE for x, y in zip(a, b, strict=True))


def _failure(identity, reason):
    raise LayoutError("E_PRESENTATION_PLACEMENT_REQUIRED", "/projection/items",
                      node_id=identity, detail=f"physical host closure: {reason}")
