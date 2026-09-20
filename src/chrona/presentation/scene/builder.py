"""Deterministic construction of completed presentation scenes."""
from __future__ import annotations

from dataclasses import replace
from datetime import date, timedelta
from itertools import groupby
from types import SimpleNamespace
from typing import Iterable

from chrona.presentation.layout.axis import AxisInterval, axis_intervals
from chrona.presentation.layout.constraints import solve_presentation_layout
from chrona.presentation.layout.lanes import LaneAssignment, LaneItem, LaneTrack, assign_stable_lanes, lane_tracks
from chrona.presentation.model.surface_content import ResolvedPresentationInput, SurfaceContentInput
from chrona.presentation.scene.marks import ComparisonMark, comparison_marks
from chrona.presentation.scene.model import ContentFamilyCounts, PresentationScene, SceneGroup, SceneManifest, ScenePrimitive, SceneRow, SceneSlot, SceneSurface
from chrona.presentation.scene.paint import resolve_facet_paint
from chrona.presentation.scene.surface_builder import _surface_primitives, _surface_scale_manifest

def _resolved_input(title: str, items: Iterable[object], window: tuple[date, date], settings: dict,
                    surface_content: SurfaceContentInput | None) -> ResolvedPresentationInput:
    copied_items = tuple(items)
    content = surface_content or SurfaceContentInput()
    if not content.template_values:
        last_visible = window[1] - timedelta(days=1) if window[1].day == 1 and window[1] > window[0] else window[1]
        values = (("title", str(title)), ("windowStart", f"{window[0]:%b %Y}"),
                  ("windowLastVisible", f"{last_visible:%b %Y}"),
                  ("selectedCount", str(len(copied_items))), ("unmatchedCount", "0"),
                  ("missingCount", str(sum(1 for item in copied_items if not getattr(item, "actual", None)))))
        content = replace(content, template_values=values)
    return ResolvedPresentationInput(str(title), window, copied_items, settings, content)


def _validate_primitive(node: ScenePrimitive) -> None:
    if node.kind == "Text" and (node.text is None or node.text_layout is None):
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    if node.kind == "Symbol" and not node.shape:
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    if node.corner_radius is not None:
        if node.kind != "Rect" or node.corner_radius < 0 or node.corner_radius > min(node.bounds[2], node.bounds[3]) / 2.0:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    if node.stack_index is not None and (node.stack_index < 0 or node.lane_group_id is None):
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    if node.kind == "Path":
        if len(node.points) < 2:
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
        connector = node.purpose in {"dependency-connector", "annotation-leader", "explanatory-arrow"}
        if connector and (not node.from_port_id or not node.to_port_id):
            raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")
    elif node.points or node.from_port_id or node.to_port_id:
        raise ValueError("E_PRESENTATION_PRIMITIVE_INVALID")


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
        item = next(value for value in resolved.items if str(getattr(value, "object_id")) == mark.source_id)
        paint = (resolve_facet_paint(resolved.settings["theme"], str(getattr(item, "group_id", "")), mark.facet)
                 if kind in {"Rect", "Symbol"} else None)
        primitives.append(ScenePrimitive(f"{projection_id}:mark", kind, mark.source_id, "object", mark.facet, mark.facet, bounds,
                                         shape=resolved.settings["theme"]["point"]["shape"] if kind == "Symbol" else None,
                                         color=str(paint["color"]) if paint else None,
                                         opacity=float(paint["opacity"]) if paint else None))
    return tuple(primitives)


def _scene_slots(settings: dict) -> tuple[SceneSlot, ...]:
    """Resolve surface bounds once; adapters must not invoke the layout solver again."""
    bounds = solve_presentation_layout(settings)
    declarations = settings["layout"]["slots"]
    return tuple(SceneSlot(slot_id, declarations[slot_id]["source"], declarations[slot_id].get("scaleId"),
                           (rect.x, rect.y, rect.width, rect.height),
                           str(declarations[slot_id]["priority"]), str(declarations[slot_id]["overflow"]))
                 for slot_id, rect in bounds.items())


