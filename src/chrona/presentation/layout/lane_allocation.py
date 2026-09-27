"""Collision-aware lane allocation for `rows.mode: lanes` (#467).

This module is schema-free: it knows nothing of View/Project resources. It
takes closed, measured candidate footprints (mark rectangles plus title/delta
text widths) and returns a deterministic group-local lane assignment with a
required, reserved label placement for every candidate. It reuses the one
#466 :class:`SurfaceObstacleIndex` machinery so that "touching" and
"collision" mean exactly what they mean for every other completed Layout
placement; each lane gets its own index instance because the ladder is
measured in the lane's local frame (translated to final block coordinates by
the caller) and lanes never share obstacles with each other.

This is the partial B1b allocator extension only. It accepts an already
closed atomic bundle and preserves each member's identity and required label;
it does not map ReviewProjection or resolve marks, typography, or icons from
render inputs. That projection-to-bundle mapper remains a separate B1b slice.

Ladder (fixed by the #467/#494 feasibility and route correction):
for each candidate in a candidate lane, try, in order:

1. ``label-row-1``: a label row above the mark level, aligned to the bar's start;
2. ``label-row-2``: a second label row above the mark level, aligned to the bar's end;
3. ``end``: same level as the mark, immediately after it;
4. ``start``: same level as the mark, immediately before it.
5. ``label-row-3-start``: third stagger row, aligned to the mark's start;
6. ``label-row-3-end``: third stagger row, aligned to the mark's end.

A lane has at most three label rows; its block extent is the mark level plus
however many label rows it actually uses (0 through 3). A name is never
suppressed: if no candidate lane, including a freshly opened one, admits a
fitting placement, the item is placed on the terminal `visible-overflow`
level (`end`, translated to the lane's own frame) and recorded as such,
never dropped.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from types import MappingProxyType
from typing import Mapping, Sequence
from urllib.parse import quote

from chrona.presentation.layout.model import Rect, geometry_sum
from chrona.presentation.layout.obstacles import (
    ObstacleRect,
    ObstacleGeometry,
    ObstacleSegment,
    SurfaceObstacle,
    SurfaceObstacleIndex,
    obstacle_envelope,
)

LADDER = ("label-row-1", "label-row-2", "end", "start",
          "label-row-3-start", "label-row-3-end")
_MARK_CLASS = "lane-mark"
_LABEL_CLASS_BY_LEVEL: Mapping[str, str] = {
    "label-row-1": "lane-label-row-1",
    "label-row-2": "lane-label-row-2",
    "label-row-3-start": "lane-label-row-3",
    "label-row-3-end": "lane-label-row-3",
    "end": "lane-label-inline",
    "start": "lane-label-inline",
}


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
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")


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
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")


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

    def __post_init__(self) -> None:
        if (self.part_index < 0 or not self.semantic_role or self.paint_order < 0
                or self.paint_mode not in {None, "fill", "stroke"}
                or (self.paint_color is not None and not isinstance(self.paint_color, str))
                or self.mark_shape not in {"point", "open-span"}
                or not isfinite(self.corner_radius) or self.corner_radius < 0
                or self.end_treatment not in {"closed", "open"}
                or (self.mark_shape == "open-span") != (self.end_treatment == "open")):
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")


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
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")


@dataclass(frozen=True)
class LaneLabelVisualProjection:
    """One resolved leading/trailing icon measured for a required label."""

    side: str
    icon_id: str
    asset_identity: str
    viewport: tuple[int, int]
    width: float
    height: float
    gap: float
    measured_bounds: Rect
    alternative: str
    decorative: bool

    def __post_init__(self) -> None:
        if (self.side not in {"leading", "trailing"} or not self.icon_id
                or not self.asset_identity or not isinstance(self.alternative, str)
                or len(self.viewport) != 2 or any(not isinstance(value, int) or value <= 0 for value in self.viewport)
                or any(not isfinite(value) or value <= 0 for value in (self.width, self.height))
                or not isinstance(self.measured_bounds, Rect)
                or not isfinite(self.gap) or self.gap < 0 or not isinstance(self.decorative, bool)):
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")


@dataclass(frozen=True)
class LaneRequiredLabelProjection:
    """Measured required title/delta run retained through preflight."""

    title: str
    delta: str | None
    content: str
    typography_role: str
    normalized_content: str
    font_family: str
    font_weight: int
    font_size: float
    line_height: float
    letter_spacing: float
    text_transform: str
    numeric_spacing: str
    theme_identity: str
    font_asset_identity: str
    scale_identity: str
    text_width: float
    delta_width: float | None
    text_block_size: float
    leading_visuals: tuple[LaneLabelVisualProjection, ...] = ()
    trailing_visuals: tuple[LaneLabelVisualProjection, ...] = ()

    def __post_init__(self) -> None:
        if (not self.title or not self.content or not self.typography_role or not self.normalized_content
                or not self.font_family or self.font_weight < 0
                or not isfinite(self.font_size) or self.font_size <= 0
                or not isfinite(self.line_height) or self.line_height <= 0
                or not isfinite(self.letter_spacing) or self.letter_spacing < 0
                or self.text_transform not in {"none", "uppercase", "lowercase", "capitalize"}
                or self.numeric_spacing not in {"proportional", "tabular"}
                or not self.theme_identity or not self.font_asset_identity or not self.scale_identity
                or not isfinite(self.text_width) or self.text_width <= 0
                or (self.delta_width is not None and (not isfinite(self.delta_width) or self.delta_width < 0))
                or not isfinite(self.text_block_size) or self.text_block_size <= 0
                or any(item.side != "leading" for item in self.leading_visuals)
                or any(item.side != "trailing" for item in self.trailing_visuals)):
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")

    @property
    def required_inline_size(self) -> float:
        return geometry_sum((self.text_width, *(item.width + item.gap
                                                for item in (*self.leading_visuals,
                                                             *self.trailing_visuals))))


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
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
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
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")

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
                    and isinstance(command[1], tuple) and bool(command[1])
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
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        left, top, right, bottom = obstacle_envelope(self.visible_footprint)
        bounds_left, bounds_top, bounds_right, bounds_bottom = self.primitive_bounds
        if not (left - 1e-9 <= bounds_left <= bounds_right <= right + 1e-9
                and top - 1e-9 <= bounds_top <= bounds_bottom <= bottom + 1e-9):
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        points = (point for _, command_points in self.completed_geometry for point in command_points)
        tolerance = 1e-9
        if any(not (bounds_left - tolerance <= point[0] <= bounds_right + tolerance
                    and bounds_top - tolerance <= point[1] <= bounds_bottom + tolerance) for point in points):
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        host = self.port_host_bounds
        if any(not (host[0] - tolerance <= port.position[0] <= host[2] + tolerance
                    and host[1] - tolerance <= port.position[1] <= host[3] + tolerance)
               for port in self.ports):
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        if self.icon_projection is not None:
            projection = self.icon_projection
            if (not isinstance(projection, LaneIconProjection)
                    or self.primitive_id != projection.placement_id
                    or self.primitive_type != "Icon"):
                raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
            if projection.kind == "raster":
                rect = projection.bounds
                expected = (float(rect.inline), float(rect.block),
                            float(rect.inline + rect.inline_size),
                            float(rect.block + rect.block_size))
                if (self.primitive_bounds != expected
                        or not isinstance(self.visible_footprint, ObstacleRect)
                        or (self.visible_footprint.left, self.visible_footprint.top,
                            self.visible_footprint.right, self.visible_footprint.bottom) != expected):
                    raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        elif self.primitive_type == "Icon":
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        payloads = (self.icon_projection, self.plain_mark_projection,
                    self.glyph_part_projection, self.progress_projection)
        if sum(value is not None for value in payloads) > 1:
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        if ((self.plain_mark_projection is not None and self.primitive_type not in {"Rect", "Path"})
                or (self.glyph_part_projection is not None and self.primitive_type != "Symbol")
                or (self.progress_projection is not None and self.primitive_type != "Rect")):
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")


@dataclass(frozen=True)
class LaneMark:
    """One candidate mark and its immutable source-keyed primitive facets.

    ``left``/``right`` are inline (time-axis) coordinates; the mark occupies
    the full mark-level block band. Every additional visual is a
    :class:`LaneMarkFacet`; visible footprints are derived from those facets
    so provenance and collision geometry cannot drift apart.
    """

    left: float
    right: float
    facets: tuple[LaneMarkFacet, ...] = ()

    def __post_init__(self) -> None:
        if not isfinite(self.left) or not isfinite(self.right) or self.right <= self.left:
            raise ValueError("E_LAYOUT_LANE_MARK_GEOMETRY")
        if (not isinstance(self.facets, tuple)
                or any(not isinstance(facet, LaneMarkFacet) for facet in self.facets)
                or len({facet.facet_id for facet in self.facets}) != len(self.facets)):
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        icon_groups: dict[str, list[LaneIconProjection]] = {}
        for facet in self.facets:
            if facet.icon_projection is not None:
                icon_groups.setdefault(facet.icon_projection.placement_id, []).append(facet.icon_projection)
        for members in icon_groups.values():
            first = members[0]
            if any(facet_value.primitive_type != "Icon"
                   or facet_value.primitive_id != first.placement_id
                   for facet_value in self.facets
                   if facet_value.icon_projection is not None
                   and facet_value.icon_projection.placement_id == first.placement_id):
                raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
            if any(item.common_metadata != first.common_metadata for item in members[1:]):
                raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
            if first.kind == "raster":
                if len(members) != 1:
                    raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
            elif (len(members) != first.path_count
                  or sorted(item.path_index for item in members) != list(range(first.path_count or 0))):
                raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")

    @property
    def footprints(self) -> tuple[ObstacleGeometry, ...]:
        """The collision-only view of facets, derived in their stable order."""
        return tuple(facet.visible_footprint for facet in self.facets)


@dataclass(frozen=True)
class LaneMember:
    """One independently identified mark and required label in a bundle.

    Comparison/Actual visuals are facets on ``mark`` and do not add a member
    or item count. ``member_id`` is reserved for one countable root or
    attached Review item; intentional overlays name facet IDs instead.
    """

    member_id: str
    mark: LaneMark
    title_width: float
    delta_width: float | None = None
    required_label: LaneRequiredLabelProjection | None = None

    @property
    def label_width(self) -> float:
        return self.title_width + (0.0 if self.delta_width is None else self.delta_width)


@dataclass(frozen=True)
class LaneCandidate:
    """One selected primary Review Item eligible for group-local lane packing."""

    candidate_id: str
    group_key: str
    order_key: tuple
    mark: LaneMark
    title_width: float
    delta_width: float | None = None
    predecessors: tuple[tuple[str, str], ...] = ()
    """``(relation_id, predecessor_candidate_id)`` pairs for immediate
    finish-to-start predecessors; the caller resolves which relations are
    immediate finish-to-start, not this module."""
    group_order: tuple = ()
    bundle: tuple[LaneMember, ...] = ()

    def __post_init__(self) -> None:
        if not self.candidate_id:
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        if (not isfinite(self.title_width) or self.title_width <= 0
                or (self.delta_width is not None and (not isfinite(self.delta_width) or self.delta_width < 0))
                or not isfinite(self.label_width)):
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        if self.bundle:
            ids = tuple(member.member_id for member in self.bundle)
            if (ids[0] != self.candidate_id or len(set(ids)) != len(ids)
                    or (self.bundle[0].mark, self.bundle[0].title_width, self.bundle[0].delta_width)
                    != (self.mark, self.title_width, self.delta_width)):
                raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
            known = set(ids)
            for member in self.bundle:
                if (not member.member_id or not isfinite(member.title_width) or member.title_width <= 0
                        or (member.delta_width is not None and
                            (not isfinite(member.delta_width) or member.delta_width < 0))
                        or not isfinite(member.label_width)):
                    raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
                if (member.required_label is not None
                        and abs(member.title_width - member.required_label.required_inline_size) > 1e-9):
                    raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        members = self.members_for_placement
        facets = tuple(facet for member in members for facet in member.mark.facets)
        facet_ids = {facet.facet_id for facet in facets}
        port_ids = [port.port_id for facet in facets for port in facet.ports]
        if len(facet_ids) != len(facets) or any(
                target not in facet_ids for facet in facets for target in facet.overlay_with
        ) or len(set(port_ids)) != len(port_ids) or any(not member.mark.facets for member in members):
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        # The explicit facet IDs are the overlay authority. Source references
        # may differ for a host and its attached point; target closure above
        # ensures an exemption cannot escape this atomic candidate bundle.

    @property
    def members_for_placement(self) -> tuple[LaneMember, ...]:
        return self.bundle or (LaneMember(self.candidate_id, self.mark, self.title_width, self.delta_width),)

    @property
    def label_width(self) -> float:
        return self.title_width + (0.0 if self.delta_width is None else self.delta_width)


@dataclass(frozen=True)
class LanePlacement:
    """One candidate's accepted, lane-local placement."""

    candidate_id: str
    level: str
    """One of :data:`LADDER`, or ``"visible-overflow"`` for the terminal case."""
    rect: ObstacleRect
    visible_overflow: bool = False
    member_placements: Mapping[str, "LanePlacement"] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True)
