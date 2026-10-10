"""Finite completed-Scene contrast policy; no renderer or Theme re-resolution."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from chrona.presentation.model.semantic_registry import (
    ContrastClass,
    contrast_binding,
    contrast_binding_for,
    is_annotation_artwork_role,
    is_frame_glyph_role,
    is_label_chip_role,
)
from chrona.presentation.scene.cone_ground import AS_OF_CONE_ROLE, ConeGround, cones_in
from chrona.presentation.scene.ink_touch import InkTouchError, fill_touches
from chrona.presentation.scene.paint_analysis import (
    blend_over,
    composited_contrast,
    is_hex_color,
    sample_linear_gradient,
)
from chrona.presentation.scene.pattern_ink import pattern_ink_touches
from chrona.presentation.scene.sparse_ink import selected_symbol_ink, valid_opacity
from chrona.presentation.scene.surface_overprint import ordered_overprint_pairs

DECORATION_FLOOR = 1.10
MARK_FLOOR = 3.0
STATE_TEXT_FLOORS = {"required": 4.5, "deemphasized": 3.0}
# Severity classes (#995). Text and data marks lose information when they are too faint: `legibility`, always a
# blocking error. A decoration (a stripe, a band, a tint) is ground, never the message: `decoration`, a warning
# unless the Theme asks for it to block. The class comes from the registry's contrast class, never from the slide.
LEGIBILITY_CLASS = "legibility"
DECORATION_CLASS = "decoration"
DECORATION_SEVERITIES = ("warning", "error")
# Contrast constraints are an opt-in design option (#1126): a Theme sets each class `off`, `warning` or `error`.
POLICY_SEVERITIES = ("none", "warning", "error")
POLICY_MEMBERS = ("mark", "stateText", "groundText", "decoration", "unsupportedGround")
# What a Theme that declares nothing gets: not opted in, never blocking.
DEFAULT_POLICY = {member: "warning" for member in POLICY_MEMBERS}
# Today's gate, the repository's: every legibility class blocks, a decoration warns (#995).
STRICT_SEVERITIES = {"mark": "error", "stateText": "error", "groundText": "error", "unsupportedGround": "error",
                     "decoration": "warning"}
_FLOOR_CODES = frozenset({"E_SCENE_MARK_CONTRAST", "E_SCENE_STATE_TEXT_CONTRAST", "E_SCENE_DECORATION_CONTRAST"})
# The warning twin of each blocking code, by (is a decoration, blocking code).
_WARNING_CODES = {
    (True, "E_SCENE_DECORATION_CONTRAST"): "W_SCENE_DECORATION_CONTRAST",
    (True, "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"): "W_SCENE_DECORATION_GROUND_UNSUPPORTED",
    (False, "E_SCENE_MARK_CONTRAST"): "W_SCENE_MARK_CONTRAST",
    (False, "E_SCENE_STATE_TEXT_CONTRAST"): "W_SCENE_STATE_TEXT_CONTRAST",
    (False, "E_SCENE_CONTRAST_GROUND_UNSUPPORTED"): "W_SCENE_CONTRAST_GROUND_UNSUPPORTED",
}
# The blocking code each contrast warning stands for (what `contrastPolicy: error` restores).
WARNING_BLOCKING_CODES = {warning: blocking for (_, blocking), warning in _WARNING_CODES.items()}
# The blocking codes a Theme that sets a class to `error` makes a render fail on.
BLOCKING_CODES = frozenset(WARNING_BLOCKING_CODES.values())
# Kept for #995's callers and tests: the decoration subset.
DECORATION_WARNING_BLOCKING_CODES = {warning: blocking for (is_decoration, blocking), warning in _WARNING_CODES.items()
                                     if is_decoration}
# Roles whose sibling parts (one source, one role) are a single ink and never each other's ground.
_SIBLING_INK_ROLES = frozenset({"annotation-kind-stamp"})
# The parts of a vector artwork behind an annotation (#848) are ink over the note box: never a host by bounds (their
# bounds are the whole note), a ground only where the part's painted area meets the label.


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
    severity_class: str | None = None

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
        if self.severity_class is not None:
            result["severityClass"] = self.severity_class
        return result


def evaluate_scene_contrast(document: Mapping[str, Any], *, decoration_severity: str = "warning",
                            policy: Mapping[str, str] | None = None) -> tuple[SceneContrastFinding, ...]:
    """Evaluate every finite classified role from serialized completed facts.

    `policy` maps each class (`mark`, `stateText`, `groundText`, `decoration`, `unsupportedGround`) to `none`,
    `warning` or `error` (a Theme's `contrastPolicy`, #1126); a class it omits keeps the evaluator's own default:
    a legibility finding is an `error`, a decoration is `decoration_severity` (`warning` or `error`, #995).
    """
    if decoration_severity not in DECORATION_SEVERITIES:
        raise ValueError(f"unsupported decoration severity {decoration_severity!r}")
    severities = _resolve_severities(policy, decoration_severity)
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
        if any(isinstance(item, Mapping) and (
                item.get("visualRole") in {"canvas-overlay", "canvas-overlay-gradient"}
                or (item.get("visualRole") == "canvas-texture" and isinstance(item.get("paint"), Mapping)
                    and item["paint"].get("fill") is None)) for item in primitives):
            ground = canvas
        try:
            cones = cones_in(primitives)
        except ValueError as error:
            raise SceneContrastPolicyError(f"E_SCENE_CONTRAST_DOCUMENT: invalid as-of cone at {scene_path}") from error
        figures = _mark_figures(primitives)
        sibling_indices = {position for parts in figures.values() for position, _ in parts[1:]}
        for index, primitive in enumerate(primitives):
            _require(isinstance(primitive, Mapping), f"invalid primitive {index} at {scene_path}")
            if index in sibling_indices:
                continue
            if index in figures:
                findings.extend(_figure_findings(scene_path, figures[index], ground, primitives,
                                                catalog_patterns=version == "chrona/scene/v0.7",
                                                cones=cones, severities=severities))
                continue
            findings.extend(_primitive_findings(scene_path, primitive, ground, primitives, index,
                                                catalog_patterns=version == "chrona/scene/v0.7", cones=cones,
                                                severities=severities))
        findings.extend(_absence_findings(scene_path, raw_surface.get("decorationDispositions", [])))
    return tuple(sorted(findings, key=lambda item: (
        item.scene_path, item.purpose, item.visual_role, item.disposition, item.primitive_id or "", item.code,
    )))


def _mark_figures(primitives: list[Any]) -> dict[int, tuple[tuple[int, Mapping[str, Any]], ...]]:
    """Recognize completed mark placements, not arbitrary same-source paint layers."""
    groups: dict[str, list[tuple[int, int, Mapping[str, Any]]]] = {}
    for index, primitive in enumerate(primitives):
        if not isinstance(primitive, Mapping) or primitive.get("kind") != "Symbol":
            continue
        identifier, role = primitive.get("id"), primitive.get("visualRole")
        if not isinstance(identifier, str) or not isinstance(role, str):
            continue
        binding = contrast_binding_for(role, None)
        if binding is None or binding.contrast_class != ContrastClass.MARK:
            continue
        base, separator, part = identifier.rpartition(":part")
        part = part.removeprefix(":")
        if not base or not separator or not part or not part.isascii() or not part.isdecimal():
            continue
        if not isinstance(primitive.get("sourceRef"), str) or not primitive["sourceRef"]:
            continue
        groups.setdefault(base, []).append((index, int(part), primitive))
    figures = {}
    common = ("sourceRef", "sourceKind", "purpose", "visualRole", "bounds", "slotId")
    for parts in groups.values():
        if len(parts) < 2 or len({number for _, number, _ in parts}) != len(parts):
            continue
        first = parts[0][2]
        if any(any(item.get(field) != first.get(field) for field in common) for _, _, item in parts[1:]):
            continue
        # Retain document order: the first part owns the observation's position;
        # equal visibility candidates keep the same deterministic paint order.
        figures[parts[0][0]] = tuple((position, item) for position, _, item in parts)
    return figures


def _figure_findings(scene_path: str, parts: tuple[tuple[int, Mapping[str, Any]], ...],
                     canvas: str | None, primitives: list[Any], *, catalog_patterns: bool,
                     cones: tuple[ConeGround, ...], severities: Mapping[str, str]
                     ) -> tuple[SceneContrastFinding, ...]:
    """Observe one mark's visible ink against external grounds, never its siblings."""
    indices = {position for position, _ in parts}
    observations = []
    candidates = []
    for index, primitive in parts:
        # Keep indices and paint order intact, including through recursive
        # translucent-host resolution. No sibling is an external substrate.
        external = [item if position not in indices or position == index else {}
                    for position, item in enumerate(primitives)]
        part_findings = _primitive_findings(scene_path, primitive, canvas, external, index,
                                           catalog_patterns=catalog_patterns, cones=cones,
                                           severities=severities)
        observations.extend(part_findings)
        if part_findings:
            # A catalogue pattern has several mandatory effective pairs;
            # preserve its worst-pair obligation before choosing figure ink.
            candidates.append(min(part_findings, key=lambda item: (
                item.contrast_ratio if item.contrast_ratio is not None else -1)))
    for item in observations:
        blocking = WARNING_BLOCKING_CODES.get(item.code, item.code)
        if blocking not in _FLOOR_CODES and blocking != "E_SCENE_CONTRAST_GROUND_UNSUPPORTED":
            return (item,)
    for item in observations:
        if WARNING_BLOCKING_CODES.get(item.code, item.code) == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED":
            return (item,)
    if not candidates:
        return ()
    # The existing dual-channel rule lets either fill or outline carry the
    # figure's visibility floor; a multipart figure has the same rule. Retain
    # the actual winning part ID/channel/sample, not an invented primitive.
    return (max(candidates, key=lambda item: item.contrast_ratio if item.contrast_ratio is not None else -1),)


def _primitive_findings(scene_path: str, primitive: Mapping[str, Any], canvas: str | None,
                        primitives: list[Any], index: int, *,
                        catalog_patterns: bool = False,
                        cones: tuple[ConeGround, ...] = (),
                        severities: Mapping[str, str] = None) -> tuple[SceneContrastFinding, ...]:
    severities = severities or _resolve_severities(None, "warning")
    role = primitive.get("visualRole")
    if not isinstance(role, str):
        return ()
    binding = contrast_binding_for(role, primitive.get("purpose") if primitive.get("kind") == "Text" else None)
    if binding is None:
        return ()
    primitive_id = _string(primitive.get("id"), f"primitive id at {scene_path}")
    purpose = _string(primitive.get("purpose"), f"primitive purpose at {scene_path}")
    severity_class = _severity_class(binding.contrast_class)
    policy_class = _policy_class(binding.contrast_class)
    if binding.contrast_class == ContrastClass.DECORATION:
        floor, disposition = DECORATION_FLOOR, "enabled"
        code = "E_SCENE_DECORATION_CONTRAST"
    elif binding.contrast_class == ContrastClass.MARK:
        floor, disposition = MARK_FLOOR, "required"
        code = "E_SCENE_MARK_CONTRAST"
    elif binding.contrast_class == ContrastClass.GROUND_TEXT:
        # Ink of the shared text role on a decoration ground: always required, never authored (#884).
        floor, disposition = STATE_TEXT_FLOORS["required"], "required"
        code = "E_SCENE_STATE_TEXT_CONTRAST"
    else:
        treatment = primitive.get("contrastTreatment")
        if (treatment not in STATE_TEXT_FLOORS
                or (role in {"variance-behind", "annotation-note-text"} and treatment != "required")):
            pointer = f"{scene_path}/primitives/{index}/contrastTreatment"
            return (SceneContrastFinding("E_SCENE_STATE_TEXT_CONTRAST_TREATMENT", "error", pointer,
                                         purpose, role, primitive_id, None, None, "invalid-treatment",
                                         severity_class=severity_class),)
        floor, disposition = STATE_TEXT_FLOORS[treatment], treatment
        code = "E_SCENE_STATE_TEXT_CONTRAST"
    paint = primitive.get("paint")
    if not isinstance(paint, Mapping):
        return (SceneContrastFinding("E_SCENE_CONTRAST_PAINT", "error", scene_path, purpose, role,
                                     primitive_id, None, floor, disposition, severity_class=severity_class),)
    opacity = paint.get("opacity", 1.0)
    if not _opacity(opacity):
        return (SceneContrastFinding("E_SCENE_CONTRAST_PAINT", "error", scene_path, purpose, role,
                                     primitive_id, None, floor, disposition, severity_class=severity_class),)
    pattern = primitive.get("pattern") if catalog_patterns else None
    is_catalog_pattern = isinstance(pattern, Mapping) and any(
        key in pattern for key in ("densityBasisPoints", "primitives", "origin", "regionBounds", "clipBounds"))
    if is_catalog_pattern:
        return _pattern_findings(scene_path, primitive, pattern, paint, opacity, floor,
                                 disposition, code, purpose, role, primitive_id, canvas,
                                 primitives, index, catalog_patterns, cones,
                                 severity_class=severity_class, severities=severities, policy_class=policy_class)
    channels = (("fill",) if binding.contrast_class in (ContrastClass.STATE_TEXT, ContrastClass.GROUND_TEXT)
                else ("fill", "stroke"))
    candidates = []
    unsupported_host: str | None = None
    unsupported_ground = False
    decoration = binding.contrast_class == ContrastClass.DECORATION
    for channel in channels:
        if not is_hex_color(paint.get(channel)):
            continue
        if channel == "stroke" and (not isinstance(paint.get("strokeWidth"), (int, float))
                                    or paint["strokeWidth"] <= 0):
            continue
        sample = _sample_point(primitive, channel)
        ground_id, groups, unsupported = _grounds_for(
            primitive, primitives, index, canvas, sample, cones=cones, catalog_patterns=catalog_patterns,
            decoration=decoration)
        if unsupported:
            unsupported_host = ground_id
            unsupported_ground = True
            continue
        if groups is None:
            continue
        # A canvas texture and a catalogue pattern are ground in two colours: a mark or a label may lie
        # on either. A decoration is a tint judged against the dominant substrate, not against thin ink lines.
        ratio = ground = ground_kind = None
        options = [option for group in groups for option in group]
        if not decoration and _has_later_overlay(primitives, primitive, index):
            try:
                pairs = ordered_overprint_pairs(primitive, primitives, index, foreground=paint[channel],
                                                opacity=float(opacity), grounds=options, sample=sample)
            except InkTouchError:
                unsupported_ground = True
                continue
            for pair in pairs:
                option_ratio = composited_contrast(fill=pair.foreground, opacity=1, ground=pair.backdrop)
                if ratio is None or option_ratio < ratio:
                    ratio, ground, ground_kind, ground_id = option_ratio, pair.backdrop, pair.ground_kind, pair.ground_id
        else:
            for option_ground, option_kind, option_id in options:
                option_ratio = composited_contrast(fill=paint[channel], opacity=float(opacity), ground=option_ground)
                if ratio is None or option_ratio < ratio:
                    ratio, ground, ground_kind, ground_id = option_ratio, option_ground, option_kind, option_id
        candidates.append((ratio, channel, ground_id, ground, sample, ground_kind))
    if not candidates:
        error_code = "E_SCENE_CONTRAST_GROUND_UNSUPPORTED" if unsupported_ground else "E_SCENE_CONTRAST_PAINT"
        severity, error_code = _failure(error_code, severity_class, policy_class, severities)
        return (SceneContrastFinding(error_code, severity, scene_path, purpose, role,
                                     primitive_id, None, floor, disposition, unsupported_host,
                                     severity_class=severity_class),)
    ratio, channel, ground_id, ground, sample, ground_kind = max(candidates, key=lambda item: item[0])
    severity = "info"
    if ratio < floor:
        severity, code = _failure(code, severity_class, policy_class, severities)
    return (SceneContrastFinding(code, severity, scene_path, purpose, role, primitive_id, ratio, floor,
                                 disposition, ground_id, ground, channel, *sample, ground_kind,
                                 severity_class=severity_class),)


def _severity_class(contrast_class: ContrastClass) -> str:
    """The severity class of a registry contrast class: only a decoration is ground (#995)."""
    return DECORATION_CLASS if contrast_class == ContrastClass.DECORATION else LEGIBILITY_CLASS


def _policy_class(contrast_class: ContrastClass) -> str:
    """The Theme `contrastPolicy` member that governs a registry contrast class (#1126)."""
    return {ContrastClass.MARK: "mark", ContrastClass.STATE_TEXT: "stateText",
            ContrastClass.GROUND_TEXT: "groundText", ContrastClass.DECORATION: "decoration"}[contrast_class]


def policy_member_of(finding: SceneContrastFinding) -> str | None:
    """The `contrastPolicy` member that governed a floor or ground finding, else nothing (a structural finding)."""
    code = WARNING_BLOCKING_CODES.get(finding.code, finding.code)
    if code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED":
        return "decoration" if finding.severity_class == DECORATION_CLASS else "unsupportedGround"
    if code not in _FLOOR_CODES:
        return None
    binding = contrast_binding_for(finding.visual_role, finding.purpose)
    return _policy_class(binding.contrast_class) if binding is not None else None


def _resolve_severities(policy: Mapping[str, str] | None, decoration_severity: str) -> dict[str, str]:
    """The severity of every class: the explicit policy over today's defaults.

    Without a policy a legibility finding is a blocking `error` and a decoration is `decoration_severity` (the
    evaluator's own default, kept so every geometry test of the gate keeps its meaning); the Theme default
    (`warning`, #1126) is applied by the callers that know a Theme.
    """
    resolved = dict(STRICT_SEVERITIES, decoration=decoration_severity)
    for member, value in (policy or {}).items():
        if member not in resolved or value not in POLICY_SEVERITIES:
            raise ValueError(f"unsupported contrast policy {member!r}: {value!r}")
        resolved[member] = value
    return resolved


def _failure(code: str, severity_class: str, policy_class: str, severities: Mapping[str, str]) -> tuple[str, str]:
    """The severity and code of a finding that missed its floor or could not be judged.

    The policy member of the finding's class decides: `error` is the blocking finding with its code, `warning`
    the same finding with its `W_` twin, `none` an `info` row. A structural failure (a malformed paint) is not a
    contrast constraint and stays an error whatever the policy says.
    """
    if code in _FLOOR_CODES:
        member = policy_class
    elif code == "E_SCENE_CONTRAST_GROUND_UNSUPPORTED":
        member = "decoration" if severity_class == DECORATION_CLASS else "unsupportedGround"
    else:
        return "error", code
    setting = severities[member]
    if setting == "error":
        return "error", code
    if setting == "none":
        return "info", code
    return "warning", _WARNING_CODES[(severity_class == DECORATION_CLASS, code)]


def _pattern_findings(scene_path: str, primitive: Mapping[str, Any], pattern: Any,
                      paint: Mapping[str, Any], opacity: float, floor: float,
                      disposition: str, code: str, purpose: str, role: str, primitive_id: str,
                      canvas: str | None, primitives: list[Any], index: int,
                      catalog_patterns: bool = True,
                      cones: tuple[ConeGround, ...] = (),
                      severity_class: str = LEGIBILITY_CLASS,
                      severities: Mapping[str, str] = None,
                      policy_class: str = "mark") -> tuple[SceneContrastFinding, ...]:
    """Gate each effective pattern channel pair; neither channel can mask another."""
    severities = severities or _resolve_severities(None, "warning")
    if (not isinstance(pattern, Mapping)
            or not isinstance(pattern.get("densityBasisPoints"), int)
            or isinstance(pattern.get("densityBasisPoints"), bool)
            or not 1 <= pattern["densityBasisPoints"] <= 10000):
        return (SceneContrastFinding("E_SCENE_CONTRAST_PAINT", "error", scene_path, purpose,
                                     role, primitive_id, None, floor, disposition,
                                     severity_class=severity_class),)
    density = int(pattern["densityBasisPoints"])
    if (opacity != 1.0 or not is_hex_color(paint.get("fill"))
            or not is_hex_color(paint.get("stroke"))):
        return (SceneContrastFinding("E_SCENE_CONTRAST_PAINT", "error", scene_path, purpose,
                                     role, primitive_id, None, floor, disposition,
                                     density_basis_points=density, severity_class=severity_class),)
    sample = _sample_point(primitive, "fill")
    decoration = code == "E_SCENE_DECORATION_CONTRAST"
    host_id, groups, unsupported = _grounds_for(
        primitive, primitives, index, canvas, sample, cones=cones, catalog_patterns=catalog_patterns,
        decoration=decoration)
    if unsupported or groups is None:
        severity, unsupported_code = _failure("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", severity_class,
                                              policy_class, severities)
        return (SceneContrastFinding(unsupported_code, severity, scene_path,
                                     purpose, role, primitive_id, None, floor, disposition,
                                     host_id, paint_channel="fill", ground_kind="unsupported",
                                     density_basis_points=density, severity_class=severity_class),)
    substrate, ink = str(paint["fill"]), str(paint["stroke"])
    # As for a flat primitive: a mark or a label sees the ink as ground, a decoration tint does not. The first
    # group is the host's substrate (its pair with the primitive's own substrate is the primitive's own); later
    # groups are ink grounds. A pattern's substrate under its ink is the primitive's own.
    pairs = [("fill", *host_ground, substrate) for host_ground in groups[0]]
    pairs.append(("stroke", substrate, "pattern-substrate", primitive_id, ink))
    pairs += [("stroke", *host_ground, ink) for host_ground in groups[0]]
    for group in groups[1:]:
        pairs += [("fill", *host_ground, substrate) for host_ground in group]
        pairs += [("stroke", *host_ground, ink) for host_ground in group]
    findings = []
    for channel, ground, ground_kind, ground_id, foreground in pairs:
        if not decoration and _has_later_overlay(primitives, primitive, index):
            try:
                overprinted = ordered_overprint_pairs(
                    primitive, primitives, index, foreground=foreground, opacity=1,
                    grounds=[(ground, ground_kind, ground_id)], sample=_sample_point(primitive, channel))
            except InkTouchError:
                severity, unsupported_code = _failure("E_SCENE_CONTRAST_GROUND_UNSUPPORTED", severity_class,
                                                      policy_class, severities)
                return (SceneContrastFinding(unsupported_code, severity, scene_path, purpose, role, primitive_id,
                                             None, floor, disposition, paint_channel=channel,
                                             ground_kind="unsupported", severity_class=severity_class),)
            worst = min(overprinted, key=lambda pair: composited_contrast(
                fill=pair.foreground, opacity=1, ground=pair.backdrop))
            foreground, ground, ground_kind, ground_id = worst.foreground, worst.backdrop, worst.ground_kind, worst.ground_id
        ratio = composited_contrast(fill=foreground, opacity=1.0, ground=ground)
        severity, pair_code = "info", code
        if ratio < floor:
            severity, pair_code = _failure(code, severity_class, policy_class, severities)
        findings.append(SceneContrastFinding(pair_code, severity, scene_path, purpose, role, primitive_id,
                                             ratio, floor, disposition, ground_id, ground, channel,
                                             *sample, ground_kind, density, severity_class=severity_class))
    return tuple(findings)


def _has_later_overlay(primitives: list[Any], subject: Mapping[str, Any], index: int) -> bool:
    key = (subject.get("paintOrder", 0), index)
    return any(isinstance(item, Mapping) and item.get("visualRole") in {
        "canvas-overlay", "canvas-overlay-gradient"} and (item.get("paintOrder", 0), position) > key
        for position, item in enumerate(primitives))


def effective_surface_paint_pairs(subject: Mapping[str, Any], primitives: list[Any], index: int,
                                   canvas: Mapping[str, Any], channel: str = "fill") -> tuple:
    """Shared quality observation of opt-in surface treatments, using real host grounds."""
    paint = subject.get("paint")
    if not isinstance(paint, Mapping) or not is_hex_color(paint.get(channel)):
        raise InkTouchError("unreadable subject channel")
    sample = _sample_point(subject, channel)
    binding = contrast_binding_for(subject.get("visualRole"), subject.get("purpose"))
    decoration = binding is not None and binding.contrast_class == ContrastClass.DECORATION
    try:
        cones = cones_in(primitives)
    except ValueError as error:
        raise InkTouchError("unreadable prior cone ground") from error
    _, groups, unsupported = _grounds_for(subject, primitives, index, canvas, sample,
                                          cones=cones, catalog_patterns=True, decoration=decoration)
    if unsupported or groups is None:
        raise InkTouchError("unsupported completed surface ground")
    return ordered_overprint_pairs(subject, [] if decoration else primitives, index,
                                    foreground=paint[channel], opacity=float(paint.get("opacity", 1)),
                                    grounds=[option for group in groups for option in group], sample=sample)


def _cone_overlay(cones: tuple[ConeGround, ...], primitives: list[Any], index: int,
                  host_id: str | None) -> tuple[ConeGround, ...]:
    """The cones painted after a primitive's host and before the primitive: the ones that tint its ground.

    A cone is translucent, so it is never the host; an opaque host painted after it hides it (#890).
    """
    if not cones:
        return ()
    primitive = primitives[index]
    key = (primitive.get("paintOrder", 0), index)
    host_key = next(((item.get("paintOrder", 0), position) for position, item in enumerate(primitives)
                     if isinstance(item, Mapping) and item.get("id") == host_id), None) if host_id else None
    return tuple(cone for cone in cones if cone.key < key and (host_key is None or cone.key > host_key))


def _under_cone(overlay: tuple[ConeGround, ...], primitive: Mapping[str, Any], ground: str, kind: str,
                ground_id: str | None) -> tuple[tuple[str, str, str | None], ...]:
    """The grounds a primitive lies on once the cones over its host are composited.

    A primitive wholly inside a cone lies on the blended grounds only (one per end of its block extent inside
    the gradient: the worst of the stops it spans decides). One that straddles the cone's edge also lies on the
    unblended host. A primitive the cone does not reach keeps its host.
    """
    box = primitive.get("bounds")
    try:
        bounds = (float(box["inline"]), float(box["block"]), float(box["inlineSize"]), float(box["blockSize"]))
    except (KeyError, TypeError, ValueError):
        return ((ground, kind, ground_id),)
    blended: list[tuple[str, str, str | None]] = []
    wholly_inside = False
    for cone in overlay:
        colours, partial = cone.blends(bounds, ground)
        blended.extend((colour, "cone-blend", cone.cone_id) for colour in colours)
        wholly_inside = wholly_inside or (bool(colours) and not partial)
    if not blended:
        return ((ground, kind, ground_id),)
    return tuple(blended) if wholly_inside else ((ground, kind, ground_id), *blended)


def _host_ink(primitives: list[Any], host_id: str | None, catalog_patterns: bool = False) -> tuple[str, str] | None:
    """Return the ink of the textured ground a host is, with its family, else nothing.

    A canvas texture (family `texture`) and a Rect with a completed catalogue pattern (family `pattern-host`,
    Scene v0.7 only) each lie in two colours: the substrate is the host's fill, the ink its stroke (#587, #884).
    """
    if host_id is None:
        return None
    for primitive in primitives:
        if not isinstance(primitive, Mapping) or primitive.get("id") != host_id:
            continue
        paint = primitive.get("paint")
        stroke = paint.get("stroke") if isinstance(paint, Mapping) else None
        if not is_hex_color(stroke):
            return None
        if primitive.get("visualRole") == "canvas-texture":
            return str(stroke), "texture"
        pattern = primitive.get("pattern")
        if catalog_patterns and isinstance(pattern, Mapping) and any(
                key in pattern for key in ("densityBasisPoints", "primitives", "origin", "regionBounds", "clipBounds")):
            return str(stroke), "pattern-host"
        return None
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


def _host_under(subject: Mapping[str, Any], primitives: list[Any], index: int,
                sample: tuple[float, float]) -> tuple[int, Mapping[str, Any], bool] | None:
    """The topmost Rect or Symbol with a fill, painted before `subject`, that covers the sample point."""
    x, y = sample
    order = subject.get("paintOrder", 0)
    candidates: list[tuple[int, int, Mapping[str, Any], bool]] = []
    for prior_index, prior in enumerate(primitives):
        # A Rect is an ordinary painted ground. A Symbol is also accepted: a multi-part
        # glyph gate (#464) paints several sibling Symbol primitives over the same
        # bounds, and a later part's true ground is the earlier part beneath it, not
        # the canvas or the band underneath the whole mark.
        if not isinstance(prior, Mapping) or prior.get("kind") not in {"Rect", "Symbol"}:
            continue
        if prior.get("visualRole") == AS_OF_CONE_ROLE:
            # A translucent light is never an opaque host: it tints the host's ground instead (#890).
            continue
        if is_annotation_artwork_role(prior.get("visualRole")):
            # Artwork parts cover the whole note by bounds but paint only their ink: see `_artwork_ink`.
            continue
        if is_frame_glyph_role(prior.get("visualRole")):
            # Frame symbols paint sparse glyph ink, not their enclosing slot bounds.
            continue
        if (subject.get("visualRole") in _SIBLING_INK_ROLES and prior.get("visualRole") == subject.get("visualRole")
                and prior.get("sourceRef") == subject.get("sourceRef")):
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
        unreadable = False
        if inside and prior.get("kind") == "Symbol" and is_label_chip_role(prior.get("visualRole")):
            symbol = prior.get("symbol")
            outline = symbol.get("outline") if isinstance(symbol, Mapping) else None
            try:
                if not isinstance(outline, list) or not outline:
                    raise InkTouchError("unreadable chip fill")
                # The same nonzero completed-path inspector used for sparse
                # artwork; zero-area bounds ask about this actual sample.
                inside = fill_touches(outline, (x, y, 0.0, 0.0))
            except InkTouchError:
                unreadable = True
        if inside:
            candidates.append((prior_order, prior_index, prior, unreadable))
    if not candidates:
        return None
    _, position, host, unreadable = max(candidates, key=lambda item: item[:2])
    return position, host, unreadable


# One ground a primitive lies on: its colour, its kind (the finding's `groundKind`) and the ground's identifier.
_Ground = tuple[str, str, "str | None"]


def _grounds_for(primitive: Mapping[str, Any], primitives: list[Any], index: int, canvas: str | None,
                 sample: tuple[float | None, float | None], *, cones: tuple[ConeGround, ...],
                 catalog_patterns: bool, decoration: bool
                 ) -> tuple[str | None, list[list[_Ground]] | None, bool]:
    """The grounds a primitive lies on: (ground id, groups, unsupported).

    `groups` is None when no ground can be read (`unsupported` says whether that is a host the gate refuses, as
    opposed to an absent canvas). The first group is the host's substrate, later groups are ink grounds (a canvas
    texture or a catalogue pattern, #587); every ground already has the cones painted over its host composited
    (#890). Note prose lies only on its own opaque note box (Specification 08, C4).
    """
    if primitive.get("visualRole") == "annotation-note-text":
        host_id, ground, unsupported, kind = _note_box_ground(primitive, primitives, index, sample)
        if unsupported or ground is None:
            return host_id, None, unsupported
        groups, unreadable = _sparse_ground_layers(
            [[(ground, kind, host_id)]], host_id, primitive, primitives, index, cones)
        if unreadable is not None:
            return unreadable, None, True
        return _with_artwork_ink(host_id, groups, primitive, primitives, index)
    # A decoration is a tint against its dominant substrate: no ink, no cone, and no composite (#995).
    host_id, groups, unsupported = _grounds_under(
        primitive, primitives, index, canvas, sample, label=primitive, cones=() if decoration else cones,
        catalog_patterns=catalog_patterns, ink=not decoration, composite=not decoration)
    if decoration or groups is None:
        return host_id, groups, unsupported
    return _with_artwork_ink(host_id, groups, primitive, primitives, index)


def _with_artwork_ink(host_id: str | None, groups: list[list[_Ground]], label: Mapping[str, Any],
                      primitives: list[Any], index: int) -> tuple[str | None, list[list[_Ground]] | None, bool]:
    """Add the ink of the vector artwork the label touches as one more ground (#848), or fail closed on it.

    The artwork behind an annotation is a few sibling Symbol parts over the note box. A part's ink is a ground
    for a label of the same source exactly where the part's painted area meets the label's bounds (a fill part
    by non-zero winding, so a hole is empty; a stroke part within half its width). The ink is composited at the
    part's opacity over every substrate ground already found, and the worst ratio decides, as for a pattern.
    A part that touches the label but whose paint cannot be read fails closed, never skipped.
    """
    ink, unreadable = _artwork_ink(label, primitives, index)
    if unreadable is not None:
        return unreadable, None, True
    if not ink:
        return host_id, groups, False
    bases = [ground for group in groups for ground, _, _ in group]
    grounds: list[_Ground] = []
    for part_id, colour, opacity in ink:
        if opacity == 1.0:
            grounds.append((colour, "artwork-ink", part_id))
        else:
            grounds.extend((blend_over(ink=colour, opacity=opacity, ground=base), "artwork-ink", part_id)
                           for base in bases)
    return host_id, [*groups, grounds], False


def _artwork_ink(label: Mapping[str, Any], primitives: list[Any], index: int
                 ) -> tuple[list[tuple[str, str, float]], str | None]:
    """The (part id, ink colour, opacity) of each earlier same-source artwork part that touches the label.

    Second member: the id of a touching part whose paint cannot be read, else None.
    """
    source_ref, box = label.get("sourceRef"), label.get("bounds")
    if not isinstance(source_ref, str) or not isinstance(box, Mapping):
        return [], None
    try:
        rect = (float(box["inline"]), float(box["block"]), float(box["inlineSize"]), float(box["blockSize"]))
    except (KeyError, TypeError, ValueError):
        return [], None
    order = label.get("paintOrder", 0)
    selected: list[Mapping[str, Any]] = []
    for prior_index, prior in enumerate(primitives):
        if (not isinstance(prior, Mapping) or not is_annotation_artwork_role(prior.get("visualRole")) or prior.get("kind") != "Symbol"
                or prior.get("sourceRef") != source_ref):
            continue
        prior_order = prior.get("paintOrder", 0)
        if not isinstance(prior_order, int) or (prior_order, prior_index) >= (order, index):
            continue
        selected.append(prior)
    return selected_symbol_ink(selected, rect, unreadable_identity="annotation-artwork")


def _grounds_under(subject: Mapping[str, Any], primitives: list[Any], index: int, canvas: str | None,
                   sample: tuple[float | None, float | None], *, label: Mapping[str, Any],
                   cones: tuple[ConeGround, ...], catalog_patterns: bool, ink: bool, composite: bool
                   ) -> tuple[str | None, list[list[_Ground]] | None, bool]:
    """The grounds under `subject` in paint order, as seen by `label` (#1013).

    An opaque host is its own colour (and its ink). A translucent host, when `composite` is set, is composited
    over every ground beneath it: the same resolution one level down, with the cones painted between the two
    hosts applied there, and each colour of the host blended over each beneath ground, so the worst decides.
    """
    found = None if sample[0] is None or sample[1] is None else _host_under(subject, primitives, index, sample)
    if found is None:
        if isinstance(canvas, Mapping):
            try:
                canvas = (sample_linear_gradient(canvas["gradient"], sample)
                          if ink and canvas.get("gradient") is not None else _ground(canvas, "canvas"))
            except (ValueError, TypeError, KeyError):
                return "canvas", None, True
        if canvas is None:
            return "canvas", None, False
        if not ink:
            return "canvas", _tinted([[(canvas, "canvas", "canvas")]], label, primitives, index, "canvas", cones), False
        groups, unreadable = _sparse_ground_layers(
            [[(canvas, "canvas", "canvas")]], "canvas", label, primitives, index, cones)
        return (unreadable, None, True) if unreadable is not None else ("canvas", groups, False)
    host_index, host, unreadable = found
    host_id = host.get("id") if isinstance(host.get("id"), str) else None
    if unreadable:
        return host_id, None, True
    paint = host["paint"]
    opacity = paint.get("opacity", 1.0)
    if opacity != 1.0 and not (composite and _opacity(opacity)):
        return host_id, None, True
    gradient = paint.get("gradient")
    if gradient is not None:
        if not isinstance(gradient, Mapping):
            return host_id, None, True
        try:
            colour = sample_linear_gradient(gradient, sample)
        except ValueError:
            return host_id, None, True
        kind = "gradient-sample"
    elif is_hex_color(paint.get("fill")):
        colour, kind = str(paint["fill"]), "flat"
    else:
        return host_id, None, True
    host_ink = _host_ink(primitives, host_id, catalog_patterns) if ink else None
    own: list[_Ground] = [(colour, f"{host_ink[1]}-substrate" if host_ink is not None else kind, host_id)]
    if host_ink is not None:
        own.append((host_ink[0], f"{host_ink[1]}-ink", host_id))
    if opacity == 1.0:
        groups = [[ground] for ground in own]
    else:
        _, beneath, unsupported = _grounds_under(host, primitives, host_index, canvas, sample, label=label,
                                                  cones=cones, catalog_patterns=catalog_patterns, ink=ink,
                                                  composite=composite)
        if beneath is None:
            return host_id, None, unsupported
        groups = [[(blend_over(ink=own_colour, opacity=float(opacity), ground=under), _translucent(own_kind, under_kind),
                    host_id) for under, under_kind, _ in group]
                  for own_colour, own_kind, _ in own for group in beneath]
    if not ink:
        return host_id, _tinted(groups, label, primitives, index, host_id, cones), False
    completed, unreadable = _sparse_ground_layers(groups, host_id, label, primitives, index, cones)
    return (unreadable, None, True) if unreadable is not None else (host_id, completed, False)


def _sparse_ground_layers(groups: list[list[_Ground]], host_id: str | None,
                          label: Mapping[str, Any],
                          primitives: list[Any], subject_index: int,
                          cones: tuple[ConeGround, ...]
                          ) -> tuple[list[list[_Ground]], str | None]:
    """Interleave sparse frame/pattern ink and cones between host and subject.

    Bounds shortlist layers; their completed symbol/tile geometry decides contact.
    Each paint-order boundary is retained so a cone before a glyph tints its substrate, while a
    cone after it tints both the substrate and glyph ink. Existing ground groups remain as the
    conservative uncovered alternatives.
    """
    subject_box = label.get("bounds")
    if not isinstance(subject_box, Mapping):
        return _tinted(groups, label, primitives, subject_index, host_id, cones), None
    try:
        bounds = (float(subject_box["inline"]), float(subject_box["block"]),
                  float(subject_box["inlineSize"]), float(subject_box["blockSize"]))
    except (KeyError, TypeError, ValueError):
        return _tinted(groups, label, primitives, subject_index, host_id, cones), None

    host_key = (-1, -1)
    if host_id is not None:
        host_key = next(((item.get("paintOrder", 0), position)
                         for position, item in enumerate(primitives)
                         if isinstance(item, Mapping) and item.get("id") == host_id), host_key)
    actual_upper = primitives[subject_index]
    upper_order = actual_upper.get("paintOrder", 0)
    subject_key = (upper_order, subject_index)
    candidates: list[tuple[tuple[int, int], int, Mapping[str, Any]]] = []
    x, y, width, height = bounds
    for part_index, part in enumerate(primitives):
        patterned_ink = (isinstance(part, Mapping) and part.get("visualRole") == "canvas-texture"
                         and isinstance(part.get("paint"), Mapping) and part["paint"].get("fill") is None)
        if (not isinstance(part, Mapping) or not patterned_ink and (
                part.get("kind") != "Symbol" or not is_frame_glyph_role(part.get("visualRole")))):
            continue
        part_order = part.get("paintOrder", 0)
        if not isinstance(part_order, int) or isinstance(part_order, bool):
            continue
        key = (part_order, part_index)
        if not (host_key < key < subject_key):
            continue
        part_box = part.get("bounds")
        if not isinstance(part_box, Mapping):
            # A malformed candidate that could have touched is fail-closed by the ink reader.
            candidates.append((key, part_index, part))
            continue
        try:
            px, py = float(part_box["inline"]), float(part_box["block"])
            pw, ph = float(part_box["inlineSize"]), float(part_box["blockSize"])
        except (KeyError, TypeError, ValueError):
            candidates.append((key, part_index, part))
            continue
        if px < x + width and x < px + pw and py < y + height and y < py + ph:
            candidates.append((key, part_index, part))

    if not candidates:
        return _tinted(groups, label, primitives, subject_index, host_id, cones), None

    boundary_id = host_id
    for _, frame_index, frame in sorted(candidates, key=lambda item: item[0]):
        patterned_ink = frame.get("visualRole") == "canvas-texture"
        if patterned_ink:
            try:
                touches = pattern_ink_touches(frame, bounds)
            except InkTouchError:
                return groups, str(frame.get("id", "canvas-texture"))
            paint = frame["paint"]
            inks = [(frame["id"], paint["stroke"], float(paint.get("opacity", 1)))] if touches else []
            unreadable = None
        else:
            inks, unreadable = selected_symbol_ink((frame,), bounds, unreadable_identity="frame-glyph")
        if unreadable is not None:
            return groups, unreadable
        if not inks:
            continue
        # Cones up to this part tint the ground below it, but not its ink.
        groups = _tinted(groups, label, primitives, frame_index, boundary_id, cones)
        bases = [ground for group in groups for ground in group]
        for part_id, colour, opacity in inks:
            ink_kind = "pattern-ink" if patterned_ink else "frame-glyph-ink"
            if opacity == 1.0:
                painted = [(colour, ink_kind, part_id)]
            else:
                painted = [(blend_over(ink=colour, opacity=opacity, ground=base),
                            ink_kind, part_id) for base, _, _ in bases]
            groups = [*groups, painted]
        boundary_id = part_id
    return _tinted(groups, label, primitives, subject_index, boundary_id, cones), None


def _translucent(own_kind: str, under_kind: str) -> str:
    """The `groundKind` of a translucent host composited over a ground of kind `under_kind`."""
    prefix = "translucent" if own_kind in {"flat", "gradient-sample"} else f"translucent-{own_kind}"
    return f"{prefix}-over-{under_kind}"


def _tinted(groups: list[list[_Ground]], label: Mapping[str, Any], primitives: list[Any], index: int,
            host_id: str | None, cones: tuple[ConeGround, ...]) -> list[list[_Ground]]:
    """Each ground with the cones painted after its host and before the primitive composited over it (#890)."""
    overlay = _cone_overlay(cones, primitives, index, host_id)
    if not overlay:
        return groups
    return [[tinted for ground in group for tinted in _under_cone(overlay, label, *ground)] for group in groups]


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
    return valid_opacity(value)


def _string(value: Any, detail: str) -> str:
    _require(isinstance(value, str) and value, f"invalid {detail}")
    return value


def _require(condition: bool, detail: str) -> None:
    if not condition:
        raise SceneContrastPolicyError("E_SCENE_CONTRAST_DOCUMENT: " + detail)
