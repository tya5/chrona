"""Completed lane mark and icon facet geometry shared by Layout composers."""
from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal
from math import isfinite
from typing import Any, Mapping, Sequence
from urllib.parse import quote

from chrona.presentation.layout.icon_geometry import complete_icon_paths
from chrona.presentation.layout.lane_projection import LaneProjectionClosure, LaneProjectionInstance
from chrona.presentation.layout.model import LayoutError, Rect
from chrona.presentation.layout.obstacles import (
    ObstacleGeometry, ObstacleRect, ObstacleSegment, obstacle_envelope,
)
from chrona.presentation.layout.surface_quality import IconPlacement, MarkPlacement, ShapePlacement, VisualRequest


def _candidate_input_error(owner: str, **operands: object) -> ValueError:
    """Keep candidate failures actionable without dumping geometry or payloads."""
    fields = []
    for name, value in operands.items():
        if isinstance(value, bytes):
            shown = "<bytes>"
        else:
            shown = repr(value)
        shown = shown.replace("\n", " ").replace("\r", " ")[:96]
        fields.append(f"{name}={shown}")
    return ValueError(f"E_LAYOUT_LANE_CANDIDATE_INPUT: {owner} " + ", ".join(fields))


@dataclass(frozen=True)
class LaneFacetPort:
    """One stable source port on a completed primitive facet."""

    port_id: str
    purpose: str
    position: tuple[float, float]

    def __post_init__(self) -> None:
        if (not self.port_id or not self.purpose or not isinstance(self.position, tuple)
                or len(self.position) != 2
                or not all(isinstance(value, (int, float)) and not isinstance(value, bool)
                           and isfinite(value) for value in self.position)):
            raise _candidate_input_error("LaneFacetPort", port_id=self.port_id,
                                         purpose=self.purpose, position=self.position)


@dataclass(frozen=True)
class LanePlainMarkProjection:
    """Completed plain mark semantics needed by the eventual Scene primitive."""

    shape: str
    semantic_role: str
    paint_order: int
    corner_radius: float
    end_treatment: str

    def __post_init__(self) -> None:
        if (self.shape not in {"span", "open-span", "point"}
                or not self.semantic_role or self.paint_order < 0
                or not isfinite(self.corner_radius) or self.corner_radius < 0
                or self.end_treatment not in {"closed", "open"}
                or (self.shape == "open-span") != (self.end_treatment == "open")):
            raise _candidate_input_error("LanePlainMarkProjection", shape=self.shape,
                                         semantic_role=self.semantic_role,
                                         paint_order=self.paint_order,
                                         corner_radius=self.corner_radius,
                                         end_treatment=self.end_treatment)


@dataclass(frozen=True)
class LaneGlyphPartProjection:
    """One ordered Theme glyph part with paint intent retained for Scene."""

    part_index: int
    semantic_role: str
    paint_order: int
    paint_mode: str | None
    paint_color: str | None
    mark_shape: str
    corner_radius: float
    end_treatment: str
    stroke_width: float | None = None
    line_cap: str | None = None
    line_join: str | None = None

    def __post_init__(self) -> None:
        if (self.part_index < 0 or not self.semantic_role or self.paint_order < 0
                or self.paint_mode not in {None, "fill", "stroke"}
                or (self.paint_color is not None and not isinstance(self.paint_color, str))
                or self.mark_shape not in {"point", "open-span"}
                or (self.stroke_width is not None and (
                    not isfinite(self.stroke_width) or self.stroke_width <= 0))
                or (self.line_cap is not None and self.line_cap not in {"butt", "round", "square"})
                or (self.line_join is not None and self.line_join not in {"miter", "round", "bevel"})
                or (self.paint_mode != "stroke" and any(
                    value is not None for value in (self.stroke_width, self.line_cap, self.line_join)))
                or not isfinite(self.corner_radius) or self.corner_radius < 0
                or self.end_treatment not in {"closed", "open"}
                or (self.mark_shape == "open-span") != (self.end_treatment == "open")):
            raise _candidate_input_error("LaneGlyphPartProjection", part_index=self.part_index,
                                         semantic_role=self.semantic_role,
                                         paint_order=self.paint_order, paint_mode=self.paint_mode,
                                         mark_shape=self.mark_shape,
                                         stroke_width=self.stroke_width)


