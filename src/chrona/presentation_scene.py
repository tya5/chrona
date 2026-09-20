"""Common presentation Scene composed before any SVG adapter is invoked."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from itertools import groupby
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
    projection_instance_id: str = ""
    surface_id: str = ""
    purpose: str = ""
    text: str | None = None
    baseline: tuple[float, float] | None = None
    z_order: int = 0


@dataclass(frozen=True)
class SceneSlot:
    """One resolved surface bound consumed verbatim by renderer adapters."""

    slot_id: str
    source: str
    scale_id: str | None
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class SceneRow:
    object_id: str
    group_id: str
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class SceneGroup:
    group_id: str
    header_bounds: tuple[float, float, float, float] | None
    content_bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class SceneSurface:
    """Resolved geometry for one public adapter route."""

    surface_id: str
    slots: tuple[SceneSlot, ...]
    rows: tuple[SceneRow, ...]
    groups: tuple[SceneGroup, ...]
    primitives: tuple[ScenePrimitive, ...] = ()


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
    rows: tuple[SceneRow, ...]
    groups: tuple[SceneGroup, ...]
    surfaces: tuple[SceneSurface, ...]


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


def _scene_rows(items: tuple[object, ...], slots: tuple[SceneSlot, ...], settings: dict) -> tuple[tuple[SceneRow, ...], tuple[SceneGroup, ...]]:
    """Resolve group headers and row bounds once for all surface adapters."""
    table = next(slot for slot in slots if slot.slot_id == "table")
    _, table_y, table_width, table_height = table.bounds
    axis_height = sum(settings["layout"]["axis"]["bandHeights"])
    mode = settings["layout"]["group"]["mode"]
    group_gap = settings["layout"]["group"]["gap"]
    header_height = settings["layout"]["group"]["headerHeight"] if mode == "header" else 0
    groups = [(group_id, tuple(group_items)) for group_id, group_items in groupby(items, lambda item: str(getattr(item, "group_id", "")))]
    available = table_height - axis_height - group_gap * max(0, len(groups) - 1) - header_height * len(groups)
    if available <= 0 or not items:
        raise ValueError("E_LAYOUT_REQUIRED_OVERFLOW:rows")
    row_height = available / len(items)
    y = table_y + axis_height
    rows: list[SceneRow] = []
    scene_groups: list[SceneGroup] = []
    for group_id, group_items in groups:
        header = (table.bounds[0], y, table_width, header_height) if header_height else None
        y += header_height
        content_y = y
        for item in group_items:
            rows.append(SceneRow(str(getattr(item, "object_id")), group_id, (table.bounds[0], y, table_width, row_height)))
            y += row_height
        scene_groups.append(SceneGroup(group_id, header, (table.bounds[0], content_y, table_width, row_height * len(group_items))))
        y += group_gap
    return tuple(rows), tuple(scene_groups)


def _linear_surface(surface_id: str, items: tuple[object, ...], window: tuple[date, date], settings: dict,
                    *, grouped: bool) -> SceneSurface:
    """Resolve legacy review/minimal coordinates before their adapters serialize them."""
    margins, viewport = settings["layout"]["margins"], settings["context"]["viewport"]
    left, top, row_height = margins["left"], margins["top"], settings["layout"]["row"]["height"]
    timeline_width = max(1, (window[1] - window[0]).days) * settings["layout"]["scale"]["dayWidth"]
    slots = (
        SceneSlot("title", "title", None, (left, 0, viewport["width"] - left - margins["right"], top)),
        SceneSlot(f"{surface_id}Timeline", "timeline", "primary", (left, top, timeline_width, viewport["height"] - top - margins["bottom"])),
        SceneSlot(f"{surface_id}Axis", "timeline-axis", "primary", (left, top, timeline_width, viewport["height"] - top - margins["bottom"])),
    )
    rows: list[SceneRow] = []
    groups: list[SceneGroup] = []
    y = top - row_height if grouped else top
    grouped_items = [(gid, tuple(group)) for gid, group in groupby(items, lambda item: str(getattr(item, "group_id", "")))] if grouped else [("", items)]
    for group_index, (group_id, group_items) in enumerate(grouped_items):
        if grouped and group_index:
            y += row_height
        header = None
        if grouped and settings["layout"]["group"]["mode"] in {"header-and-separator", "band", "header", "merged"}:
            header = (left, y, timeline_width, row_height)
            y += row_height
        content_y = y
        for item in group_items:
            y += row_height
            rows.append(SceneRow(str(getattr(item, "object_id")), group_id,
                                 (left, y - row_height / 2, timeline_width, row_height)))
        groups.append(SceneGroup(group_id, header, (left, content_y, timeline_width, y - content_y)))
    return SceneSurface(surface_id, slots, tuple(rows), tuple(groups))


def _surface_slot(surface: SceneSurface, source: str) -> SceneSlot:
    try:
        return next(slot for slot in surface.slots if slot.source == source)
    except StopIteration as error:
        raise ValueError("E_PRESENTATION_PRIMITIVE_MISSING") from error


def _surface_x(slot: SceneSlot, start: date, end: date, value: date) -> float:
    """Map a Date-only value into one completed surface slot, once."""
    x, _, width, _ = slot.bounds
    inset = min(20.0, width / 2.0)
    days = max(1, (end - start).days)
    return x + inset + (value - start).days / days * max(0.0, width - 2.0 * inset)


def _surface_primitives(surface: SceneSurface, title: str, items: tuple[object, ...],
                        window: tuple[date, date], axes: tuple[AxisInterval, ...],
                        ticks: tuple[AxisInterval, ...], marks: tuple[ComparisonMark, ...],
                        settings: dict) -> tuple[ScenePrimitive, ...]:
    """Emit core I3 geometry for one public surface before adapter selection."""
    title_slot, timeline, axis = (_surface_slot(surface, source) for source in ("title", "timeline", "timeline-axis"))
    start, end = window
    rows = {row.object_id: row for row in surface.rows}
    items_by_id = {str(getattr(item, "object_id")): item for item in items}
    primitives: list[ScenePrimitive] = []

    def add(kind: str, source_ref: str, source_kind: str, facet: str, role: str,
            purpose: str, bounds: tuple[float, float, float, float], *, text: str | None = None,
            baseline: tuple[float, float] | None = None) -> None:
        projection = f"{surface.surface_id}:{purpose}:{source_ref}:{facet}"
        primitives.append(ScenePrimitive(
            scene_id=f"{projection}:primitive", kind=kind, source_ref=source_ref,
            source_kind=source_kind, semantic_facet=facet, visual_role=role, bounds=bounds,
            projection_instance_id=projection, surface_id=surface.surface_id, purpose=purpose,
            text=text, baseline=baseline, z_order=len(primitives),
        ))

    title_height = float(settings["theme"]["typography"]["heading"]["size"])
    add("Text", "project", "project", "", "heading", "title-text",
        title_slot.bounds, text=title, baseline=(title_slot.bounds[0], title_slot.bounds[1] + title_height))

    band_heights = dict(zip(settings["layout"]["axis"]["levels"], settings["layout"]["axis"]["bandHeights"], strict=True))
    axis_y = axis.bounds[1]
    for level in settings["layout"]["axis"]["levels"]:
        level_axes = tuple(interval for interval in axes if interval.level == level)
        band_height = float(band_heights[level])
        for interval in level_axes:
            x1, x2 = _surface_x(axis, start, end, interval.start), _surface_x(axis, start, end, interval.end)
            source = f"axis:{interval.level}:{interval.index}"
            add("Rect", source, "axis", "axis", interval.level, "axis-band", (x1, axis_y, x2 - x1, band_height))
            add("Text", source, "axis", "axis", interval.level, "axis-label", (x1, axis_y, x2 - x1, band_height),
                text=interval.label, baseline=((x1 + x2) / 2.0, axis_y + band_height * 0.75))
        axis_y += band_height
    bottom = max((row.bounds[1] + row.bounds[3] for row in surface.rows), default=timeline.bounds[1] + timeline.bounds[3])
    for tick in ticks:
        x = _surface_x(axis, start, end, tick.start)
        add("Path", f"tick:{tick.level}:{tick.index}", "axis", "axis", tick.level, "tick", (x, axis.bounds[1], 0.0, bottom - axis.bounds[1]))

    planned_height = float(settings["theme"]["bar"]["plannedHeight"])
    actual_height = float(settings["theme"]["bar"]["actualHeight"])
    gap = float(settings["layout"]["bars"]["gap"])
    point_size = float(settings["theme"]["point"]["size"])
    comparison_mode = settings["layout"]["bars"]["comparisonMode"]
    for mark in marks:
        row = rows.get(mark.source_id)
        item = items_by_id.get(mark.source_id)
        if row is None or item is None:
            raise ValueError("E_PRESENTATION_PRIMITIVE_MISSING")
        _, row_y, _, row_height = row.bounds
        if mark.at is not None:
            x = _surface_x(timeline, start, end, mark.at)
            if mark.facet == "finish-delta":
                text = f"{mark.variance_days:+d}d"
                add("Text", mark.source_id, "object", mark.facet, "variance", "comparison-mark",
                    (x, row_y, max(1.0, point_size), row_height), text=text, baseline=(x, row_y + row_height * 0.75))
            else:
                add("Symbol", mark.source_id, "object", mark.facet, mark.facet, "comparison-mark",
                    (x - point_size / 2.0, row_y + (row_height - point_size) / 2.0, point_size, point_size))
            continue
        assert mark.start is not None and mark.end is not None
        x1, x2 = _surface_x(timeline, start, end, mark.start), _surface_x(timeline, start, end, mark.end)
        height = actual_height if mark.facet == "actual" else planned_height
        if mark.facet == "actual" and comparison_mode != "overlaid":
            y = row_y + row_height / 2.0 + gap / 2.0
        else:
            y = row_y + row_height / 2.0 - height - gap / 2.0
        add("Rect", mark.source_id, "object", mark.facet, mark.facet, "comparison-mark", (x1, y, max(0.0, x2 - x1), height))

    label_size = float(settings["theme"]["typography"]["body"]["size"])
    for object_id, row in rows.items():
        item = items_by_id.get(object_id)
        if item is None:
            raise ValueError("E_PRESENTATION_PRIMITIVE_MISSING")
        value = str(getattr(item, "title", object_id))
        add("Text", object_id, "object", "", "body", "item-label", row.bounds,
            text=value, baseline=(row.bounds[0], row.bounds[1] + row.bounds[3] / 2.0 + label_size * 0.35))
    return tuple(primitives)


def _scene_surfaces(items: tuple[object, ...], window: tuple[date, date], settings: dict,
                    slots: tuple[SceneSlot, ...], rows: tuple[SceneRow, ...], groups: tuple[SceneGroup, ...],
                    title: str, axes: tuple[AxisInterval, ...], ticks: tuple[AxisInterval, ...],
                    marks: tuple[ComparisonMark, ...]) -> tuple[SceneSurface, ...]:
    raw = (
        SceneSurface("table-timeline", slots, rows, groups),
        _linear_surface("review", items, window, settings, grouped=True),
        _linear_surface("minimal", items, window, settings, grouped=False),
    )
    return tuple(SceneSurface(surface.surface_id, surface.slots, surface.rows, surface.groups,
                              _surface_primitives(surface, title, items, window, axes, ticks, marks, settings))
                 for surface in raw)


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
    rows, groups = _scene_rows(copied_items, slots, settings)
    surfaces = _scene_surfaces(copied_items, (start, end), settings, slots, rows, groups, resolved.title, axes, ticks, marks)
    return PresentationScene(resolved.title, (start, end), axes, ticks, marks, lanes, tracks, primitives, slots, rows, groups, surfaces)


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
