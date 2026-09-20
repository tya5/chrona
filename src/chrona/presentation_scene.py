"""Common presentation Scene composed before any SVG adapter is invoked."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Iterable

from .presentation_axis import AxisInterval, axis_intervals
from .presentation_marks import ComparisonMark, comparison_marks
from .presentation_lanes import LaneAssignment, LaneItem, LaneTrack, assign_stable_lanes, lane_tracks


@dataclass(frozen=True)
class PresentationScene:
    title: str
    window: tuple[date, date]
    axes: tuple[AxisInterval, ...]
    ticks: tuple[AxisInterval, ...]
    marks: tuple[ComparisonMark, ...]
    lanes: tuple[LaneAssignment, ...]
    lane_tracks: tuple[LaneTrack, ...]


def build_presentation_scene(title: str, items: Iterable[object], window: tuple[date, date], settings: dict) -> PresentationScene:
    """Build shared temporal primitives; adapters may only assign coordinates and emit output."""
    start, end = window
    axis = settings["layout"]["axis"]
    levels, heights = axis["levels"], axis["bandHeights"]
    order = {"quarter": 0, "month": 1, "week": 2, "day": 3}
    if len(levels) != len(heights) or len(set(levels)) != len(levels) or any(level not in order for level in levels) or levels != sorted(levels, key=order.__getitem__):
        raise ValueError("E_PRESENTATION_AXIS_INVALID")
    copied_items = tuple(items)
    axes = tuple(interval for level in levels for interval in axis_intervals(start, end, level))
    ticks = axis_intervals(start, end, axis["tickUnit"], tick_step=axis["tickStep"])
    marks = comparison_marks(copied_items, comparison_mode=settings["layout"]["bars"]["comparisonMode"], show_zero=settings["layout"]["variance"]["showZero"])
    lane_items = []
    for item in copied_items:
        planned = getattr(item, "planned")
        if getattr(item, "source_type") == "span":
            lane_items.append(LaneItem(str(getattr(item, "object_id")), str(getattr(item, "group_id", "")), planned["start"], planned["end"]))
        else:
            at = planned["at"]
            lane_items.append(LaneItem(str(getattr(item, "object_id")), str(getattr(item, "group_id", "")), at, at + timedelta(days=1)))
    group_order = tuple(dict.fromkeys(item.group_id for item in lane_items))
    lanes = assign_stable_lanes(lane_items, max_stack=settings["layout"]["lanes"]["maxStack"], group_order=group_order)
    lane_spec = settings["layout"]["lanes"]
    bar = settings["theme"]["bar"]
    mark_extent = (bar["plannedHeight"] + settings["layout"]["bars"]["gap"] + bar["actualHeight"]
                   if settings["layout"]["bars"]["comparisonMode"] == "stacked"
                   else max(bar["plannedHeight"], bar["actualHeight"]))
    tracks = lane_tracks(lanes, surface=lane_spec["surface"], mark_extent=mark_extent,
                         clearance=settings["layout"]["routing"]["clearance"], padding=lane_spec["trackPadding"])
    return PresentationScene(str(title), (start, end), axes, ticks, marks, lanes, tracks)


def presentation_scene_from_schedule(title: str, placements: dict[str, dict[str, date]], settings: dict) -> PresentationScene:
    """Adapt a resolved schedule to the shared Scene without making it authoritative."""
    if not placements:
        raise ValueError("E_PRESENTATION_MARK_INPUT")
    items = []
    dates: list[date] = []
    for object_id, placement in placements.items():
        source_type = "point" if "at" in placement else "span"
        items.append(SimpleNamespace(object_id=object_id, source_type=source_type, planned=placement, actual=None))
        dates.extend(placement.values())
    start, end = min(dates), max(dates)
    if start == end:
        end += timedelta(days=settings["layout"]["scale"]["singlePointSpanDays"])
    return build_presentation_scene(title, items, (start, end), settings)