@dataclass(frozen=True)
class LaneProgressProjection:
    """Completed progress fill and its exact host clip relation."""

    host_placement_id: str
    host_bounds: Rect
    clip_bounds: Rect
    semantic_role: str
    paint_order: int
    corner_radius: float

    def __post_init__(self) -> None:
        if (not self.host_placement_id or not self.semantic_role or self.paint_order < 0
                or not isfinite(self.corner_radius) or self.corner_radius < 0
                or not isinstance(self.host_bounds, Rect) or not isinstance(self.clip_bounds, Rect)
                or self.clip_bounds.inline < self.host_bounds.inline
                or self.clip_bounds.block < self.host_bounds.block
                or self.clip_bounds.inline + self.clip_bounds.inline_size
                > self.host_bounds.inline + self.host_bounds.inline_size
                or self.clip_bounds.block + self.clip_bounds.block_size
                > self.host_bounds.block + self.host_bounds.block_size):
            raise _candidate_input_error("LaneProgressProjection",
                                         host_placement_id=self.host_placement_id,
                                         semantic_role=self.semantic_role,
                                         host_bounds=self.host_bounds,
                                         clip_bounds=self.clip_bounds)


@dataclass(frozen=True)
class LaneIconProjection:
    """Completed renderer-neutral icon emission data copied from IconPlacement."""

    placement_id: str
    icon_id: str
    kind: str
    asset_identity: str
    viewport: tuple[int, int]
    bounds: Rect
    visual_capability_source_ref: str
    alternative: str
    decorative: bool
    slot_id: str
    paint_order: int
    stroke_scale: float
    path_index: int | None = None
    path_count: int | None = None
    paint: str | None = None
    stroke_width: float | None = None
    line_cap: str | None = None
    line_join: str | None = None
    raster_payload: bytes | None = None

    def __post_init__(self) -> None:
        common_strings = (self.placement_id, self.icon_id, self.asset_identity,
                          self.visual_capability_source_ref, self.slot_id)
        valid_rect = (isinstance(self.bounds, Rect)
                      and all(isfinite(float(value)) for value in
                              (self.bounds.inline, self.bounds.block,
                               self.bounds.inline_size, self.bounds.block_size))
                      and self.bounds.inline_size > 0 and self.bounds.block_size > 0)
        if not (
            all(isinstance(value, str) and value for value in common_strings)
            and isinstance(self.kind, str) and self.kind in {"vector", "raster"}
            and isinstance(self.viewport, tuple) and len(self.viewport) == 2
            and all(isinstance(value, int) and not isinstance(value, bool) and value > 0
                    for value in self.viewport)
            and valid_rect and isinstance(self.alternative, str)
            and isinstance(self.decorative, bool)
            and isinstance(self.paint_order, int) and not isinstance(self.paint_order, bool)
            and self.paint_order >= 0
            and isinstance(self.stroke_scale, (int, float)) and not isinstance(self.stroke_scale, bool)
            and isfinite(self.stroke_scale) and self.stroke_scale > 0
        ):
            raise _candidate_input_error("LaneIconProjection", placement_id=self.placement_id,
                                         icon_id=self.icon_id, kind=self.kind,
                                         path_index=self.path_index, path_count=self.path_count,
                                         paint=self.paint, bounds=self.bounds)
        if self.kind == "vector":
            valid_path = (
                isinstance(self.path_index, int) and not isinstance(self.path_index, bool)
                and isinstance(self.path_count, int) and not isinstance(self.path_count, bool)
                and self.path_count > 0 and 0 <= self.path_index < self.path_count
                and isinstance(self.paint, str) and self.paint in {"fill", "stroke"}
                and self.raster_payload is None
                and (self.stroke_width is None or (
                    isinstance(self.stroke_width, (int, float)) and not isinstance(self.stroke_width, bool)
                    and isfinite(self.stroke_width) and self.stroke_width >= 0))
                and (self.paint != "stroke" or (self.stroke_width is not None
                     and self.stroke_width > 0))
                and (self.line_cap is None or (isinstance(self.line_cap, str)
                                               and self.line_cap in {"butt", "round", "square"}))
                and (self.line_join is None or (isinstance(self.line_join, str)
                                                and self.line_join in {"miter", "round", "bevel"}))
            )
        else:
            valid_path = (
                self.path_index is None and self.path_count is None
                and self.paint is None and self.stroke_width is None
                and self.line_cap is None and self.line_join is None
                and isinstance(self.raster_payload, bytes) and bool(self.raster_payload)
            )
        if not valid_path:
            raise _candidate_input_error("LaneIconProjection", placement_id=self.placement_id,
                                         icon_id=self.icon_id, kind=self.kind,
                                         path_index=self.path_index, path_count=self.path_count,
                                         paint=self.paint, stroke_width=self.stroke_width)

    @property
    def common_metadata(self) -> tuple[object, ...]:
        """Fields that must agree across facets belonging to one emitted icon."""
        return (self.placement_id, self.icon_id, self.kind, self.asset_identity,
                self.viewport, self.bounds, self.visual_capability_source_ref,
                self.alternative, self.decorative, self.slot_id, self.paint_order,
                self.path_count, self.stroke_scale)


