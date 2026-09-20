"""Common presentation Scene composed before any SVG adapter is invoked."""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
from itertools import groupby
from types import SimpleNamespace
from typing import Iterable

from .presentation_axis import AxisInterval, axis_intervals, format_axis_label
from .presentation_marks import ComparisonMark, comparison_marks
from .presentation_lanes import LaneAssignment, LaneItem, LaneTrack, assign_stable_lanes, lane_tracks
from .presentation_layout import solve_presentation_layout
from .font_metrics import FontMetrics, resolve_font_metrics
from .presentation_routing import route_orthogonal
from .presentation_paint import resolve_facet_paint


@dataclass(frozen=True)
class TextLayout:
    """One measured text result shared by Scene geometry and renderer serialization."""

    bounds: tuple[float, float, float, float]
    baseline: tuple[float, float]
    lines: tuple[str, ...]
    family: str
    weight: int
    asset_identity: str


@dataclass(frozen=True)
class SurfaceContentInput:
    """Selected presentation facts normalized once before Scene construction."""

    table_columns: tuple[tuple[str, str], ...] = ()
    table_cells: tuple[tuple[str, str, str], ...] = ()
    relations: tuple[dict, ...] = ()
    annotations: tuple[dict, ...] = ()
    notes: tuple[tuple[str, str], ...] = ()
    legend_entries: tuple[tuple[str, str], ...] = ()
    coverage_text: str = ""
    summary_panels: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = ()
    template_values: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class ResolvedPresentationInput:
    """One derived input boundary between authoring resources and Scene geometry."""

    title: str
    window: tuple[date, date]
    items: tuple[object, ...]
    settings: dict
    surface_content: SurfaceContentInput


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
    text_layout: TextLayout | None = None
    shape: str | None = None
    color: str | None = None
    opacity: float | None = None
    optional: bool = False
    corner_radius: float | None = None
    lane_group_id: str | None = None
    stack_index: int | None = None
    points: tuple[tuple[float, float], ...] = ()
    from_port_id: str | None = None
    to_port_id: str | None = None
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
class SurfaceScaleManifest:
    """Closed temporal scale evidence carried by one completed surface."""

    surface_id: str
    scale_id: str
    domain_start: date
    domain_end: date
    range_start: float
    range_end: float
    origin: float
    unit_ratio: float


@dataclass(frozen=True)
class ContentFamilyCounts:
    relations: int
    annotations: int
    notes: int
    legend_entries: int
    summary_panels: int


@dataclass(frozen=True)
class SceneManifest:
    """Non-authoritative inspection evidence for one completed Scene."""

    version: str
    settings_version: str
    viewport: tuple[float, float]
    selected_object_ids: tuple[str, ...]
    font_asset_identities: tuple[str, ...]
    content_family_counts: ContentFamilyCounts
    surface_scales: tuple[SurfaceScaleManifest, ...]


@dataclass(frozen=True)
class SceneSurface:
    """Resolved geometry for one public adapter route."""

    surface_id: str
    slots: tuple[SceneSlot, ...]
    rows: tuple[SceneRow, ...]
    groups: tuple[SceneGroup, ...]
    scale_manifest: SurfaceScaleManifest
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
    manifest: SceneManifest
    diagnostics: tuple[str, ...]


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
                           (rect.x, rect.y, rect.width, rect.height))
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


def _surface_slot(surface: SceneSurface, source: str) -> SceneSlot:
    try:
        return next(slot for slot in surface.slots if slot.source == source)
    except StopIteration as error:
        raise ValueError("E_PRESENTATION_PRIMITIVE_MISSING") from error


def _optional_surface_slot(surface: SceneSurface, *sources: str) -> SceneSlot | None:
    return next((slot for slot in surface.slots if slot.source in sources), None)


def _path_bounds(points: tuple[tuple[float, float], ...]) -> tuple[float, float, float, float]:
    xs, ys = zip(*points, strict=True)
    return min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys)


def _surface_x(slot: SceneSlot, start: date, end: date, value: date) -> float:
    """Map a Date-only value into one completed surface slot, once."""
    x, _, width, _ = slot.bounds
    inset = min(20.0, width / 2.0)
    days = max(1, (end - start).days)
    return x + inset + (value - start).days / days * max(0.0, width - 2.0 * inset)


def _surface_scale_manifest(surface_id: str, slots: tuple[SceneSlot, ...],
                            window: tuple[date, date]) -> SurfaceScaleManifest:
    timeline = next((slot for slot in slots if slot.source == "timeline"), None)
    axis = next((slot for slot in slots if slot.source == "timeline-axis"), None)
    if timeline is None or axis is None or not timeline.scale_id or timeline.scale_id != axis.scale_id:
        raise ValueError("E_PRESENTATION_SCALE_MISMATCH")
    start, end = window
    range_start = _surface_x(timeline, start, end, start)
    range_end = _surface_x(timeline, start, end, end)
    return SurfaceScaleManifest(
        surface_id=surface_id,
        scale_id=timeline.scale_id,
        domain_start=start,
        domain_end=end,
        range_start=range_start,
        range_end=range_end,
        origin=range_start,
        unit_ratio=(range_end - range_start) / max(1, (end - start).days),
    )