class LaneAssignment:
    """One generated lane's stable identity, members and reserved block extent."""

    lane_id: str
    group_key: str
    representative_id: str
    members: tuple[str, ...]
    placements: Mapping[str, LanePlacement]
    label_rows_used: int
    block_extent: float
    """Mark-level height plus ``label_rows_used`` label-row heights."""


@dataclass(frozen=True)
class LaneAllocationResult:
    lanes: tuple[LaneAssignment, ...]

    def lane_of(self, candidate_id: str) -> LaneAssignment:
        for lane in self.lanes:
            if candidate_id in lane.members:
                return lane
        raise KeyError(candidate_id)


class _Lane:
    """Mutable working state for one candidate lane during allocation."""

    def __init__(self, lane_id: str, group_key: str, representative_id: str,
                 mark_row_height: float, label_row_height: float, clearance: float,
                 canvas_left: float | None, canvas_right: float | None) -> None:
        self.lane_id = lane_id
        self.group_key = group_key
        self.representative_id = representative_id
        self.members: list[str] = []
        self.placements: dict[str, LanePlacement] = {}
        self.label_rows_used = 0
        self._mark_row_height = mark_row_height
        self._label_row_height = label_row_height
        self._clearance = clearance
        self._canvas_left = canvas_left
        self._canvas_right = canvas_right
        self._index = SurfaceObstacleIndex()

    def try_place(self, candidate: LaneCandidate, *, allow_visible_overflow: bool = False) -> LanePlacement | None:
        """Return the first ladder placement that fits, or ``None``."""
        members = candidate.members_for_placement
        all_mark_geometries = {member.member_id: self._member_mark_geometries(member) for member in members}
        # Compare every proposed member with already accepted lane content.
        for member in members:
            mark_geometries = all_mark_geometries[member.member_id]
            if any(self._index.collisions(geometry, classes=(_MARK_CLASS, "lane-label-inline"),
                                          clearance=self._clearance) for geometry in mark_geometries):
                return None
        # All emitted marks are facets. Their candidate interval rectangles
        # are coarse placement bands and are intentionally excluded here;
        # exact facet pairs must either fit or name their explicit overlay.
        facets = tuple(facet for member in members for facet in member.mark.facets)
        for index, facet in enumerate(facets):
            for other in facets[index + 1:]:
                allowed = (other.facet_id in facet.overlay_with
                           or facet.facet_id in other.overlay_with)
                if (not allowed and _geometries_collide(
                        facet.visible_footprint, other.visible_footprint, self._clearance)):
                    raise ValueError("E_LAYOUT_LANE_BUNDLE_MARK_COLLISION")
        # A new mark shares its band with any earlier item's already-accepted
        # `end`/`start` label (the same two-way check `try_place` applies to
        # a new `end`/`start` candidate against earlier marks, below): a
        # later mark must not land inside an earlier inline label either.
        trial = SurfaceObstacleIndex()
        for existing in self._index.all():
            trial.add(existing)
        for member in members:
            for index, geometry in enumerate(all_mark_geometries[member.member_id]):
                trial.add(SurfaceObstacle(f"bundle-mark:{member.member_id}:{index}", _MARK_CLASS,
                                          self.lane_id, geometry, clearance=self._clearance))
        per_member: dict[str, LanePlacement] = {}
        for member in members:
            chosen: LanePlacement | None = None
            for level in LADDER:
                rect = self._member_rect(member, level)
                if ((self._canvas_left is not None and rect.left < self._canvas_left)
                        or (self._canvas_right is not None and rect.right > self._canvas_right)):
                    continue
                classes = tuple(_LABEL_CLASS_BY_LEVEL.values())
                if level in ("end", "start"):
                    classes += (_MARK_CLASS,)
                if not trial.collisions(rect, classes=classes, clearance=self._clearance):
                    chosen = LanePlacement(member.member_id, level, rect)
                    break
            if chosen is None:
                if not allow_visible_overflow:
                    return None
                chosen = LanePlacement(member.member_id, "visible-overflow",
                                       self.overflow_rect_for_member(member), visible_overflow=True)
            per_member[member.member_id] = chosen
            trial.add(SurfaceObstacle(f"bundle-label:{member.member_id}",
                                      _LABEL_CLASS_BY_LEVEL.get(chosen.level, "lane-label-overflow"),
                                      self.lane_id, chosen.rect, clearance=self._clearance))
        root = per_member[candidate.candidate_id]
        return LanePlacement(candidate.candidate_id, root.level, root.rect, root.visible_overflow,
                             MappingProxyType(per_member))

    def _mark_geometries(self, candidate: LaneCandidate) -> tuple[ObstacleGeometry, ...]:
        return self._member_mark_geometries(LaneMember(candidate.candidate_id, candidate.mark,
                                                       candidate.title_width, candidate.delta_width))

    def _member_mark_geometries(self, member: LaneMember) -> tuple[ObstacleGeometry, ...]:
        primary = ObstacleRect(member.mark.left, 0.0, member.mark.right, self._mark_row_height)
        footprints = member.mark.footprints
        for geometry in footprints:
            _, top, _, bottom = obstacle_envelope(geometry)
            if top < 0.0 or bottom > self._mark_row_height:
                raise ValueError("E_LAYOUT_LANE_MARK_GEOMETRY")
        return (primary, *footprints)

    def _candidate_rect(self, candidate: LaneCandidate, level: str) -> ObstacleRect:
        return self._member_rect(candidate.members_for_placement[0], level)

    def _member_rect(self, member: LaneMember, level: str) -> ObstacleRect:
        left, right = member.mark.left, member.mark.right
        width = member.label_width
        if level == "label-row-1":
            top = -self._label_row_height
            return ObstacleRect(left, top, left + width, top + self._label_row_height)
        if level == "label-row-2":
            top = -2 * self._label_row_height
            return ObstacleRect(right - width, top, right, top + self._label_row_height)
        if level == "label-row-3-start":
            top = -3 * self._label_row_height
            return ObstacleRect(left, top, left + width, top + self._label_row_height)
        if level == "label-row-3-end":
            top = -3 * self._label_row_height
            return ObstacleRect(right - width, top, right, top + self._label_row_height)
        if level == "end":
            return ObstacleRect(right, 0.0, right + width, self._mark_row_height)
        if level == "start":
            return ObstacleRect(left - width, 0.0, left, self._mark_row_height)
        raise ValueError("E_LAYOUT_LANE_LADDER_LEVEL")

    def accept(self, candidate: LaneCandidate, placement: LanePlacement) -> None:
        members = candidate.members_for_placement
        for member in members:
            for index, geometry in enumerate(self._member_mark_geometries(member)):
                self._index.add(SurfaceObstacle(f"{member.member_id}:mark:{index}", _MARK_CLASS,
                                                self.lane_id, geometry, clearance=self._clearance))
            member_placement = placement.member_placements.get(member.member_id, placement)
            obstacle_class = _LABEL_CLASS_BY_LEVEL.get(member_placement.level, "lane-label-overflow")
            rect = (self.overflow_rect_for_member(member) if member_placement.visible_overflow
                    else self._member_rect(member, member_placement.level))
            self._index.add(SurfaceObstacle(f"{member.member_id}:label", obstacle_class, self.lane_id,
                                            rect, clearance=self._clearance))
            self.members.append(member.member_id)
            self.placements[member.member_id] = LanePlacement(member.member_id, member_placement.level, rect,
                                                               member_placement.visible_overflow)
            rows = {"label-row-1": 1, "label-row-2": 2,
                    "label-row-3-start": 3, "label-row-3-end": 3}
            self.label_rows_used = max(self.label_rows_used, rows.get(member_placement.level, 0))

    def block_extent(self) -> float:
        return self._mark_row_height + self.label_rows_used * self._label_row_height

    def overflow_rect(self, candidate: LaneCandidate) -> ObstacleRect:
        return self.overflow_rect_for_member(candidate.members_for_placement[0])

    def overflow_rect_for_member(self, member: LaneMember) -> ObstacleRect:
        right = member.mark.right
        return ObstacleRect(right, 0.0, right + member.label_width, self._mark_row_height)