@dataclass(frozen=True)
class LaneMarkFacet:
    """One source-keyed, completed primitive and its collision footprint.

    ``projection_instance_id`` distinguishes repeated source objects in
    different Review rows; ``source_ref`` separately retains the stable
    source/object reference. A compound semantic mark has one facet per
    emitted primitive/part, all nested under its countable LaneMember.
    ``primitive_bounds`` are the completed, unexpanded bounds consumed by
    downstream projection; ``visible_footprint`` is the separately completed
    stroke/clearance-aware collision geometry. Semantic ports attach to the
    completed mark slot recorded in ``port_host_bounds``, distinct from both.
    """

    facet_id: str
    projection_instance_id: str
    source_item_id: str
    source_ref: str
    source_kind: str
    purpose: str
    primitive_id: str
    primitive_type: str
    completed_geometry: tuple[tuple[str, tuple[tuple[float, float], ...]], ...]
    primitive_bounds: tuple[float, float, float, float]
    visible_footprint: ObstacleGeometry
    ports: tuple[LaneFacetPort, ...] = ()
    overlay_with: tuple[str, ...] = ()
    port_host_bounds: tuple[float, float, float, float] | None = None
    icon_projection: LaneIconProjection | None = None
    plain_mark_projection: LanePlainMarkProjection | None = None
    glyph_part_projection: LaneGlyphPartProjection | None = None
    progress_projection: LaneProgressProjection | None = None

    def __post_init__(self) -> None:
        identities = (self.facet_id, self.projection_instance_id, self.source_item_id,
                      self.source_ref, self.source_kind, self.purpose, self.primitive_id,
                      self.primitive_type)
        geometry_valid = (
            isinstance(self.completed_geometry, tuple) and bool(self.completed_geometry)
            and all(isinstance(command, tuple) and len(command) == 2
                    and isinstance(command[0], str) and command[0]
                    and isinstance(command[1], tuple)
                    and (bool(command[1]) or command[0] == "close")
                    and all(isinstance(point, tuple) and len(point) == 2
                            and all(isinstance(value, (int, float)) and not isinstance(value, bool)
                                    and isfinite(value) for value in point)
                            for point in command[1])
                    for command in self.completed_geometry)
        )
        if (not all(isinstance(identity, str) and identity for identity in identities)
                or self.primitive_type not in {"Rect", "Path", "Symbol", "Icon", "Raster"}
                or not geometry_valid
                or not isinstance(self.primitive_bounds, tuple) or len(self.primitive_bounds) != 4
                or not all(isinstance(value, (int, float)) and not isinstance(value, bool)
                           and isfinite(value) for value in self.primitive_bounds)
                or self.primitive_bounds[2] < self.primitive_bounds[0]
                or self.primitive_bounds[3] < self.primitive_bounds[1]
                or not isinstance(self.visible_footprint, (ObstacleRect, ObstacleSegment))
                or not isinstance(self.ports, tuple)
                or any(not isinstance(port, LaneFacetPort) for port in self.ports)
                or len({port.port_id for port in self.ports}) != len(self.ports)
                or not isinstance(self.overlay_with, tuple)
                or any(not isinstance(target, str) or not target or target == self.facet_id
                       for target in self.overlay_with)
                or len(set(self.overlay_with)) != len(self.overlay_with)
                or (self.ports and self.port_host_bounds is None)
                or (not self.ports and self.port_host_bounds is not None)
                or (self.port_host_bounds is not None and (
                    not isinstance(self.port_host_bounds, tuple) or len(self.port_host_bounds) != 4
                    or not all(isinstance(value, (int, float)) and not isinstance(value, bool)
                               and isfinite(value) for value in self.port_host_bounds)
                    or self.port_host_bounds[2] < self.port_host_bounds[0]
                    or self.port_host_bounds[3] < self.port_host_bounds[1]))):
            raise _candidate_input_error("LaneMarkFacet", facet_id=self.facet_id,
                                         source_ref=self.source_ref,
                                         primitive_id=self.primitive_id,
                                         primitive_type=self.primitive_type)
        left, top, right, bottom = obstacle_envelope(self.visible_footprint)
        bounds_left, bounds_top, bounds_right, bounds_bottom = self.primitive_bounds
        if not (left - 1e-9 <= bounds_left <= bounds_right <= right + 1e-9
                and top - 1e-9 <= bounds_top <= bounds_bottom <= bottom + 1e-9):
            raise _candidate_input_error("LaneMarkFacet", facet_id=self.facet_id,
                                         primitive_bounds=self.primitive_bounds,
                                         visible_footprint=self.visible_footprint)
        points = (point for _, command_points in self.completed_geometry for point in command_points)
        tolerance = 1e-9
        if any(not (bounds_left - tolerance <= point[0] <= bounds_right + tolerance
                    and bounds_top - tolerance <= point[1] <= bounds_bottom + tolerance) for point in points):
            raise _candidate_input_error("LaneMarkFacet", facet_id=self.facet_id,
                                         primitive_bounds=self.primitive_bounds,
                                         reason="completed point outside bounds")
        host = self.port_host_bounds
        if any(not (host[0] - tolerance <= port.position[0] <= host[2] + tolerance
                    and host[1] - tolerance <= port.position[1] <= host[3] + tolerance)
               for port in self.ports):
            raise _candidate_input_error("LaneMarkFacet", facet_id=self.facet_id,
                                         port_host_bounds=host, port_ids=tuple(p.port_id for p in self.ports))
        if self.icon_projection is not None:
            projection = self.icon_projection
            if (not isinstance(projection, LaneIconProjection)
                    or self.primitive_id != projection.placement_id
                    or self.primitive_type != "Icon"):
                raise _candidate_input_error("LaneMarkFacet", facet_id=self.facet_id,
                                             primitive_id=self.primitive_id,
                                             icon_placement_id=getattr(projection, "placement_id", None),
                                             primitive_type=self.primitive_type)
            if projection.kind == "raster":
                rect = projection.bounds
                expected = (float(rect.inline), float(rect.block),
                            float(rect.inline + rect.inline_size),
                            float(rect.block + rect.block_size))
                if (self.primitive_bounds != expected
                        or not isinstance(self.visible_footprint, ObstacleRect)
                        or (self.visible_footprint.left, self.visible_footprint.top,
                            self.visible_footprint.right, self.visible_footprint.bottom) != expected):
                    raise _candidate_input_error("LaneMarkFacet", facet_id=self.facet_id,
                                                 primitive_bounds=self.primitive_bounds,
                                                 raster_bounds=expected)
        elif self.primitive_type == "Icon":
            raise _candidate_input_error("LaneMarkFacet", facet_id=self.facet_id,
                                         primitive_type=self.primitive_type,
                                         reason="Icon primitive requires icon projection")
        payloads = (self.icon_projection, self.plain_mark_projection,
                    self.glyph_part_projection, self.progress_projection)
        if sum(value is not None for value in payloads) > 1:
            raise _candidate_input_error("LaneMarkFacet", facet_id=self.facet_id,
                                         projection_types=tuple(type(value).__name__
                                                                for value in payloads if value is not None),
                                         reason="at most one projection payload is allowed")
        if ((self.plain_mark_projection is not None and self.primitive_type not in {"Rect", "Path"})
                or (self.glyph_part_projection is not None and self.primitive_type != "Symbol")
                or (self.progress_projection is not None and self.primitive_type != "Rect")):
            raise _candidate_input_error("LaneMarkFacet", facet_id=self.facet_id,
                                         primitive_type=self.primitive_type,
                                         projection_types=tuple(type(value).__name__
                                                                for value in payloads if value is not None))