def _surface_primitives(surface: SceneSurface, title: str, items: tuple[object, ...],
                        window: tuple[date, date], axes: tuple[AxisInterval, ...],
                        ticks: tuple[AxisInterval, ...], marks: tuple[ComparisonMark, ...],
                        lanes: tuple[LaneAssignment, ...], tracks: tuple[LaneTrack, ...],
                        settings: dict, content: SurfaceContentInput) -> tuple[ScenePrimitive, ...]:
    """Emit core I3 geometry for one public surface before adapter selection."""
    title_slot, timeline, axis = (_surface_slot(surface, source) for source in ("title", "timeline", "timeline-axis"))
    start, end = window
    rows = {row.object_id: row for row in surface.rows}
    items_by_id = {str(getattr(item, "object_id")): item for item in items}
    lane_stacks = {lane.object_id: lane.stack for lane in lanes}
    lane_assignments = {lane.object_id: lane for lane in lanes}
    lane_tracks_by_group = {track.group_id: track for track in tracks}
    primitives: list[ScenePrimitive] = []

    def text_layout(value: str, x: float, top: float, *, role: str, available: float,
                    center: bool = False, wrap: bool = False, max_height: float | None = None) -> TextLayout:
        typography = settings["theme"]["typography"].get(role, settings["theme"]["typography"]["body"])
        size, weight = float(typography["size"]), int(typography["weight"])
        line_height = float(typography.get("lineHeight", 1.2))
        metrics: FontMetrics = resolve_font_metrics(settings["theme"]["fontFamily"], settings["context"]["fontMetrics"], weight=weight)
        spacing = float(typography.get("letterSpacing", 0))
        lines = [value]
        if wrap and metrics.width(value, size, spacing) > available:
            lines, current = [], ""
            for word in value.split():
                candidate = f"{current} {word}".strip()
                if metrics.width(candidate, size, spacing) > available:
                    if not current:
                        raise ValueError("E_LAYOUT_REQUIRED_OVERFLOW:text")
                    lines.append(current)
                    current = word
                else:
                    current = candidate
            lines.append(current)
        width = max((metrics.width(line, size, spacing) for line in lines), default=0.0)
        if width > available:
            raise ValueError("E_LAYOUT_REQUIRED_OVERFLOW:text")
        height = size * line_height * len(lines)
        if max_height is not None and height > max_height:
            raise ValueError("E_LAYOUT_REQUIRED_OVERFLOW:text")
        left = x - width / 2.0 if center else x
        return TextLayout(
            bounds=(left, top, width, height),
            baseline=(left if not center else x, metrics.baseline(top, size, line_height)),
            lines=tuple(lines), family=settings["theme"]["fontFamily"], weight=weight,
            asset_identity=metrics.content_identity,
        )

    def add(kind: str, source_ref: str, source_kind: str, facet: str, role: str,
            purpose: str, bounds: tuple[float, float, float, float], *, text: str | None = None,
            baseline: tuple[float, float] | None = None, layout: TextLayout | None = None,
            shape: str | None = None, points: tuple[tuple[float, float], ...] = (),
            from_port_id: str | None = None, to_port_id: str | None = None,
            color: str | None = None, opacity: float | None = None,
            optional: bool = False,
            corner_radius: float | None = None, lane_group_id: str | None = None,
            stack_index: int | None = None) -> None:
        projection = f"{surface.surface_id}:{purpose}:{source_ref}:{facet}"
        primitives.append(ScenePrimitive(
            scene_id=f"{projection}:primitive", kind=kind, source_ref=source_ref,
            source_kind=source_kind, semantic_facet=facet, visual_role=role, bounds=bounds,
            projection_instance_id=projection, surface_id=surface.surface_id, purpose=purpose,
            text=text, baseline=baseline, text_layout=layout, shape=shape, color=color, opacity=opacity,
            optional=optional,
            corner_radius=corner_radius, lane_group_id=lane_group_id, stack_index=stack_index, points=points,
            from_port_id=from_port_id, to_port_id=to_port_id, z_order=len(primitives),
        ))

    template_values = dict(content.template_values)
    expected_template_keys = {"title", "windowStart", "windowLastVisible", "selectedCount", "unmatchedCount", "missingCount"}
    if set(template_values) != expected_template_keys:
        raise ValueError("E_PRESENTATION_INPUT_INCOMPLETE")
    visible_title = settings["detail"]["title"].format_map(template_values)
    title_layout = text_layout(visible_title, title_slot.bounds[0], title_slot.bounds[1], role="heading", available=title_slot.bounds[2])
    add("Text", "project", "project", "", "heading", "title-text",
        title_layout.bounds, text=visible_title, baseline=title_layout.baseline, layout=title_layout)
    if settings["layout"]["title"]["showSubtitle"]:
        subtitle = settings["detail"]["subtitle"].format_map(template_values)
        subtitle_top = (title_layout.bounds[1] + title_layout.bounds[3]
                        + float(settings["layout"]["title"]["subtitleGap"]))
        subtitle_layout = text_layout(subtitle, title_slot.bounds[0], subtitle_top,
                                      role="subtitle", available=title_slot.bounds[2])
        add("Text", "view:window", "view", "", "subtitle", "subtitle-text",
            subtitle_layout.bounds, text=subtitle, baseline=subtitle_layout.baseline, layout=subtitle_layout)

    band_heights = dict(zip(settings["layout"]["axis"]["levels"], settings["layout"]["axis"]["bandHeights"], strict=True))
    axis_y = axis.bounds[1]
    for level in settings["layout"]["axis"]["levels"]:
        level_axes = tuple(interval for interval in axes if interval.level == level)
        band_height = float(band_heights[level])
        for interval in level_axes:
            x1, x2 = _surface_x(axis, start, end, interval.start), _surface_x(axis, start, end, interval.end)
            source = f"axis:{interval.level}:{interval.index}"
            add("Rect", source, "axis", "axis", interval.level, "axis-band", (x1, axis_y, x2 - x1, band_height))
            label = format_axis_label(interval, settings["detail"]["formatting"], settings["context"]["locale"])
            label_layout = text_layout(label, (x1 + x2) / 2.0, axis_y, role=level,
                                       available=axis.bounds[2], center=True)
            add("Text", source, "axis", "axis", interval.level, "axis-label", label_layout.bounds,
                text=label, baseline=label_layout.baseline, layout=label_layout)
        axis_y += band_height
    bottom = max((row.bounds[1] + row.bounds[3] for row in surface.rows), default=timeline.bounds[1] + timeline.bounds[3])
    for tick in ticks:
        x = _surface_x(axis, start, end, tick.start)
        points = ((x, axis.bounds[1]), (x, bottom))
        add("Path", f"tick:{tick.level}:{tick.index}", "axis", "axis", tick.level, "tick",
            (x, axis.bounds[1], 0.0, bottom - axis.bounds[1]), points=points)
    if settings["layout"]["axis"]["minorVisible"]:
        finer = {"year": "quarter", "quarter": "month", "month": "week", "week": "day"}.get(
            settings["layout"]["axis"]["tickUnit"])
        if finer is not None:
            major_boundaries = {tick.start for tick in ticks}
            for tick in axis_intervals(start, end, finer):
                if tick.start in major_boundaries:
                    continue
                x = _surface_x(axis, start, end, tick.start)
                points = ((x, axis.bounds[1]), (x, bottom))
                add("Path", f"minor-tick:{tick.level}:{tick.index}", "axis", "axis", tick.level,
                    "minor-tick", (x, axis.bounds[1], 0.0, bottom - axis.bounds[1]), points=points)

    planned_height = float(settings["theme"]["bar"]["plannedHeight"])
    actual_height = float(settings["theme"]["bar"]["actualHeight"])
    gap = float(settings["layout"]["bars"]["gap"])
    point_size = float(settings["theme"]["point"]["size"])
    comparison_mode = settings["layout"]["bars"]["comparisonMode"]

    def label_rule(source: str, facet: str, endpoint: str) -> dict | None:
        return next((rule for rule in settings["detail"]["labelRules"]
                     if rule["source"] == source and rule["facet"] == facet
                     and rule["endpoint"] == endpoint), None)

    def aligned_label(value: str, x: float, marker_bounds: tuple[float, float, float, float],
                      *, role: str, align: str, required: bool = True) -> TextLayout | None:
        left = float(settings["layout"]["margins"]["left"])
        right = float(settings["context"]["viewport"]["width"]) - float(settings["layout"]["margins"]["right"])
        try:
            layout = text_layout(value, x, marker_bounds[1], role=role, available=max(1.0, right - left))
        except ValueError as exc:
            if (str(exc) == "E_LAYOUT_REQUIRED_OVERFLOW:text" and not required
                    and settings["layout"]["labelPlacement"]["overflow"] == "clip-optional"):
                return None
            if str(exc) == "E_LAYOUT_REQUIRED_OVERFLOW:text":
                raise ValueError("E_PRESENTATION_LABEL_UNPLACEABLE") from exc
            raise
        resolved_x = min(max(x, left), right - layout.bounds[2])
        if align == "center":
            top = marker_bounds[1] + (marker_bounds[3] - layout.bounds[3]) / 2.0
        elif align == "end":
            top = marker_bounds[1] + marker_bounds[3] - layout.bounds[3]
        else:
            top = marker_bounds[1]
        dx, dy = resolved_x - layout.bounds[0], top - layout.bounds[1]
        return replace(layout, bounds=(resolved_x, top, layout.bounds[2], layout.bounds[3]),
                       baseline=(layout.baseline[0] + dx, layout.baseline[1] + dy))

    def add_variance_family(source_id: str, lane_assignment: LaneAssignment, *,
                            status: str, text: str, anchor_x: float,
                            vertical_bounds: tuple[float, float]) -> None:
        variance = settings["layout"]["variance"]
        marker_width = float(settings["theme"]["varianceMarkerWidth"])
        marker_bounds = (anchor_x + float(variance["offset"]), vertical_bounds[0],
                         marker_width, vertical_bounds[1] - vertical_bounds[0])
        add("Rect", source_id, "object", "finish-delta", status, "variance-marker", marker_bounds,
            lane_group_id=lane_assignment.group_id, stack_index=lane_assignment.stack)
        label_x = marker_bounds[0] + marker_width + float(variance["labelGap"])
        rule = label_rule("comparison-delta", "variance", "finish")
        required = True if rule is None else bool(rule["required"])
        layout = aligned_label(text, label_x, marker_bounds, role="variance",
                               align=str(variance["labelAlign"]),
                               required=required)
        if layout is not None:
            add("Text", source_id, "object", "finish-delta", status, "variance-label", layout.bounds,
                text=text, baseline=layout.baseline, layout=layout,
                optional=not required,
                lane_group_id=lane_assignment.group_id, stack_index=lane_assignment.stack)

    for mark in marks:
        row = rows.get(mark.source_id)
        item = items_by_id.get(mark.source_id)
        if row is None or item is None:
            raise ValueError("E_PRESENTATION_PRIMITIVE_MISSING")
        lane_assignment = lane_assignments.get(mark.source_id)
        if lane_assignment is None:
            raise ValueError("E_PRESENTATION_PRIMITIVE_MISSING")
        _, row_y, _, row_height = row.bounds
        independent_lane = (surface.surface_id == "table-timeline"
                            and settings["layout"]["lanes"]["surface"] == "independent-lane-track")
        if independent_lane:
            group_id = str(getattr(item, "group_id", ""))
            group = next((candidate for candidate in surface.groups if candidate.group_id == group_id), None)
            track = lane_tracks_by_group.get(group_id)
            if group is None or track is None:
                raise ValueError("E_PRESENTATION_PRIMITIVE_MISSING")
            row_y = (group.content_bounds[1] + float(settings["layout"]["lanes"]["trackPadding"])
                     + lane_stacks.get(mark.source_id, 0) * track.pitch)
        if mark.at is not None:
            x = _surface_x(timeline, start, end, mark.at)
            if mark.facet == "finish-delta":
                if not settings["layout"]["variance"]["visible"]:
                    continue
                assert mark.variance_days is not None
                status = ("variance-ahead" if mark.variance_days < 0 else
                          "variance-behind" if mark.variance_days > 0 else "variance-on-track")
                sign = settings["detail"]["formatting"]["positiveSign"] if mark.variance_days > 0 else ""
                text = f'{sign}{mark.variance_days}{settings["detail"]["formatting"]["signedDaysSuffix"]}'
                owned = [node for node in primitives
                         if node.source_ref == mark.source_id and node.purpose == "comparison-mark"
                         and node.kind == "Rect" and node.semantic_facet in {"planned", "baseline", "actual"}]
                top = min(node.bounds[1] for node in owned)
                bottom = max(node.bounds[1] + node.bounds[3] for node in owned)
                right = max(node.bounds[0] + node.bounds[2] for node in owned)
                add_variance_family(mark.source_id, lane_assignment, status=status, text=text,
                                    anchor_x=right, vertical_bounds=(top, bottom))
            else:
                symbol_y = row_y if independent_lane else row_y + (row_height - point_size) / 2.0
                paint = resolve_facet_paint(settings["theme"], str(getattr(item, "group_id", "")), mark.facet)
                add("Symbol", mark.source_id, "object", mark.facet, mark.facet, "comparison-mark",
                    (x - point_size / 2.0, symbol_y, point_size, point_size),
                    shape=settings["theme"]["point"]["shape"], color=str(paint["color"]), opacity=float(paint["opacity"]),
                    lane_group_id=lane_assignment.group_id, stack_index=lane_assignment.stack)
            continue
        assert mark.start is not None and mark.end is not None
        x1, x2 = _surface_x(timeline, start, end, mark.start), _surface_x(timeline, start, end, mark.end)
        height = actual_height if mark.facet == "actual" else planned_height
        if independent_lane:
            y = row_y + (planned_height + gap if mark.facet == "actual" and comparison_mode != "overlaid" else 0.0)
        elif mark.facet == "actual" and comparison_mode != "overlaid":
            y = row_y + row_height / 2.0 + gap / 2.0
        else:
            y = row_y + row_height / 2.0 - height - gap / 2.0
        width = max(float(settings["theme"]["bar"]["minWidth"]), max(0.0, x2 - x1))
        corner_radius = min(float(settings["theme"]["bar"]["radius"]), width / 2.0, height / 2.0)
        paint = resolve_facet_paint(settings["theme"], str(getattr(item, "group_id", "")), mark.facet)
        add("Rect", mark.source_id, "object", mark.facet, mark.facet, "comparison-mark",
            (x1, y, width, height), color=str(paint["color"]), opacity=float(paint["opacity"]),
            corner_radius=corner_radius, lane_group_id=lane_assignment.group_id, stack_index=lane_assignment.stack)

    comparison_rects = {(node.source_ref, node.semantic_facet): node for node in primitives
                        if node.purpose == "comparison-mark" and node.kind == "Rect"}
    missing_mode = settings["layout"]["missingActual"]["mode"]
    for item in items:
        if str(getattr(item, "source_type")) != "span":
            continue
        object_id = str(getattr(item, "object_id"))
        planned = (comparison_rects.get((object_id, "planned"))
                   or comparison_rects.get((object_id, "baseline")))
        if planned is None or (object_id, "actual") in comparison_rects:
            continue
        lane_assignment = lane_assignments[object_id]
        actual = getattr(item, "actual", None)
        if actual and settings["layout"]["variance"]["visible"]:
            add_variance_family(object_id, lane_assignment, status="variance-unknown",
                                text=str(settings["detail"]["formatting"]["unknown"]),
                                anchor_x=planned.bounds[0] + planned.bounds[2],
                                vertical_bounds=(planned.bounds[1], planned.bounds[1] + planned.bounds[3]))
        actual_band_y = planned.bounds[1] if comparison_mode == "overlaid" else planned.bounds[1] + planned.bounds[3] + gap
        pattern = settings["theme"]["missingPattern"]
        pattern_bounds = (planned.bounds[0], actual_band_y + (actual_height - float(pattern["height"])) / 2.0,
                          float(pattern["width"]), float(pattern["height"]))
        if missing_mode in {"pattern", "label-and-pattern"}:
            add("Rect", object_id, "object", "missing-actual", "missing-actual", "missing-actual-pattern",
                pattern_bounds, lane_group_id=lane_assignment.group_id, stack_index=lane_assignment.stack)
        if missing_mode in {"label", "label-and-pattern"}:
            label_x = (pattern_bounds[0] + pattern_bounds[2] + float(settings["layout"]["missingActual"]["gap"])
                       if missing_mode == "label-and-pattern" else planned.bounds[0])
            label = str(settings["detail"]["missingActualLabel"])
            label_layout = aligned_label(label, label_x, (label_x, actual_band_y, 0.0, actual_height),
                                         role="missingActual", align="center")
            assert label_layout is not None
            add("Text", object_id, "object", "missing-actual", "missing-actual", "missing-actual-label",
                label_layout.bounds, text=label, baseline=label_layout.baseline, layout=label_layout,
                lane_group_id=lane_assignment.group_id, stack_index=lane_assignment.stack)

    from .presentation_labels import LabelRect, place_label

    mark_primitives = tuple(node for node in primitives
                            if node.purpose == "comparison-mark" and node.kind in {"Rect", "Symbol"})
    label_spec = settings["layout"]["labelPlacement"]
    candidate_sides = label_spec["candidateSides"][:int(label_spec["maxCandidates"])]
    placed_item_labels: list[LabelRect] = []

    def formatted_date(value: date) -> str:
        if settings["detail"]["formatting"]["date"] == "iso-date":
            return value.isoformat()
        language = settings["context"]["locale"].split("-", 1)[0].lower()
        if language == "ja":
            return f"{value.year}/{value.month:02d}/{value.day:02d}"
        months = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
                  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
        return f"{months[value.month - 1]} {value.day}, {value.year}"

    if surface.surface_id != "table-timeline":
        title_rule = next((rule for rule in settings["detail"]["labelRules"]
                           if rule["source"] == "title" and rule["endpoint"] == "body"), None)
        required = True if title_rule is None else bool(title_rule["required"])
        for object_id, row in rows.items():
            item = items_by_id[object_id]
            value = str(getattr(item, "title", object_id))
            body = settings["theme"]["typography"]["body"]
            top = row.bounds[1] + (row.bounds[3] - float(body["size"]) * float(body.get("lineHeight", 1.2))) / 2.0
            try:
                layout = text_layout(value, row.bounds[0], top, role="body", available=row.bounds[2])
            except ValueError as exc:
                if (str(exc) == "E_LAYOUT_REQUIRED_OVERFLOW:text" and not required
                        and label_spec["overflow"] == "clip-optional"):
                    continue
                raise ValueError("E_PRESENTATION_LABEL_UNPLACEABLE") from exc
            add("Text", object_id, "object", "", "body", "item-label", layout.bounds,
                text=value, baseline=layout.baseline, layout=layout)
        rules = []
    else:
        rules = list(settings["detail"]["labelRules"])
    if surface.surface_id == "table-timeline" and not any(rule["source"] == "title" for rule in rules):
        rules.append({"source": "title", "facet": "planned", "endpoint": "body", "required": True})
    seen_targets: set[tuple[str, str, str]] = set()
    for rule in rules:
        if rule["source"] not in {"title", "planned-date", "actual-date"}:
            continue
        target = (str(rule["source"]), str(rule["facet"]), str(rule["endpoint"]))
        if target in seen_targets:
            continue
        seen_targets.add(target)
        for item in items:
            object_id = str(getattr(item, "object_id"))
            facet = str(rule["facet"])
            facets = {facet, "baseline"} if rule["source"] == "title" and facet == "planned" else {facet}
            node = next((candidate for candidate in mark_primitives
                         if candidate.source_ref == object_id and candidate.semantic_facet in facets), None)
            if node is None:
                continue
            if rule["source"] == "title":
                text, purpose, role = str(getattr(item, "title", object_id)), "item-label", "body"
            else:
                values = getattr(item, "actual", None) if rule["source"] == "actual-date" else getattr(item, "planned")
                if not isinstance(values, dict):
                    continue
                endpoint = str(rule["endpoint"])
                key = "finish" if endpoint == "finish" else endpoint
                if key == "body":
                    key = "at" if getattr(item, "source_type") == "point" else "start"
                value = values.get(key)
                if not isinstance(value, date):
                    continue
                text, purpose, role = formatted_date(value), f'{rule["source"]}-label', "text-muted"
            measured = text_layout(text, 0.0, 0.0, role="body", available=timeline.bounds[2])
            obstacles = [LabelRect(*candidate.bounds) for candidate in mark_primitives if candidate is not node]
            obstacles.extend(placed_item_labels)
            placement = place_label(
                LabelRect(*node.bounds), (measured.bounds[2], measured.bounds[3]), candidate_sides,
                bounds=LabelRect(*timeline.bounds), obstacles=obstacles,
                required=bool(rule["required"]), overflow=label_spec["overflow"],
            )
            if placement is None:
                continue
            dx, dy = placement.bounds.x - measured.bounds[0], placement.bounds.y - measured.bounds[1]
            layout = replace(measured,
                             bounds=(placement.bounds.x, placement.bounds.y,
                                     measured.bounds[2], measured.bounds[3]),
                             baseline=(measured.baseline[0] + dx, measured.baseline[1] + dy))
            add("Text", object_id, "object", facet, role, purpose, layout.bounds,
                text=text, baseline=layout.baseline, layout=layout, optional=not bool(rule["required"]))
            placed_item_labels.append(placement.bounds)

    if surface.surface_id == "table-timeline" and content.table_columns:
        table = _surface_slot(surface, "table")
        table_x, table_y, table_width, table_height = table.bounds
        axis_height = sum(float(value) for value in settings["layout"]["axis"]["bandHeights"])
        add("Rect", "table", "surface", "", "table-frame", "table-frame",
            (table_x, table_y, timeline.bounds[0] + timeline.bounds[2] - table_x, table_height))
        add("Rect", "table-header", "surface", "", "table-header", "table-header-band",
            (table_x, table_y, table_width, axis_height))
        column_width = table_width / len(content.table_columns)
        for index, (column_id, label) in enumerate(content.table_columns):
            x = table_x + index * column_width
            layout = text_layout(label, x + 12.0, table_y, role="tableHeader",
                                 available=max(1.0, column_width - 24.0))
            add("Text", column_id, "table-column", "", "tableHeader", "table-column-label",
                layout.bounds, text=label, baseline=layout.baseline, layout=layout)
        for group in surface.groups:
            if settings["layout"]["group"]["mode"] != "none":
                add("Rect", group.group_id, "group", "", "group-band", "group-surface", group.content_bounds)
                group_items = tuple(item for item in items if str(getattr(item, "group_id", "")) == group.group_id)
                label = str(getattr(group_items[0], "group_label", group.group_id)) if group_items else group.group_id
                label_bounds = group.header_bounds or group.content_bounds
                layout = text_layout(label, label_bounds[0] + 12.0, label_bounds[1],
                                     role="group", available=max(1.0, label_bounds[2] - 24.0),
                                     wrap=True, max_height=label_bounds[3])
                add("Text", group.group_id, "group", "", "group", "group-header", layout.bounds,
                    text=label, baseline=layout.baseline, layout=layout)
                if settings["layout"]["group"]["mode"] in {"header-and-separator", "merged"}:
                    separator_y = group.content_bounds[1] + group.content_bounds[3]
                    add("Path", group.group_id, "group", "", "group-separator", "group-separator",
                        (table_x, separator_y, table_width, 0.0),
                        points=((table_x, separator_y), (table_x + table_width, separator_y)))
        cells = {(object_id, column_id): value for object_id, column_id, value in content.table_cells}
        for row_index, row in enumerate(surface.rows):
            if row_index % 2:
                add("Rect", row.object_id, "object", "", "row-shade", "row-shade", row.bounds)
            y = row.bounds[1] + row.bounds[3]
            add("Path", row.object_id, "object", "", "table-row", "table-row-rule",
                (table_x, y, table_width, 0.0), points=((table_x, y), (table_x + table_width, y)))
            for index, (column_id, _) in enumerate(content.table_columns):
                value = cells.get((row.object_id, column_id))
                if value is None:
                    raise ValueError("E_PRESENTATION_INPUT_INCOMPLETE")
                x = table_x + index * column_width + 12.0
                top = row.bounds[1] + 4.0
                layout = text_layout(value, x, top, role="body", available=max(1.0, column_width - 24.0),
                                     wrap=True, max_height=max(1.0, row.bounds[3] - 8.0))
                add("Text", f"{row.object_id}:{column_id}", "table-cell", "", "body", "table-cell",
                    layout.bounds, text=value, baseline=layout.baseline, layout=layout)

    if surface.surface_id in {"table-timeline", "review", "minimal"}:
        mark_nodes = {(node.source_ref, node.semantic_facet): node for node in primitives
                      if node.purpose == "comparison-mark" and node.kind in {"Rect", "Symbol"}}
        planned_nodes = {source: node for (source, facet), node in mark_nodes.items()
                         if facet in {"planned", "baseline"}}
        clearance = float(settings["layout"]["routing"]["clearance"])
        routing = settings["layout"]["routing"]

        def mark_port(node: ScenePrimitive, endpoint: str, outward: int) -> tuple[tuple[float, float], str, int]:
            x, y, width, height = node.bounds
            if endpoint == "start":
                point, direction = (x, y + height / 2.0), -1
            elif endpoint in {"end", "finish"}:
                point, direction = (x + width, y + height / 2.0), 1
            elif endpoint == "at":
                direction = outward
                point = (x + width if direction > 0 else x, y + height / 2.0)
            elif endpoint == "body":
                direction = outward
                point = (x + width / 2.0, y + height / 2.0)
            else:
                raise ValueError("E_CONNECTOR_ENDPOINT")
            return point, f"{node.projection_instance_id}:{endpoint}", direction

        obstacle_nodes = tuple(node for node in primitives
                               if node.purpose in {"comparison-mark", "item-label"})
        def routed_obstacles(excluded_label_refs: set[str] | None = None):
            excluded_label_refs = excluded_label_refs or set()
            return tuple(
                (node.bounds[0] - clearance, node.bounds[1] - clearance,
                 node.bounds[0] + node.bounds[2] + clearance,
                 node.bounds[1] + node.bounds[3] + clearance)
                for node in obstacle_nodes
                if not (node.kind == "Text" and node.source_ref in excluded_label_refs)
            )
        for relation in content.relations:
            if not routing["enabled"]:
                break
            if relation.get("type", "dependency") != "dependency":
                continue
            source_spec, target_spec = relation.get("from", {}), relation.get("to", {})
            source_node = planned_nodes.get(str(source_spec.get("object", "")))
            target_node = planned_nodes.get(str(target_spec.get("object", "")))
            if source_node is None or target_node is None:
                continue
            source_endpoint = str(source_spec.get("endpoint", "end"))
            target_endpoint = str(target_spec.get("endpoint", "start"))
            source_point, source_port, source_direction = mark_port(source_node, source_endpoint, 1)
            target_point, target_port, target_direction = mark_port(target_node, target_endpoint, -1)
            port_offset = float(routing["portOffset"])
            source_route = (source_point[0] + source_direction * port_offset, source_point[1])
            target_route = (target_point[0] + target_direction * port_offset, target_point[1])
            relation_obstacles = routed_obstacles({source_node.source_ref, target_node.source_ref})
            route_bounds = (timeline.bounds[0], timeline.bounds[1],
                            timeline.bounds[0] + timeline.bounds[2], timeline.bounds[1] + timeline.bounds[3])
            route = route_orthogonal(source_route, target_route, relation_obstacles,
                                     grid_offset=float(routing["gridOffset"]),
                                     bend_penalty=float(routing["bendPenalty"]), limit=int(routing["limit"]),
                                     bounds=route_bounds)
            points = (source_point, *route, target_point)
            relation_id = str(relation.get("id", "relation"))
            add("Path", relation_id, "relation", "dependency", "dependency", "dependency-connector",
                _path_bounds(points), shape=settings["theme"]["arrow"]["shape"], points=points,
                from_port_id=source_port, to_port_id=target_port)

        if content.annotations:
            from .presentation_annotations import (nearest_box_port, project_annotation_box,
                                                   resolve_annotation_anchor, route_annotation_leader)
            from .presentation_labels import LabelRect

            viewport = LabelRect(timeline.bounds[0], timeline.bounds[1], timeline.bounds[2], timeline.bounds[3])
            placed_annotation_boxes: list[LabelRect] = []
            for annotation in content.annotations:
                annotation_id = str(annotation.get("id", ""))
                purpose = annotation.get("purpose")
                if purpose == "explanatory-arrow":
                    if not routing["enabled"]:
                        continue
                    def anchor_node(value: dict) -> tuple[ScenePrimitive, str]:
                        facet = str(value.get("facet", "planned"))
                        node = mark_nodes.get((str(value.get("id", "")), facet))
                        if node is None:
                            raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
                        return node, str(value.get("endpoint", "body"))
                    source_node, source_endpoint = anchor_node(annotation.get("source", {}))
                    target_node, target_endpoint = anchor_node(annotation.get("target", {}))
                    source_point, source_port, source_direction = mark_port(source_node, source_endpoint, 1)
                    target_point, target_port, target_direction = mark_port(target_node, target_endpoint, -1)
                    offset = float(routing["portOffset"])
                    arrow_obstacles = routed_obstacles({source_node.source_ref, target_node.source_ref})
                    route = route_orthogonal((source_point[0] + source_direction * offset, source_point[1]),
                                             (target_point[0] + target_direction * offset, target_point[1]), arrow_obstacles,
                                             grid_offset=float(routing["gridOffset"]),
                                             bend_penalty=float(routing["bendPenalty"]), limit=int(routing["limit"]),
                                             bounds=(timeline.bounds[0], timeline.bounds[1],
                                                     timeline.bounds[0] + timeline.bounds[2],
                                                     timeline.bounds[1] + timeline.bounds[3]))
                    points = (source_point, *route, target_point)
                    add("Path", annotation_id, "explanatory-arrow", "", "explanatory-arrow", "explanatory-arrow",
                        _path_bounds(points), shape=settings["theme"]["arrow"]["shape"], points=points,
                        from_port_id=source_port, to_port_id=target_port)
                    continue
                resolved = resolve_annotation_anchor(annotation, marks)
                node = mark_nodes.get((resolved.object_id, resolved.facet))
                if node is None:
                    raise ValueError("E_PRESENTATION_ANCHOR_MISSING")
                x, y, width, height = node.bounds
                if purpose == "highlight":
                    add("Rect", annotation_id, "presentation-annotation", resolved.facet,
                        "presentation-annotation", "annotation-highlight", node.bounds)
                    continue
                value = str(annotation.get("text", ""))
                typography = settings["theme"]["typography"]["body"]
                metric = resolve_font_metrics(settings["theme"]["fontFamily"], settings["context"]["fontMetrics"],
                                              weight=int(typography["weight"]))
                text_size = (metric.width(value, float(typography["size"])),
                             float(typography["size"]) * float(typography.get("lineHeight", 1.2)))
                anchor_bounds = LabelRect(x, y, width, height)
                own_obstacle = LabelRect(x - clearance, y - clearance,
                                         width + 2.0 * clearance, height + 2.0 * clearance)
                base_obstacles = [LabelRect(left, top, right - left, bottom - top)
                                  for left, top, right, bottom in routed_obstacles({resolved.object_id})]
                route_obstacles = [obstacle for obstacle in (*base_obstacles, *placed_annotation_boxes)
                                   if obstacle != own_obstacle]
                annotation_rule = label_rule("annotation-text", "annotation", "body")
                annotation_required = True if annotation_rule is None else bool(annotation_rule["required"])
                box = project_annotation_box(annotation, resolved, anchor_bounds=anchor_bounds, text_size=text_size,
                                             candidate_sides=settings["layout"]["labelPlacement"]["candidateSides"],
                                             viewport=viewport,
                                             obstacles=route_obstacles,
                                             overflow=settings["layout"]["labelPlacement"]["overflow"],
                                             required=annotation_required)
                if box is None:
                    continue
                box_bounds = (box.placement.bounds.x, box.placement.bounds.y,
                              box.placement.bounds.width, box.placement.bounds.height)
                add("Rect", annotation_id, "presentation-annotation", resolved.facet,
                    "presentation-annotation", "annotation-box", box_bounds, optional=not annotation_required)
                if value:
                    layout = text_layout(value, box_bounds[0], box_bounds[1], role="body", available=box_bounds[2],
                                         wrap=True, max_height=box_bounds[3])
                    add("Text", annotation_id, "presentation-annotation", resolved.facet,
                        "presentation-annotation", "annotation-text", layout.bounds,
                        text=value, baseline=layout.baseline, layout=layout, optional=not annotation_required)
                if box.leader_required and routing["enabled"]:
                    anchor_point, anchor_port, direction = mark_port(node, resolved.endpoint, 1)
                    target = nearest_box_port(box.placement.bounds, anchor_point)
                    route = route_annotation_leader((anchor_point[0] + direction * 5.0, anchor_point[1]), target,
                                                    obstacles=route_obstacles, limit=int(routing["limit"]))
                    points = (anchor_point, *route)
                    add("Path", annotation_id, "presentation-annotation", resolved.facet,
                        "presentation-annotation", "annotation-leader", _path_bounds(points), points=points,
                        from_port_id=anchor_port, to_port_id=f"{surface.surface_id}:annotation:{annotation_id}:box",
                        optional=not annotation_required)
                placed_annotation_boxes.append(LabelRect(*box_bounds))

        notes_slot = _optional_surface_slot(surface, "notes", "annotations")
        if notes_slot is not None:
            note_y = notes_slot.bounds[1]
            for note_id, value in content.notes:
                layout = text_layout(value, notes_slot.bounds[0], note_y, role="notes", available=notes_slot.bounds[2],
                                     wrap=True, max_height=notes_slot.bounds[3])
                if layout.bounds[1] + layout.bounds[3] > notes_slot.bounds[1] + notes_slot.bounds[3]:
                    raise ValueError("E_LAYOUT_REQUIRED_OVERFLOW:notes")
                add("Text", note_id, "project-annotation", "", "presentation-annotation", "project-note",
                    layout.bounds, text=value, baseline=layout.baseline, layout=layout)
                note_y += layout.bounds[3]

        legend_slot = _optional_surface_slot(surface, "legend")
        if legend_slot is not None and (content.legend_entries or content.coverage_text):
            spec = settings["layout"]["legend"]
            legend_type = settings["theme"]["typography"]["legend"]
            size = float(legend_type["size"])
            line_height = size * float(legend_type["lineHeight"])
            left = legend_slot.bounds[0] + float(spec["padding"]["left"])
            limit = legend_slot.bounds[0] + legend_slot.bounds[2] - float(spec["padding"]["right"])
            x, baseline_y = left, legend_slot.bounds[1] + float(spec["padding"]["top"]) + size
            swatch_width, swatch_height = float(spec["swatchWidth"]), float(spec["swatchHeight"])
            for role, label in content.legend_entries:
                metric = resolve_font_metrics(settings["theme"]["fontFamily"], settings["context"]["fontMetrics"],
                                              weight=int(legend_type["weight"]))
                item_width = swatch_width + float(spec["labelGap"]) + metric.width(label, size, float(legend_type.get("letterSpacing", 0)))
                if x + item_width > limit and x > left and spec["wrap"]:
                    x, baseline_y = left, baseline_y + line_height + float(spec["rowGap"])
                if x + item_width > limit:
                    raise ValueError("E_LAYOUT_REQUIRED_OVERFLOW:legend")
                swatch_bounds = (x, baseline_y - size / 3.0 - swatch_height / 2.0, swatch_width, swatch_height)
                if role in {"milestone"}:
                    add("Symbol", role, "legend", role, role, "legend-swatch", swatch_bounds,
                        shape=settings["theme"]["point"]["shape"])
                elif role == "dependency":
                    points = ((x, baseline_y - size / 3.0), (x + swatch_width, baseline_y - size / 3.0))
                    add("Path", role, "legend", role, role, "legend-swatch", _path_bounds(points),
                        shape=settings["theme"]["arrow"]["shape"], points=points)
                else:
                    add("Rect", role, "legend", role, role, "legend-swatch", swatch_bounds)
                label_x = x + swatch_width + float(spec["labelGap"])
                layout = text_layout(label, label_x, baseline_y - size, role="legend", available=max(1.0, limit - label_x))
                add("Text", role, "legend", role, "text-muted", "legend-label", layout.bounds,
                    text=label, baseline=layout.baseline, layout=layout)
                x += item_width + float(spec["itemGap"])
            if content.coverage_text:
                coverage = settings["theme"]["typography"]["coverage"]
                top = baseline_y + float(spec["coverageGap"])
                layout = text_layout(content.coverage_text, left, top, role="coverage", available=max(1.0, limit - left))
                if layout.bounds[1] + layout.bounds[3] > legend_slot.bounds[1] + legend_slot.bounds[3]:
                    raise ValueError("E_LAYOUT_REQUIRED_OVERFLOW:legend")
                add("Text", "coverage", "legend", "", "text-muted", "coverage-text", layout.bounds,
                    text=content.coverage_text, baseline=layout.baseline, layout=layout)

        summary_slot = _optional_surface_slot(surface, "summary")
        if summary_slot is not None:
            panel_count = max(1, len(content.summary_panels))
            panel_width = summary_slot.bounds[2] / panel_count
            for panel_index, (panel_id, heading_text, metrics_values) in enumerate(content.summary_panels):
                panel_bounds = (summary_slot.bounds[0] + panel_index * panel_width, summary_slot.bounds[1],
                                panel_width, summary_slot.bounds[3])
                add("Rect", panel_id, "summary", "", "summary-panel", "summary-panel", panel_bounds)
                header = text_layout(heading_text, panel_bounds[0] + 8.0, panel_bounds[1] + 8.0,
                                     role="summaryHeader", available=max(1.0, panel_width - 16.0), wrap=True)
                add("Text", panel_id, "summary", "", "summary-header", "summary-header", header.bounds,
                    text=heading_text, baseline=header.baseline, layout=header)
                metric_y = header.bounds[1] + header.bounds[3] + 6.0
                for metric_id, formatted_text in metrics_values:
                    layout = text_layout(formatted_text, panel_bounds[0] + 8.0, metric_y,
                                         role="summaryMetric", available=max(1.0, panel_width - 16.0), wrap=True)
                    if layout.bounds[1] + layout.bounds[3] > panel_bounds[1] + panel_bounds[3]:
                        raise ValueError("E_LAYOUT_REQUIRED_OVERFLOW:summary")
                    add("Text", f"{panel_id}:{metric_id}", "summary", "", "summary-metric", "summary-metric",
                        layout.bounds, text=formatted_text, baseline=layout.baseline, layout=layout)
                    metric_y += layout.bounds[3]

    rank = {
        "table-frame": 0, "table-header-band": 1, "group-surface": 2, "row-shade": 3,
        "table-row-rule": 4, "axis-band": 5, "tick": 6, "comparison-mark": 7,
        "table-column-label": 8, "group-header": 9, "table-cell": 10,
        "axis-label": 11, "item-label": 12, "title-text": 13, "subtitle-text": 13,
        "dependency-connector": 14, "annotation-box": 15, "annotation-text": 16,
        "annotation-leader": 17, "legend-swatch": 18, "legend-label": 19,
        "project-note": 20, "coverage-text": 21, "summary-panel": 22,
        "summary-header": 23, "summary-metric": 24,
    }
    primitives = sorted(primitives, key=lambda node: (rank.get(node.purpose, 99), node.z_order, node.scene_id))
    primitives = [ScenePrimitive(**{**node.__dict__, "z_order": index}) for index, node in enumerate(primitives)]
    for node in primitives:
        _validate_primitive(node)
    return tuple(primitives)


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
