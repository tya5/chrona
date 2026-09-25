"""Finite completed-Scene contrast policy; no renderer or Theme re-resolution."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping

from chrona.presentation.model.semantic_registry import ContrastClass, contrast_binding
from chrona.presentation.scene.paint_analysis import composited_contrast, is_hex_color


DECORATION_FLOOR = 1.10
STATE_TEXT_FLOORS = {"required": 4.5, "deemphasized": 3.0}


class SceneContrastPolicyError(ValueError):
    """Stable diagnostic for an incomplete completed-Scene policy input."""


@dataclass(frozen=True)
class SceneContrastFinding:
    """One deterministic classified-paint observation or policy failure."""

    code: str
    severity: str
    scene_path: str
    purpose: str
    visual_role: str
    primitive_id: str | None
    contrast_ratio: float | None
    floor: float | None
    disposition: str

    def as_mapping(self) -> dict[str, Any]:
        return {
            "code": self.code, "severity": self.severity, "scenePath": self.scene_path,
            "purpose": self.purpose, "visualRole": self.visual_role,
            "primitiveId": self.primitive_id, "contrastRatio": self.contrast_ratio,
            "floor": self.floor, "disposition": self.disposition,
        }


def evaluate_scene_contrast(document: Mapping[str, Any]) -> tuple[SceneContrastFinding, ...]:
    """Evaluate every finite classified role from serialized completed facts."""
    _require(document.get("version") == "chrona/scene/v0.6", "unsupported scene version")
    _require(document.get("kind") == "scene", "invalid scene kind")
    surfaces = document.get("surfaces")
    _require(isinstance(surfaces, list) and surfaces, "scene has no surfaces")
    findings: list[SceneContrastFinding] = []
    for surface_index, raw_surface in enumerate(surfaces):
        _require(isinstance(raw_surface, Mapping), f"invalid surface {surface_index}")
        surface_id = _string(raw_surface.get("id"), f"surface {surface_index} id")
        scene_path = f"/surfaces/{surface_index}:{surface_id}"
        canvas = raw_surface.get("canvasPaint")
        ground = _ground(canvas, scene_path)
        primitives = raw_surface.get("primitives")
        _require(isinstance(primitives, list), f"missing primitives at {scene_path}")
        for index, primitive in enumerate(primitives):
            _require(isinstance(primitive, Mapping), f"invalid primitive {index} at {scene_path}")
            findings.extend(_primitive_findings(scene_path, primitive, ground))
        findings.extend(_absence_findings(scene_path, raw_surface.get("decorationDispositions", [])))
    return tuple(sorted(findings, key=lambda item: (
        item.scene_path, item.purpose, item.visual_role, item.disposition, item.primitive_id or "", item.code,
    )))


def _primitive_findings(scene_path: str, primitive: Mapping[str, Any], ground: str | None) -> tuple[SceneContrastFinding, ...]:
    role = primitive.get("visualRole")
    if not isinstance(role, str):
        return ()
    binding = contrast_binding(role)
    if binding is None:
        return ()
    primitive_id = _string(primitive.get("id"), f"primitive id at {scene_path}")
    purpose = _string(primitive.get("purpose"), f"primitive purpose at {scene_path}")
    if binding.contrast_class == ContrastClass.DECORATION:
        floor, disposition = DECORATION_FLOOR, "enabled"
        code = "E_SCENE_DECORATION_CONTRAST"
    else:
        treatment = primitive.get("contrastTreatment")
        if treatment not in STATE_TEXT_FLOORS:
            return (SceneContrastFinding("E_SCENE_STATE_TEXT_CONTRAST_TREATMENT", "error", scene_path,
                                         purpose, role, primitive_id, None, None, "invalid-treatment"),)
        floor, disposition = STATE_TEXT_FLOORS[treatment], treatment
        code = "E_SCENE_STATE_TEXT_CONTRAST"
    if ground is None:
        return (SceneContrastFinding("E_SCENE_CONTRAST_GROUND", "error", scene_path, purpose, role,
                                     primitive_id, None, floor, disposition),)
    paint = primitive.get("paint")
    if not isinstance(paint, Mapping):
        return (SceneContrastFinding("E_SCENE_CONTRAST_PAINT", "error", scene_path, purpose, role,
                                     primitive_id, None, floor, disposition),)
    color = paint.get("fill") if binding.contrast_class == ContrastClass.STATE_TEXT else (paint.get("fill") or paint.get("stroke"))
    opacity = paint.get("opacity", 1.0)
    if not is_hex_color(color) or not _opacity(opacity):
        return (SceneContrastFinding("E_SCENE_CONTRAST_PAINT", "error", scene_path, purpose, role,
                                     primitive_id, None, floor, disposition),)
    ratio = composited_contrast(fill=color, opacity=float(opacity), ground=ground)
    severity = "error" if ratio < floor else "info"
    return (SceneContrastFinding(code, severity, scene_path, purpose, role, primitive_id, ratio, floor, disposition),)


def _absence_findings(scene_path: str, raw: Any) -> tuple[SceneContrastFinding, ...]:
    _require(isinstance(raw, list), f"invalid decoration dispositions at {scene_path}")
    findings: list[SceneContrastFinding] = []
    for index, item in enumerate(raw):
        _require(isinstance(item, Mapping), f"invalid decoration disposition {index} at {scene_path}")
        role = _string(item.get("visualRole"), f"decoration role {index} at {scene_path}")
        binding = contrast_binding(role)
        _require(binding is not None and binding.contrast_class == ContrastClass.DECORATION,
                 f"unclassified decoration role {role} at {scene_path}")
        _require(item.get("disposition") == "absent", f"invalid decoration disposition {role} at {scene_path}")
        findings.append(SceneContrastFinding("I_SCENE_DECORATION_ABSENT", "info", scene_path,
                                             binding.purpose, role, None, None, DECORATION_FLOOR, "absent"))
    return tuple(findings)


def _ground(canvas: Any, scene_path: str) -> str | None:
    if not isinstance(canvas, Mapping) or not is_hex_color(canvas.get("fill")) or canvas.get("opacity", 1.0) != 1:
        return None
    return str(canvas["fill"])


def _opacity(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and isfinite(float(value)) and 0 <= float(value) <= 1


def _string(value: Any, detail: str) -> str:
    _require(isinstance(value, str) and value, f"invalid {detail}")
    return value


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise SceneContrastPolicyError("E_SCENE_CONTRAST_DOCUMENT: " + detail)
