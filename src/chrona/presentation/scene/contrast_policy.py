"""Finite completed-Scene contrast policy; no renderer or Theme re-resolution."""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Mapping

from chrona.presentation.model.semantic_registry import ContrastClass, contrast_binding
from chrona.presentation.scene.paint_analysis import composited_contrast, is_hex_color, sample_linear_gradient


DECORATION_FLOOR = 1.10
MARK_FLOOR = 3.0
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
    ground_id: str | None = None
    ground_color: str | None = None
    paint_channel: str | None = None
    sample_inline: float | None = None
    sample_block: float | None = None
    ground_kind: str | None = None

    def as_mapping(self) -> dict[str, Any]:
        return {
            "code": self.code, "severity": self.severity, "scenePath": self.scene_path,
            "purpose": self.purpose, "visualRole": self.visual_role,
            "primitiveId": self.primitive_id, "contrastRatio": self.contrast_ratio,
            "floor": self.floor, "disposition": self.disposition,
            "groundId": self.ground_id, "groundColor": self.ground_color,
            "paintChannel": self.paint_channel,
            "sampleInline": self.sample_inline, "sampleBlock": self.sample_block,
            "groundKind": self.ground_kind,
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
            findings.extend(_primitive_findings(scene_path, primitive, ground, primitives, index))
        findings.extend(_absence_findings(scene_path, raw_surface.get("decorationDispositions", [])))
    return tuple(sorted(findings, key=lambda item: (
        item.scene_path, item.purpose, item.visual_role, item.disposition, item.primitive_id or "", item.code,
    )))


def _primitive_findings(scene_path: str, primitive: Mapping[str, Any], canvas: str | None,
                        primitives: list[Any], index: int) -> tuple[SceneContrastFinding, ...]:
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
    elif binding.contrast_class == ContrastClass.MARK:
        floor, disposition = MARK_FLOOR, "required"
        code = "E_SCENE_MARK_CONTRAST"
    else:
        treatment = primitive.get("contrastTreatment")
        if treatment not in STATE_TEXT_FLOORS or (role == "variance-behind" and treatment != "required"):
            return (SceneContrastFinding("E_SCENE_STATE_TEXT_CONTRAST_TREATMENT", "error", scene_path,
                                         purpose, role, primitive_id, None, None, "invalid-treatment"),)
        floor, disposition = STATE_TEXT_FLOORS[treatment], treatment
        code = "E_SCENE_STATE_TEXT_CONTRAST"
    paint = primitive.get("paint")
    if not isinstance(paint, Mapping):
        return (SceneContrastFinding("E_SCENE_CONTRAST_PAINT", "error", scene_path, purpose, role,
                                     primitive_id, None, floor, disposition),)
    opacity = paint.get("opacity", 1.0)
    if not _opacity(opacity):
        return (SceneContrastFinding("E_SCENE_CONTRAST_PAINT", "error", scene_path, purpose, role,
                                     primitive_id, None, floor, disposition),)
    channels = ("fill",) if binding.contrast_class == ContrastClass.STATE_TEXT else ("fill", "stroke")
    candidates = []
    unsupported_host: str | None = None
    for channel in channels:
        if not is_hex_color(paint.get(channel)):
            continue
        if channel == "stroke" and (not isinstance(paint.get("strokeWidth"), (int, float))
                                    or paint["strokeWidth"] <= 0):
            continue
        sample = _sample_point(primitive, channel)
        ground_id, ground, unsupported, ground_kind = _ground_under(primitive, primitives, index, canvas, sample)
        if unsupported:
            unsupported_host = ground_id
            continue
        if ground is None:
            continue
        ratio = composited_contrast(fill=paint[channel], opacity=float(opacity), ground=ground)
        candidates.append((ratio, channel, ground_id, ground, sample, ground_kind))
    if not candidates:
        error_code = "E_SCENE_CONTRAST_GROUND_UNSUPPORTED" if unsupported_host else "E_SCENE_CONTRAST_PAINT"
        return (SceneContrastFinding(error_code, "error", scene_path, purpose, role,
                                     primitive_id, None, floor, disposition, unsupported_host),)
    ratio, channel, ground_id, ground, sample, ground_kind = max(candidates, key=lambda item: item[0])
    severity = "error" if ratio < floor else "info"
    return (SceneContrastFinding(code, severity, scene_path, purpose, role, primitive_id, ratio, floor,
                                 disposition, ground_id, ground, channel, *sample, ground_kind),)


def _sample_point(primitive: Mapping[str, Any], channel: str) -> tuple[float | None, float | None]:
    bounds = primitive.get("bounds")
    if not isinstance(bounds, Mapping):
        return None, None
    try:
        inline = float(bounds["inline"])
        block = float(bounds["block"])
        width = float(bounds["inlineSize"])
        height = float(bounds["blockSize"])
    except (KeyError, TypeError, ValueError):
        return None, None
    if channel == "stroke" and primitive.get("kind") in {"Rect", "Symbol"}:
        return (inline, block + height / 2) if width else (inline + width / 2, block)
    return inline + width / 2, block + height / 2


def _ground_under(primitive: Mapping[str, Any], primitives: list[Any], index: int,
                  canvas: str | None,
                  sample: tuple[float | None, float | None]) -> tuple[str | None, str | None, bool, str]:
    if sample[0] is None or sample[1] is None:
        return "canvas", canvas, False, "canvas"
    x, y = sample
    order = primitive.get("paintOrder", 0)
    candidates: list[tuple[int, int, Mapping[str, Any]]] = []
    for prior_index, prior in enumerate(primitives):
        # A Rect is an ordinary painted ground. A Symbol is also accepted: a multi-part
        # glyph gate (#464) paints several sibling Symbol primitives over the same
        # bounds, and a later part's true ground is the earlier part beneath it, not
        # the canvas or the band underneath the whole mark.
        if not isinstance(prior, Mapping) or prior.get("kind") not in {"Rect", "Symbol"}:
            continue
        prior_order = prior.get("paintOrder", 0)
        if not isinstance(prior_order, int) or (prior_order, prior_index) >= (order, index):
            continue
        box, paint = prior.get("bounds"), prior.get("paint")
        if not isinstance(box, Mapping) or not isinstance(paint, Mapping) or paint.get("fill") is None:
            continue
        try:
            inside = (float(box["inline"]) <= x < float(box["inline"]) + float(box["inlineSize"])
                      and float(box["block"]) <= y < float(box["block"]) + float(box["blockSize"]))
        except (KeyError, TypeError, ValueError):
            inside = False
        if inside:
            candidates.append((prior_order, prior_index, prior))
    if not candidates:
        return "canvas", canvas, False, "canvas"
    host = max(candidates, key=lambda item: item[:2])[2]
    paint = host["paint"]
    host_id = host.get("id") if isinstance(host.get("id"), str) else None
    if paint.get("opacity", 1.0) != 1.0:
        return host_id, None, True, "unsupported"
    gradient = paint.get("gradient")
    if gradient is not None:
        if not isinstance(gradient, Mapping):
            return host_id, None, True, "unsupported"
        try:
            sampled = sample_linear_gradient(gradient, (x, y))
        except ValueError:
            return host_id, None, True, "unsupported"
        return host_id, sampled, False, "gradient-sample"
    if not is_hex_color(paint.get("fill")):
        return host_id, None, True, "unsupported"
    return host_id, str(paint["fill"]), False, "flat"


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