def _item_by_instance(projection: Any, closure: LaneProjectionClosure) -> dict[LaneProjectionInstance, Any]:
    result: dict[LaneProjectionInstance, Any] = {}
    for row in projection.rows:
        for item in row.items:
            instance = next((value for value in closure.instances
                             if value.row_id == row.row_id
                             and value.item_id == (item.item_id or item.object_id)), None)
            if instance is None:
                raise LayoutError("E_LAYOUT_LANE_PROJECTION_INVALID", f"/projection/rows/{row.row_id}")
            result[instance] = item
    return result

def _compose_mark_icons(marks: Sequence[MarkPlacement],
                        requests: Mapping[tuple[LaneProjectionInstance, str], VisualRequest],
                        icon_assets: Mapping[str, Any], theme_tokens: Any) -> dict[str, tuple[IconPlacement, ...]]:
    result: dict[str, list[IconPlacement]] = {}
    for (instance, role), visual in requests.items():
        hosts = [mark for mark in marks if mark.placement_id == f"{role}:{instance.placement_key}"]
        icon = icon_assets.get(visual.ref or "")
        if len(hosts) != 1 or icon is None:
            raise LayoutError("E_LAYOUT_LANE_ICON_UNAVAILABLE", visual.source_ref)
        host = hosts[0]
        try:
            scale, _ = theme_tokens.icon_ratios("icon-mark")
        except Exception as error:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref) from error
        height = float(host.bounds.block_size) * float(scale)
        if height <= 0 or icon.viewport[1] <= 0:
            raise LayoutError("E_THEME_ICON_RATIO", visual.source_ref)
        width = min(float(host.bounds.inline_size), height * icon.viewport[0] / icon.viewport[1])
        bounds = Rect(host.bounds.inline + (host.bounds.inline_size - Decimal(str(width))) / 2,
                      host.bounds.block + (host.bounds.block_size - Decimal(str(height))) / 2,
                      Decimal(str(width)), Decimal(str(height)))
        placement = IconPlacement(
            f"visual:{host.placement_id}", host.source_ref, visual.source_ref, icon.icon_id,
            icon.kind, icon.content_identity, icon.viewport, icon.payload, icon.alternative,
            visual.decorative, bounds, "iconMark", width / icon.viewport[0], host.slot_id,
            paint_order=host.paint_order + 1,
            completed_paths=complete_icon_paths(icon.payload,
                                                (float(bounds.inline), float(bounds.block),
                                                 float(bounds.inline_size), float(bounds.block_size)),
                                                width / icon.viewport[0]) if icon.kind == "vector" else (),
        )
        result.setdefault(host.placement_id, []).append(placement)
    return {key: tuple(values) for key, values in result.items()}


