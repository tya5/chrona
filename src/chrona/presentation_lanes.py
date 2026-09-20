"""Stable, group-preserving lane stacking for projected presentation marks."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class LaneItem:
    object_id: str
    group_id: str
    start: date
    end: date
    label_start: date | None = None
    label_end: date | None = None
    required_label: bool = False


@dataclass(frozen=True)
class LaneAssignment:
    object_id: str
    group_id: str
    stack: int


@dataclass(frozen=True)
class LaneTrack:
    """Derived geometry contract for one independent logical lane."""
    group_id: str
    stack_count: int
    mark_extent: float
    pitch: float
    height: float


def assign_stable_lanes(items: Iterable[LaneItem], *, max_stack: int,
                        group_order: Iterable[str] | None = None) -> tuple[LaneAssignment, ...]:
    """Use the lowest non-overlapping stack within each group, with stable ties."""
    if max_stack < 1:
        raise ValueError("E_PRESENTATION_STACK_OVERFLOW")
    result: list[LaneAssignment] = []
    by_group: dict[str, list[LaneItem]] = {}
    for item in items:
        if item.end <= item.start:
            raise ValueError("E_PRESENTATION_MARK_INPUT")
        by_group.setdefault(item.group_id, []).append(item)
    ordered_groups = tuple(group_order) if group_order is not None else tuple(sorted(by_group))
    if set(ordered_groups) != set(by_group):
        raise ValueError("E_PRESENTATION_MARK_INPUT")
    for group_id in ordered_groups:
        occupied: list[list[tuple[date, date]]] = []
        for item in sorted(by_group[group_id], key=lambda item: (item.start, item.object_id)):
            start = min(item.start, item.label_start) if item.required_label and item.label_start else item.start
            end = max(item.end, item.label_end) if item.required_label and item.label_end else item.end
            stack = next((index for index, ranges in enumerate(occupied)
                          if all(end <= left or right <= start for left, right in ranges)), None)
            if stack is None:
                if len(occupied) >= max_stack:
                    raise ValueError("E_PRESENTATION_STACK_OVERFLOW")
                occupied.append([]); stack = len(occupied) - 1
            occupied[stack].append((start, end))
            result.append(LaneAssignment(item.object_id, group_id, stack))
    return tuple(result)


def lane_tracks(assignments: Iterable[LaneAssignment], *, surface: str, mark_extent: float,
                clearance: float, padding: float) -> tuple[LaneTrack, ...]:
    """Derive independent track heights without changing lane membership or order."""
    if surface not in {"row-aligned", "independent-lane-track"} or mark_extent <= 0 or clearance < 0 or padding < 0:
        raise ValueError("E_PRESENTATION_STACK_SURFACE_INCOMPATIBLE")
    grouped: dict[str, list[LaneAssignment]] = {}
    for assignment in assignments:
        grouped.setdefault(assignment.group_id, []).append(assignment)
    if surface == "row-aligned":
        return ()
    pitch = mark_extent + clearance
    return tuple(LaneTrack(group_id, max(item.stack for item in values) + 1, mark_extent, pitch,
                           2 * padding + mark_extent + (max(item.stack for item in values) * pitch))
                 for group_id, values in grouped.items())


def lane_stack_offset(track: LaneTrack, *, stack: int, padding: float) -> float:
    """Map a Scene stack index to an independent-track y offset, without reordering."""
    if stack < 0 or stack >= track.stack_count or padding < 0:
        raise ValueError("E_PRESENTATION_STACK_OVERFLOW")
    return padding + stack * track.pitch
