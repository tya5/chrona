"""Pure perceptibility observations over serialized completed Scene mappings."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping, Sequence

from chrona.presentation.scene.paint_analysis import composited_contrast, is_hex_color


MICRO_POINT_TOLERANCE = 0.001
TEXT_INTERSECTION_AREA = 4.0
OCCLUSION_RATIO = 0.5


class ScenePerceptibilityError(ValueError):
    """A mapping is not a complete scene-v0.6 document for observation."""


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
    """Evaluate serialized scene-v0.6 facts without measuring or changing them."""
    _require(document.get("version") == "chrona/scene/v0.6", "unsupported scene version")
    _require(document.get("kind") == "scene", "invalid scene kind")
    surfaces = _list(document.get("surfaces"), "surfaces")
    _require(bool(surfaces), "scene has no surfaces")
    findings: list[ScenePerceptibilityFinding] = []
    for surface_index, raw_surface in enumerate(surfaces):
        surface = _mapping(raw_surface, f"surfaces[{surface_index}]")
        surface_id = _string(surface.get("id"), f"surfaces[{surface_index}].id")
        scene_path = f"/surfaces/{surface_index}:{surface_id}"
        slots = _slots(surface.get("slots"), scene_path)
        primitives = _primitives(surface.get("primitives"), scene_path)
        findings.extend(_slot_findings(scene_path, slots, primitives))
        findings.extend(_occlusion_findings(scene_path, primitives))
        findings.extend(_text_intersection_findings(scene_path, primitives))
        findings.extend(_paint_findings(scene_path, surface, primitives))
    return tuple(sorted(findings, key=lambda item: (item.scene_path, item.code, item.primitive_ids)))


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
        primitives.append(_Primitive(index, primitive_id, kind, slot_id,
                                     _rect(primitive.get("bounds"), f"{scene_path}.primitives[{index}].bounds"),
                                     paint_order, host, paint))
    return tuple(primitives)


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
            if rect.kind != "Rect" or not rect.bounds.positive_area or not _later(rect, text) or not _opaque_fill(rect.paint):
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
            area = _intersection(first.bounds, second.bounds)
            if area <= TEXT_INTERSECTION_AREA + MICRO_POINT_TOLERANCE:
                continue
            ids = tuple(sorted((first.primitive_id, second.primitive_id)))
            findings.append(_finding("E_SCENE_TEXT_INTERSECTION", "error", scene_path, ids, None,
                                     (("area", area), ("threshold", TEXT_INTERSECTION_AREA))))
    return findings


def _paint_findings(scene_path: str, surface: Mapping[str, Any], primitives: Sequence[_Primitive]) -> list[ScenePerceptibilityFinding]:
    canvas = surface.get("canvasPaint")
    if not isinstance(canvas, Mapping) or not is_hex_color(canvas.get("fill")):
        return []
    ground_opacity = _opacity(canvas)
    if ground_opacity != 1.0:
        return []
    findings: list[ScenePerceptibilityFinding] = []
    for item in primitives:
        if not item.bounds.positive_area or not isinstance(item.paint, Mapping) or not is_hex_color(item.paint.get("fill")):
            continue
        ratio = composited_contrast(fill=str(item.paint["fill"]), opacity=_opacity(item.paint), ground=str(canvas["fill"]))
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