def allocate_lanes(candidates: Sequence[LaneCandidate], *, mark_row_height: float = 1.0,
                   label_row_height: float = 1.0, clearance: float = 0.0,
                   canvas_left: float | None = None,
                   canvas_right: float | None = None) -> LaneAllocationResult:
    """Deterministically pack ``candidates`` into group-local collision-free lanes.

    Candidates must already be measured (finite mark and text footprints).
    Ordering, group isolation and predecessor preference follow the #467
    design; the label ladder follows the #467 L0 ladder correction. No
    candidate is ever dropped: a candidate that fits nowhere else gets the
    terminal ``visible-overflow`` placement in a fresh lane.

    ``canvas_left``/``canvas_right`` are the finite plot bounds a label
    candidate must stay within to count as "fitting"; omit either to leave
    that side unbounded (as neutral algorithm tests do).
    """
    if (not isfinite(mark_row_height) or mark_row_height <= 0
            or not isfinite(label_row_height) or label_row_height <= 0
            or not isfinite(clearance) or clearance < 0
            or any(bound is not None and not isfinite(bound) for bound in (canvas_left, canvas_right))
            or (canvas_left is not None and canvas_right is not None and canvas_right <= canvas_left)):
        raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
    all_member_ids = [member.member_id for item in candidates for member in item.members_for_placement]
    if len(set(all_member_ids)) != len(all_member_ids):
        raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
    all_facet_ids = [facet.facet_id for item in candidates for member in item.members_for_placement
                     for facet in member.mark.facets]
    if len(set(all_facet_ids)) != len(all_facet_ids):
        raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
    all_port_ids = [port.port_id for item in candidates for member in item.members_for_placement
                    for facet in member.mark.facets for port in facet.ports]
    if len(set(all_port_ids)) != len(all_port_ids):
        raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
    orders: dict[str, tuple] = {}
    for item in candidates:
        if item.group_key in orders and orders[item.group_key] != item.group_order:
            raise ValueError("E_LAYOUT_LANE_CANDIDATE_INPUT")
        orders[item.group_key] = item.group_order
    ordered = sorted(candidates, key=lambda item: (item.group_order, item.group_key,
                                                    item.order_key, item.candidate_id))
    lanes: list[_Lane] = []
    lane_by_candidate: dict[str, _Lane] = {}
    by_id = {item.candidate_id: item for item in candidates}
    lane_counters: dict[str, int] = {}

    def open_lane(group_key: str, representative_id: str) -> _Lane:
        lane_counters[group_key] = lane_counters.get(group_key, 0) + 1
        group_identity = "u" if not group_key else "g" + quote(group_key, safe="")
        lane = _Lane(f"lane:{group_identity}:{quote(representative_id, safe='')}", group_key, representative_id,
                    mark_row_height, label_row_height, clearance, canvas_left, canvas_right)
        lanes.append(lane)
        return lane

    for candidate in ordered:
        group_lanes = [lane for lane in lanes if lane.group_key == candidate.group_key]
        predecessor_lane = _eligible_predecessor_lane(candidate, by_id, lane_by_candidate)
        search_order: list[_Lane] = []
        if predecessor_lane is not None:
            search_order.append(predecessor_lane)
        search_order.extend(lane for lane in group_lanes if lane is not predecessor_lane)
        accepted = False
        for lane in search_order:
            placement = lane.try_place(candidate)
            if placement is not None:
                lane.accept(candidate, placement)
                for member in candidate.members_for_placement:
                    lane_by_candidate[member.member_id] = lane
                accepted = True
                break
        if not accepted:
            lane = open_lane(candidate.group_key, candidate.candidate_id)
            placement = lane.try_place(candidate, allow_visible_overflow=True)
            if placement is None:
                # Even alone, no label candidate fits: record the terminal
                # visible-overflow placement rather than dropping the name.
                member_overflow = {member.member_id: LanePlacement(
                    member.member_id, "visible-overflow", lane.overflow_rect_for_member(member), True)
                    for member in candidate.members_for_placement}
                placement = LanePlacement(candidate.candidate_id, "visible-overflow",
                                          lane.overflow_rect(candidate), visible_overflow=True,
                                          member_placements=MappingProxyType(member_overflow))
            lane.accept(candidate, placement)
            for member in candidate.members_for_placement:
                lane_by_candidate[member.member_id] = lane

    return LaneAllocationResult(tuple(
        LaneAssignment(lane.lane_id, lane.group_key, lane.representative_id, tuple(lane.members),
                       MappingProxyType(dict(lane.placements)), lane.label_rows_used, lane.block_extent())
        for lane in lanes
    ))


