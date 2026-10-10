"""Renderer-neutral presentation Scene model."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import math
from typing import Any

from chrona.presentation.layout.surface_quality import FitWarning, MarkerGeometry, PaintClip, PathCommand, RelationFanIn, StrokeClip, TextFit
from chrona.presentation.layout.relation_terminals import project_marker_outline
from chrona.presentation.layout.canvas_viewport import CanvasViewportWarning
from chrona.presentation.layout.pattern_placement import PatternTilePrimitive
from chrona.presentation.model.font_metrics import FontTabularWarning
from chrona.presentation.model.info_diagnostics import PresentationInfo
from chrona.presentation.model.diagnostic_sources import DiagnosticProvenance, PrimitiveProvenance
from chrona.presentation.model.semantic_registry import ContrastClass, contrast_binding, semantic_binding
from chrona.presentation.model.theme_tokens import BOX_FOLLOWS_TEXT, TEXT_FOLLOWS_BOX, VIEWER_FIT_MODES


LANE_MEMBER_BINDING_IDS = (
    "planned", "actual", "snapshot", "missingActual", "summaryBar", "progressFill",
    "memberLabel", "memberLabelInsidePlanned", "memberLabelInsideActual",
    "memberLabelInsideSnapshot", "memberLabelInsideScenario", "finishDelta",
    "varianceAhead", "varianceBehind", "iconMark", "labelVisual",
)
LANE_MEMBER_PURPOSES = frozenset(semantic_binding(identifier).purpose
                                 for identifier in LANE_MEMBER_BINDING_IDS)
PRIMARY_LANE_MARK_PURPOSES = frozenset(
    semantic_binding(identifier).purpose for identifier in ("planned", "snapshot")
)
_LANE_PURPOSE_KINDS = frozenset(
    (scene_kind, semantic_binding(identifier).purpose)
    for identifier in LANE_MEMBER_BINDING_IDS
    for scene_kind in ({"Rect", "Symbol", "Path"} if semantic_binding(identifier).primitive_kind == "mark"
                       else {"Text"} if semantic_binding(identifier).primitive_kind == "label"
                       else {"Icon"})
)


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _brief(value: object, *, limit: int = 72) -> str:
    """Describe a scalar or tuple shape without dumping Scene payloads."""
    if isinstance(value, str):
        return repr(value if len(value) <= limit else value[:limit - 1] + "…")
    if value is None or isinstance(value, (int, float, bool)):
        return repr(value)
    if isinstance(value, (tuple, list)):
        members = ", ".join(_brief(item, limit=24) for item in value[:8])
        suffix = ", …" if len(value) > 8 else ""
        return f"{type(value).__name__}(len={len(value)}, [{members}{suffix}])"
    return f"<{type(value).__name__}>"


def _pair_brief(value: object) -> str:
    if isinstance(value, (tuple, list)) and len(value) == 2:
        return f"({_brief(value[0])}, {_brief(value[1])})"
    return _brief(value)


def _invalid(field: str, value: object, expected: str, *, owner: str = "Scene") -> ValueError:
    return ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: {owner}.{field}; expected {expected}; found {_brief(value)}")


def _paint_clip_contains(clip: PaintClip, bounds: object, points: object) -> bool:
    """Check completed absolute geometry against a supplied clip, without interpreting routes."""
    if not isinstance(bounds, tuple) or len(bounds) != 4 or not all(_finite_number(value) for value in bounds):
        return False
    left, top, width, height = bounds
    if width < 0 or height < 0 or not math.isfinite(left + width) or not math.isfinite(top + height):
        return False
    x0, y0, clip_width, clip_height = clip.bounds
    x1, y1 = x0 + clip_width, y0 + clip_height
    if not math.isfinite(x1) or not math.isfinite(y1):
        return False
    if left < x0 or top < y0 or left + width > x1 or top + height > y1:
        return False
    if not isinstance(points, tuple):
        return False
    for point in points:
        if (not isinstance(point, tuple) or len(point) != 2
                or not all(_finite_number(value) for value in point)
                or not (x0 <= point[0] <= x1 and y0 <= point[1] <= y1)):
            return False
    return True


def _path_points(commands: object) -> tuple[object, ...] | None:
    if not isinstance(commands, tuple):
        return None
    points: list[object] = []
    for command in commands:
        if not isinstance(command, PathCommand) or not isinstance(command.points, tuple):
            return None
        points.extend(command.points)
    return tuple(points)


def requires_lane_member_provenance(kind: str, purpose: str) -> bool:
    """Whether a non-icon primitive's semantics alone imply lane ownership.

    Icons can decorate global labels as well as lane members. Member icons are
    instead closed by the exact typed Layout emission inventory.
    """
    return kind != "Icon" and purpose in LANE_MEMBER_PURPOSES and (kind, purpose) in _LANE_PURPOSE_KINDS


@dataclass(frozen=True)
class ScenePaint:
    """Completed renderer-neutral appearance selected before adapter invocation."""

    fill: str | None
    stroke: str | None
    stroke_width: float | None
    dash: tuple[float, ...]
    opacity: float
    gradient: "LinearGradient | None" = None
    shadow: "DropShadow | None" = None
    stroke_finish: "StrokeFinish | None" = None
    image: "ImageFill | None" = None
    glow: "Glow | None" = None
    wobble: "StrokeWobble | None" = None
    radial_gradient: "RadialGradient | None" = None


@dataclass(frozen=True)
class ImageTile:
    """One completed nine-slice tile: a source rect stretched to a destination rect (#465)."""

    source: tuple[float, float, float, float]
    destination: tuple[float, float, float, float]


@dataclass(frozen=True)
class ImageFill:
    """A container's completed nine-slice raster fill; adapters only serialize it.

    ``payload`` is the verified PNG bytes -- carried in memory only, exactly
    as an Icon's raster payload is (never part of the serialized Scene
    document; see ``icon_asset_identity`` for the identity that is).
    """

    asset_identity: str
    viewport: tuple[int, int]
    payload: bytes
    tiles: tuple[ImageTile, ...]

    def __post_init__(self) -> None:
        if not self.tiles or self.viewport[0] <= 0 or self.viewport[1] <= 0:
            raise _invalid("tiles/viewport", (self.tiles, self.viewport), "non-empty tiles and positive viewport dimensions", owner="ImageFill")


@dataclass(frozen=True)
class LinearGradient:
    """A completed two-stop linear gradient.

    ``stop_opacities`` (#890) optionally gives each stop its own opacity, so a gradient can fade from ink
    to transparent without naming the ground; absent, every stop is opaque.
    """

    start: tuple[float, float]
    end: tuple[float, float]
    stops: tuple[tuple[float, str], ...]
    fidelity: str
    stop_opacities: tuple[float, ...] | None = None


@dataclass(frozen=True)
class RadialGradientStop:
    """One completed opacity stop for a fixed-ink radial surface fade."""

    offset: float
    color: str
    opacity: float


@dataclass(frozen=True)
class RadialGradient:
    """A completed finite elliptical surface fade (#888); adapters only serialize it."""

    center: tuple[float, float]
    radii: tuple[float, float]
    stops: tuple[RadialGradientStop, ...]
    fidelity: str

    def __post_init__(self) -> None:
        if (len(self.center) != 2 or len(self.radii) != 2
                or not all(_finite_number(value) for value in (*self.center, *self.radii))
                or any(value <= 0 for value in self.radii)
                or len(self.stops) not in {2, 3}
                or self.fidelity not in {"required", "decorative-optional"}):
            raise ValueError(
                f"E_PRESENTATION_PRIMITIVE_INVALID: radial geometry requires a finite center pair, positive finite "
                f"radii pair, 2 or 3 stops, and fidelity 'required' or 'decorative-optional'; received "
                f"center={_pair_brief(self.center)}, radii={_pair_brief(self.radii)}, stopCount={len(self.stops)}, fidelity={_brief(self.fidelity)}")
        if (self.stops[0].offset != 0 or self.stops[-1].offset != 1
                or any(not _finite_number(stop.offset) or not 0 <= stop.offset <= 1
                       or not _finite_number(stop.opacity) or not 0 <= stop.opacity <= 1
                       or not isinstance(stop.color, str) or not stop.color
                       for stop in self.stops)
                or any(left.offset >= right.offset for left, right in zip(self.stops, self.stops[1:]))
                or len({stop.color for stop in self.stops}) != 1
                or self.stops[0].opacity != 0 or self.stops[-1].opacity != 1
                or (len(self.stops) == 3 and self.stops[1].opacity != 0)):
            raise ValueError(
                f"E_PRESENTATION_PRIMITIVE_INVALID: radial stops require strictly increasing finite offsets from 0 "
                f"to 1, one shared color, opacity 0 at the first and optional middle stop, and opacity 1 at the last; "
                f"received offsets={_brief(tuple(stop.offset for stop in self.stops))}, "
                f"colors={_brief(tuple(stop.color for stop in self.stops))}, "
                f"opacities={_brief(tuple(stop.opacity for stop in self.stops))}")


@dataclass(frozen=True)
class DropShadow:
    color: str
    offset_x: float
    offset_y: float
    blur: float
    opacity: float
    fidelity: str


@dataclass(frozen=True)
class Glow:
    """A completed halo of colour around a primitive (#587).

    ``region`` is the primitive's visible extent grown by three blur on every side and
    clipped to the canvas, completed by Scene: the halo never leaves the slide and is no
    part of the primitive's bounds. Adapters serialize it and decide nothing.
    """

    color: str
    blur: float
    opacity: float
    fidelity: str
    region: tuple[float, float, float, float]


@dataclass(frozen=True)
class StrokeWobble:
    """A completed hand-wobble of a stroke's geometry (#588).

    ``outline`` is the perturbed geometry, completed by Scene from Layout's geometry with the declared
    ``amplitude``, ``wavelength`` and ``seed``: one closed polygon for a Rect, one open polyline per
    sub-path for a Path, in final surface coordinates rounded to three decimals. The primitive's
    bounds, points and commands stay the Layout values; adapters draw ``outline`` verbatim.
    """

    amplitude: float
    wavelength: float
    seed: int
    fidelity: str
    closed: bool = False
    outline: tuple[tuple[tuple[float, float], ...], ...] = ()


@dataclass(frozen=True)
class StrokeFinish:
    line_cap: str
    line_join: str
    fidelity: str


@dataclass(frozen=True)
class TextRun:
    """One run of a text line at its own size, as Layout measured it (a small-caps line has several, #1285)."""

    text: str
    font_size: float
    inline_size: float


@dataclass(frozen=True)
class TextLayout:
    """One measured text result shared by Scene geometry and renderer serialization."""

    bounds: tuple[float, float, float, float]
    baseline: tuple[float, float]
    lines: tuple[str, ...]
    family: str
    weight: int
    font_size: float
    line_height: float
    asset_identity: str
    letter_spacing: float = 0.0
    text_transform: str = "none"
    numeric_spacing: str = "proportional"
    orientation: str = "horizontal"
    rotation_degrees: int | float = 0
    # Declared horizontal compression of the painted run along its own inline axis (#585); the bounds above already
    # carry the compressed width. 1 is no compression.
    horizontal_scale: float = 1.0
    # The completed viewer-fit facts of a box role's text (#1050); None is `raw`.
    fit: TextFit | None = None
    # One tuple of runs per line when the role is `small-caps` (#1285); empty otherwise. The runs' texts join to the line.
    runs: tuple[tuple[TextRun, ...], ...] = ()

    def __post_init__(self) -> None:
        if self.runs and (len(self.runs) != len(self.lines) or any(
                "".join(run.text for run in line) != text for line, text in zip(self.runs, self.lines))):
            raise ValueError(f"E_PRESENTATION_TEXT_LAYOUT_INVALID: TextLayout.runs; expected one run tuple per line whose texts join to that line; found {_brief(self.runs)}")
        # `tilt` (#584) is a Layout-completed rigid rotation of a note by a small non-zero angle about the
        # baseline start; the quarter turns remain the only other rotations.
        tilted = (self.orientation == "tilt" and not isinstance(self.rotation_degrees, bool)
                  and isinstance(self.rotation_degrees, (int, float)) and self.rotation_degrees == self.rotation_degrees
                  and 0 < abs(self.rotation_degrees) <= 15)
        if (self.numeric_spacing not in {"proportional", "tabular"}
                or not (tilted or (self.orientation, self.rotation_degrees) in {
                    ("horizontal", 0), ("rotate-cw", 90), ("rotate-ccw", -90)})):
            raise ValueError(f"E_PRESENTATION_TEXT_LAYOUT_INVALID: TextLayout.numeric_spacing/orientation/rotation_degrees; expected proportional or tabular spacing and horizontal/0, rotate-cw/90, rotate-ccw/-90, or tilt within 15 degrees; found {_brief((self.numeric_spacing, self.orientation, self.rotation_degrees))}")
        if (isinstance(self.horizontal_scale, bool) or not isinstance(self.horizontal_scale, (int, float))
                or not 0.5 <= self.horizontal_scale <= 1):
            raise ValueError(f"E_PRESENTATION_TEXT_LAYOUT_INVALID: TextLayout.horizontal_scale; expected finite numeric value in [0.5, 1]; found {_brief(self.horizontal_scale)}")
        if self.fit is not None and (not isinstance(self.fit, TextFit) or (
                self.fit.mode == TEXT_FOLLOWS_BOX and len(self.fit.line_inline_sizes) != len(self.lines))):
            raise ValueError(f"E_PRESENTATION_TEXT_LAYOUT_INVALID: TextLayout.fit.line_inline_sizes; expected a TextFit with one fit size per line when box-follows-text; found fit={_brief(self.fit)}, lineCount={len(self.lines)}")


@dataclass(frozen=True)
class SceneIconPath:
    """One adapter-ready icon path in final surface coordinates and paint."""

    commands: tuple[tuple[str, tuple[tuple[float, float], ...]], ...]
    fill: str | None
    stroke: str | None
    stroke_width: float | None
    line_cap: str | None = None
    line_join: str | None = None
    opacity: float = 1.0


@dataclass(frozen=True)
class PatternStroke:
    start: tuple[float, float]
    end: tuple[float, float]
    width: float

    def __post_init__(self) -> None:
        if self.width <= 0:
            raise _invalid("width", self.width, "a positive stroke width", owner="PatternStroke")


@dataclass(frozen=True)
class PatternGeometry:
    """Completed repeat-tile geometry; target adapters choose syntax, not values."""

    tile_inline_size: float
    tile_block_size: float
    angle_degrees: float
    strokes: tuple[PatternStroke, ...] = ()
    density_basis_points: int | None = None
    primitives: tuple[PatternTilePrimitive, ...] = ()
    origin: tuple[float, float] | None = None
    region_bounds: tuple[float, float, float, float] | None = None
    clip_bounds: tuple[float, float, float, float] | None = None
    corner_radius: float | None = None

    def __post_init__(self) -> None:
        catalog = bool(self.primitives)
        if (self.tile_inline_size <= 0 or self.tile_block_size <= 0
                or not 0 <= self.angle_degrees < 360
                or (catalog and (self.strokes or self.density_basis_points is None
                                 or not 1 <= self.density_basis_points <= 10_000
                                 or self.origin is None or self.region_bounds is None
                                 or self.clip_bounds is None or self.corner_radius is None))
                or (not catalog and (not self.strokes or self.density_basis_points is not None
                                     or self.origin is not None or self.region_bounds is not None
                                     or self.clip_bounds is not None or self.corner_radius is not None))):
            raise _invalid("tile_inline_size/tile_block_size/angle_degrees/density_basis_points/strokes/origin/region_bounds/clip_bounds/corner_radius",
                           (self.tile_inline_size, self.tile_block_size, self.angle_degrees, self.density_basis_points,
                            self.strokes, self.origin, self.region_bounds, self.clip_bounds, self.corner_radius),
                           "positive tile sizes, angle in [0,360), and either catalog primitives with complete region facts or legacy strokes without catalog facts",
                           owner="PatternGeometry")


@dataclass(frozen=True)
class SymbolGeometry:
    """Completed absolute point-symbol outline from Theme treatment and Layout bounds."""

    outline: tuple[PathCommand, ...]

    def __post_init__(self) -> None:
        if not self.outline:
            raise _invalid("outline", self.outline, "a non-empty tuple of completed path commands", owner="SymbolGeometry")


@dataclass(frozen=True)
class ScenePrimitive:
    """A measured renderer-neutral primitive; adapters serialize but never reinterpret it."""

    scene_id: str
    kind: str
    source_ref: str
    source_kind: str
    purpose: str
    visual_role: str
    bounds: tuple[float, float, float, float]
    slot_id: str = ""
    text: str | None = None
    baseline: tuple[float, float] | None = None
    text_layout: TextLayout | None = None
    marker_start: MarkerGeometry | None = None
    marker_end: MarkerGeometry | None = None
    pattern: PatternGeometry | None = None
    symbol: SymbolGeometry | None = None
    paint: ScenePaint | None = None
    corner_radius: float | None = None
    path_commands: tuple[PathCommand, ...] = ()
    points: tuple[tuple[float, float], ...] = ()
    href: str | None = None
    link_title: str | None = None
    icon_kind: str | None = None
    icon_asset_identity: str | None = None
    icon_viewport: tuple[int, int] | None = None
    icon_paths: tuple[SceneIconPath, ...] = ()
    icon_path_geometry: tuple[Any, ...] = ()
    icon_raster: bytes | None = None
    icon_alternative: str | None = None
    icon_decorative: bool = True
    visual_capability_source_ref: str = "/"
    table_row_id: str | None = None
    table_column_id: str | None = None
    paint_order: int = 0
    host_placement_id: str | None = None
    clip_source_id: str | None = None
    end_treatment: str = "closed"
    contrast_treatment: str | None = None
    glyph_paint_mode: str | None = None
    glyph_paint_color: str | None = None
    glyph_stroke_width: float | None = None
    glyph_line_cap: str | None = None
    glyph_line_join: str | None = None
    image_fill_pending: "ImageFill | None" = None
    lane_row_id: str | None = None
    lane_member_id: str | None = None
    from_instance_id: str | None = None
    to_instance_id: str | None = None
    fan_in: RelationFanIn | None = None
    # The viewer-fit mode of a text-bearing box (#1050); `raw` is today's output.
    viewer_fit: str = "raw"
    stroke_clip: StrokeClip | None = None
    paint_clip: PaintClip | None = None

    def __post_init__(self) -> None:
        if self.stroke_clip is not None and (self.kind not in {"Rect", "Symbol", "Path"}
                or (self.kind != "Rect" and not self.stroke_clip.outline)
                or self.viewer_fit == BOX_FOLLOWS_TEXT
                or (self.paint is not None and (self.paint.stroke is None
                    or self.paint.stroke_width != self.stroke_clip.stroke_width))):
            raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: primitive {_brief(self.scene_id)} stroke_clip; expected a Rect, or a non-empty clipped Symbol/Path stroke outside box-follows-text with matching stroke paint; found kind={_brief(self.kind)}, viewer_fit={_brief(self.viewer_fit)}, stroke_width={_brief(getattr(self.paint, 'stroke_width', self.paint) if self.paint is not None else None)}, clip_width={_brief(getattr(self.stroke_clip, 'stroke_width', self.stroke_clip))}")
        if (self.viewer_fit not in VIEWER_FIT_MODES
                or (self.viewer_fit != "raw" and self.kind not in {"Rect", "Symbol"})
                or (self.viewer_fit == BOX_FOLLOWS_TEXT and (
                    self.kind != "Rect" or (self.pattern is not None and self.pattern.primitives)
                    or self.clip_source_id is not None or self.image_fill_pending is not None))):
            raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: primitive {_brief(self.scene_id)} viewer_fit/pattern/clip_source_id/image_fill_pending; expected a known fit mode on Rect or Symbol, with box-follows-text only on a plain Rect; found mode={_brief(self.viewer_fit)}, kind={_brief(self.kind)}, pattern={_brief(self.pattern)}, clip_source_id={_brief(self.clip_source_id)}, image_fill_pending={_brief(self.image_fill_pending)}")
        if (((self.marker_start is not None or self.marker_end is not None) and self.kind != "Path")
                or (self.pattern is not None and self.kind != "Rect")
                or (self.image_fill_pending is not None and self.kind not in {"Rect", "Symbol"})
                or (self.paint is not None and self.paint.radial_gradient is not None and (
                    self.kind != "Rect" or self.pattern is not None
                    or self.paint.fill is None
                    or any(stop.color != self.paint.fill for stop in self.paint.radial_gradient.stops)
                    or self.paint.stroke is not None or self.paint.stroke_width is not None
                    or self.paint.dash or self.paint.gradient is not None
                    or self.paint.shadow is not None or self.paint.glow is not None
                    or self.paint.wobble is not None or self.paint.stroke_finish is not None
                    or self.paint.image is not None))
                or (self.symbol is not None and self.kind != "Symbol")
                or (self.kind == "Symbol" and self.symbol is None)
                or (self.glyph_paint_mode is not None and self.kind != "Symbol")
                or (self.glyph_paint_mode not in (None, "fill", "stroke"))
                or (self.glyph_paint_color is not None and self.glyph_paint_mode is None)
                or (self.glyph_stroke_width is not None and (self.glyph_paint_mode != "stroke"
                    or self.glyph_stroke_width <= 0 or not math.isfinite(self.glyph_stroke_width)))
                or ((self.glyph_line_cap is None) != (self.glyph_stroke_width is None))
                or ((self.glyph_line_join is None) != (self.glyph_stroke_width is None))
                or (self.glyph_line_cap not in (None, "butt", "round", "square"))
                or (self.glyph_line_join not in (None, "miter", "round", "bevel"))
                or (self.purpose == "table-cell" and self.table_row_id is None)
                or (self.purpose == "table-cell" and self.table_column_id is None)
                or (self.purpose != "table-cell" and self.table_row_id is not None)
                or (self.purpose not in {"table-cell", "table-column-label"}
                    and self.table_column_id is not None)
                or ((self.lane_row_id is None) != (self.lane_member_id is None))
                or (self.lane_row_id is not None and not self.lane_row_id)
                or (self.lane_member_id is not None and not self.lane_member_id)
                or ((self.from_instance_id is None) != (self.to_instance_id is None))
                or (self.from_instance_id is not None and
                    (not isinstance(self.from_instance_id, str) or not self.from_instance_id or self.kind != "Path"))
                or (self.to_instance_id is not None and
                    (not isinstance(self.to_instance_id, str) or not self.to_instance_id or self.kind != "Path"))
                or (self.fan_in is not None and
                    (self.kind != "Path" or self.source_kind != "relation" or self.to_instance_id is None
                     or not isinstance(self.fan_in, RelationFanIn)))
                or (self.kind == "Icon" and (self.icon_kind not in {"vector", "raster"}
                                               or self.icon_viewport is None
                                               or any(item <= 0 for item in self.icon_viewport)))
                or (self.kind != "Icon" and self.icon_viewport is not None)):
            raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: primitive {_brief(self.scene_id)} has incompatible completed fields; expected marker_start/marker_end only on Path, pattern only on Rect, symbol exactly on Symbol, radial paint only on plain filled Rect, glyph paint only on Symbol, table/lane/relation fields consistent with purpose/kind, and icon viewport only on Icon; found sourceRef={_brief(self.source_ref)}, kind={_brief(self.kind)}, purpose={_brief(self.purpose)}, marker_start={_brief(self.marker_start)}, marker_end={_brief(self.marker_end)}, pattern={_brief(self.pattern)}, symbol={_brief(self.symbol)}, radial_gradient={_brief(getattr(self.paint, 'radial_gradient', self.paint) if self.paint is not None else None)}, glyph_mode={_brief(self.glyph_paint_mode)}, table_row_id={_brief(self.table_row_id)}, table_column_id={_brief(self.table_column_id)}, lane_row_id={_brief(self.lane_row_id)}, lane_member_id={_brief(self.lane_member_id)}, from_instance_id={_brief(self.from_instance_id)}, to_instance_id={_brief(self.to_instance_id)}, icon_kind={_brief(self.icon_kind)}, icon_viewport={_brief(self.icon_viewport)}")
        if self.end_treatment not in {"closed", "open"}:
            raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: primitive {_brief(self.scene_id)} end_treatment; expected 'closed' or 'open'; found {_brief(self.end_treatment)}")
        classified = contrast_binding(self.visual_role)
        if ((classified is not None and classified.contrast_class == ContrastClass.STATE_TEXT
             and self.contrast_treatment not in {"required", "deemphasized"})
                or (self.visual_role == "annotation-note-text" and self.contrast_treatment != "required")
                or ((classified is None or classified.contrast_class != ContrastClass.STATE_TEXT)
                    and self.contrast_treatment is not None)):
            raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: primitive {_brief(self.scene_id)} visual_role/contrast_treatment; expected required or deemphasized for state text, required for annotation-note-text, and absent otherwise; found role={_brief(self.visual_role)}, treatment={_brief(self.contrast_treatment)}")
        if self.paint_order < 0:
            raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: primitive {_brief(self.scene_id)} paint_order; expected a non-negative integer; found {_brief(self.paint_order)}")
        if self.end_treatment == "open" and (self.kind != "Symbol" or self.symbol is None or self.purpose != "actual"):
            raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: primitive {_brief(self.scene_id)} end_treatment/kind/symbol/purpose; expected open treatment only on an actual Symbol with completed symbol geometry; found treatment={_brief(self.end_treatment)}, kind={_brief(self.kind)}, symbol={_brief(self.symbol)}, purpose={_brief(self.purpose)}")
        if self.paint_clip is not None:
            if not isinstance(self.paint_clip, PaintClip):
                raise _invalid("paint_clip", self.paint_clip, "a completed finite positive PaintClip", owner=f"primitive {_brief(self.scene_id)}")
            if not isinstance(self.bounds, tuple) or len(self.bounds) != 4:
                raise _invalid("bounds", self.bounds, "four completed coordinates", owner=f"primitive {_brief(self.scene_id)} paint_clip")
            geometry = [("bounds", self.bounds, ())]
            geometry.append(("points", (self.bounds[0], self.bounds[1], 0, 0), self.points))
            path_points = _path_points(self.path_commands)
            if path_points is None:
                raise _invalid("path_commands", self.path_commands, "completed path commands", owner=f"primitive {_brief(self.scene_id)} paint_clip")
            if path_points:
                geometry.append(("path_commands", (self.bounds[0], self.bounds[1], 0, 0), path_points))
            if self.symbol is not None:
                symbol_points = _path_points(self.symbol.outline)
                if symbol_points is None:
                    raise _invalid("symbol.outline", self.symbol.outline, "completed absolute path commands", owner=f"primitive {_brief(self.scene_id)} paint_clip")
                geometry.append(("symbol.outline", (self.bounds[0], self.bounds[1], 0, 0), symbol_points))
            for index, icon_path in enumerate(self.icon_paths):
                if not isinstance(icon_path, SceneIconPath) or not isinstance(icon_path.commands, tuple):
                    raise _invalid(f"icon_paths[{index}]", icon_path, "completed absolute icon path geometry",
                                   owner=f"primitive {_brief(self.scene_id)} paint_clip")
                icon_points: list[object] = []
                for command in icon_path.commands:
                    if (not isinstance(command, tuple) or len(command) != 2
                            or not isinstance(command[1], tuple)):
                        raise _invalid(f"icon_paths[{index}].commands", command,
                                       "completed command kind and absolute point tuples",
                                       owner=f"primitive {_brief(self.scene_id)} paint_clip")
                    icon_points.extend(command[1])
                geometry.append((f"icon_paths[{index}]", (self.bounds[0], self.bounds[1], 0, 0),
                                 tuple(icon_points)))
            for index, icon_path in enumerate(self.icon_path_geometry):
                commands = getattr(icon_path, "commands", None)
                if not isinstance(commands, tuple):
                    raise _invalid(f"icon_path_geometry[{index}]", icon_path,
                                   "Layout-completed absolute icon path commands",
                                   owner=f"primitive {_brief(self.scene_id)} paint_clip")
                icon_points = []
                for command in commands:
                    if (not isinstance(command, tuple) or len(command) != 2
                            or not isinstance(command[1], tuple)):
                        raise _invalid(f"icon_path_geometry[{index}].commands", command,
                                       "completed command kind and absolute point tuples",
                                       owner=f"primitive {_brief(self.scene_id)} paint_clip")
                    icon_points.extend(command[1])
                geometry.append((f"icon_path_geometry[{index}]", (self.bounds[0], self.bounds[1], 0, 0),
                                 tuple(icon_points)))
            for field_name, marker, side in (("marker_start", self.marker_start, "start"),
                                             ("marker_end", self.marker_end, "end")):
                if marker is None:
                    continue
                try:
                    projected = project_marker_outline(
                        marker, side=side, points=self.points, path_commands=self.path_commands,
                        stroke_width=self.paint.stroke_width if self.paint is not None else None)
                except ValueError as error:
                    raise _invalid(field_name, marker, "a finite completed terminal projection within paint_clip",
                                   owner=f"primitive {_brief(self.scene_id)}") from error
                marker_points = _path_points(projected)
                geometry.append((field_name, (self.bounds[0], self.bounds[1], 0, 0), marker_points or ()))
            for field_name, bounds, points in geometry:
                if not _paint_clip_contains(self.paint_clip, bounds, points):
                    raise _invalid(field_name, self.paint_clip.bounds,
                                   "completed absolute geometry contained by paint_clip.bounds",
                                   owner=f"primitive {_brief(self.scene_id)}")

@dataclass(frozen=True)
class SceneSlot:
    """One resolved surface bound consumed verbatim by renderer adapters."""

    slot_id: str
    source: str
    scale_id: str | None
    bounds: tuple[float, float, float, float]
    priority: str = "required"
    overflow: str = "visible-overflow"


@dataclass(frozen=True)
class SceneRow:
    object_id: str
    group_id: str
    bounds: tuple[float, float, float, float]
    row_id: str = ""
    lane_mark_band_block: float | None = None

    def __post_init__(self) -> None:
        if self.lane_mark_band_block is not None:
            inline, block, _inline_size, block_size = self.bounds
            if (not math.isfinite(self.lane_mark_band_block)
                    or not math.isfinite(block) or not math.isfinite(block_size)
                    or self.lane_mark_band_block < block
                    or self.lane_mark_band_block > block + block_size):
                raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: SceneRow { _brief(self.row_id or self.object_id)} lane_mark_band_block; expected a finite block coordinate inside bounds {_brief(self.bounds)}; found {_brief(self.lane_mark_band_block)}")


@dataclass(frozen=True)
class SceneColumn:
    """One typed table column completed by Layout; never inferred from a text ID."""

    column_id: str
    label: str
    bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class SceneGroup:
    group_id: str
    header_bounds: tuple[float, float, float, float] | None
    content_bounds: tuple[float, float, float, float]


@dataclass(frozen=True)
class SceneLaneMember:
    """Closed lane membership and primitive-emission inventory for one member."""

    row_id: str
    member_id: str
    emitted_primitive_ids: tuple[str, ...]
    primary_mark_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (not isinstance(self.row_id, str) or not self.row_id
                or not isinstance(self.member_id, str) or not self.member_id
                or not isinstance(self.emitted_primitive_ids, tuple)
                or not isinstance(self.primary_mark_ids, tuple)
                or not self.emitted_primitive_ids or not self.primary_mark_ids
                or any(not isinstance(item, str) or not item
                       for item in (*self.emitted_primitive_ids, *self.primary_mark_ids))
                or len(set(self.emitted_primitive_ids)) != len(self.emitted_primitive_ids)
                or len(set(self.primary_mark_ids)) != len(self.primary_mark_ids)
                or not set(self.primary_mark_ids) <= set(self.emitted_primitive_ids)):
            raise _invalid("row_id/member_id/emitted_primitive_ids/primary_mark_ids",
                           (self.row_id, self.member_id, self.emitted_primitive_ids, self.primary_mark_ids),
                           "non-empty row/member IDs, non-empty unique tuple IDs, and primary marks drawn from emitted IDs",
                           owner="SceneLaneMember")


@dataclass(frozen=True)
class SceneLaneRectObstacle:
    """One Layout-completed rectangular visible lane obstacle."""

    left: float
    top: float
    right: float
    bottom: float

    def __post_init__(self) -> None:
        if (not all(_finite_number(value) for value in (self.left, self.top, self.right, self.bottom))
                or self.right <= self.left or self.bottom <= self.top):
            raise _invalid("left/top/right/bottom", (self.left, self.top, self.right, self.bottom),
                           "finite edges with right > left and bottom > top", owner="SceneLaneRectObstacle")


@dataclass(frozen=True)
class SceneLaneSegmentObstacle:
    """One Layout-completed stroked path segment visible footprint."""

    start: tuple[float, float]
    end: tuple[float, float]
    stroke_width: float

    def __post_init__(self) -> None:
        if (not isinstance(self.start, tuple) or len(self.start) != 2
                or not isinstance(self.end, tuple) or len(self.end) != 2
                or not all(_finite_number(value) for value in (*self.start, *self.end, self.stroke_width))
                or self.start == self.end or self.stroke_width < 0):
            raise _invalid("start/end/stroke_width", (self.start, self.end, self.stroke_width),
                           "finite point pairs, distinct endpoints, and non-negative stroke width", owner="SceneLaneSegmentObstacle")


@dataclass(frozen=True)
class SceneLaneObstacle:
    """Layout-owned visible obstacle evidence for one emitted Scene primitive."""

    facet_id: str
    primitive_id: str
    row_id: str
    member_id: str
    obstacle_class: str
    geometry: SceneLaneRectObstacle | SceneLaneSegmentObstacle

    def __post_init__(self) -> None:
        if (not all(isinstance(value, str) and value for value in
                    (self.facet_id, self.primitive_id, self.row_id, self.member_id))
                or self.obstacle_class not in {"mark", "required-label"}
                or not isinstance(self.geometry, (SceneLaneRectObstacle, SceneLaneSegmentObstacle))):
            raise _invalid("facet_id/primitive_id/row_id/member_id/obstacle_class/geometry",
                           (self.facet_id, self.primitive_id, self.row_id, self.member_id, self.obstacle_class, self.geometry),
                           "non-empty identifiers, class mark or required-label, and a completed lane obstacle geometry",
                           owner="SceneLaneObstacle")


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
    group_details: int = 0
    milestones: int = 0
    observation_rows: int = 0


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
    visual_role_counts: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True)