def _compose_progress(closure: LaneProjectionClosure, items: Mapping[LaneProjectionInstance, Any],
                      marks: Mapping[LaneProjectionInstance, tuple[MarkPlacement, ...]],
                      source: str | None, theme: Any,
                      *, original_marks: Mapping[str, MarkPlacement] | None = None,
                      ) -> dict[str, tuple[Any, ...]]:
    if source is None:
        return {}
    from chrona.presentation.layout.surface_marks import complete_progress_shape

    try:
        inset, radius = theme.progress_track("progress-fill")
    except Exception as error:
        raise LayoutError("E_LAYOUT_LANE_PROGRESS_UNAVAILABLE", "/body/progressFill") from error
    result: dict[str, list[Any]] = {}
    for instance in closure.instances:
        item = items[instance]
        fraction = ((item.actual or {}).get("progress") if source == "actual"
                    else item.planned_progress)
        prefix = "actual" if source == "actual" else "planned"
        host = next((mark for mark in marks[instance]
                     if mark.placement_id.startswith(prefix + ":")), None)
        if not isinstance(fraction, (int, float)) or isinstance(fraction, bool):
            continue
        if not isfinite(float(fraction)) or not 0 <= fraction <= 1:
            raise LayoutError("E_LAYOUT_LANE_PROGRESS_INVALID",
                              f"/projection/rows/{instance.row_id}/items/{instance.item_id}/progress")
        if fraction == 0:
            continue
        if host is None:
            continue
        if host.paint_clip is not None and (original_marks is None or host.placement_id not in original_marks):
            raise LayoutError("E_LAYOUT_WINDOW_CLIP", "/body/progressFill",
                              detail="stage=progress; reason=missing-original-host")
        original_host = original_marks.get(host.placement_id, host) if original_marks is not None else host
        shape = complete_progress_shape(host, original_host=original_host,
            fraction=float(fraction), inset_ratio=inset, radius_ratio=radius)
        if shape is None:
            continue
        if not _rect_contains(host.bounds, shape.bounds):
            raise LayoutError("E_LAYOUT_LANE_PROGRESS_INVALID", shape.placement_id)
        result.setdefault(host.placement_id, []).append(shape)
    return {key: tuple(values) for key, values in result.items()}