def _eligible_predecessor_lane(candidate: LaneCandidate, by_id: Mapping[str, LaneCandidate],
                               lane_by_candidate: Mapping[str, "_Lane"]) -> "_Lane | None":
    """Return the unique eligible immediate predecessor's lane, if any.

    Eligibility requires the predecessor to already be assigned to a lane and
    its mark to end at or before this candidate's mark start (a nonnegative
    gap, including exact touch). Several eligible predecessors are broken by
    stable relation ID then predecessor candidate ID, matching the design.
    """
    eligible: list[tuple[str, str, "_Lane"]] = []
    for relation_id, predecessor_id in candidate.predecessors:
        predecessor = by_id.get(predecessor_id)
        lane = lane_by_candidate.get(predecessor_id)
        if predecessor is None or lane is None:
            continue
        if predecessor.mark.right <= candidate.mark.left:
            eligible.append((relation_id, predecessor_id, lane))
    if not eligible:
        return None
    eligible.sort(key=lambda item: (item[0], item[1]))
    return eligible[0][2]


def _geometries_collide(left: ObstacleGeometry, right: ObstacleGeometry, clearance: float) -> bool:
    index = SurfaceObstacleIndex()
    index.add(SurfaceObstacle("other", _MARK_CLASS, "bundle", right))
    return bool(index.collisions(left, classes=(_MARK_CLASS,), clearance=clearance))
