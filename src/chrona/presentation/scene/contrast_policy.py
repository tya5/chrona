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
# Roles whose sibling parts (one source, one role) are a single ink and never each other's ground.
_SIBLING_INK_ROLES = frozenset({"annotation-kind-stamp"})


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
    density_basis_points: int | None = None

    def as_mapping(self) -> dict[str, Any]:
        result = {
            "code": self.code, "severity": self.severity, "scenePath": self.scene_path,
            "purpose": self.purpose, "visualRole": self.visual_role,
            "primitiveId": self.primitive_id, "contrastRatio": self.contrast_ratio,
            "floor": self.floor, "disposition": self.disposition,
            "groundId": self.ground_id, "groundColor": self.ground_color,
            "paintChannel": self.paint_channel,
            "sampleInline": self.sample_inline, "sampleBlock": self.sample_block,
            "groundKind": self.ground_kind,
        }
        if self.density_basis_points is not None:
            result["densityBasisPoints"] = self.density_basis_points
        return result


def evaluate_scene_contrast(document: Mapping[str, Any]) -> tuple[SceneContrastFinding, ...]:
    """Evaluate every finite classified role from serialized completed facts."""
    version = document.get("version")
    _require(version == "chrona/scene/v0.6" or version == "chrona/scene/v0.7",
             "unsupported scene version")
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
            findings.extend(_primitive_findings(scene_path, primitive, ground, primitives, index,
                                                catalog_patterns=version == "chrona/scene/v0.7"))
        findings.extend(_absence_findings(scene_path, raw_surface.get("decorationDispositions", [])))
    return tuple(sorted(findings, key=lambda item: (
        item.scene_path, item.purpose, item.visual_role, item.disposition, item.primitive_id or "", item.code,
    )))