def span_mark_footprint(mark: MarkPlacement, theme: Any) -> ObstacleRect:
    """Complete a span's visible paint bounds without changing semantic ports."""
    width = _stroke_width(theme, mark.semantic_id)
    return _expanded_rect(_bounds(mark.bounds), width / 2 if width is not None else 0.0, mark.placement_id)


def _mark_facets(item: Any, instance: LaneProjectionInstance, mark: MarkPlacement,
                 theme: Any) -> tuple[LaneMarkFacet, ...]:
    if mark.mark_shape == "span":
        bounds = _bounds(mark.bounds)
        footprint = span_mark_footprint(mark, theme)
        payload = LanePlainMarkProjection(mark.mark_shape, mark.semantic_id, mark.paint_order,
                                          mark.corner_radius, mark.end_treatment)
        return (_facet(instance, item, mark, mark.placement_id, "Rect",
                       (("rect", _rect_points(bounds)),), bounds, footprint,
                       mark, plain=payload),)
    if not mark.symbol_parts:
        raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", mark.placement_id)
    result: list[LaneMarkFacet] = []
    for index, part in enumerate(mark.symbol_parts):
        commands = _commands(part.commands)
        points = tuple(point for _, pairs in commands for point in pairs)
        if not points:
            raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", mark.placement_id)
        bounds = _point_bounds(points)
        stroke_width = (part.stroke_width if part.stroke_width is not None else
                        _stroke_width(theme, mark.semantic_id) if part.paint_mode == "stroke" else None)
        if part.paint_mode == "stroke" and (stroke_width is None or stroke_width <= 0):
            raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", mark.placement_id,
                              detail="stroke glyph has no finite positive Theme width")
        footprint = _path_footprint(points, stroke_width, mark.placement_id)
        part_payload = LaneGlyphPartProjection(
            index, mark.semantic_id, mark.paint_order + index,
            part.paint_mode, part.paint_color,
            mark.mark_shape, mark.corner_radius, mark.end_treatment,
            stroke_width, part.line_cap, part.line_join,
        )
        primitive_id = mark.placement_id if len(mark.symbol_parts) == 1 else f"{mark.placement_id}:part:{index}"
        result.append(_facet(instance, item, mark, primitive_id, "Symbol", commands,
                             bounds, footprint, mark if index == 0 else None,
                             glyph=part_payload))
    return tuple(result)


def _with_mark_visuals(item: Any, instance: LaneProjectionInstance, mark: MarkPlacement,
                       facets: tuple[LaneMarkFacet, ...], icons: Sequence[IconPlacement],
                       progress: Sequence[Any], theme: Any) -> tuple[LaneMarkFacet, ...]:
    result = list(facets)
    for icon in icons:
        icon_facets = _overlay_all(_icon_facets(item, instance, icon))
        result.extend(_with_overlay_targets(icon_facets,
                                            tuple(facet.facet_id for facet in facets)))
        result[:len(facets)] = list(_with_overlay_targets(tuple(result[:len(facets)]),
                                                         tuple(facet.facet_id for facet in icon_facets)))
    for shape in progress:
        bounds = _bounds(shape.bounds)
        width = _stroke_width(theme, "progress-fill")
        footprint = _expanded_rect(bounds, width / 2 if width is not None else 0.0, shape.placement_id)
        host = mark
        payload = LaneProgressProjection(host.placement_id, host.bounds, shape.bounds,
                                         shape.semantic_id, shape.paint_order,
                                         shape.corner_radius)
        result.append(_facet(instance, item, mark, shape.placement_id, "Rect",
                             (("rect", _rect_points(bounds)),), bounds, footprint, None,
                             progress=payload))
        result[-1] = _with_overlay_targets((result[-1],),
                                           tuple(facet.facet_id for facet in facets))[0]
        # The host relation is symmetric and restricted to this exact mark.
        result[:len(facets)] = list(_with_overlay_targets(tuple(result[:len(facets)]),
                                                         (result[-1].facet_id,)))
    return tuple(result)


