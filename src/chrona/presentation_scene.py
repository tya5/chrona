"""Common presentation Scene composed before any SVG adapter is invoked."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from types import SimpleNamespace
from typing import Iterable

from .presentation_axis import AxisInterval, axis_intervals
from .presentation_marks import ComparisonMark, comparison_marks
from .presentation_lanes import LaneAssignment, LaneItem, LaneTrack, assign_stable_lanes, lane_tracks
from .presentation_layout import solve_presentation_layout


@dataclass(frozen=True)
class ResolvedPresentationInput:
    """One derived input boundary between authoring resources and Scene geometry."""

    title: str
    window: tuple[date, date]
    items: tuple[object, ...]
    settings: dict


@dataclass(frozen=True)
class ScenePrimitive:
    """A measured renderer-neutral primitive; adapters serialize but never reinterpret it."""

    scene_id: str
    kind: str
    source_ref: str
    source_kind: str
    semantic_facet: str
    visual_role: str
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class SceneSlot:
    """One resolved surface bound consumed verbatim by renderer adapters."""

    slot_id: str
    source: str
    scale_id: str | None
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class PresentationScene:
    title: str
    window: tuple[date, date]
    axes: tuple[AxisInterval, ...]
    ticks: tuple[AxisInterval, ...]
    marks: tuple[ComparisonMark, ...]
    lanes: tuple[LaneAssignment, ...]
    lane_tracks: tuple[LaneTrack, ...]
    primitives: tuple[ScenePrimitive, ...]
    slots: tuple[SceneSlot, ...]


def _resolved_input(title: str, items: Iterable[object], window: tuple[date, date], settings: dict) -> ResolvedPresentationInput:
    return ResolvedPresentationInput(str(title), window, tuple(items), settings)


def _scene_primitives(resolved: ResolvedPresentationInput, axes: tuple[AxisInterval, ...],
                      marks: tuple[ComparisonMark, ...]) -> tuple[ScenePrimitive, ...]:
    """Materialize stable Scene identity and geometry before any renderer adapter."""
    start, end = resolved.window
    width = float(resolved.settings["context"]["viewport"]["width"])
    day_width = float(resolved.settings["layout"]["scale"]["dayWidth"])
    available = max(day_width, width - 2 * float(resolved.settings["layout"]["margins"]["left"]))
    days = max(1, (end - start).days)
    scale = available / days
    primitives: list[ScenePrimitive] = []
    for interval in axes:
        x = (interval.start - start).days * scale
        w = max(scale, (interval.end - interval.start).days * scale)
        scene_id = f"axis:primary:{interval.level}:{interval.index}:band"
        primitives.append(ScenePrimitive(scene_id, "Rect", "view:window", "axis", "axis", interval.level, (x, 0.0, w, 1.0)))
    for mark in marks:
        projection_id = f"timeline:{mark.source_id}:{mark.facet}"
        if mark.at is not None:
            x = (mark.at - start).days * scale
            bounds = (x, 0.0, 0.0, 0.0)
            kind = "Symbol" if mark.facet != "finish-delta" else "Text"
        else:
            assert mark.start is not None and mark.end is not None
            x = (mark.start - start).days * scale
            bounds = (x, 0.0, max(scale, (mark.end - mark.start).days * scale), 0.0)
            kind = "Rect"
        primitives.append(ScenePrimitive(f"{projection_id}:mark", kind, mark.source_id, "object", mark.facet, mark.facet, bounds))
    return tuple(primitives)


def _scene_slots(settings: dict) -> tuple[SceneSlot, ...]:
    """Resolve surface bounds once; adapters must not invoke the layout solver again."""
    bounds = solve_presentation_layout(settings)
    declarations = settings["layout"]["slots"]
    return tuple(SceneSlot(slot_id, declarations[slot_id]["source"], declarations[slot_id].get("scaleId"),
                           (rect.x, rect.y, rect.width, rect.height))
                 for slot_id, rect in bounds.items())


def build_presentation_scene(title: str, items: Iterable[object], window: tuple[date, date], settings: dict) -> PresentationScene:
    """Build a completed shared Scene; adapters may only serialize its primitives."""
    resolved = _resolved_input(title, items, window, settings)
    start, end = resolved.window
    axis = settings["layout"]["axis"]
    levels, heights = axis["levels"], axis["bandHeights"]
    order = {"quarter": 0, "month": 1, "week": 2, "day": 3}
    if len(levels) != len(heights) or len(set(levels)) != len(levels) or any(level not in order for level in levels) or levels != sorted(levels, key=order.__getitem__):
        raise ValueError("E_PRESENTATION_AXIS_INVALID")
    copied_items = resolved.items
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
    primitives = _scene_primitives(resolved, axes, marks)
    slots = _scene_slots(settings)
    return PresentationScene(resolved.title, (start, end), axes, ticks, marks, lanes, tracks, primitives, slots)


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