class DecorationDisposition:
    """One classified decoration deliberately omitted from a completed surface."""

    visual_role: str
    disposition: str

    def __post_init__(self) -> None:
        if self.disposition != "absent":
            raise _invalid("disposition", self.disposition, "'absent'", owner=f"DecorationDisposition({self.visual_role})")


@dataclass(frozen=True)
class SceneSurface:
    """Resolved geometry for one public adapter route."""

    surface_id: str
    slots: tuple[SceneSlot, ...]
    rows: tuple[SceneRow, ...]
    groups: tuple[SceneGroup, ...]
    scale_manifest: SurfaceScaleManifest | None
    primitives: tuple[ScenePrimitive, ...] = ()
    canvas_paint: ScenePaint | None = None
    columns: tuple[SceneColumn, ...] = ()
    diagnostics: tuple[str, ...] = ()
    canvas_bounds: tuple[float, float, float, float] | None = None
    fit_warnings: tuple[FitWarning, ...] = ()
    decoration_dispositions: tuple[DecorationDisposition, ...] = ()
    info_diagnostics: tuple[PresentationInfo, ...] = ()
    lane_mode: str | None = None
    lane_members: tuple[SceneLaneMember, ...] = ()
    lane_obstacles: tuple[SceneLaneObstacle, ...] = ()
    lane_clearance: float | None = None
    diagnostic_provenance: tuple[DiagnosticProvenance, ...] = ()
    primitive_provenance: tuple[PrimitiveProvenance, ...] = ()
    canvas_warning: CanvasViewportWarning | None = None

    def __post_init__(self) -> None:
        """Reject incomplete clip references before any adapter can serialize them."""
        if (self.canvas_paint is not None and self.canvas_paint.radial_gradient is not None
                or (self.canvas_bounds is not None and (len(self.canvas_bounds) != 4
                    or self.canvas_bounds[2] <= 0 or self.canvas_bounds[3] <= 0))):
            raise _invalid("canvas_paint/canvas_bounds", (self.canvas_paint, self.canvas_bounds),
                           "no radial-gradient canvas paint and, when supplied, positive-size four-value canvas bounds",
                           owner=f"SceneSurface({_brief(self.surface_id)})")
        by_id = {item.scene_id: (index, item) for index, item in enumerate(self.primitives)}
        if len(by_id) != len(self.primitives):
            duplicates = tuple(key for key in by_id if sum(item.scene_id == key for item in self.primitives) > 1)
            raise _invalid("primitives.scene_id", duplicates, "unique primitive identities", owner=f"SceneSurface({_brief(self.surface_id)})")
        if len({item.visual_role for item in self.decoration_dispositions}) != len(self.decoration_dispositions):
            duplicates = tuple(role for role in {item.visual_role for item in self.decoration_dispositions}
                               if sum(item.visual_role == role for item in self.decoration_dispositions) > 1)
            raise _invalid("decoration_dispositions.visual_role", duplicates, "one disposition per visual role", owner=f"SceneSurface({_brief(self.surface_id)})")
        lane_rows = {item.row_id: item for item in self.rows if item.row_id}
        if self.lane_mode not in (None, "lanes"):
            raise _invalid("lane_mode", self.lane_mode, "None or 'lanes'", owner=f"SceneSurface({_brief(self.surface_id)})")
        if self.lane_mode is None:
            if self.lane_members or self.lane_obstacles or self.lane_clearance is not None:
                raise _invalid("lane_members/lane_obstacles/lane_clearance", (self.lane_members, self.lane_obstacles, self.lane_clearance),
                               "empty lane facts when lane_mode is None", owner=f"SceneSurface({_brief(self.surface_id)})")
        else:
            if (not self.lane_members or not self.lane_obstacles
                    or not _finite_number(self.lane_clearance)
                    or self.lane_clearance < 0
                    or any(not isinstance(item, SceneLaneObstacle) for item in self.lane_obstacles) or any(
                    not member.row_id or member.row_id not in lane_rows
                    or lane_rows[member.row_id].lane_mark_band_block is None
                    for member in self.lane_members)):
                raise _invalid("lane_members/lane_obstacles/lane_clearance/rows", (self.lane_members, self.lane_obstacles, self.lane_clearance, self.rows),
                               "non-empty typed lane facts, finite non-negative clearance, and member rows with lane bands",
                               owner=f"SceneSurface({_brief(self.surface_id)})")
            if (len(lane_rows) != len(self.rows)
                    or any(row.lane_mark_band_block is None for row in self.rows)):
                raise _invalid("rows.lane_mark_band_block", tuple((row.row_id, row.lane_mark_band_block) for row in self.rows),
                               "a lane mark band for every row in lane mode", owner=f"SceneSurface({_brief(self.surface_id)})")
            member_keys = [(member.row_id, member.member_id) for member in self.lane_members]
            emitted_ids = [primitive_id for member in self.lane_members
                           for primitive_id in member.emitted_primitive_ids]
            if len(set(member_keys)) != len(member_keys) or len(set(emitted_ids)) != len(emitted_ids):
                raise _invalid("lane_members.row_id/member_id/emitted_primitive_ids", (member_keys, emitted_ids),
                               "unique (row, member) keys and unique emitted primitive IDs", owner=f"SceneSurface({_brief(self.surface_id)})")
            if {row_id for row_id, _member_id in member_keys} != set(lane_rows):
                raise _invalid("lane_members.row_id", tuple(sorted({row_id for row_id, _ in member_keys})),
                               f"exactly the row IDs {tuple(sorted(lane_rows))!r}", owner=f"SceneSurface({_brief(self.surface_id)})")
            expected = {primitive_id: (member.row_id, member.member_id)
                        for member in self.lane_members
                        for primitive_id in member.emitted_primitive_ids}
            tagged = {item.scene_id: (item.lane_row_id, item.lane_member_id)
                      for item in self.primitives if item.lane_row_id is not None}
            if expected != tagged or any(
                    primitive_id not in by_id for primitive_id in expected):
                raise _invalid("lane_members.emitted_primitive_ids/lane_row_id/lane_member_id", (tuple(expected.items()), tuple(tagged.items())),
                               "emitted IDs to match primitive lane tags and all IDs to exist in primitives",
                               owner=f"SceneSurface({_brief(self.surface_id)})")
            primary_ids = {primitive_id for member in self.lane_members
                           for primitive_id in member.primary_mark_ids}
            if any(by_id[primitive_id][1].purpose not in PRIMARY_LANE_MARK_PURPOSES
                   for primitive_id in primary_ids):
                bad_primary = tuple((primitive_id, by_id[primitive_id][1].purpose) for primitive_id in primary_ids
                                    if by_id[primitive_id][1].purpose not in PRIMARY_LANE_MARK_PURPOSES)
                raise _invalid("lane_members.primary_mark_ids", bad_primary, f"mark purposes in {tuple(sorted(PRIMARY_LANE_MARK_PURPOSES))!r}",
                               owner=f"SceneSurface({_brief(self.surface_id)})")
            if any(requires_lane_member_provenance(item.kind, item.purpose)
                   and item.lane_row_id is None for item in self.primitives):
                missing = tuple(item.scene_id for item in self.primitives
                                if requires_lane_member_provenance(item.kind, item.purpose) and item.lane_row_id is None)
                raise _invalid("primitives.lane_row_id/lane_member_id", missing,
                               "lane ownership tags for every lane-member semantic", owner=f"SceneSurface({_brief(self.surface_id)})")
            obstacle_facets = [item.facet_id for item in self.lane_obstacles]
            obstacle_owners: dict[str, tuple[str, str]] = {}
            for obstacle in self.lane_obstacles:
                if obstacle.primitive_id in obstacle_owners and obstacle_owners[obstacle.primitive_id] != (
                        obstacle.row_id, obstacle.member_id):
                    raise _invalid("lane_obstacles.primitive_id/row_id/member_id", (obstacle.primitive_id, obstacle.row_id, obstacle.member_id),
                                   f"one owner per obstacle primitive; existing owner {_brief(obstacle_owners.get(obstacle.primitive_id))}",
                                   owner=f"SceneSurface({_brief(self.surface_id)})")
                obstacle_owners[obstacle.primitive_id] = (obstacle.row_id, obstacle.member_id)
                if expected.get(obstacle.primitive_id) != (obstacle.row_id, obstacle.member_id):
                    raise _invalid("lane_obstacles.primitive_id/row_id/member_id", (obstacle.primitive_id, obstacle.row_id, obstacle.member_id),
                                   f"owner matching lane member {_brief(expected.get(obstacle.primitive_id))}",
                                   owner=f"SceneSurface({_brief(self.surface_id)})")
            if (len(set(obstacle_facets)) != len(obstacle_facets)
                    or set(obstacle_owners) != set(expected)):
                raise _invalid("lane_obstacles.facet_id/primitive_id", (tuple(obstacle_facets), tuple(obstacle_owners)),
                               "unique facet IDs and one obstacle owner for each emitted primitive",
                               owner=f"SceneSurface({_brief(self.surface_id)})")
        followers = [item for item in self.primitives if item.text_layout is not None
                     and item.text_layout.fit is not None and item.text_layout.fit.mode == BOX_FOLLOWS_TEXT]
        if ({item.text_layout.fit.box_id for item in followers} != {
                item.scene_id for item in self.primitives if item.viewer_fit == BOX_FOLLOWS_TEXT}
                or len({item.text_layout.fit.box_id for item in followers}) != len(followers)):
            # A box that follows its text and that text name each other, one to one (#1050).
            raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: SceneSurface({_brief(self.surface_id)}).viewer_fit; expected one-to-one reciprocal box/text IDs for box-follows-text; found box_ids={_brief(tuple(item.scene_id for item in self.primitives if item.viewer_fit == BOX_FOLLOWS_TEXT))}, text_box_ids={_brief(tuple(item.text_layout.fit.box_id for item in followers))}")
        for index, item in enumerate(self.primitives):
            if item.lane_row_id is not None:
                row = lane_rows.get(item.lane_row_id)
                if row is None or row.lane_mark_band_block is None:
                    raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: primitive {_brief(item.scene_id)} lane_row_id; expected a SceneRow with lane_mark_band_block; found {_brief(item.lane_row_id)}")
            if item.host_placement_id is not None:
                host = by_id.get(item.host_placement_id)
                if (item.kind != "Text" or host is None or host[1].slot_id != item.slot_id
                        or host[1].paint_order >= item.paint_order):
                    raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: primitive {_brief(item.scene_id)} host_placement_id; expected an earlier same-slot non-text host; found host={_brief(item.host_placement_id)}, kind={_brief(item.kind)}, slot={_brief(item.slot_id)}, paint_order={_brief(item.paint_order)}, host_found={_brief(host[1].scene_id if host else None)}, host_slot={_brief(host[1].slot_id if host else None)}, host_order={_brief(host[1].paint_order if host else None)}")
            if item.clip_source_id is None:
                continue
            source = by_id.get(item.clip_source_id)
            if (source is None or source[1].paint_order > item.paint_order
                    or (source[1].paint_order == item.paint_order and source[0] >= index)
                    or source[1].kind not in {"Rect", "Symbol"}
                    or (source[1].kind == "Symbol" and source[1].symbol is None)
                    or source[1].slot_id != item.slot_id):
                raise ValueError(f"E_PRESENTATION_PRIMITIVE_INVALID: primitive {_brief(item.scene_id)} clip_source_id; expected an earlier-or-equal Rect/Symbol source in the same slot; found source={_brief(item.clip_source_id)}, paint_order={_brief(item.paint_order)}, source_kind={_brief(source[1].kind if source else None)}, source_slot={_brief(source[1].slot_id if source else None)}, item_slot={_brief(item.slot_id)}")


@dataclass(frozen=True)
class SceneProvenance:
    """Immutable render closure evidence for an inspection-only Scene."""

    mode: str
    chrona_version: str
    resources: tuple[tuple[str, str, str, str], ...]


@dataclass(frozen=True)
class InspectionScene:
    """The one completed runtime Scene exposed to adapters and inspection tooling."""

    provenance: SceneProvenance
    viewport: tuple[float, float]
    required_capabilities: tuple[str, ...]
    surfaces: tuple[SceneSurface, ...]
    manifest: SceneManifest
    diagnostics: tuple[str, ...]
    font_warnings: tuple[FontTabularWarning, ...] = ()
