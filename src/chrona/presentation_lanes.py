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


def assign_stable_lanes(items: Iterable[LaneItem], *, max_stack: int) -> tuple[LaneAssignment, ...]:
    """Use the lowest non-overlapping stack within each group, with stable ties."""
    if max_stack < 1:
        raise ValueError("E_PRESENTATION_STACK_OVERFLOW")
    result: list[LaneAssignment] = []
    by_group: dict[str, list[LaneItem]] = {}
    for item in items:
        if item.end <= item.start:
            raise ValueError("E_PRESENTATION_MARK_INPUT")
        by_group.setdefault(item.group_id, []).append(item)
    for group_id in sorted(by_group):
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