def _scene_rows(items: tuple[object, ...], slots: tuple[SceneSlot, ...], settings: dict) -> tuple[tuple[SceneRow, ...], tuple[SceneGroup, ...]]:
    """Resolve group headers and row bounds once for all surface adapters."""
    table = next(slot for slot in slots if slot.slot_id == "table")
    _, table_y, table_width, table_height = table.bounds
    axis_height = sum(settings["layout"]["axis"]["bandHeights"])
    mode = settings["layout"]["group"]["mode"]
    group_gap = settings["layout"]["group"]["gap"]
    header_modes = {"header", "header-and-separator", "band", "merged"}
    header_height = settings["layout"]["group"]["headerHeight"] if mode in header_modes else 0
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
                    *, grouped: bool, optional_slots: tuple[SceneSlot, ...] = ()) -> SceneSurface:
    """Resolve legacy review/minimal coordinates before their adapters serialize them."""
    margins, viewport = settings["layout"]["margins"], settings["context"]["viewport"]
    left, top, row_height = margins["left"], margins["top"], settings["layout"]["row"]["height"]
    timeline_width = max(1, (window[1] - window[0]).days) * settings["layout"]["scale"]["dayWidth"]
    slots = (
        SceneSlot("title", "title", None, (left, 0, viewport["width"] - left - margins["right"], top)),
        SceneSlot(f"{surface_id}Timeline", "timeline", "primary", (left, top, timeline_width, viewport["height"] - top - margins["bottom"])),
        SceneSlot(f"{surface_id}Axis", "timeline-axis", "primary", (left, top, timeline_width, viewport["height"] - top - margins["bottom"])),
        *optional_slots,
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
    return SceneSurface(surface_id, slots, tuple(rows), tuple(groups),
                        _surface_scale_manifest(surface_id, slots, window))



def _scene_surfaces(items: tuple[object, ...], window: tuple[date, date], settings: dict,
                    slots: tuple[SceneSlot, ...], rows: tuple[SceneRow, ...], groups: tuple[SceneGroup, ...],
                    title: str, axes: tuple[AxisInterval, ...], ticks: tuple[AxisInterval, ...],
                    marks: tuple[ComparisonMark, ...], lanes: tuple[LaneAssignment, ...],
                    tracks: tuple[LaneTrack, ...], content: SurfaceContentInput) -> tuple[SceneSurface, ...]:
    raw = (
        SceneSurface("table-timeline", slots, rows, groups,
                     _surface_scale_manifest("table-timeline", slots, window)),
        _linear_surface("review", items, window, settings, grouped=True,
                        optional_slots=tuple(slot for slot in slots if slot.source == "summary")),
        _linear_surface("minimal", items, window, settings, grouped=False),
    )
    return tuple(SceneSurface(surface.surface_id, surface.slots, surface.rows, surface.groups,
                              surface.scale_manifest,
                              _surface_primitives(surface, title, items, window, axes, ticks, marks, lanes, tracks,
                                                  settings, content))
                 for surface in raw)


def _scene_manifest(resolved: ResolvedPresentationInput,
                    surfaces: tuple[SceneSurface, ...]) -> SceneManifest:
    viewport = resolved.settings["context"]["viewport"]
    identities = tuple(
        str(asset["contentIdentity"])
        for asset in resolved.settings["context"]["fontMetrics"]["assets"]
    )
    content = resolved.surface_content
    return SceneManifest(
        version="chrona/presentation-scene-manifest/v0.1",
        settings_version=str(resolved.settings["version"]),
        viewport=(float(viewport["width"]), float(viewport["height"])),
        selected_object_ids=tuple(str(getattr(item, "object_id")) for item in resolved.items),
        font_asset_identities=identities,
        content_family_counts=ContentFamilyCounts(
            relations=len(content.relations),
            annotations=len(content.annotations),
            notes=len(content.notes),
            legend_entries=len(content.legend_entries),
            summary_panels=len(content.summary_panels),
            group_details=len(content.group_details),
            milestones=len(content.milestones),
            observation_rows=len(content.observation_rows),
        ),
        surface_scales=tuple(surface.scale_manifest for surface in surfaces),
    )


def build_presentation_scene(title: str, items: Iterable[object], window: tuple[date, date], settings: dict,
                             surface_content: SurfaceContentInput | None = None) -> PresentationScene:
    """Build a completed shared Scene; adapters may only serialize its primitives."""
    resolved = _resolved_input(title, items, window, settings, surface_content)
    start, end = resolved.window
    axis = settings["layout"]["axis"]
    levels, heights = axis["levels"], axis["bandHeights"]
    order = {"year": 0, "quarter": 1, "month": 2, "week": 3, "day": 4}
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
    surfaces = _scene_surfaces(copied_items, (start, end), settings, slots, rows, groups, resolved.title, axes, ticks, marks,
                              lanes, tracks, resolved.surface_content)
    manifest = _scene_manifest(resolved, surfaces)
    return PresentationScene(resolved.title, (start, end), axes, ticks, marks, lanes, tracks,
                             primitives, slots, rows, groups, surfaces, manifest, ())


def presentation_scene_from_schedule(title: str, placements: dict[str, dict[str, date]], settings: dict,
                                     labels: dict[str, str] | None = None,
                                     surface_content: SurfaceContentInput | None = None) -> PresentationScene:
    """Adapt a resolved schedule to the shared Scene without making it authoritative."""
    if not placements:
        raise ValueError("E_PRESENTATION_MARK_INPUT")
    items = []
    dates: list[date] = []
    for object_id, placement in placements.items():
        source_type = "point" if "at" in placement else "span"
        items.append(SimpleNamespace(object_id=object_id, title=(labels or {}).get(object_id, object_id),
                                     source_type=source_type, planned=placement, actual=None,
                                     group_id="", group_label=""))
        dates.extend(placement.values())
    start, end = min(dates), max(dates)
    if start == end:
        end += timedelta(days=settings["layout"]["scale"]["singlePointSpanDays"])
    return build_presentation_scene(title, items, (start, end), settings, surface_content)