def _icon_facets(item: Any, instance: LaneProjectionInstance,
                 icon: IconPlacement) -> tuple[LaneMarkFacet, ...]:
    if icon.kind == "raster":
        if not isinstance(icon.payload, bytes) or not icon.payload:
            raise LayoutError("E_LAYOUT_LANE_ICON_UNAVAILABLE", icon.placement_id)
        bounds = _bounds(icon.bounds)
        projection = LaneIconProjection(
            icon.placement_id, icon.icon_id, "raster", icon.asset_identity,
            icon.viewport, icon.bounds, icon.visual_capability_source_ref,
            icon.alternative, icon.decorative, icon.slot_id, icon.paint_order,
            icon.stroke_scale, raster_payload=icon.payload,
        )
        return (_facet(instance, item, None, icon.placement_id, "Icon",
                       (("viewport", _rect_points(bounds)),), bounds,
                       _expanded_rect(bounds, 0, icon.placement_id), None,
                       icon=projection),)
    if icon.kind != "vector" or not icon.completed_paths:
        raise LayoutError("E_LAYOUT_LANE_ICON_UNAVAILABLE", icon.placement_id)
    result: list[LaneMarkFacet] = []
    count = len(icon.completed_paths)
    for index, path in enumerate(icon.completed_paths):
        commands = _commands(path.commands)
        points = tuple(point for _, pairs in commands for point in pairs)
        if not points:
            raise LayoutError("E_LAYOUT_LANE_ICON_UNAVAILABLE", icon.placement_id)
        bounds = _point_bounds(points)
        width = path.stroke_width
        if path.paint == "stroke" and (width is None or not isfinite(width) or width <= 0):
            raise LayoutError("E_LAYOUT_LANE_ICON_UNAVAILABLE", icon.placement_id,
                              detail="stroke icon path has no finite positive width")
        projection = LaneIconProjection(
            icon.placement_id, icon.icon_id, "vector", icon.asset_identity,
            icon.viewport, icon.bounds, icon.visual_capability_source_ref,
            icon.alternative, icon.decorative, icon.slot_id, icon.paint_order,
            icon.stroke_scale, path_index=index, path_count=count,
            paint=path.paint, stroke_width=width, line_cap=path.line_cap,
            line_join=path.line_join,
        )
        result.append(_facet(instance, item, None, icon.placement_id, "Icon",
                             commands, bounds, _path_footprint(points, width, icon.placement_id),
                             None, icon=projection, facet_suffix=f"{icon.placement_id}:path:{index}"))
    return tuple(result)


def _facet(instance: LaneProjectionInstance, item: Any, mark: MarkPlacement | None,
           primitive_id: str, primitive_type: str, commands: tuple,
           bounds: tuple[float, float, float, float], footprint: ObstacleGeometry,
           port_mark: MarkPlacement | None, *, plain=None, glyph=None,
           progress=None, icon=None, facet_suffix: str | None = None) -> LaneMarkFacet:
    source_item = item.item_id or item.object_id
    purpose = ("progress" if progress is not None else "icon" if icon is not None else
               mark.semantic_id if mark is not None else "mark")
    id_value = facet_suffix or primitive_id
    facet_id = f"{instance.placement_key}:{quote(purpose, safe='-._~')}:{quote(id_value, safe='-._~')}"
    ports: tuple[LaneFacetPort, ...] = ()
    host_bounds = None
    if port_mark is not None:
        port_prefix = f"{instance.placement_key}:{quote(primitive_id, safe='-._~')}"
        ports = tuple(LaneFacetPort(f"{port_prefix}:{suffix}", suffix, position)
                      for suffix, position in (("start", port_mark.start_port),
                                               ("end", port_mark.end_port))
                      if position is not None)
        if ports:
            host_bounds = _bounds(port_mark.bounds)
    return LaneMarkFacet(
        facet_id, instance.placement_key, source_item, item.object_id,
        "primary" if item.source_kind == "combined" else item.source_kind,
        purpose, primitive_id, primitive_type, commands, bounds, footprint,
        ports, port_host_bounds=host_bounds, icon_projection=icon,
        plain_mark_projection=plain, glyph_part_projection=glyph,
        progress_projection=progress,
    )


