"""Validated v0.5 Scene construction input boundary.

This module is intentionally renderer-neutral.  Primitive composition follows
in I27-R2; this seam ensures that it can only receive completed current inputs.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from chrona.presentation.layout.dependency_network import compose_dependency_network_surface
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.layout.model import LayoutError, LayoutManifest
from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment
from chrona.presentation.layout.lane_subtracks import FixedLanePreflight
from chrona.presentation.layout.surface_composer import SurfacePreRowGeometry, compose_surface_layout
from chrona.presentation.layout.surface_quality import AlignedStrokePlacement, CapacitySourceEvidence, SurfaceLayoutRequest
from chrona.presentation.layout.sources import MeasuredSources
from chrona.presentation.layout.pattern_placement import PatternedPlacement
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.semantic_registry import (
    axis_band_semantic_ids, axis_label_semantic_ids, ContrastClass, PrimitiveKind, contrast_binding, contrast_bindings,
    inside_member_label_semantic, semantic_binding)
from chrona.presentation.model.projection import shared_track_member_key
from chrona.presentation.model.info_diagnostics import PaintOmission
from chrona.presentation.model.diagnostic_sources import DiagnosticSubject, PrimitiveProvenance, review_row_subjects
from chrona.presentation.model.theme_tokens import BOX_FOLLOWS_TEXT, ThemeTokenView
from chrona.presentation.scene.pattern_geometry import pattern_geometry, pattern_kind, project_pattern_placement
from chrona.presentation.scene.model import DecorationDisposition, ImageFill, ImageTile, SceneColumn, SceneGroup, ScenePrimitive, SceneRow, SceneSlot, SceneSurface, SurfaceScaleManifest, SymbolGeometry, TextLayout
from chrona.presentation.scene.model import (
    SceneLaneMember, SceneLaneObstacle, SceneLaneRectObstacle, SceneLaneSegmentObstacle,
    requires_lane_member_provenance,
)
from chrona.presentation.scene.paint import (
    AS_OF_CONE_ROLE, PaintFamily, ScenePaintError, complete_icon_path_paints, resolve_artwork_admission,
    is_ink_only_surface_pattern, resolve_cone_paint, resolve_scene_paint, resolve_surface_pattern_admission,
)
from chrona.presentation.scene.surface_overlays import project_canvas_overlays
from chrona.presentation.scene.stroke_wobble import (
    MAX_OUTLINE_POINTS, WobbleLimitError, complete_path_wobble, complete_rect_wobble,
)
from chrona.presentation.scene.visual_capabilities import VisualProfile


class SceneBuildError(ValueError):
    """Stable diagnostic emitted before v0.5 primitive construction."""

    def __init__(self, diagnostic_id: str, path: str, detail: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.path = path
        self.detail = detail


@dataclass(frozen=True)
class SceneBuildInput:
    """Closed current-runtime inputs for one v0.5 Scene construction."""

    projection: Any
    surface_content: SurfaceContentInput
    layout_manifest: LayoutManifest
    theme_tokens: ThemeTokenView
    font_metrics: Any
    measured_sources: MeasuredSources
    capabilities: Mapping[str, bool]
    visual_profile: VisualProfile | None = None
    viewport: tuple[float, float] = (0.0, 0.0)
    icon_assets: dict[str, Any] | None = None
    visual_requests: tuple[Any, ...] = ()
    fixed_lane_preflight: FixedLanePreflight | None = None
    capacity_short_sources: tuple[CapacitySourceEvidence, ...] = ()
    surface_preparation: SurfacePreRowGeometry | None = None


_REQUIRED_SOURCES = {
    "table-timeline": frozenset(("table", "timeline", "timeline-axis")),
    "dependency-network": frozenset(("network",)),
}


def _heading_paint_role(tokens: ThemeTokenView, role: str = "heading") -> str:
    # A glow payload selects its declared role, including that role's own ink.
    # Fidelity alone is not a request; malformed tuples reach generic validation.
    if (tokens.optional_color(role, "glowColor") is not None
            or tokens.optional_number(role, "glowBlur") is not None
            or tokens.optional_number(role, "glowOpacity") is not None):
        return role
    return tokens.title_paint_role(role)


def _paint_family(primitive: ScenePrimitive, tokens: ThemeTokenView) -> PaintFamily:
    if primitive.pattern is not None and primitive.pattern.primitives:
        return PaintFamily.SOLID
    if primitive.kind == PrimitiveKind.TEXT:
        return PaintFamily.TEXT
    if primitive.kind == PrimitiveKind.PATH:
        return PaintFamily.PATH
    if primitive.purpose in {"group-decoration", "row-decoration", "group-header-band", "group-tab", "calendar-closed", "calendar-exception", "period-band"}:
        treatment, _ = tokens.background(primitive.visual_role)
        if treatment == "none":
            raise SceneBuildError("E_THEME_BACKGROUND_ABSENT", f"/body/roles/{primitive.visual_role}")
        return PaintFamily.OUTLINE if treatment == "outline" else PaintFamily.SOLID
    pattern = tokens.optional_pattern(primitive.visual_role)
    if pattern is not None and pattern_kind(pattern) == "outline":
        return PaintFamily.OUTLINE
    if pattern is not None and pattern_kind(pattern) == "diagonal-hatch":
        return PaintFamily.HATCH
    if primitive.kind == PrimitiveKind.SYMBOL and primitive.glyph_paint_mode == "stroke":
        # Preserve explicit outline overrides above, then require only the
        # channel the completed catalogue part actually paints.
        return PaintFamily.PATH
    if primitive.purpose == "region-frame" and tokens.optional_color(primitive.visual_role, "fill") is None:
        # A frame role that declares no fill is an outline panel (#889).
        return PaintFamily.OUTLINE
    return PaintFamily.SOLID


def _symbol_primitives(scene_id: str, source_ref: str, source_kind: str, purpose: str, visual_role: str,
                       bounds: tuple[float, float, float, float], completed_parts: tuple[Any, ...],
                       primitive_ids: tuple[str, ...] | None = None, **shared: Any) -> list[ScenePrimitive]:
    """Emit one milestone's Symbol primitive(s): one for a built-in shape, several sibling

    primitives (one per painted part, ascending paint order) for a Theme-bound glyph.
    Geometry and paint intents arrive completed by Layout. Scene assigns
    primitive identity and delegates each part's paint conversion.
    """
    base_paint_order = shared.pop("paint_order", 0)
    # Parts stack in ascending paint order, except where the whole glyph is one layer (a note's artwork, #848).
    order_step = shared.pop("part_order_step", 1)
    if primitive_ids is not None and len(primitive_ids) != len(completed_parts):
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", scene_id,
                              "typed lane handoff part count differs from Layout geometry")
    return [ScenePrimitive((primitive_ids[index] if primitive_ids is not None else
                            f"{scene_id}:part{index}" if part.paint_mode is not None else scene_id),
                           PrimitiveKind.SYMBOL, source_ref, source_kind, purpose, visual_role,
                           bounds, symbol=SymbolGeometry(part.commands), paint_order=base_paint_order + index * order_step,
                           glyph_paint_mode=part.paint_mode, glyph_paint_color=part.paint_color,
                           glyph_stroke_width=part.stroke_width,
                           glyph_line_cap=part.line_cap, glyph_line_join=part.line_join, **shared)
            for index, part in enumerate(completed_parts)]


def _attach_completed_patterns(primitives: tuple[ScenePrimitive, ...],
                               placements: tuple[PatternedPlacement, ...]) -> tuple[ScenePrimitive, ...]:
    """Project exact Layout-owned tile placements onto matching Rect IDs."""
    by_id = {item.placement_id: item for item in placements}
    if len(by_id) != len(placements):
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", "/patterns", "duplicate placement ID")
    projected = []
    for primitive in primitives:
        placed = by_id.pop(primitive.scene_id, None)
        if placed is not None and primitive.kind != PrimitiveKind.RECT:
            raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", primitive.scene_id,
                                  "catalogue pattern requires completed Rect")
        projected.append(replace(primitive, pattern=project_pattern_placement(placed.pattern))
                         if placed is not None else primitive)
    if by_id:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", next(iter(by_id)),
                              "Layout pattern has no emitted Rect")
    return tuple(projected)


def _complete_surface_paint(surface: SceneSurface, tokens: ThemeTokenView, visual_profile: VisualProfile | None = None,
                            viewport: tuple[float, float] = (0.0, 0.0),
                            *, scale_target_role: str | None = None,
                            scale_paints: Mapping[str, str] | None = None,
                            scale_legend_paints: Mapping[str, str] | None = None,
                            group_tints: Mapping[str, str] | None = None,
                            annotation_kind_paints: Mapping[str, str] | None = None,
                            axis_band_paints: Mapping[str, str] | None = None) -> SceneSurface:
    """Attach the sole adapter-ready paint payload to every completed primitive."""
    # Layer admission has already happened at the typed placement boundary.
    # Keep the existing canvas/artwork/part omission order and deduplication.
    artwork_omissions = tuple(item for item in surface.info_diagnostics
                             if isinstance(item, PaintOmission) and item.treatment in {"annotation-artwork", "frame-glyph"})
    base_info = tuple(item for item in surface.info_diagnostics
                      if not (isinstance(item, PaintOmission) and item.treatment in {"annotation-artwork", "frame-glyph"}))
    clip_hosts = frozenset(item.clip_source_id for item in surface.primitives if item.clip_source_id)
    try:
        resolved = tuple(_complete_primitive_paint(
            primitive, tokens, visual_profile, scale_target_role, scale_paints or {}, scale_legend_paints or {},
            group_tints or {}, surface.canvas_bounds or (0.0, 0.0, *viewport), annotation_kind_paints or {},
            clip_hosts, axis_band_paints or {})
                         for primitive in surface.primitives)
        canvas = resolve_scene_paint(tokens, "background", PaintFamily.CANVAS,
                                     visual_profile=visual_profile,
                                     gradient_bounds=(0.0, 0.0, *viewport))
    except ScenePaintError as error:
        raise SceneBuildError(error.diagnostic_id, error.path, error.detail) from error
    absent_decorations = tuple(
        DecorationDisposition(binding.scene_role, "absent")
        for binding in contrast_bindings(ContrastClass.DECORATION)
        if (background := tokens.optional_background(binding.scene_role)) is not None
        and background[0] == "none"
    )
    # An omitted as-of cone (#890) has no primitive left to carry paint, but its omission is still reported.
    completed = tuple(item for item in resolved if item[0] is not None)
    omissions = (*canvas.omissions, *artwork_omissions, *(omission for _, facts in resolved for omission in facts))
    unique_omissions: list[PaintOmission] = []
    seen: set[tuple[str, str, str, str]] = set()
    for omission in omissions:
        identity = (omission.role, omission.treatment, omission.visual_profile, omission.target_kind)
        if identity not in seen:
            seen.add(identity)
            unique_omissions.append(omission)
    return replace(surface, primitives=tuple(item for item, _ in completed), canvas_paint=canvas.paint,
                   decoration_dispositions=absent_decorations,
                   info_diagnostics=(*base_info, *unique_omissions))


def _visible_extent(primitive: ScenePrimitive) -> tuple[float, float, float, float]:
    """The box a primitive paints in: its bounds, or for a Path (whose bounds are zero) its points."""
    if primitive.stroke_clip is not None:
        return primitive.stroke_clip.region
    points = [point for command in primitive.path_commands for point in command.points] or list(primitive.points)
    if primitive.kind != "Path" or not points:
        return primitive.bounds
    xs, ys = [point[0] for point in points], [point[1] for point in points]
    return (min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))


def _complete_wobble(primitive: ScenePrimitive, paint: ScenePaint, clip_host: bool) -> ScenePaint:
    """Complete a declared hand-wobble into its outline, or drop it where it does not apply (#588).

    It applies to a stroked Rect and to a Path. A Symbol, Text or Icon, a Rect that carries a
    pattern or an image fill, a fill-only Rect and a clip host keep their exact geometry: a pattern
    region, an image tile and a clip are defined to equal the rectangle.
    """
    wobble = paint.wobble
    assert wobble is not None
    if paint.stroke is None or paint.image is not None or clip_host:
        return replace(paint, wobble=None)
    try:
        if primitive.kind == "Rect" and primitive.pattern is None:
            outline = complete_rect_wobble(primitive.scene_id, primitive.bounds, primitive.corner_radius,
                                           amplitude=wobble.amplitude, wavelength=wobble.wavelength,
                                           seed=wobble.seed)
            closed = True
        elif primitive.kind == "Path" and (len(primitive.points) >= 2 or primitive.path_commands):
            outline = complete_path_wobble(primitive.scene_id, primitive.path_commands, primitive.points,
                                           amplitude=wobble.amplitude, wavelength=wobble.wavelength,
                                           seed=wobble.seed)
            closed = False
        else:
            return replace(paint, wobble=None)
    except WobbleLimitError as error:
        raise SceneBuildError("E_VISUAL_CAPABILITY_LIMIT",
                              f"/body/roles/{primitive.visual_role}/wobbleWavelength",
                              f"the wobbled outline of {primitive.scene_id} has {error} points, over "
                              f"{MAX_OUTLINE_POINTS}") from error
    return replace(paint, wobble=replace(wobble, closed=closed, outline=outline))


def _require_followable_paint(primitive: ScenePrimitive) -> None:
    """A box that follows its text is painted by a flood: a solid or absent fill and nothing else (#1050).

    An outline, gradient, shadow, glow, pattern, image or wobble would sit on the measured box edge, which is not
    where a viewer ends the background, so the declaration is refused with its role rather than painted wrongly.
    """
    paint = primitive.paint
    assert paint is not None
    if (paint.stroke is not None or paint.gradient is not None or paint.shadow is not None or paint.glow is not None
            or paint.wobble is not None or paint.image is not None or primitive.pattern is not None):
        raise SceneBuildError("E_PRESENTATION_VIEWER_FIT_PAINT", f"/body/roles/{primitive.visual_role}",
                              "a box that follows its text takes a solid fill and no outline, gradient, shadow, "
                              "glow, pattern, image or wobble")


def _complete_primitive_paint(primitive: ScenePrimitive, tokens: ThemeTokenView, visual_profile: VisualProfile | None,
                              scale_target_role: str | None, scale_paints: Mapping[str, str],
                              scale_legend_paints: Mapping[str, str],
                              group_tints: Mapping[str, str] = {},
                              canvas: tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0),
                              annotation_kind_paints: Mapping[str, str] = {},
                              clip_hosts: frozenset[str] = frozenset(),
                              axis_band_paints: Mapping[str, str] = {},
                              ) -> tuple[ScenePrimitive | None, tuple[PaintOmission, ...]]:
    if primitive.visual_role == AS_OF_CONE_ROLE:
        # The cone's paint is its gradient; a profile that cannot paint one omits the whole cone (#890).
        cone = resolve_cone_paint(tokens, primitive.visual_role, visual_profile=visual_profile, bounds=primitive.bounds)
        return (replace(primitive, paint=cone.paint) if cone.paint is not None else None), cone.omissions
    if primitive.visual_role == "canvas-overlay-gradient":
        if primitive.paint is None or primitive.paint.radial_gradient is None:
            raise SceneBuildError("E_PRESENTATION_PAINT_INVALID", "/body/roles/canvas-overlay-gradient")
        return primitive, ()
    ink_only_pattern = bool(primitive.pattern and primitive.pattern.primitives
                            and is_ink_only_surface_pattern(tokens, primitive.visual_role))
    if ink_only_pattern:
        admission = resolve_surface_pattern_admission(tokens, primitive.visual_role, visual_profile=visual_profile)
        if not admission.admitted:
            return None, admission.omissions
    family = _paint_family(primitive, tokens)
    paint_role = primitive.visual_role
    resolution = resolve_scene_paint(tokens, paint_role, family,
                                     visual_profile=visual_profile, gradient_bounds=primitive.bounds,
                                     glow_extent=_visible_extent(primitive), canvas_bounds=canvas,
                                     part_mode=primitive.glyph_paint_mode,
                                     part_color=primitive.glyph_paint_color,
                                     catalog_pattern=bool(primitive.pattern and primitive.pattern.primitives),
                                     ink_only_pattern=ink_only_pattern,
                                     pattern_has_substrate=bool(primitive.pattern and any(
                                         item.kind == "circle" and item.fill_channel == "substrate"
                                         for item in primitive.pattern.primitives)),
                                     catalog_glyph_stroke_width=primitive.glyph_stroke_width,
                                     catalog_glyph_line_cap=primitive.glyph_line_cap,
                                     catalog_glyph_line_join=primitive.glyph_line_join)
    paint = resolution.paint
    if primitive.glyph_paint_mode is None:
        override = (scale_paints.get(primitive.source_ref)
                    if primitive.visual_role == scale_target_role else None)
        if primitive.source_kind == "legend":
            override = scale_legend_paints.get(primitive.source_ref, override)
        completed = replace(paint, fill=override) if override is not None else paint
    else:
        completed = paint
    tint = (group_tints.get(primitive.source_ref)
            if primitive.purpose in {"group-decoration", "group-header-band"} else None)
    if tint is not None:
        # A group's tint replaces only the band's visible channel (#583).
        completed = replace(completed, stroke=tint) if family == PaintFamily.OUTLINE else replace(completed, fill=tint)
    axis_fill = axis_band_paints.get(primitive.scene_id)
    if axis_fill is not None:
        completed = replace(completed, fill=axis_fill)
    # A bar-end stamp lies on the kind-coloured bar, so its declared role ink
    # must remain independently selectable. Column stamps keep their legacy tint.
    kind_painted = (primitive.purpose in {"annotation-kind-bar", "annotation-kind-accent"}
                    or (primitive.purpose == "annotation-kind-stamp"
                        and tokens.annotation_kind_frame().stamp_placement == "column"))
    kind_paint = annotation_kind_paints.get(primitive.source_ref) if kind_painted else None
    # `colorAlso` (#991): the same colour also paints the header text and the leader line of the note.
    also_paint = (annotation_kind_paints.get(f"{primitive.source_ref}#header")
                  if primitive.purpose in {"annotation-kind-label", "annotation-kind-secondary", "annotation-heading"}
                  else annotation_kind_paints.get(f"{primitive.source_ref}#leader")
                  if primitive.purpose == "annotation-leader" else None)
    if also_paint is not None:
        completed = (replace(completed, stroke=also_paint) if primitive.kind == PrimitiveKind.PATH
                     else replace(completed, fill=also_paint))
    if kind_paint is not None:
        # A kind's colour replaces only the visible channel of its bar, accent and stamp (#584): the
        # fill of a bar, accent or fill part, the stroke of a stroke part of the stamp glyph.
        completed = (replace(completed, stroke=kind_paint) if primitive.glyph_paint_mode == "stroke"
                     else replace(completed, fill=kind_paint))
    if primitive.image_fill_pending is not None:
        completed = replace(completed, image=primitive.image_fill_pending)
    if primitive.stroke_clip is not None:
        completed = replace(completed, stroke_width=primitive.stroke_clip.stroke_width)
    treatment = tokens.optional_pattern(primitive.visual_role)
    result = replace(primitive, paint=completed,
                     pattern=(primitive.pattern if primitive.pattern is not None and primitive.pattern.primitives
                              else pattern_geometry(treatment) if treatment is not None else None),
                     glyph_paint_mode=None, glyph_paint_color=None,
                     glyph_stroke_width=None, glyph_line_cap=None, glyph_line_join=None,
                     image_fill_pending=None)
    if result.viewer_fit == BOX_FOLLOWS_TEXT:
        _require_followable_paint(result)
    if completed.wobble is not None:
        result = replace(result, paint=_complete_wobble(result, completed, primitive.scene_id in clip_hosts))
    if result.kind == "Icon" and result.icon_kind == "vector":
        try:
            icon_paths = complete_icon_path_paints(completed, primitive.icon_path_geometry, primitive.visual_role)
        except ScenePaintError as error:
            raise SceneBuildError(error.diagnostic_id, error.path, error.detail) from error
        return (replace(result, icon_paths=icon_paths,
                        icon_path_geometry=()), resolution.omissions)
    return result, resolution.omissions


def build_scene_input(*, projection: Any, surface_content: SurfaceContentInput,
                      layout_manifest: LayoutManifest, resolved_theme: Mapping[str, Any],
                      font_metrics: Any, measured_sources: MeasuredSources,
                      capabilities: Mapping[str, bool],
                      visual_profile: VisualProfile | None = None,
                      viewport: tuple[float, float] = (0.0, 0.0),
                      icon_assets: dict[str, Any] | None = None,
                      visual_requests: tuple[Any, ...] = (),
                      fixed_lane_preflight: FixedLanePreflight | None = None,
                      capacity_short_sources: tuple[CapacitySourceEvidence, ...] = (),
                      surface_preparation: SurfacePreRowGeometry | None = None) -> SceneBuildInput:
    """Bind validated v0.5 inputs without reopening authoring or legacy contracts."""
    if not isinstance(layout_manifest, LayoutManifest):
        raise SceneBuildError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    if not isinstance(measured_sources, MeasuredSources):
        raise SceneBuildError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources")
    surface = getattr(projection, "surface", "table-timeline")
    if surface not in _REQUIRED_SOURCES:
        raise SceneBuildError("E_PRESENTATION_SURFACE_UNSUPPORTED", "/projection/surface")
    required_sources = {decision.source for decision in layout_manifest.decisions
                        if decision.source and decision.priority in {None, "required"}}
    missing = sorted(_REQUIRED_SOURCES[surface] - required_sources)
    if missing:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_MISSING", "/layoutManifest/sources/" + missing[0])
    if surface == "dependency-network":
        table_sources = {"table", "timeline", "timeline-axis"}
        if required_sources & table_sources:
            raise SceneBuildError("E_PRESENTATION_SURFACE_SLOT_SET", "/layoutManifest/sources")
    if not all(isinstance(name, str) and isinstance(enabled, bool) for name, enabled in capabilities.items()):
        raise SceneBuildError("E_PRESENTATION_CAPABILITY_SCHEMA", "/capabilities")
    if fixed_lane_preflight is not None and not isinstance(fixed_lane_preflight, FixedLanePreflight):
        raise SceneBuildError("E_LAYOUT_LANE_PREFLIGHT_INVALID", "/layoutManifest")
    return SceneBuildInput(projection, surface_content, layout_manifest,
                           ThemeTokenView(resolved_theme), font_metrics, measured_sources,
                           dict(capabilities), visual_profile, viewport, icon_assets, visual_requests,
                           fixed_lane_preflight, capacity_short_sources, surface_preparation)


def compose_review_surface(value: SceneBuildInput) -> SceneSurface:
    """Dispatch a typed surface intent to an adapter of completed Layout output."""
    surface = getattr(value.projection, "surface", "table-timeline")
    if surface == "table-timeline":
        return _complete_surface_paint(_compose_table_timeline_surface(value), value.theme_tokens, value.visual_profile, value.viewport,
                                       scale_target_role=value.surface_content.scale_target_role,
                                       scale_paints=dict(value.surface_content.scale_paints),
                                       scale_legend_paints=dict(value.surface_content.scale_legend_paints),
                                       group_tints=dict(value.surface_content.group_tints),
                                       annotation_kind_paints=dict(value.surface_content.annotation_kind_paints),
                                       axis_band_paints=dict(value.surface_content.axis_band_paints))
    if surface == "dependency-network":
        return _complete_surface_paint(_compose_dependency_network_surface(value), value.theme_tokens, value.visual_profile, value.viewport)
    raise SceneBuildError("E_PRESENTATION_SURFACE_UNSUPPORTED", "/projection/surface")


def _compose_table_timeline_surface(value: SceneBuildInput) -> SceneSurface:
    """Build the core, fully measured table/timeline surface from the frozen closure."""
    projection = value.projection
    if not hasattr(projection, "items") or not hasattr(projection, "window"):
        raise SceneBuildError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection")
    metric = value.measured_sources.metric_values
    if "text.body.size" not in metric or "text.body.lineHeight" not in metric:
        raise SceneBuildError("E_PRESENTATION_MEASUREMENTS_REQUIRED", "/measuredSources/metricValues")
    try:
        request = (value.surface_preparation.inline.request if value.surface_preparation is not None
                   else SurfaceLayoutRequest(
            projection=projection, presentation_contract=normalize_presentation_input(value.surface_content),
            surface_content=value.surface_content, layout_manifest=value.layout_manifest,
            measured_sources=value.measured_sources, theme_tokens=value.theme_tokens,
            font_metrics=value.font_metrics,
            capabilities=dict(value.capabilities), icon_assets=value.icon_assets or {},
            visual_requests=value.visual_requests,
            fixed_lane_preflight=value.fixed_lane_preflight,
            capacity_short_sources=value.capacity_short_sources,
        ))
        composition = compose_surface_layout(request, prepared=value.surface_preparation)
    except LayoutError as error:
        raise SceneBuildError(error.diagnostic_id, error.path, error.detail) from error
    placed_surface = composition.placement
    slots = tuple(SceneSlot(item.slot_id, item.source_ref, item.scale_id,
                            (float(item.bounds.inline), float(item.bounds.block),
                             float(item.bounds.inline_size), float(item.bounds.block_size)),
                            item.priority, item.overflow)
                  for item in placed_surface.slots)
    by_source = {slot.source: slot for slot in slots}
    table, timeline, axis = (by_source[name] for name in ("table", "timeline", "timeline-axis"))
    review_rows = composition.review_rows
    rows = tuple(
        SceneRow(placement.object_id, placement.group_id,
                 (float(placement.bounds.inline), float(placement.bounds.block),
                  float(placement.bounds.inline_size), float(placement.bounds.block_size)), placement.row_id,
                 None if placement.lane_mark_band_block is None
                 else float(placement.lane_mark_band_block))
        for placement in placed_surface.rows
    )
    columns = tuple(
        SceneColumn(placement.column_id, placement.label,
                    (float(placement.bounds.inline), float(placement.bounds.block),
                     float(placement.bounds.inline_size), float(placement.bounds.block_size)))
        for placement in placed_surface.columns
    )
    groups = tuple(
        SceneGroup(item.group_id,
                   None if item.header_bounds is None else (float(item.header_bounds.inline), float(item.header_bounds.block),
                                                             float(item.header_bounds.inline_size), float(item.header_bounds.block_size)),
                   (float(item.content_bounds.inline), float(item.content_bounds.block),
                    float(item.content_bounds.inline_size), float(item.content_bounds.block_size)))
        for item in placed_surface.groups
    )
    if placed_surface.scale is None:
        raise SceneBuildError("E_PRESENTATION_LAYOUT_REQUIRED", "/layoutManifest")
    scale = SurfaceScaleManifest(placed_surface.scale.surface_id, placed_surface.scale.scale_id,
                                 placed_surface.scale.domain_start, placed_surface.scale.domain_end,
                                 placed_surface.scale.range_start, placed_surface.scale.range_end,
                                 placed_surface.scale.origin, placed_surface.scale.unit_ratio)
    primitives: list[ScenePrimitive] = []
    primitive_provenance: list[PrimitiveProvenance] = []
    row_subjects = review_row_subjects(review_rows)
    table_subjects = {
        review_row.row_id: next((item for item in review_row.items
                                if (item.item_id or item.object_id) == review_row.table_subject_id), None)
        for review_row in review_rows
    }

    def record_project_primitives(primitive_ids: tuple[str, ...] | list[str], item: Any) -> None:
        subject = DiagnosticSubject.project_object(item.object_id, item.title)
        primitive_provenance.extend(PrimitiveProvenance(primitive_id, (subject,))
                                    for primitive_id in primitive_ids)

    explicit_annotation_subjects = {
        annotation.annotation_id: DiagnosticSubject.project_object(
            annotation.subject_id, annotation.subject or None)
        for annotation in value.surface_content.annotations if annotation.subject_id
    }

    def record_annotation_primitives(primitive_ids: tuple[str, ...] | list[str],
                                    annotation_id: str) -> None:
        subject = explicit_annotation_subjects.get(annotation_id)
        if subject is not None:
            primitive_provenance.extend(PrimitiveProvenance(primitive_id, (subject,))
                                        for primitive_id in primitive_ids)

    artwork_omissions: list[PaintOmission] = []
    layout_text = {item.placement_id: item for item in placed_surface.text}
    lane_emissions_by_placement = {
        (item.placement_type, item.placement_id): item for item in placed_surface.lane_emissions
    }

    def lane_scene_ids(placement_type: str, placement_id: str) -> tuple[str, ...] | None:
        emission = lane_emissions_by_placement.get((placement_type, placement_id))
        if emission is None:
            return None
        # A primitive may own multiple visible obstacle facets (for example, a
        # stroked path). Identity is emitted once; preserve the explicit Layout
        # paint-part order for glyphs so _symbol_primitives can enforce the
        # exact number of completed parts.
        ordered_ids = (facet.primitive_id for facet in sorted(
            emission.facets,
            key=lambda facet: (-1 if facet.part_index is None else facet.part_index)))
        return tuple(dict.fromkeys(ordered_ids))
    primary_links = {
        item.object_id: item.link for item in projection.items
        if item.link is not None
    }
    table_cells = {
        (row_id, column_id): (object_id, is_primary)
        for row_id, column_id, object_id, is_primary in value.surface_content.table_cell_objects
    }

    def link_for_item(item: Any, source_kind: str) -> tuple[str | None, str | None]:
        """Return row-mode metadata for a selected current item only."""
        if value.surface_content.link_mode != "row" or source_kind not in {"primary", "combined"}:
            return None, None
        link = primary_links.get(item.object_id)
        return ((link or {}).get("href"), (link or {}).get("title"))

    def link_for_cell(row_id: str, column_id: str) -> tuple[str | None, str | None]:
        """Return table metadata without inspecting placement or source geometry."""
        object_id, is_primary = table_cells.get((row_id, column_id), (None, False))
        if not is_primary:
            return None, None
        if value.surface_content.link_mode == "title" and column_id not in value.surface_content.title_link_columns:
            return None, None
        if value.surface_content.link_mode not in {"title", "row"}:
            return None, None
        link = primary_links.get(object_id)
        return ((link or {}).get("href"), (link or {}).get("title"))

    def emit_layout_text(scene_id: str, purpose: str, role: str,
                         href: str | None = None, link_title: str | None = None,
                         table_row_id: str | None = None, table_column_id: str | None = None,
                         project_item: Any | None = None) -> None:
        placed = layout_text[scene_id]
        if placed.overflow == "suppressed":
            return
        layout = TextLayout((float(placed.bounds.inline), float(placed.bounds.block),
                             float(placed.bounds.inline_size), float(placed.bounds.block_size)),
                            placed.baseline or (float(placed.bounds.inline), float(placed.bounds.block)),
                            placed.lines, placed.font_family, placed.font_weight, placed.font_size,
                            placed.line_height, placed.font_asset_identity, placed.letter_spacing,
                            placed.text_transform, placed.numeric_spacing, placed.orientation, placed.rotation_degrees,
                            placed.horizontal_scale, placed.fit)
        classification = contrast_binding(role)
        treatment = (value.theme_tokens.contrast_treatment(role)
                     if classification is not None and classification.contrast_class == ContrastClass.STATE_TEXT else None)
        primitives.append(ScenePrimitive(scene_id, PrimitiveKind.TEXT, placed.source_ref, "review", purpose, role, layout.bounds,
                                         text=placed.content, baseline=layout.baseline, text_layout=layout,
                                         href=href, link_title=link_title, table_row_id=table_row_id,
                                         table_column_id=table_column_id, paint_order=placed.paint_order,
                                         host_placement_id=placed.host_placement_id,
                                         contrast_treatment=treatment))
        if project_item is not None:
            record_project_primitives((scene_id,), project_item)
    def emit_semantic_text(scene_id: str, semantic_id: str, role: str | None = None,
                           href: str | None = None, link_title: str | None = None,
                           table_row_id: str | None = None, table_column_id: str | None = None,
                           project_item: Any | None = None) -> None:
        binding = semantic_binding(semantic_id)
        emit_layout_text(scene_id, binding.purpose, role or binding.scene_role, href, link_title,
                         table_row_id, table_column_id, project_item)

    # The canvas texture is ground: it is the first primitive, below every paint order.
    for placed in placed_surface.shapes:
        if placed.semantic_id == "canvasTexture":
            texture = semantic_binding("canvasTexture")
            primitives.append(ScenePrimitive(
                placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "decoration", texture.purpose,
                texture.scene_role, (float(placed.bounds.inline), float(placed.bounds.block),
                                     float(placed.bounds.inline_size), float(placed.bounds.block_size)),
                slot_id=placed.slot_id, paint_order=placed.paint_order))
    # Region frames (#889) are ground too: emitted right after the texture, a parent before its children.
    for placed in placed_surface.shapes:
        if placed.semantic_id == "regionFrame":
            frame = semantic_binding("regionFrame")
            primitives.append(ScenePrimitive(
                placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "decoration", frame.purpose,
                placed.visual_role or frame.scene_role, (float(placed.bounds.inline), float(placed.bounds.block),
                                   float(placed.bounds.inline_size), float(placed.bounds.block_size)),
                slot_id=placed.slot_id, paint_order=placed.paint_order,
                corner_radius=placed.corner_radius or None))
        elif placed.semantic_id == "frameGlyph":
            frame = semantic_binding("frameGlyph")
            role = placed.visual_role or frame.scene_role
            try:
                admission = resolve_artwork_admission(
                    value.theme_tokens, needs_finish=any(part.paint_mode == "stroke" for part in placed.symbol_parts),
                    visual_profile=value.visual_profile, role=role, treatment="frame-glyph")
            except ScenePaintError as error:
                raise SceneBuildError(error.diagnostic_id, error.path, error.detail) from error
            artwork_omissions.extend(admission.omissions)
            if admission.admitted:
                bounds = (float(placed.bounds.inline), float(placed.bounds.block),
                          float(placed.bounds.inline_size), float(placed.bounds.block_size))
                primitives.extend(_symbol_primitives(
                    placed.placement_id, placed.source_ref, "decoration", frame.purpose,
                    role, bounds, placed.symbol_parts, slot_id=placed.slot_id,
                    paint_order=placed.paint_order, part_order_step=0))
    if "kicker" in layout_text:
        emit_semantic_text("kicker", "kickerText", _heading_paint_role(value.theme_tokens, "kicker"))
    if "title" in layout_text:
        emit_semantic_text("title", "titleText", _heading_paint_role(value.theme_tokens))
    if "subtitle" in layout_text:
        emit_semantic_text("subtitle", "subtitleText", _heading_paint_role(value.theme_tokens, "subtitle"))
    for column in value.surface_content.table_columns:
        # A Theme that declares `tableColumnLabel` with a fill paints its headers with it (#991).
        header_paint = ("tableColumnLabel" if value.theme_tokens.optional_color("tableColumnLabel", "fill") is not None else None)
        emit_semantic_text(f"column:{column.column_id}", "tableColumnLabel", header_paint, table_column_id=column.column_id)
    row_ids = {row.object_id: row.row_id for row in rows} | {row.row_id: row.row_id for row in rows}
    for cell in value.surface_content.table_cells:
        if f"cell:{cell.object_id}:{cell.column_id}" in layout_text:
            href, link_title = link_for_cell(cell.object_id, cell.column_id)
            row_id = row_ids.get(cell.object_id)
            if row_id is None:
                raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", f"cell:{cell.object_id}:{cell.column_id}")
            # A plain cell in a View-named text role (`textRole`, #1062) is painted with that role's fill when the
            # Theme binds one; a state-coloured cell keeps its own ink and takes only the role's typography.
            cell_paint = (cell.typography_role if cell.semantic_id == "tableCell" and cell.typography_role not in {"text", "numeric"}
                          and value.theme_tokens.optional_color(cell.typography_role, "fill") is not None else None)
            emit_semantic_text(f"cell:{cell.object_id}:{cell.column_id}", cell.semantic_id, cell_paint, href=href, link_title=link_title,
                               table_row_id=row_id, table_column_id=cell.column_id,
                               project_item=table_subjects.get(cell.object_id))
    # A Theme that binds `group-header.fill` inks the unmarked header text with it (#1244); a marked span keeps its
    # own role ink, and without the binding the header takes the body text ink as before.
    header_paint = "group-header" if value.theme_tokens.optional_color("group-header", "fill") is not None else "text"
    for group in groups:
        if group.header_bounds is not None and f"group-header:{group.group_id}" in layout_text:
            emit_semantic_text(f"group-header:{group.group_id}", "groupHeader", header_paint)
        run_index = 0
        while f"group-header:{group.group_id}#run{run_index}" in layout_text:  # the runs of a marked header (#1192)
            run_id = f"group-header:{group.group_id}#run{run_index}"
            run_role = layout_text[run_id].typography_role
            emit_semantic_text(run_id, "groupHeader", header_paint if run_role == "groupHeader" else run_role)
            run_index += 1
        segment = 0
        while f"group-tag:{group.group_id}:{segment}" in layout_text:  # the segments of a vertical label (#585)
            emit_semantic_text(f"group-tag:{group.group_id}:{segment}", "groupHeader", header_paint)
            segment += 1
    # A slot's caption (#1064): painted by the Theme's `slot-heading` role when it declares a fill, else as body text.
    heading_paint = "slot-heading" if value.theme_tokens.optional_color("slot-heading", "fill") is not None else "text"
    for heading_id in [scene_id for scene_id in layout_text if scene_id.startswith("slot-heading:")]:
        emit_semantic_text(heading_id, "slotHeading", heading_paint)
    for period in projection.periods:
        if f"period-label:{period.period_id}" in layout_text:
            emit_semantic_text(f"period-label:{period.period_id}", "periodLabel")
    for placed in placed_surface.shapes:
        if placed.semantic_id in {"groupBand", "rowBand", "groupHeaderBand", "groupTab", "calendarClosed", "calendarException", "periodBand"}:
            binding = semantic_binding(placed.semantic_id)
            bounds = (float(placed.bounds.inline), float(placed.bounds.block), float(placed.bounds.inline_size), float(placed.bounds.block_size))
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "decoration",
                                             binding.purpose, binding.scene_role, bounds, slot_id=placed.slot_id,
                                             paint_order=placed.paint_order))
            if placed.semantic_id == "rowBand" and row_subjects.get(placed.source_ref):
                primitive_provenance.append(PrimitiveProvenance(
                    placed.placement_id, row_subjects[placed.source_ref]))
    mark_placements = {placement.placement_id: placement for placement in placed_surface.marks}
    for review_row, row in zip(review_rows, rows, strict=True):
      members = sorted(enumerate(review_row.items),
                       key=lambda pair: shared_track_member_key(pair[1], pair[0]))
      for _, item in members:
        layout_instance_id = f"{review_row.row_id}:{item.item_id or item.object_id}"
        instance_id = (layout_instance_id if projection.rows else item.object_id)
        source_kind = item.source_kind if projection.rows else "combined"
        href, link_title = link_for_item(item, source_kind)
        planned = item.planned
        planned_binding = semantic_binding("snapshot" if source_kind in {"snapshot", "scenario"} else "planned")
        planned_role = planned_binding.scene_role
        planned_mark = mark_placements.get(f"planned:{instance_id}")
        if planned_mark is not None:
            planned_ids = lane_scene_ids("mark", planned_mark.placement_id)
            planned_id = planned_ids[0] if planned_ids else planned_mark.placement_id
            bounds = (float(planned_mark.bounds.inline), float(planned_mark.bounds.block),
                      float(planned_mark.bounds.inline_size), float(planned_mark.bounds.block_size))
            if item.source_type == "point":
                # A Theme that declares the `gate` role paints primary gates with it (#991); a baseline or
                # scenario gate keeps its own role.
                gate_role = ("gate" if planned_role == "planned" and value.theme_tokens.has_role("gate") else planned_role)
                primitives.extend(_symbol_primitives(planned_id, item.object_id, "object", planned_binding.purpose, gate_role,
                                                    bounds, planned_mark.symbol_parts,
                                                    primitive_ids=planned_ids,
                                                    corner_radius=planned_mark.corner_radius,
                                                    path_commands=planned_mark.path_commands,
                                                    href=href, link_title=link_title, slot_id=planned_mark.slot_id,
                                                    paint_order=planned_mark.paint_order, end_treatment=planned_mark.end_treatment))
                record_project_primitives(planned_ids or (planned_id,), item)
            else:
                primitives.append(ScenePrimitive(planned_id, PrimitiveKind.RECT, item.object_id, "object", planned_binding.purpose, planned_role,
                                                 bounds,
                                                 corner_radius=planned_mark.corner_radius,
                                                 href=href, link_title=link_title, slot_id=planned_mark.slot_id,
                                                 paint_order=planned_mark.paint_order, end_treatment=planned_mark.end_treatment))
                record_project_primitives((planned_id,), item)
        actual = item.actual or {}
        actual_binding = semantic_binding("actual")
        actual_mark = mark_placements.get(f"actual:{instance_id}")
        if actual_mark is not None:
            actual_ids = lane_scene_ids("mark", actual_mark.placement_id)
            actual_id = actual_ids[0] if actual_ids else actual_mark.placement_id
            bounds = (float(actual_mark.bounds.inline), float(actual_mark.bounds.block),
                      float(actual_mark.bounds.inline_size), float(actual_mark.bounds.block_size))
            if item.source_type == "span":
                if actual_mark.mark_shape == "open-span":
                    primitives.extend(_symbol_primitives(actual_id, item.object_id, "object", actual_binding.purpose, actual_binding.scene_role,
                                                        bounds, actual_mark.symbol_parts,
                                                        primitive_ids=actual_ids,
                                                        corner_radius=actual_mark.corner_radius, slot_id=actual_mark.slot_id,
                                                        paint_order=actual_mark.paint_order, end_treatment=actual_mark.end_treatment))
                    record_project_primitives(actual_ids or (actual_id,), item)
                else:
                    primitives.append(ScenePrimitive(actual_id, PrimitiveKind.RECT, item.object_id, "object", actual_binding.purpose, actual_binding.scene_role,
                                                     bounds, corner_radius=actual_mark.corner_radius, slot_id=actual_mark.slot_id,
                                                     paint_order=actual_mark.paint_order, end_treatment=actual_mark.end_treatment))
                    record_project_primitives((actual_id,), item)
            else:
                primitives.extend(_symbol_primitives(actual_id, item.object_id, "object", actual_binding.purpose, actual_binding.scene_role,
                                                    bounds, actual_mark.symbol_parts, corner_radius=actual_mark.corner_radius,
                                                    primitive_ids=actual_ids,
                                                    path_commands=actual_mark.path_commands, slot_id=actual_mark.slot_id,
                                                    paint_order=actual_mark.paint_order, end_treatment=actual_mark.end_treatment))
                record_project_primitives(actual_ids or (actual_id,), item)
        missing_mark = mark_placements.get(f"missing-actual:{instance_id}")
        if missing_mark is not None and (projection.lane_membership is not None or
                                         "missingActual" in (getattr(projection, "comparison_facets", ()) or ("missingActual",))):
            missing_ids = lane_scene_ids("mark", missing_mark.placement_id)
            missing_id = missing_ids[0] if missing_ids else missing_mark.placement_id
            bounds = (float(missing_mark.bounds.inline), float(missing_mark.bounds.block),
                      float(missing_mark.bounds.inline_size), float(missing_mark.bounds.block_size))
            missing_binding = semantic_binding("missingActual")
            primitives.append(ScenePrimitive(missing_id, PrimitiveKind.RECT, item.object_id, "object", missing_binding.purpose, missing_binding.scene_role,
                                             bounds, corner_radius=missing_mark.corner_radius, slot_id=missing_mark.slot_id,
                                             paint_order=missing_mark.paint_order, end_treatment=missing_mark.end_treatment))
            record_project_primitives((missing_id,), item)
        label_id = f"member-label:{instance_id}"
        if label_id in layout_text and layout_text[label_id].overflow != "suppressed":
            semantic_id = inside_member_label_semantic(source_kind) if layout_text[label_id].selected_rung == "inside" else "memberLabel"
            # An outside label in a View-named role (`visibility.labels.textRole`, #1141) is painted with that role's
            # fill when the Theme binds one; the inside rungs keep their own roles.
            label_role = value.surface_content.label_text_role
            label_paint = (label_role if label_role is not None and semantic_id == "memberLabel"
                           and value.theme_tokens.optional_color(label_role, "fill") is not None else None)
            emit_semantic_text(label_id, semantic_id, label_paint, href=href, link_title=link_title,
                               project_item=item)
        variance_id = f"variance:{instance_id}"
        if source_kind == "combined" and item.finish_delta is not None and variance_id in layout_text:
            role = (semantic_binding("varianceBehind").scene_role if item.finish_delta > 0
                    else semantic_binding("varianceAhead").scene_role if item.finish_delta < 0
                    else semantic_binding("finishDelta").scene_role)
            emit_semantic_text(variance_id, "finishDelta", role, href, link_title,
                               project_item=item)
    for folded in getattr(projection, "folded_points", ()):
        for item in folded.all_items:
            instance_id = f"group-header:{folded.group_id}:{item.item_id or item.object_id}"
            source_kind = item.source_kind
            href, link_title = link_for_item(item, source_kind)
            planned_mark = mark_placements.get(f"planned:{instance_id}")
            if planned_mark is not None:
                binding = semantic_binding("snapshot" if source_kind in {"snapshot", "scenario"} else "planned")
                bounds = (float(planned_mark.bounds.inline), float(planned_mark.bounds.block),
                          float(planned_mark.bounds.inline_size), float(planned_mark.bounds.block_size))
                primitives.extend(_symbol_primitives(f"planned:{instance_id}", item.object_id, "object",
                                                    binding.purpose,
                                                    "gate" if (binding.scene_role == "planned" and item.source_type == "point"
                                                               and value.theme_tokens.has_role("gate")) else binding.scene_role,
                                                    bounds, planned_mark.symbol_parts,
                                                    corner_radius=planned_mark.corner_radius,
                                                    path_commands=planned_mark.path_commands, href=href, link_title=link_title,
                                                    slot_id=planned_mark.slot_id, paint_order=planned_mark.paint_order,
                                                    end_treatment=planned_mark.end_treatment))
                folded_id = f"planned:{instance_id}"
                record_project_primitives(tuple(
                    f"{folded_id}:part{index}" if part.paint_mode is not None else folded_id
                    for index, part in enumerate(planned_mark.symbol_parts)), item)
            actual_mark = mark_placements.get(f"actual:{instance_id}")
            if actual_mark is not None:
                binding = semantic_binding("actual")
                bounds = (float(actual_mark.bounds.inline), float(actual_mark.bounds.block),
                          float(actual_mark.bounds.inline_size), float(actual_mark.bounds.block_size))
                primitives.extend(_symbol_primitives(f"actual:{instance_id}", item.object_id, "object",
                                                    binding.purpose, binding.scene_role, bounds, actual_mark.symbol_parts,
                                                    corner_radius=actual_mark.corner_radius,
                                                    path_commands=actual_mark.path_commands, slot_id=actual_mark.slot_id,
                                                    paint_order=actual_mark.paint_order, end_treatment=actual_mark.end_treatment))
                folded_id = f"actual:{instance_id}"
                record_project_primitives(tuple(
                    f"{folded_id}:part{index}" if part.paint_mode is not None else folded_id
                    for index, part in enumerate(actual_mark.symbol_parts)), item)
        label_id = f"member-label:group-header:{folded.group_id}:{folded.item.object_id}"
        if label_id in layout_text:
            semantic_id = (inside_member_label_semantic(folded.item.source_kind)
                           if layout_text[label_id].selected_rung == "inside" else "memberLabel")
            emit_semantic_text(label_id, semantic_id, project_item=folded.item)
    for placed in placed_surface.text:
        if placed.semantic_id == "axisBand" or placed.semantic_id in axis_label_semantic_ids():
            # No role override: each id's own registered scene role resolves
            # its paint, so a second/third labels tier (#426) can take a
            # colour distinct from the shared "text" role axisLabel keeps.
            emit_semantic_text(placed.placement_id, placed.semantic_id)
    for placed in placed_surface.shapes:
        if placed.semantic_id in axis_band_semantic_ids():
            band = semantic_binding(placed.semantic_id)
            cell = (float(placed.bounds.inline), float(placed.bounds.block),
                    float(placed.bounds.inline_size), float(placed.bounds.block_size))
            if placed.kind == "Chamfer":
                # A chamfered cell (#491) is Layout's closed polygon, carried as a Symbol outline.
                primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.SYMBOL, "timeline-axis", "axis",
                                                 band.purpose, band.scene_role, cell,
                                                 symbol=SymbolGeometry(placed.path_commands),
                                                 paint_order=placed.paint_order))
            else:
                primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, "timeline-axis", "axis", band.purpose,
                                                 band.scene_role, cell, paint_order=placed.paint_order,
                                                 corner_radius=placed.corner_radius or None))
        if placed.semantic_id in {"axisGrid", "axisGridMinor", "axisRule", "axisCellSeparator"}:
            bounds = (float(placed.bounds.inline), float(placed.bounds.block), float(placed.bounds.inline_size), float(placed.bounds.block_size))
            axis_grid = semantic_binding(placed.semantic_id)
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.PATH, "timeline-axis", "axis", axis_grid.purpose, axis_grid.scene_role,
                                             bounds, points=placed.points, paint_order=placed.paint_order))
    for placed in placed_surface.shapes:
        if placed.placement_id == "as-of":
            as_of_binding = semantic_binding("asOf")
            primitives.append(ScenePrimitive("as-of", PrimitiveKind.PATH, "actual-set", "actual", as_of_binding.purpose, as_of_binding.scene_role,
                                             (float(placed.bounds.inline), float(placed.bounds.block), float(placed.bounds.inline_size), float(placed.bounds.block_size)),
                                             points=placed.points, paint_order=placed.paint_order))
            # A Theme that binds `as-of-label.fill` paints the label with it, on its chip (#1110); else it keeps `text`.
            emit_semantic_text("as-of-label", "asOfLabel",
                               "as-of-label" if value.theme_tokens.optional_color("as-of-label", "fill") is not None else None)
        elif placed.semantic_id == "asOfCone":
            # The marker's light (#890): a closed polygon Symbol; its gradient is completed with its paint.
            cone_binding = semantic_binding("asOfCone")
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.SYMBOL, placed.source_ref, "actual",
                                             cone_binding.purpose, cone_binding.scene_role,
                                             (float(placed.bounds.inline), float(placed.bounds.block),
                                              float(placed.bounds.inline_size), float(placed.bounds.block_size)),
                                             symbol=SymbolGeometry(placed.path_commands), paint_order=placed.paint_order))
    legend_binding = semantic_binding("legendEntry")
    for mark in placed_surface.marks:
        if not mark.placement_id.startswith("legend-swatch:"):
            continue
        bounds = (float(mark.bounds.inline), float(mark.bounds.block),
                  float(mark.bounds.inline_size), float(mark.bounds.block_size))
        if mark.mark_shape == "point":
            # A legend key is a miniature of the chart's own gate, including a
            # Theme-bound multi-part glyph (#427, #464).
            primitives.extend(_symbol_primitives(mark.placement_id, mark.source_ref, "legend", legend_binding.purpose,
                                                 "gate" if (mark.source_ref == "milestone" and value.theme_tokens.has_role("gate"))
                                                 else mark.source_ref, bounds, mark.symbol_parts,
                                                 corner_radius=mark.corner_radius, slot_id=mark.slot_id,
                                                 paint_order=mark.paint_order))
        else:
            primitives.append(ScenePrimitive(mark.placement_id, PrimitiveKind.RECT, mark.source_ref, "legend",
                                             legend_binding.purpose, mark.source_ref, bounds,
                                             corner_radius=mark.corner_radius, slot_id=mark.slot_id, paint_order=mark.paint_order))
    for relation in placed_surface.relations:
        if relation.suppressed or relation.relation_id.startswith("annotation-leader:"):
            continue
        if relation.relation_id.startswith("legend-swatch:"):
            source = relation.relation_id.removeprefix("legend-swatch:")
        else:
            source = relation.relation_id.removeprefix("relation:").split(":", 1)[0]
        dependency = semantic_binding(relation.semantic_id)
        primitives.append(ScenePrimitive(relation.relation_id, PrimitiveKind.PATH, source, "relation", dependency.purpose, dependency.scene_role,
                                         (0, 0, 0, 0), marker_start=relation.marker_start, marker_end=relation.marker_end,
                                         points=relation.points, path_commands=relation.path_commands,
                                         paint_order=relation.paint_order, slot_id=relation.slot_id,
                                         from_instance_id=relation.from_instance_id,
                                         to_instance_id=relation.to_instance_id,
                                         fan_in=relation.fan_in))
    for placed in placed_surface.shapes:
        bounds = (float(placed.bounds.inline), float(placed.bounds.block),
                  float(placed.bounds.inline_size), float(placed.bounds.block_size))
        if placed.placement_id.startswith("legend-swatch:"):
            role = (semantic_binding("scaleLegendEntry").scene_role
                    if placed.source_ref.startswith("scale:") else placed.source_ref)
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "legend",
                                             legend_binding.purpose, role, bounds, paint_order=placed.paint_order,
                                             slot_id=placed.slot_id, corner_radius=placed.corner_radius or None))
        elif placed.placement_id.startswith("progress-fill:"):
            progress = semantic_binding("progressFill")
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "object",
                                             progress.purpose, progress.scene_role, bounds, slot_id=placed.slot_id,
                                             paint_order=placed.paint_order, clip_source_id=placed.clip_host_id,
                                             corner_radius=placed.corner_radius or None))
            if placed.subjects:
                primitive_provenance.append(PrimitiveProvenance(placed.placement_id, placed.subjects))
        elif placed.semantic_id == "deadlineMark":
            deadline = semantic_binding("deadlineMark")
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.PATH, placed.source_ref, "object",
                                             deadline.purpose, deadline.scene_role, bounds, slot_id=placed.slot_id,
                                             points=placed.points, paint_order=placed.paint_order))
            if placed.subjects:
                primitive_provenance.append(PrimitiveProvenance(placed.placement_id, placed.subjects))
        elif placed.placement_id.startswith("chip:"):
            chip_binding = semantic_binding(placed.semantic_id)
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "review",
                                             chip_binding.purpose, chip_binding.scene_role, bounds, slot_id=placed.slot_id,
                                             paint_order=placed.paint_order,
                                             corner_radius=placed.corner_radius or None, viewer_fit=placed.viewer_fit))
            if placed.subjects:
                primitive_provenance.append(PrimitiveProvenance(placed.placement_id, placed.subjects))
        elif placed.placement_id.startswith("summary-bar:"):
            summary_bar = semantic_binding("summaryBar")
            primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "summary",
                                             summary_bar.purpose, summary_bar.scene_role, bounds,
                                             paint_order=placed.paint_order))
        elif placed.semantic_id == "annotationArtwork":
            artwork = semantic_binding("annotationArtwork")
            role = placed.visual_role or artwork.scene_role
            try:
                admission = resolve_artwork_admission(
                    value.theme_tokens, needs_finish=any(part.paint_mode == "stroke" for part in placed.symbol_parts),
                    visual_profile=value.visual_profile, role=role)
            except ScenePaintError as error:
                raise SceneBuildError(error.diagnostic_id, error.path, error.detail) from error
            artwork_omissions.extend(admission.omissions)
            if not admission.admitted:
                continue
            emitted = _symbol_primitives(placed.placement_id, placed.source_ref, "annotation", artwork.purpose,
                                         role, bounds, placed.symbol_parts,
                                         paint_order=placed.paint_order, part_order_step=0)
            primitives.extend(emitted)
            record_annotation_primitives(tuple(item.scene_id for item in emitted), placed.source_ref)
        elif placed.semantic_id == "rowRule":
            row_rule = semantic_binding("rowRule")
            primitives.append(ScenePrimitive(
                placed.placement_id, PrimitiveKind.PATH, placed.source_ref, "decoration",
                row_rule.purpose, row_rule.scene_role, bounds, points=placed.points,
                slot_id=placed.slot_id, paint_order=placed.paint_order))
        elif placed.semantic_id == "annotationKindStamp":
            stamp = semantic_binding("annotationKindStamp")
            emitted = _symbol_primitives(placed.placement_id, placed.source_ref, "annotation", stamp.purpose,
                                         stamp.scene_role, bounds, placed.symbol_parts,
                                         paint_order=placed.paint_order)
            primitives.extend(emitted)
            record_annotation_primitives(tuple(item.scene_id for item in emitted), placed.source_ref)
        elif placed.annotation is not None:
            annotation_box = semantic_binding(placed.semantic_id)
            image_fill_pending = (ImageFill(placed.image_fill.asset_identity, placed.image_fill.viewport,
                                            placed.image_fill.payload,
                                            tuple(ImageTile(source, destination)
                                                  for source, destination in placed.image_fill.tiles))
                                  if placed.image_fill is not None else None)
            if placed.kind in {"Balloon", "Tilt", "Polygon"}:
                primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.SYMBOL, placed.source_ref, "annotation",
                                                 annotation_box.purpose, annotation_box.scene_role, bounds,
                                                 symbol=SymbolGeometry(placed.path_commands), paint_order=placed.paint_order,
                                                 image_fill_pending=image_fill_pending, viewer_fit=placed.viewer_fit))
                record_annotation_primitives((placed.placement_id,), placed.source_ref)
            else:
                primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.RECT, placed.source_ref, "annotation",
                                                 annotation_box.purpose, annotation_box.scene_role,
                                                 bounds, paint_order=placed.paint_order,
                                                 image_fill_pending=image_fill_pending, viewer_fit=placed.viewer_fit,
                                                 corner_radius=placed.corner_radius or None))
                record_annotation_primitives((placed.placement_id,), placed.source_ref)
    for placed in placed_surface.icons:
        bounds = (float(placed.bounds.inline), float(placed.bounds.block),
                  float(placed.bounds.inline_size), float(placed.bounds.block_size))
        icon_binding = semantic_binding(placed.semantic_id)
        primitives.append(ScenePrimitive(placed.placement_id, PrimitiveKind.ICON, placed.source_ref, "object", icon_binding.purpose, icon_binding.scene_role, bounds,
                                         icon_kind=placed.kind, icon_asset_identity=placed.asset_identity,
                                         icon_viewport=placed.viewport,
                                         icon_path_geometry=placed.completed_paths,
                                         icon_raster=placed.payload if placed.kind == "raster" else None,
                                         icon_alternative=placed.alternative, icon_decorative=placed.decorative,
                                         visual_capability_source_ref=placed.visual_capability_source_ref,
                                         slot_id=placed.slot_id, paint_order=placed.paint_order))
        if placed.subjects:
            primitive_provenance.append(PrimitiveProvenance(placed.placement_id, placed.subjects))
    # A Theme that binds `legend.fill` paints the legend labels with it (#1062); otherwise they keep `text`.
    legend_paint = "legend" if value.theme_tokens.optional_color("legend", "fill") is not None else None
    text_roles = tuple(
        (prefix, semantic_binding(semantic_id).purpose, role or semantic_binding(semantic_id).scene_role)
        for prefix, semantic_id, role in (
            ("legend:", "legendLabel", legend_paint), ("note:", "projectNote", None),
            ("group-detail:", "groupDetail", None), ("milestone:", "milestoneDigestEntry", None),
            ("summary:", "summaryMetric", None), ("note-index:", "noteIndex", None),
            ("relation-label:", "relationLabel", None),
        ))
    for placed in placed_surface.text:
        if placed.overflow == "suppressed":
            continue
        if placed.annotation is not None:
            emit_semantic_text(placed.placement_id, placed.semantic_id)
            record_annotation_primitives((placed.placement_id,), placed.source_ref)
            continue
        if placed.placement_id.startswith("observations:"):
            header_paint = ("tableColumnLabel" if placed.semantic_id == "observationColumnLabel"
                            and value.theme_tokens.optional_color("tableColumnLabel", "fill") is not None
                            else None)
            emit_semantic_text(placed.placement_id, placed.semantic_id, header_paint)
            continue
        if placed.semantic_id in {"summaryCaption", "summaryUnit", "summaryFigureValue",
                                  "summaryHeader", "summaryMetric", "summaryFigureCaption"}:
            emit_semantic_text(placed.placement_id, placed.semantic_id)
            continue
        for prefix, purpose, role in text_roles:
            if placed.placement_id.startswith(prefix):
                if ":value" in placed.placement_id:
                    figure = semantic_binding("summaryFigureValue")
                    purpose, role = figure.purpose, figure.scene_role
                elif ":caption" in placed.placement_id:
                    caption = semantic_binding("summaryFigureCaption")
                    purpose, role = caption.purpose, caption.scene_role
                elif placed.placement_id.count(":") == 1 and placed.placement_id.startswith("summary:"):
                    purpose = semantic_binding("summaryHeader").purpose
                emit_layout_text(placed.placement_id, purpose, role)
                if purpose == "noteIndex":
                    record_annotation_primitives((placed.placement_id,), placed.source_ref)
                break
    for relation in placed_surface.relations:
        if relation.suppressed or relation.annotation is None:
            continue
        source = relation.source_ref
        leader = semantic_binding(relation.semantic_id)
        purpose, role, layer = leader.purpose, leader.scene_role, "annotation"
        primitives.append(ScenePrimitive(relation.relation_id, PrimitiveKind.PATH, source, layer, purpose, role, (0, 0, 0, 0),
                                         points=relation.points, path_commands=relation.path_commands,
                                         marker_end=relation.marker_end,
                                         paint_order=relation.paint_order))
        record_annotation_primitives((relation.relation_id,), relation.source_ref)
    ownership = {item.placement_id: item.slot_id for item in placed_surface.text}
    ownership.update({item.placement_id: item.slot_id for item in placed_surface.marks})
    ownership.update({item.placement_id: item.slot_id for item in placed_surface.shapes})
    ownership.update({item.relation_id: item.slot_id for item in placed_surface.relations})
    ownership.update({item.placement_id: item.slot_id for item in placed_surface.icons})
    for emission in placed_surface.lane_emissions:
        slot_id = ownership.get(emission.placement_id)
        if slot_id is None:
            raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", emission.placement_id,
                                  "typed lane handoff names an unknown Layout placement")
        for facet in emission.facets:
            existing = ownership.setdefault(facet.primitive_id, slot_id)
            if existing != slot_id:
                raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", facet.primitive_id,
                                      "typed lane handoff primitive slot differs from placement")
    def owning_slot(scene_id: str) -> str:
        if scene_id in ownership:
            return ownership[scene_id]
        # A multi-part glyph's sibling Symbol primitives share their one mark
        # placement's slot; only the mark's own placement_id is in `ownership`.
        base, separator, suffix = scene_id.rpartition(":part")
        if separator and suffix.isdigit() and base in ownership:
            return ownership[base]
        raise KeyError(scene_id)
    try:
        completed_primitives = tuple(replace(item, slot_id=owning_slot(item.scene_id)) for item in primitives)
    except KeyError as error:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", str(error)) from error
    lane_members: tuple[SceneLaneMember, ...] = ()
    lane_obstacles: tuple[SceneLaneObstacle, ...] = ()
    lane_mode: str | None = None
    lane_clearance: float | None = None
    if projection.lane_membership is not None:
        lane_mode = "lanes"
        lane_clearance = 0.0
        owner_by_primitive: dict[str, tuple[str, str]] = {}
        placement_by_primitive: dict[str, tuple[str, str, str, str]] = {}
        obstacle_values: list[SceneLaneObstacle] = []
        for emission in placed_surface.lane_emissions:
            owner = (emission.row_id, emission.member_id)
            for facet in emission.facets:
                placement_identity = (emission.placement_type, emission.placement_id,
                                      emission.row_id, emission.member_id)
                prior_placement = placement_by_primitive.setdefault(facet.primitive_id, placement_identity)
                if prior_placement != placement_identity:
                    raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", facet.primitive_id,
                                          "typed lane handoff assigns one primitive to multiple placements")
                prior = owner_by_primitive.setdefault(facet.primitive_id, owner)
                if prior != owner:
                    raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", facet.primitive_id,
                                          "typed lane handoff assigns one primitive to different members")
                if isinstance(facet.obstacle, ObstacleRect):
                    geometry = SceneLaneRectObstacle(facet.obstacle.left, facet.obstacle.top,
                                                     facet.obstacle.right, facet.obstacle.bottom)
                elif isinstance(facet.obstacle, ObstacleSegment):
                    geometry = SceneLaneSegmentObstacle(facet.obstacle.start, facet.obstacle.end,
                                                        facet.obstacle.stroke_width)
                else:
                    raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", facet.primitive_id,
                                          "typed lane handoff contains unsupported obstacle geometry")
                obstacle_values.append(SceneLaneObstacle(
                    facet.facet_id, facet.primitive_id, emission.row_id, emission.member_id,
                    facet.obstacle_class, geometry,
                ))
        primitive_by_id = {item.scene_id: item for item in completed_primitives}
        unexpected = next((identifier for identifier in owner_by_primitive
                           if identifier not in primitive_by_id), None)
        missing = next((item.scene_id for item in completed_primitives
                        if requires_lane_member_provenance(item.kind, item.purpose)
                        and item.scene_id not in owner_by_primitive), None)
        if not owner_by_primitive or unexpected is not None or missing is not None:
            mismatch = unexpected or missing or "lane-emission-inventory"
            raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", mismatch,
                                  f"Scene lane emission differs from typed Layout handoff: {mismatch}")
        completed_primitives = tuple(
            replace(item, lane_row_id=owner_by_primitive[item.scene_id][0],
                    lane_member_id=owner_by_primitive[item.scene_id][1])
            if item.scene_id in owner_by_primitive else item
            for item in completed_primitives
        )
        emitted_by_member: dict[tuple[str, str], list[str]] = {}
        for primitive_id, owner in owner_by_primitive.items():
            emitted_by_member.setdefault(owner, []).append(primitive_id)
        primary_purposes = {"planned", "snapshot"}
        member_values = []
        for row in projection.lane_rows:
            for member_id in dict.fromkeys(row.member_item_ids):
                identifiers = tuple(emitted_by_member.get((row.lane_id, member_id), ()))
                primary_ids = tuple(identifier for identifier in identifiers
                                     if primitive_by_id[identifier].purpose in primary_purposes)
                try:
                    member_values.append(SceneLaneMember(row.lane_id, member_id, identifiers, primary_ids))
                except ValueError as error:
                    raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", member_id,
                                          f"invalid lane member inventory row={row.lane_id}; "
                                          f"emitted={identifiers}; primary={primary_ids}") from error
        lane_members = tuple(member_values)
        lane_obstacles = tuple(obstacle_values)
    canvas = placed_surface.canvas_bounds
    completed_primitives = _attach_completed_patterns(completed_primitives, placed_surface.patterns)
    completed_primitives = _attach_completed_strokes(completed_primitives, placed_surface.aligned_strokes)
    surface = SceneSurface("table-timeline", slots, rows, groups, scale, completed_primitives, columns=columns,
                        diagnostics=placed_surface.diagnostics,
                        canvas_bounds=(float(canvas.inline), float(canvas.block), float(canvas.inline_size),
                                       float(canvas.block_size)) if canvas is not None else None,
                        fit_warnings=placed_surface.fit_warnings,
                        info_diagnostics=(*placed_surface.info_diagnostics, *artwork_omissions),
                        lane_mode=lane_mode, lane_members=lane_members,
                        lane_obstacles=lane_obstacles, lane_clearance=lane_clearance,
                        diagnostic_provenance=placed_surface.diagnostic_provenance,
                        primitive_provenance=tuple(primitive_provenance))
    return project_canvas_overlays(surface, placed_surface.canvas_overlays, value.theme_tokens, value.visual_profile)


def _attach_completed_strokes(primitives: tuple[ScenePrimitive, ...],
                              placements: tuple[AlignedStrokePlacement, ...]) -> tuple[ScenePrimitive, ...]:
    clips = {item.primitive_id: item.clip for item in placements}
    if len(clips) != len(placements) or clips.keys() - {item.scene_id for item in primitives}:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", "/layout/strokes",
                              "completed stroke identity differs from projected primitives")
    return tuple(replace(item, stroke_clip=clips[item.scene_id])
                 if item.scene_id in clips else item for item in primitives)


def _compose_dependency_network_surface(value: SceneBuildInput) -> SceneSurface:
    """Project completed network placements; never measure, rank, or route here."""
    projection = value.projection
    network = getattr(projection, "network", None)
    if network is None:
        raise SceneBuildError("E_PRESENTATION_PROJECTION_REQUIRED", "/projection/network")
    decisions = tuple(item for item in value.layout_manifest.decisions if item.kind == "slot" and item.source)
    try:
        placed = compose_dependency_network_surface(SurfaceLayoutRequest(
            projection=projection, surface_content=value.surface_content,
            layout_manifest=value.layout_manifest, measured_sources=value.measured_sources,
            theme_tokens=value.theme_tokens, font_metrics=value.font_metrics))
    except LayoutError as error:
        raise SceneBuildError(error.diagnostic_id, error.path) from error
    slots = tuple(SceneSlot(item.node_id, item.source, None,
                            (float(item.bounds.inline), float(item.bounds.block),
                             float(item.bounds.inline_size), float(item.bounds.block_size)),
                            item.priority or "required", item.overflow or "visible-overflow")
                  for item in decisions)
    primitives: list[ScenePrimitive] = []
    primitive_provenance: list[PrimitiveProvenance] = []
    project_items = {node.object_id: node for node in network.nodes}
    project_items.update({item.object_id: item for item in getattr(projection, "items", ())})
    texture_slot: dict[str, str] = {}
    if placed.texture is not None:
        # Ground first, as on the table-timeline surface: below every paint order.
        shape, slot, texture = placed.texture.shape, placed.texture.slot, semantic_binding("canvasTexture")
        slots += (SceneSlot(slot.slot_id, slot.source_ref, None,
                            (float(slot.bounds.inline), float(slot.bounds.block),
                             float(slot.bounds.inline_size), float(slot.bounds.block_size)),
                            slot.priority, slot.overflow),)
        primitives.append(ScenePrimitive(
            shape.placement_id, PrimitiveKind.RECT, shape.source_ref, "decoration", texture.purpose,
            texture.scene_role, (float(shape.bounds.inline), float(shape.bounds.block),
                                 float(shape.bounds.inline_size), float(shape.bounds.block_size)),
            paint_order=shape.paint_order))
        texture_slot[shape.placement_id] = shape.slot_id
    node_binding = semantic_binding("networkNode")
    edge_bindings = {"dependency": semantic_binding("networkEdge"),
                     "dependency-critical": semantic_binding("criticalEdge")}
    heading_part_slots = {item.node_id for item in value.layout_manifest.decisions
                          if item.kind == "slot" and item.source in {
                              "heading.title", "heading.kicker", "heading.subtitle"}}
    def emit_text(text: Any) -> None:
        binding = semantic_binding(text.semantic_id)
        heading_roles = {"titleText": "heading", "kickerText": "kicker", "subtitleText": "subtitle"}
        paint_role = (_heading_paint_role(value.theme_tokens, heading_roles[text.semantic_id])
                      if text.semantic_id in heading_roles else binding.scene_role)
        layout = TextLayout((float(text.bounds.inline), float(text.bounds.block),
                             float(text.bounds.inline_size), float(text.bounds.block_size)),
                            text.baseline or (float(text.bounds.inline), float(text.bounds.block)),
                            text.lines, text.font_family, text.font_weight, text.font_size,
                            text.line_height, text.font_asset_identity, text.letter_spacing,
                            text.text_transform, text.numeric_spacing, text.orientation, text.rotation_degrees,
                            text.horizontal_scale)
        primitives.append(ScenePrimitive(text.placement_id, PrimitiveKind.TEXT, text.source_ref,
                                         text.slot_id if text.slot_id in heading_part_slots else "network",
                                         binding.purpose, paint_role, layout.bounds, text=text.content,
                                         baseline=layout.baseline, text_layout=layout,
                                         paint_order=text.paint_order, host_placement_id=text.host_placement_id))
        project_item = project_items.get(text.source_ref)
        if project_item is not None:
            subject = DiagnosticSubject.project_object(project_item.object_id, project_item.title)
            primitive_provenance.append(PrimitiveProvenance(text.placement_id, (subject,)))
    title_text = next((item for item in placed.text if item.placement_id == "title"), None)
    if title_text is not None:
        emit_text(title_text)
    for relation in placed.relations:
        binding = edge_bindings[relation.semantic_id]
        primitives.append(ScenePrimitive(f"network-edge:{relation.relation_id}", PrimitiveKind.PATH,
                                         relation.relation_id, "network", binding.purpose, binding.scene_role,
                                         (0, 0, 0, 0), points=relation.points,
                                         paint_order=relation.paint_order))
    for node in placed.nodes:
        bounds = (float(node.bounds.inline), float(node.bounds.block),
                  float(node.bounds.inline_size), float(node.bounds.block_size))
        primitives.append(ScenePrimitive(f"network-node:{node.object_id}", PrimitiveKind.RECT, node.object_id,
                                         "network", node_binding.purpose, node_binding.scene_role, bounds,
                                         paint_order=node.paint_order))
        subject = DiagnosticSubject.project_object(node.object_id, getattr(node, "title", None))
        primitive_provenance.append(PrimitiveProvenance(f"network-node:{node.object_id}", (subject,)))
    for text in placed.text:
        if text.placement_id != "title":
            emit_text(text)
    ownership = {item.placement_id: item.slot_id for item in placed.text}
    ownership.update({item.relation_id: item.slot_id for item in placed.relations})
    ownership.update({f"network-node:{item.object_id}": item.slot_id for item in placed.nodes})
    ownership.update({f"network-edge:{item.relation_id}": item.slot_id for item in placed.relations})
    ownership.update(texture_slot)
    try:
        completed_primitives = tuple(replace(item, slot_id=ownership[item.scene_id]) for item in primitives)
    except KeyError as error:
        raise SceneBuildError("E_PRESENTATION_PRIMITIVE_INVALID", str(error)) from error
    completed_primitives = _attach_completed_patterns(completed_primitives, placed.patterns)
    completed_primitives = _attach_completed_strokes(completed_primitives, placed.aligned_strokes)
    surface = SceneSurface("dependency-network", slots, (), (), None, completed_primitives,
                        diagnostics=placed.diagnostics,
                        canvas_bounds=(float(placed.canvas_bounds.inline), float(placed.canvas_bounds.block),
                                       float(placed.canvas_bounds.inline_size), float(placed.canvas_bounds.block_size)),
                        fit_warnings=placed.fit_warnings,
                        diagnostic_provenance=getattr(placed, "diagnostic_provenance", ()),
                        primitive_provenance=tuple(primitive_provenance))
    return project_canvas_overlays(surface, placed.canvas_overlays, value.theme_tokens, value.visual_profile)
