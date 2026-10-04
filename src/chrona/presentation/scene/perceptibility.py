"""Pure perceptibility observations over serialized completed Scene mappings."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping, Sequence

from chrona.presentation.layout.obstacles import ObstacleRect, ObstacleSegment, segment_length_inside_rect
from chrona.presentation.layout.path_geometry import flatten_corner
from chrona.presentation.model.semantic_registry import axis_band_semantic_ids, semantic_binding
from chrona.presentation.scene.paint_analysis import composited_contrast, is_hex_color


MICRO_POINT_TOLERANCE = 0.001
TEXT_INTERSECTION_AREA = 4.0
OCCLUSION_RATIO = 0.5
# A chamfered axis cell (#491) is a Symbol outline inside its bounds; it grounds text as a band Rect does.
_BAND_CELL_ROLES = frozenset(semantic_binding(identifier).scene_role for identifier in axis_band_semantic_ids())


class ScenePerceptibilityError(ValueError):
    """A mapping is not a complete supported Scene document for observation."""


@dataclass(frozen=True)
class ScenePerceptibilityFinding:
    """One stable, renderer-neutral observation over published Scene facts."""

    version: str
    code: str
    severity: str
    scene_path: str
    primitive_ids: tuple[str, ...]
    slot_id: str | None
    measured_facts: tuple[tuple[str, float | str], ...]
    disposition: str | None = None

    def as_mapping(self) -> dict[str, Any]:
        """Return the shared transport representation for tools and draft feedback."""
        result: dict[str, Any] = {
            "version": self.version,
            "code": self.code,
            "severity": self.severity,
            "scenePath": self.scene_path,
            "primitiveIds": list(self.primitive_ids),
            "measuredFacts": dict(self.measured_facts),
        }
        if self.slot_id is not None:
            result["slotId"] = self.slot_id
        if self.disposition is not None:
            result["disposition"] = self.disposition
        return result


def evaluate_scene_perceptibility(document: Mapping[str, Any]) -> tuple[ScenePerceptibilityFinding, ...]:
    """Evaluate serialized completed Scene facts without measuring or changing them."""
    version = document.get("version")
    _require(version == "chrona/scene/v0.6" or version == "chrona/scene/v0.7",
             "unsupported scene version")
    _require(document.get("kind") == "scene", "invalid scene kind")
    surfaces = _list(document.get("surfaces"), "surfaces")
    _require(bool(surfaces), "scene has no surfaces")
    findings: list[ScenePerceptibilityFinding] = []
    diagnostics = document.get("diagnostics", [])
    _require(isinstance(diagnostics, list), "invalid scene diagnostics")
    suppressed_ids: set[str] = set()
    for diagnostic in diagnostics:
        _require(isinstance(diagnostic, str), "invalid scene diagnostic")
        if diagnostic.startswith("W_LAYOUT_LABEL_SUPPRESSED:"):
            suppressed_ids.add(diagnostic.removeprefix("W_LAYOUT_LABEL_SUPPRESSED:"))
        elif diagnostic.startswith("W_LAYOUT_RELATION_LABEL_SUPPRESSED:relation:"):
            suppressed_ids.add("relation-label:" + diagnostic.removeprefix("W_LAYOUT_RELATION_LABEL_SUPPRESSED:relation:"))
        elif diagnostic.startswith("W_LAYOUT_RELATION_SUPPRESSED:"):
            suppressed_ids.add(diagnostic.removeprefix("W_LAYOUT_RELATION_SUPPRESSED:"))
    for surface_index, raw_surface in enumerate(surfaces):
        surface = _mapping(raw_surface, f"surfaces[{surface_index}]")
        surface_id = _string(surface.get("id"), f"surfaces[{surface_index}].id")
        scene_path = f"/surfaces/{surface_index}:{surface_id}"
        slots = _slots(surface.get("slots"), scene_path)
        primitives = _primitives(surface.get("primitives"), scene_path)
        findings.extend(_suppressed_primitive_findings(scene_path, primitives, suppressed_ids))
        findings.extend(_relation_duplicate_findings(scene_path, surface.get("primitives")))
        findings.extend(_relation_reversal_findings(scene_path, surface.get("primitives")))
        findings.extend(_relation_mark_findings(scene_path, surface.get("primitives")))
        findings.extend(_slot_findings(scene_path, slots, primitives))
        findings.extend(_occlusion_findings(scene_path, primitives))
        findings.extend(_text_intersection_findings(scene_path, primitives))
        findings.extend(_paint_findings(scene_path, surface, primitives,
                                        catalog_patterns=version == "chrona/scene/v0.7"))
    return tuple(sorted(findings, key=lambda item: (item.scene_path, item.code, item.primitive_ids)))


def _suppressed_primitive_findings(scene_path: str, primitives: Sequence[_Primitive],
                                   suppressed_ids: set[str]) -> list[ScenePerceptibilityFinding]:
    return [_finding("E_SCENE_SUPPRESSED_PRIMITIVE_EMITTED", "error", scene_path,
                     (item.primitive_id,), item.slot_id, (), "suppressed")
            for item in primitives if item.primitive_id in suppressed_ids]


def _relation_duplicate_findings(scene_path: str, raw_primitives: Any) -> list[ScenePerceptibilityFinding]:
    """A relation is drawn once: two paths for one relation id are a duplication, never silent (#1031).

    Only relation placements (`relation:` ids) count; the legend's dependency swatch shares the source kind.
    """
    paths: dict[str, list[str]] = {}
    for raw in raw_primitives if isinstance(raw_primitives, list) else ():
        if (isinstance(raw, Mapping) and raw.get("kind") == "Path" and raw.get("sourceKind") == "relation"
                and isinstance(raw.get("sourceRef"), str) and str(raw.get("id")).startswith("relation:")):
            paths.setdefault(raw["sourceRef"], []).append(raw["id"])
    return [_finding("E_SCENE_RELATION_PATH_DUPLICATE", "error", scene_path, tuple(ids), None,
                     (("relation", relation), ("paths", len(ids))))
            for relation, ids in sorted(paths.items()) if len(ids) > 1]


def _relation_reversal_findings(scene_path: str, raw_primitives: Any) -> list[ScenePerceptibilityFinding]:
    """A relation path never overlaps itself: a reversal leaves a tail behind the arrowhead (#1059)."""
    findings = []
    for raw in raw_primitives if isinstance(raw_primitives, list) else ():
        if not (isinstance(raw, Mapping) and raw.get("kind") == "Path" and raw.get("sourceKind") == "relation"
                and str(raw.get("id")).startswith("relation:") and isinstance(raw.get("points"), list)):
            continue
        points = [tuple(point) for point in raw["points"]
                  if isinstance(point, (list, tuple)) and len(point) == 2
                  and all(isinstance(value, (int, float)) for value in point)]
        segments = [(a, b) for a, b in zip(points, points[1:]) if a != b]
        overlap = 0.0
        for index, (a, b) in enumerate(segments):
            for c, d in segments[index + 1:]:
                if a[1] == b[1] == c[1] == d[1]:
                    span = min(max(a[0], b[0]), max(c[0], d[0])) - max(min(a[0], b[0]), min(c[0], d[0]))
                elif a[0] == b[0] == c[0] == d[0]:
                    span = min(max(a[1], b[1]), max(c[1], d[1])) - max(min(a[1], b[1]), min(c[1], d[1]))
                else:
                    continue
                overlap = max(overlap, span)
        if overlap > 1e-6:
            findings.append(_finding("E_SCENE_RELATION_PATH_REVERSES", "error", scene_path, (str(raw["id"]),), None,
                                     (("relation", str(raw.get("sourceRef"))), ("overlap", round(overlap, 3)))))
    return findings


def _relation_mark_findings(scene_path: str, raw_primitives: Any) -> list[ScenePerceptibilityFinding]:
    """Observe completed relation strokes crossing planned primary-mark interiors."""
    primitives = raw_primitives if isinstance(raw_primitives, list) else ()
    marks = [raw for raw in primitives if isinstance(raw, Mapping)
             and str(raw.get("id", "")).startswith("planned:")
             and ":snapshot:" not in str(raw["id"]) and ":scenario:" not in str(raw["id"])
             and isinstance(raw.get("bounds"), Mapping)]
    findings = []
    for raw in primitives:
        if not (isinstance(raw, Mapping) and raw.get("kind") == "Path" and raw.get("sourceKind") == "relation"
                and str(raw.get("id", "")).startswith("relation:") and isinstance(raw.get("points"), list)):
            continue
        paint = raw.get("paint", {})
        width = paint.get("strokeWidth", 0) if isinstance(paint, Mapping) else 0.0
        _require(isinstance(width, (int, float)) and not isinstance(width, bool) and isfinite(width) and width >= 0,
                 "invalid relation stroke width")
        inset = width / 2
        points = _observed_relation_points(raw)
        for mark in marks:
            bounds = mark["bounds"]
            if bounds["inlineSize"] <= width or bounds["blockSize"] <= width:
                continue
            rect = ObstacleRect(bounds["inline"] + inset, bounds["block"] + inset,
                                bounds["inline"] + bounds["inlineSize"] - inset,
                                bounds["block"] + bounds["blockSize"] - inset)
            length = sum(segment_length_inside_rect(ObstacleSegment(tuple(a), tuple(b)), rect)
                         for a, b in zip(points, points[1:]) if a != b)
            if length > 1e-9:
                findings.append(_finding("E_SCENE_RELATION_THROUGH_MARK", "error", scene_path,
                    (str(raw["id"]), str(mark["id"])), None,
                    (("relation", str(raw.get("sourceRef"))), ("inside", round(length, 3)))))
    return findings


def _observed_relation_points(raw: Mapping[str, Any]) -> list[tuple[float, float]]:
    """Use drawn path commands when present, not only the orthogonal control polyline."""
    def point(value: Any) -> tuple[float, float]:
        _require(isinstance(value, (list, tuple)) and len(value) == 2 and all(
            isinstance(x, (int, float)) and not isinstance(x, bool) and isfinite(x) for x in value),
            "invalid relation point")
        return tuple(value)

    commands = raw.get("pathCommands")
    if not commands:
        return [point(p) for p in raw["points"]]
    _require(isinstance(commands, list), "invalid relation commands")
    points: list[tuple[float, float]] = []
    start = None
    for raw_command in commands:
        command = _mapping(raw_command, "relation command")
        kind = command.get("kind")
        values = [point(p) for p in _list(command.get("points"), "relation command points")]
        count = {"move": 1, "line": 1, "quadratic": 2, "cubic": 3, "close": 0}.get(kind)
        _require(count is not None and len(values) == count and (kind == "move" or bool(points)),
                 "invalid relation command")
        if kind == "move":
            _require(not points, "a relation must have one continuous path")
            start = values[0]
            points.append(start)
        elif kind == "line":
            points.append(values[0])
        elif kind == "quadratic":
            points.extend(flatten_corner(points[-1], *values)[1:])
        elif kind == "cubic":
            a, b, c, d = points[-1], *values
            for step in range(1, 5):
                t = step / 4
                points.append(tuple((1-t)**3*a[i] + 3*(1-t)**2*t*b[i]
                                    + 3*(1-t)*t*t*c[i] + t**3*d[i] for i in (0, 1)))
        elif points[-1] != start:
            points.append(start)
    return points


def _slots(raw_slots: Any, scene_path: str) -> dict[str, tuple[Rect, str]]:
    slots: dict[str, tuple[Rect, str]] = {}
    for index, raw_slot in enumerate(_list(raw_slots, f"{scene_path}.slots")):
        slot = _mapping(raw_slot, f"{scene_path}.slots[{index}]")
        slot_id = _string(slot.get("id"), f"{scene_path}.slots[{index}].id")
        _require(slot_id not in slots, f"duplicate slot {slot_id}")
        overflow = _string(slot.get("overflow"), f"{scene_path}.slots[{index}].overflow")
        slots[slot_id] = (_rect(slot.get("bounds"), f"{scene_path}.slots[{index}].bounds"), overflow)
    return slots


@dataclass(frozen=True)
class _Primitive:
    index: int
    primitive_id: str
    kind: str
    slot_id: str
    bounds: "Rect"
    paint_order: int
    host_placement_id: str | None
    paint: Mapping[str, Any] | None
    pattern: Mapping[str, Any] | None
    visual_role: str | None = None
    # (source ref) of a tilted text run (#584): the lines of one rigid, tilted note never overlap by construction,
    # but the axis-aligned bounds of two rotated neighbouring lines do.
    tilted_source: str | None = None


@dataclass(frozen=True)
class Rect:
    inline: float
    block: float
    inline_size: float
    block_size: float

    @property
    def positive_area(self) -> bool:
        return self.inline_size > 0 and self.block_size > 0

    @property
    def area(self) -> float:
        return self.inline_size * self.block_size


def _primitives(raw_primitives: Any, scene_path: str) -> tuple[_Primitive, ...]:
    primitives: list[_Primitive] = []
    ids: set[str] = set()
    for index, raw_primitive in enumerate(_list(raw_primitives, f"{scene_path}.primitives")):
        primitive = _mapping(raw_primitive, f"{scene_path}.primitives[{index}]")
        primitive_id = _string(primitive.get("id"), f"{scene_path}.primitives[{index}].id")
        _require(primitive_id not in ids, f"duplicate primitive {primitive_id}")
        ids.add(primitive_id)
        kind = _string(primitive.get("kind"), f"{scene_path}.primitives[{index}].kind")
        slot_id = _string(primitive.get("slotId"), f"{scene_path}.primitives[{index}].slotId")
        paint_order = primitive.get("paintOrder", 0)
        _require(isinstance(paint_order, int) and paint_order >= 0, f"invalid paint order for {primitive_id}")
        host = primitive.get("hostPlacementId")
        _require(host is None or isinstance(host, str), f"invalid host relation for {primitive_id}")
        paint = primitive.get("paint")
        _require(paint is None or isinstance(paint, Mapping), f"invalid paint for {primitive_id}")
        pattern = primitive.get("pattern")
        _require(pattern is None or isinstance(pattern, Mapping), f"invalid pattern for {primitive_id}")
        primitives.append(_Primitive(index, primitive_id, kind, slot_id,
                                     _rect(primitive.get("bounds"), f"{scene_path}.primitives[{index}].bounds"),
                                     paint_order, host, paint, pattern,
                                     primitive.get("visualRole") if isinstance(primitive.get("visualRole"), str) else None,
                                     _tilted_source(primitive)))
    return tuple(primitives)


def _tilted_source(primitive: Mapping[str, Any]) -> str | None:
    layout = primitive.get("textLayout")
    source = primitive.get("sourceRef")
    if isinstance(layout, Mapping) and layout.get("orientation") == "tilt" and isinstance(source, str):
        return source
    return None


def _slot_findings(scene_path: str, slots: Mapping[str, tuple[Rect, str]], primitives: Sequence[_Primitive]) -> list[ScenePerceptibilityFinding]:
    findings: list[ScenePerceptibilityFinding] = []
    for item in primitives:
        if item.kind != "Text" or not item.bounds.positive_area:
            continue
        _require(item.slot_id in slots, f"unknown slot {item.slot_id} for {item.primitive_id}")
        slot, overflow = slots[item.slot_id]
        excess = _excess(item.bounds, slot)
        if excess <= MICRO_POINT_TOLERANCE or overflow == "suppressed":
            continue
        facts = (("excess", excess), ("tolerance", MICRO_POINT_TOLERANCE))
        if overflow == "visible-overflow":
            findings.append(_finding("I_SCENE_DECLARED_VISIBLE_OVERFLOW", "info", scene_path, (item.primitive_id,),
                                     item.slot_id, facts, overflow))
        else:
            findings.append(_finding("E_SCENE_TEXT_SLOT_ESCAPE", "error", scene_path, (item.primitive_id,),
                                     item.slot_id, facts, overflow))
    return findings


def _occlusion_findings(scene_path: str, primitives: Sequence[_Primitive]) -> list[ScenePerceptibilityFinding]:
    findings: list[ScenePerceptibilityFinding] = []
    for text in primitives:
        if text.kind != "Text" or not text.bounds.positive_area:
            continue
        for rect in primitives:
            ground = rect.kind == "Rect" or (rect.kind == "Symbol" and rect.visual_role in _BAND_CELL_ROLES)
            if not ground or not rect.bounds.positive_area or not _later(rect, text) or not _opaque_fill(rect.paint):
                continue
            ratio = _intersection(text.bounds, rect.bounds) / text.bounds.area
            if ratio < OCCLUSION_RATIO:
                continue
            if text.host_placement_id == rect.primitive_id:
                findings.append(_finding("I_SCENE_HOSTED_TEXT_OVERLAP", "info", scene_path,
                                         (text.primitive_id, rect.primitive_id), text.slot_id,
                                         (("coverageRatio", ratio), ("threshold", OCCLUSION_RATIO))))
            else:
                findings.append(_finding("E_SCENE_TEXT_OCCLUDED", "error", scene_path,
                                         (text.primitive_id, rect.primitive_id), text.slot_id,
                                         (("coverageRatio", ratio), ("threshold", OCCLUSION_RATIO))))
    return findings


def _text_intersection_findings(scene_path: str, primitives: Sequence[_Primitive]) -> list[ScenePerceptibilityFinding]:
    findings: list[ScenePerceptibilityFinding] = []
    texts = tuple(item for item in primitives if item.kind == "Text" and item.bounds.positive_area)
    for first_index, first in enumerate(texts):
        for second in texts[first_index + 1:]:
            if first.tilted_source is not None and first.tilted_source == second.tilted_source:
                continue
            area = _intersection(first.bounds, second.bounds)
            if area <= TEXT_INTERSECTION_AREA + MICRO_POINT_TOLERANCE:
                continue
            ids = tuple(sorted((first.primitive_id, second.primitive_id)))
            findings.append(_finding("E_SCENE_TEXT_INTERSECTION", "error", scene_path, ids, None,
                                     (("area", area), ("threshold", TEXT_INTERSECTION_AREA))))
    return findings


def _paint_findings(scene_path: str, surface: Mapping[str, Any], primitives: Sequence[_Primitive], *,
                    catalog_patterns: bool = False) -> list[ScenePerceptibilityFinding]:
    findings: list[ScenePerceptibilityFinding] = []
    if catalog_patterns:
        for item in primitives:
            pattern, paint = item.pattern, item.paint
            is_catalog = isinstance(pattern, Mapping) and any(
                key in pattern for key in ("densityBasisPoints", "primitives", "origin", "regionBounds", "clipBounds"))
            if not is_catalog:
                continue
            density = pattern.get("densityBasisPoints")
            _require(isinstance(density, int) and not isinstance(density, bool) and 1 <= density <= 10000,
                     f"invalid catalogue pattern density for {item.primitive_id}")
            _require(isinstance(paint, Mapping) and _opacity(paint) == 1.0
                     and is_hex_color(paint.get("fill")) and is_hex_color(paint.get("stroke")),
                     f"invalid catalogue pattern channels for {item.primitive_id}")
            tile_inline, tile_block, angle = (pattern.get(key) for key in
                                               ("tileInlineSize", "tileBlockSize", "angleDegrees"))
            _require(_positive_finite(tile_inline) and _positive_finite(tile_block) and _finite(angle),
                     f"invalid catalogue pattern geometry for {item.primitive_id}")
            facts: tuple[tuple[str, float | str], ...] = (
                ("substrate", str(paint["fill"])), ("ink", str(paint["stroke"])),
                ("densityBasisPoints", float(density)), ("tileInlineSize", float(tile_inline)),
                ("tileBlockSize", float(tile_block)), ("angleDegrees", float(angle)),
            )
            origin = pattern.get("origin")
            _require(isinstance(origin, list) and len(origin) == 2 and all(_finite(value) for value in origin),
                     f"invalid catalogue pattern origin for {item.primitive_id}")
            facts += (("originInline", float(origin[0])), ("originBlock", float(origin[1])))
            for key, labels in (("regionBounds", ("regionInline", "regionBlock", "regionInlineSize", "regionBlockSize")),
                                ("clipBounds", ("clipInline", "clipBlock", "clipInlineSize", "clipBlockSize"))):
                bounds = pattern.get(key)
                _require(isinstance(bounds, Mapping), f"invalid catalogue pattern {key} for {item.primitive_id}")
                coordinates = tuple(bounds.get(name) for name in ("inline", "block", "inlineSize", "blockSize"))
                _require(all(_finite(value) for value in coordinates),
                         f"invalid catalogue pattern {key} for {item.primitive_id}")
                facts += tuple((label, float(value)) for label, value in zip(labels, coordinates))
            corner_radius = pattern.get("cornerRadius")
            _require(_finite(corner_radius) and float(corner_radius) >= 0,
                     f"invalid catalogue pattern corner radius for {item.primitive_id}")
            facts += (("cornerRadius", float(corner_radius)),)
            findings.append(_finding("I_SCENE_PATTERN_PERCEPTIBILITY", "info", scene_path,
                                     (item.primitive_id,), item.slot_id, facts, "observed"))
    canvas = surface.get("canvasPaint")
    if not isinstance(canvas, Mapping) or not is_hex_color(canvas.get("fill")):
        return findings
    ground_opacity = _opacity(canvas)
    if ground_opacity != 1.0:
        return findings
    # A canvas texture covers the canvas, so what lies on it lies on its substrate or on its ink.
    texture = next((item for item in primitives if item.visual_role == "canvas-texture"
                    and isinstance(item.paint, Mapping) and is_hex_color(item.paint.get("fill"))
                    and is_hex_color(item.paint.get("stroke"))), None)
    for item in primitives:
        if not item.bounds.positive_area or not isinstance(item.paint, Mapping) or not is_hex_color(item.paint.get("fill")):
            continue
        grounds = ((str(texture.paint["fill"]), str(texture.paint["stroke"]))
                   if texture is not None and item is not texture else (str(canvas["fill"]),))
        ratio = min(composited_contrast(fill=str(item.paint["fill"]), opacity=_opacity(item.paint), ground=ground)
                    for ground in grounds)
        findings.append(_finding("I_SCENE_PAINT_CONTRAST", "info", scene_path, (item.primitive_id,), item.slot_id,
                                 (("contrastRatio", ratio),), None))
    return findings


def _finding(code: str, severity: str, scene_path: str, primitive_ids: tuple[str, ...], slot_id: str | None,
             facts: tuple[tuple[str, float | str], ...], disposition: str | None = None) -> ScenePerceptibilityFinding:
    return ScenePerceptibilityFinding("v1", code, severity, scene_path, primitive_ids, slot_id, facts, disposition)


def _later(candidate: _Primitive, reference: _Primitive) -> bool:
    return (candidate.paint_order, candidate.index) > (reference.paint_order, reference.index)


def _opaque_fill(paint: Mapping[str, Any] | None) -> bool:
    return isinstance(paint, Mapping) and is_hex_color(paint.get("fill")) and _opacity(paint) == 1.0


def _excess(item: Rect, slot: Rect) -> float:
    return max(slot.inline - item.inline, slot.block - item.block,
               item.inline + item.inline_size - slot.inline - slot.inline_size,
               item.block + item.block_size - slot.block - slot.block_size, 0.0)


def _intersection(first: Rect, second: Rect) -> float:
    inline = max(0.0, min(first.inline + first.inline_size, second.inline + second.inline_size) - max(first.inline, second.inline))
    block = max(0.0, min(first.block + first.block_size, second.block + second.block_size) - max(first.block, second.block))
    return inline * block


def _rect(value: Any, label: str) -> Rect:
    mapping = _mapping(value, label)
    values = tuple(_number(mapping.get(name), f"{label}.{name}") for name in ("inline", "block", "inlineSize", "blockSize"))
    _require(values[2] >= 0 and values[3] >= 0, f"negative extent in {label}")
    return Rect(*values)


def _number(value: Any, label: str) -> float:
    _require(isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value)), f"invalid number {label}")
    return float(value)


def _opacity(paint: Mapping[str, Any]) -> float:
    value = paint.get("opacity", 1.0)
    _require(isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value)) and 0 <= float(value) <= 1,
             "invalid paint opacity")
    return float(value)


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value))


def _positive_finite(value: Any) -> bool:
    return _finite(value) and float(value) > 0


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    _require(isinstance(value, Mapping), f"expected mapping at {label}")
    return value


def _list(value: Any, label: str) -> list[Any]:
    _require(isinstance(value, list), f"expected list at {label}")
    return value


def _string(value: Any, label: str) -> str:
    _require(isinstance(value, str), f"expected string at {label}")
    return value


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise ScenePerceptibilityError("E_SCENE_PERCEPTIBILITY_DOCUMENT: " + detail)