def _stroke_width(theme: Any, role: str) -> float | None:
    value = theme.optional_number(role, "strokeWidth")
    if value is None:
        return None
    width = float(value)
    if not isfinite(width) or width < 0:
        raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", f"/body/roles/{role}/strokeWidth")
    return width


def _path_footprint(points: tuple[tuple[float, float], ...], stroke_width: float | None,
                    path: str) -> ObstacleGeometry:
    if stroke_width is not None and len(points) == 2 and points[0] != points[1]:
        return ObstacleSegment(points[0], points[1], stroke_width=stroke_width)
    bounds = _point_bounds(points)
    if bounds[2] <= bounds[0] or bounds[3] <= bounds[1]:
        if len(points) >= 2 and points[0] != points[-1]:
            return ObstacleSegment(points[0], points[-1], stroke_width=stroke_width or 0.0)
        raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", path)
    return _expanded_rect(bounds, 10 * stroke_width if stroke_width is not None else 0.0, path)


def _expanded_rect(bounds: tuple[float, float, float, float], expansion: float,
                   path: str) -> ObstacleRect:
    left, top, right, bottom = bounds
    result = ObstacleRect(left - expansion, top - expansion,
                          right + expansion, bottom + expansion)
    if not all(isfinite(value) for value in (result.left, result.top, result.right, result.bottom)):
        raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", path)
    return result


def _bounds(rect: Rect) -> tuple[float, float, float, float]:
    left, top = float(rect.inline), float(rect.block)
    return left, top, left + float(rect.inline_size), top + float(rect.block_size)


def _rect_points(bounds: tuple[float, float, float, float]) -> tuple[tuple[float, float], ...]:
    left, top, right, bottom = bounds
    return ((left, top), (right, top), (right, bottom), (left, bottom))


def _commands(commands: Sequence[Any]) -> tuple[tuple[str, tuple[tuple[float, float], ...]], ...]:
    result = tuple((command.kind, tuple(tuple(point) for point in command.points))
                   if hasattr(command, "kind") else
                   (command[0], tuple(tuple(point) for point in command[1]))
                   for command in commands)
    if (not result or any(not all(isinstance(value, (int, float)) and isfinite(value)
                                  for point in points for value in point)
                          for _, points in result)):
        raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", "/layout/geometry")
    return result


def _point_bounds(points: Sequence[tuple[float, float]]) -> tuple[float, float, float, float]:
    if not points:
        raise LayoutError("E_LAYOUT_LANE_FACET_UNAVAILABLE", "/layout/geometry")
    return (min(point[0] for point in points), min(point[1] for point in points),
            max(point[0] for point in points), max(point[1] for point in points))


def _rect_contains(host: Rect, child: Rect) -> bool:
    return (host.inline <= child.inline and host.block <= child.block
            and host.inline + host.inline_size >= child.inline + child.inline_size
            and host.block + host.block_size >= child.block + child.block_size)


def _overlay_compound_facets(facets: tuple[LaneMarkFacet, ...]) -> tuple[LaneMarkFacet, ...]:
    return _with_overlay_targets(
        facets, tuple(other.facet_id for other in facets)) if len(facets) > 1 else facets


def _overlay_all(facets: tuple[LaneMarkFacet, ...]) -> tuple[LaneMarkFacet, ...]:
    return tuple(_with_overlay_targets((facet,),
                                       tuple(other.facet_id for other in facets if other is not facet))[0]
                 for facet in facets)


def _with_overlay_targets(facets: tuple[LaneMarkFacet, ...], targets: tuple[str, ...]
                          ) -> tuple[LaneMarkFacet, ...]:
    return tuple(replace(facet, overlay_with=tuple(dict.fromkeys((*facet.overlay_with,
                                                                  *(target for target in targets
                                                                    if target != facet.facet_id)))))
                 for facet in facets)