def _primitive_findings(scene_path: str, primitive: Mapping[str, Any], canvas: str | None,
                        primitives: list[Any], index: int, *,
                        catalog_patterns: bool = False) -> tuple[SceneContrastFinding, ...]:
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
        if (treatment not in STATE_TEXT_FLOORS
                or (role in {"variance-behind", "annotation-note-text"} and treatment != "required")):
            pointer = f"{scene_path}/primitives/{index}/contrastTreatment"
            return (SceneContrastFinding("E_SCENE_STATE_TEXT_CONTRAST_TREATMENT", "error", pointer,
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
    pattern = primitive.get("pattern") if catalog_patterns else None
    is_catalog_pattern = isinstance(pattern, Mapping) and any(
        key in pattern for key in ("densityBasisPoints", "primitives", "origin", "regionBounds", "clipBounds"))
    if is_catalog_pattern:
        return _pattern_findings(scene_path, primitive, pattern, paint, opacity, floor,
                                 disposition, code, purpose, role, primitive_id, canvas,
                                 primitives, index)
    channels = ("fill",) if binding.contrast_class == ContrastClass.STATE_TEXT else ("fill", "stroke")
    candidates = []
    unsupported_host: str | None = None
    unsupported_ground = False
    for channel in channels:
        if not is_hex_color(paint.get(channel)):
            continue
        if channel == "stroke" and (not isinstance(paint.get("strokeWidth"), (int, float))
                                    or paint["strokeWidth"] <= 0):
            continue
        sample = _sample_point(primitive, channel)
        if role == "annotation-note-text":
            ground_id, ground, unsupported, ground_kind = _note_box_ground(
                primitive, primitives, index, sample)
        else:
            ground_id, ground, unsupported, ground_kind = _ground_under(
                primitive, primitives, index, canvas, sample)
        if unsupported:
            unsupported_host = ground_id
            unsupported_ground = True
            continue
        if ground is None:
            continue
        ratio = composited_contrast(fill=paint[channel], opacity=float(opacity), ground=ground)
        ink = _texture_ink(primitives, ground_id) if binding.contrast_class != ContrastClass.DECORATION else None
        if ink is not None:
            # A canvas texture is ground in two colours: a mark or a label may lie on either.
            # A decoration is a tint judged against the dominant substrate, not against thin ink lines.
            ground_kind = "texture-substrate"
            ink_ratio = composited_contrast(fill=paint[channel], opacity=float(opacity), ground=ink)
            if ink_ratio < ratio:
                ratio, ground, ground_kind = ink_ratio, ink, "texture-ink"
        candidates.append((ratio, channel, ground_id, ground, sample, ground_kind))
    if not candidates:
        error_code = "E_SCENE_CONTRAST_GROUND_UNSUPPORTED" if unsupported_ground else "E_SCENE_CONTRAST_PAINT"
        return (SceneContrastFinding(error_code, "error", scene_path, purpose, role,
                                     primitive_id, None, floor, disposition, unsupported_host),)
    ratio, channel, ground_id, ground, sample, ground_kind = max(candidates, key=lambda item: item[0])
    severity = "error" if ratio < floor else "info"
    return (SceneContrastFinding(code, severity, scene_path, purpose, role, primitive_id, ratio, floor,
                                 disposition, ground_id, ground, channel, *sample, ground_kind),)


def _pattern_findings(scene_path: str, primitive: Mapping[str, Any], pattern: Any,
                      paint: Mapping[str, Any], opacity: float, floor: float,
                      disposition: str, code: str, purpose: str, role: str, primitive_id: str,
                      canvas: str | None, primitives: list[Any], index: int
                      ) -> tuple[SceneContrastFinding, ...]:
    """Gate each effective pattern channel pair; neither channel can mask another."""
    if (not isinstance(pattern, Mapping)
            or not isinstance(pattern.get("densityBasisPoints"), int)
            or isinstance(pattern.get("densityBasisPoints"), bool)
            or not 1 <= pattern["densityBasisPoints"] <= 10000):
        return (SceneContrastFinding("E_SCENE_CONTRAST_PAINT", "error", scene_path, purpose,
                                     role, primitive_id, None, floor, disposition),)
    density = int(pattern["densityBasisPoints"])
    if (opacity != 1.0 or not is_hex_color(paint.get("fill"))
            or not is_hex_color(paint.get("stroke"))):
        return (SceneContrastFinding("E_SCENE_CONTRAST_PAINT", "error", scene_path, purpose,
                                     role, primitive_id, None, floor, disposition,
                                     density_basis_points=density),)
    sample = _sample_point(primitive, "fill")
    if role == "annotation-note-text":
        host_id, host, unsupported, host_kind = _note_box_ground(primitive, primitives, index, sample)
    else:
        host_id, host, unsupported, host_kind = _ground_under(primitive, primitives, index, canvas, sample)
    if unsupported or host is None:
        return (SceneContrastFinding("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", "error", scene_path,
                                     purpose, role, primitive_id, None, floor, disposition,
                                     host_id, paint_channel="fill", ground_kind="unsupported",
                                     density_basis_points=density),)
    substrate, ink = str(paint["fill"]), str(paint["stroke"])
    pairs = [("fill", host_id, host, host_kind, substrate),
             ("stroke", primitive_id, substrate, "pattern-substrate", ink),
             ("stroke", host_id, host, host_kind, ink)]
    # As for a flat primitive: a mark or a label sees the ink as ground, a decoration tint does not.
    texture_ink = _texture_ink(primitives, host_id) if code != "E_SCENE_DECORATION_CONTRAST" else None
    if texture_ink is not None:
        # The host is a canvas texture: its ink is a second ground under this primitive.
        pairs[0] = ("fill", host_id, host, "texture-substrate", substrate)
        pairs[2] = ("stroke", host_id, host, "texture-substrate", ink)
        pairs += [("fill", host_id, texture_ink, "texture-ink", substrate),
                  ("stroke", host_id, texture_ink, "texture-ink", ink)]
    findings = []
    for channel, ground_id, ground, ground_kind, foreground in pairs:
        ratio = composited_contrast(fill=foreground, opacity=1.0, ground=ground)
        severity = "error" if ratio < floor else "info"
        findings.append(SceneContrastFinding(code, severity, scene_path, purpose, role, primitive_id,
                                             ratio, floor, disposition, ground_id, ground, channel,
                                             *sample, ground_kind, density))
    return tuple(findings)


def _texture_ink(primitives: list[Any], host_id: str | None) -> str | None:
    """Return the ink of the canvas texture a ground host is, else nothing."""
    if host_id is None:
        return None
    for primitive in primitives:
        if (isinstance(primitive, Mapping) and primitive.get("id") == host_id
                and primitive.get("visualRole") == "canvas-texture"):
            paint = primitive.get("paint")
            stroke = paint.get("stroke") if isinstance(paint, Mapping) else None
            return str(stroke) if is_hex_color(stroke) else None
    return None


def _note_box_ground(primitive: Mapping[str, Any], primitives: list[Any], index: int,
                     sample: tuple[float | None, float | None]
                     ) -> tuple[str | None, str | None, bool, str]:
    """Resolve note prose only against its earlier, same-source opaque note box."""
    source_ref = primitive.get("sourceRef")
    if not isinstance(source_ref, str) or not source_ref or sample[0] is None or sample[1] is None:
        return None, None, True, "unsupported"
    x, y = sample
    order = primitive.get("paintOrder", 0)
    candidates: list[tuple[int, int, Mapping[str, Any]]] = []
    for prior_index, prior in enumerate(primitives):
        if (not isinstance(prior, Mapping) or prior.get("visualRole") != "annotation-note-box"
                or prior.get("sourceRef") != source_ref or prior.get("kind") not in {"Rect", "Symbol"}):
            continue
        prior_order = prior.get("paintOrder", 0)
        if not isinstance(prior_order, int) or (prior_order, prior_index) >= (order, index):
            continue
        box = prior.get("bounds")
        if not isinstance(box, Mapping):
            continue
        try:
            inside = (float(box["inline"]) <= x < float(box["inline"]) + float(box["inlineSize"])
                      and float(box["block"]) <= y < float(box["block"]) + float(box["blockSize"]))
        except (KeyError, TypeError, ValueError):
            inside = False
        if inside:
            candidates.append((prior_order, prior_index, prior))
    if not candidates:
        return None, None, True, "unsupported"
    host = max(candidates, key=lambda item: item[:2])[2]
    paint = host.get("paint")
    host_id = host.get("id") if isinstance(host.get("id"), str) else None
    if (not isinstance(paint, Mapping) or paint.get("opacity", 1.0) != 1.0
            or paint.get("gradient") is not None or host.get("pattern") is not None
            or not is_hex_color(paint.get("fill"))):
        return host_id, None, True, "unsupported"
    return host_id, str(paint["fill"]), False, "flat"


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
        if (primitive.get("visualRole") in _SIBLING_INK_ROLES and prior.get("visualRole") == primitive.get("visualRole")
                and prior.get("sourceRef") == primitive.get("sourceRef")):
            # The parts of one stamp glyph are one ink, not grounds for each other (#584).
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
