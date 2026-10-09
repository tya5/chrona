"""Immutable Color Scheme validation and deterministic paint resolution."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from re import fullmatch
from typing import Any, Mapping

from chrona.presentation.annotation_kind_text import AnnotationKindTextError, kind_header
from chrona.presentation.model.semantic_registry import ContrastClass, contrast_bindings
from chrona.presentation.model.theme_tokens import ThemeTokenError, checked_horizontal_scale
from chrona.presentation.scene.capabilities import theme_role_property_consumer
from chrona.presentation.scene.contrast_policy import POLICY_MEMBERS, POLICY_SEVERITIES
from chrona.presentation.scene.paint_analysis import composited_contrast


class ColorSchemeError(ValueError):
    """Stable diagnostic emitted before Scene construction."""

    def __init__(self, diagnostic_id: str, source_ref: str = "/", detail: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.source_ref = source_ref
        self.detail = detail


def _shown(value: object) -> str:
    """Bound diagnostic operands and never include an invalid document value."""
    if isinstance(value, int) and not isinstance(value, bool) and value.bit_length() > 320:
        return f"<int bits={value.bit_length()}>"
    if value is None or isinstance(value, (str, int, float, bool)):
        text = repr(value)
        return text if len(text) <= 96 else text[:93] + "..."
    if isinstance(value, Mapping):
        return f"<mapping keys={len(value)}>"
    if isinstance(value, (list, tuple)):
        if len(value) <= 8 and all(
                item is None or isinstance(item, (str, int, float, bool)) for item in value):
            rendered = repr(value)
            if len(rendered) <= 96:
                return rendered
        sample = tuple(_shown(item) for item in value[:8])
        return f"<{type(value).__name__} length={len(value)} sample={sample!r}>"
    return f"<{type(value).__name__}>"


_INTENTS = {"surface", "surfaceRaised", "text", "textMuted", "accent", "positive", "negative", "warning", "neutral",
            "insideLabelPlanned", "insideLabelActual", "insideLabelSnapshot", "insideLabelScenario"}
# An intent a Scheme may declare and need not (#991): the line colour of rules and separators.
_OPTIONAL_INTENTS = frozenset({"rule"})
_INSIDE_LABEL_HOSTS = {
    "member-label-inside-planned": "planned",
    "member-label-inside-actual": "actual",
    "member-label-inside-snapshot": "snapshot",
    "member-label-inside-scenario": "snapshot",
}
_INSIDE_LABEL_INTENTS = {
    "member-label-inside-planned": "insideLabelPlanned",
    "member-label-inside-actual": "insideLabelActual",
    "member-label-inside-snapshot": "insideLabelSnapshot",
    "member-label-inside-scenario": "insideLabelScenario",
}


def _contrast(first: str, second: str) -> float:
    try:
        return composited_contrast(fill=first, opacity=1.0, ground=second)
    except ValueError as error:
        raise ColorSchemeError("E_SCHEME_SCHEMA", detail=f"color operands expected #RRGGBB; firstType={type(first).__name__}, secondType={type(second).__name__}") from error


_STATE_TEXT_CONTRAST_FLOORS = {"required": 4.5, "deemphasized": 3.0}
# State-text roles a Theme may omit entirely: the feature they belong to is opt-in. A declared one is still checked.
_OPTIONAL_STATE_TEXT_ROLES = frozenset({"annotation-note-text", "period-label"})
# The annotation kind header text (#584) lies on a per-kind bar, not on the canvas surface, so it is judged
# against its real grounds by `_annotation_kind_text_contrast` instead of by `_state_text_contrast`.
_KIND_TEXT_ROLES = ("annotation-kind-label", "annotation-kind-secondary", "annotation-heading")
_KIND_BOX_ROLES = ("annotation-callout-box", "annotation-highlight-box", "annotation-note-box", "annotation-arrow-box")
# Note prose lies on its own note box (the Scene gate pairs them, #466), never on the canvas it floats above (#950).
_NOTE_TEXT_ROLE = "annotation-note-text"
_NOTE_BOX_ROLE = "annotation-note-box"


def _state_text_ground(role: str, *, resolved_roles: Mapping[str, Any], values: Mapping[str, Any],
                       surface: str) -> tuple[str, str | None]:
    """The colour a state-text role lies on, and the box role that supplies it (None for the canvas).

    Note prose is judged on the resolved note box fill, the ground the Scene gate reads; the canvas only
    where the box declares no readable colour. Every other state text lies on the canvas surface.
    """
    if role == _NOTE_TEXT_ROLE:
        box = _role_color(resolved_roles, values, _NOTE_BOX_ROLE)
        if box is not None and fullmatch(r"#[0-9A-Fa-f]{6}", box) is not None:
            return box, _NOTE_BOX_ROLE
    return surface, None


def _state_text_contrast(*, declared_roles: Mapping[str, Any], resolved_roles: Mapping[str, Any],
                         values: Mapping[str, Any], surface: str) -> None:
    """Enforce the finite state-text policy at Theme/Scheme closure.

    The check intentionally reads the declared treatment while resolving its
    colour from the completed Theme role: Scheme bindings must not sidestep a
    role's author-visible contrast declaration.
    """
    for binding in contrast_bindings(ContrastClass.STATE_TEXT):
        role = binding.theme_role
        if role in _KIND_TEXT_ROLES:
            continue
        path = f"/body/roles/{role}"
        declared = declared_roles.get(role)
        if role in _OPTIONAL_STATE_TEXT_ROLES and not isinstance(declared, Mapping) and role not in resolved_roles:
            continue
        treatment = declared.get("contrastTreatment") if isinstance(declared, Mapping) else None
        if role == "annotation-note-text" and treatment != "required":
            raise ColorSchemeError("E_SCHEME_STATE_TEXT_TREATMENT", f"{path}/contrastTreatment",
                                   f"role={_shown(role)}, treatment={_shown(treatment)}; expected required")
        if treatment not in _STATE_TEXT_CONTRAST_FLOORS:
            raise ColorSchemeError("E_SCHEME_STATE_TEXT_TREATMENT", path,
                                   f"role={_shown(role)}, treatment={_shown(treatment)}; expected required or deemphasized")
        if role == "variance-behind" and treatment != "required":
            raise ColorSchemeError("E_SCHEME_STATE_TEXT_TREATMENT", path,
                                   f"role={_shown(role)}, treatment={_shown(treatment)}; expected required for variance-behind")
        resolved = resolved_roles.get(role)
        token = resolved.get("fill") if isinstance(resolved, Mapping) else None
        value = values.get(token) if isinstance(token, str) else None
        if not isinstance(value, Mapping) or value.get("type") != "color" or not isinstance(value.get("value"), str):
            raise ColorSchemeError("E_SCHEME_STATE_TEXT_CONTRAST", f"{path}/fill",
                                   detail=f"role={_shown(role)}, token={_shown(token)}, valueType={type(value).__name__}; expected color token with string value")
        opacity = 1.0
        opacity_token = resolved.get("opacity") if isinstance(resolved, Mapping) else None
        if opacity_token is not None:
            opacity_value = values.get(opacity_token) if isinstance(opacity_token, str) else None
            if (not isinstance(opacity_value, Mapping) or opacity_value.get("type") != "number"
                    or not isinstance(opacity_value.get("value"), (int, float))):
                raise ColorSchemeError("E_SCHEME_STATE_TEXT_CONTRAST", f"{path}/opacity",
                                       detail=f"role={_shown(role)}, token={_shown(opacity_token)}, valueType={type(opacity_value).__name__}; expected numeric opacity token")
            opacity = float(opacity_value["value"])
        try:
            ground, box_role = _state_text_ground(role, resolved_roles=resolved_roles, values=values,
                                                  surface=surface)
            contrast = composited_contrast(fill=value["value"], opacity=opacity, ground=ground)
        except ValueError as error:
            raise ColorSchemeError("E_SCHEME_STATE_TEXT_CONTRAST", f"{path}/fill") from error
        if contrast < _STATE_TEXT_CONTRAST_FLOORS[treatment]:
            raise ColorSchemeError("E_SCHEME_STATE_TEXT_CONTRAST", f"{path}/fill",
                                   detail=(f"{_shown(role)}:{contrast:.2f}" if box_role is None
                                           else f"{_shown(role)}:{_shown(box_role)}:{contrast:.2f}"))


def _role_color(roles: Mapping[str, Any], values: Mapping[str, Any], role: str, property_name: str = "fill") -> str | None:
    """The resolved ``#RRGGBB`` of one role property, or None when the role does not declare it."""
    binding = roles.get(role)
    token = binding.get(property_name) if isinstance(binding, Mapping) else None
    value = values.get(token) if isinstance(token, str) else None
    if isinstance(value, Mapping) and value.get("type") == "color" and isinstance(value.get("value"), str):
        return str(value["value"])
    return None


def _annotation_kinds(*, declared: Any, colors: Mapping[str, str]) -> dict[str, dict[str, str]]:
    """Validate the Theme's `annotationKinds` and resolve each kind colour (#584)."""
    if declared is None:
        return {}
    if not isinstance(declared, Mapping):
        raise ColorSchemeError("E_THEME_ANNOTATION_KIND_TEMPLATE", "/body/annotationKinds",
                               f"valueType={type(declared).__name__}; expected mapping of kind identifiers to declarations")
    resolved: dict[str, dict[str, str]] = {}
    for kind, declaration in declared.items():
        pointer = f"/body/annotationKinds/{kind}"
        if not isinstance(kind, str) or not kind or not isinstance(declaration, Mapping):
            raise ColorSchemeError("E_THEME_ANNOTATION_KIND_TEMPLATE", pointer,
                                   f"kindType={type(kind).__name__}, declarationType={type(declaration).__name__}; expected nonempty id and mapping")
        try:
            kind_header(kind, declaration)
        except AnnotationKindTextError as error:
            raise ColorSchemeError(error.code, pointer, error.detail) from error
        entry = {name: str(declaration[name]) for name in ("label", "secondary", "title", "heading", "stamp") if name in declaration}
        intent = declaration.get("color")
        if intent is not None:
            if not isinstance(intent, str) or (intent not in _INTENTS and intent not in colors):
                raise ColorSchemeError("E_SCHEME_INTENT_UNKNOWN", f"{pointer}/color",
                                       f"intent={_shown(intent)}; expected one of declared scheme intents or color category slots")
            entry["color"] = colors[intent]
        also = declaration.get("colorAlso")
        if also is not None:
            if (not isinstance(also, (list, tuple)) or not also or len(set(also)) != len(also)
                    or any(item not in {"header", "leader"} for item in also) or intent is None):
                raise ColorSchemeError("E_THEME_ANNOTATION_KIND_TEMPLATE", f"{pointer}/colorAlso",
                                       f"valueType={type(also).__name__}, colorIntent={_shown(intent)}; expected unique nonempty header/leader list and a color intent")
            entry["colorAlso"] = list(also)
        resolved[kind] = entry
    return resolved


def _horizontal_scales(*, declared_roles: Mapping[str, Any], values: Mapping[str, Any]) -> None:
    """Reject a declared horizontal compression outside its range at the Theme, whether or not a role is used (#585)."""
    for role, binding in declared_roles.items():
        if not isinstance(binding, Mapping) or "horizontalScale" not in binding:
            continue
        pointer = f"/body/roles/{role}/horizontalScale"
        declared = values.get(binding["horizontalScale"])
        if not isinstance(declared, Mapping) or declared.get("type") != "number" or "value" not in declared:
            raise ColorSchemeError("E_THEME_TOKEN_TYPE", pointer,
                                   f"role={_shown(role)}, property='horizontalScale', token={_shown(binding['horizontalScale'])}, declarationType={type(declared).__name__}; expected number token")
        try:
            checked_horizontal_scale(Decimal(str(declared["value"])), pointer)
        except InvalidOperation as error:
            raise ColorSchemeError("E_THEME_TOKEN_TYPE", pointer,
                                   f"role={role!r}, property='horizontalScale', valueType={type(declared['value']).__name__}; expected finite number in [0.5, 1]") from error
        except ThemeTokenError as error:
            raise ColorSchemeError(error.diagnostic_id, pointer, detail=str(declared["value"])) from error


def _writing_modes(*, declared_roles: Mapping[str, Any], values: Mapping[str, Any]) -> None:
    """Validate every declared writing mode and reject one combined with a horizontal compression (#585)."""
    for role, binding in declared_roles.items():
        if not isinstance(binding, Mapping) or "writingMode" not in binding:
            continue
        pointer = f"/body/roles/{role}/writingMode"
        declared = values.get(binding["writingMode"])
        if (not isinstance(declared, Mapping) or declared.get("type") != "writingMode"
                or declared.get("value") not in {"horizontal", "vertical"}):
            raise ColorSchemeError("E_THEME_TOKEN_TYPE", pointer,
                                   f"role={_shown(role)}, property='writingMode', token={_shown(binding['writingMode'])}, valueType={type(declared).__name__}; expected horizontal or vertical writingMode token")
        if declared["value"] == "vertical" and "horizontalScale" in binding:
            scale = values.get(binding["horizontalScale"])
            if isinstance(scale, Mapping) and Decimal(str(scale.get("value", 1))) != 1:
                raise ColorSchemeError("E_THEME_TEXT_TREATMENT_CONFLICT", f"/body/roles/{role}/horizontalScale",
                                       detail="a horizontal scale has no meaning on a vertical inline axis")


def _annotation_kind_text_contrast(*, declared_roles: Mapping[str, Any], resolved_roles: Mapping[str, Any],
                                   values: Mapping[str, Any], kinds: Mapping[str, Mapping[str, str]]) -> None:
    """Judge the kind header text against the grounds it lies on (#584).

    With a bar role the ground is each declared kind's colour (the bar's own fill for a kind
    without one); without a bar the text lies on the note box, so every declared box fill is a ground.
    """
    for role in _KIND_TEXT_ROLES:
        declared = declared_roles.get(role)
        if not isinstance(declared, Mapping) and role not in resolved_roles:
            continue
        path = f"/body/roles/{role}"
        treatment = declared.get("contrastTreatment") if isinstance(declared, Mapping) else None
        if treatment not in _STATE_TEXT_CONTRAST_FLOORS:
            raise ColorSchemeError("E_SCHEME_STATE_TEXT_TREATMENT", path,
                                   f"role={_shown(role)}, treatment={_shown(treatment)}; expected required or deemphasized")
        ink = _role_color(resolved_roles, values, role)
        if ink is None:
            raise ColorSchemeError("E_SCHEME_STATE_TEXT_CONTRAST", f"{path}/fill")
        grounds: list[tuple[str, str, str]] = []  # (name, ink, ground)
        bar_fill = _role_color(resolved_roles, values, "annotation-kind-bar")
        if "annotation-kind-bar" in resolved_roles and role != "annotation-heading":
            if kinds:
                for kind, entry in kinds.items():
                    ground = entry.get("color", bar_fill)
                    # A kind whose colour also paints its header text (`colorAlso`, #991) writes in that colour.
                    kind_ink = entry["color"] if "header" in entry.get("colorAlso", ()) and "color" in entry else ink
                    if ground is not None:
                        grounds.append((kind, kind_ink, ground))
            elif bar_fill is not None:
                grounds.append(("bar", ink, bar_fill))
        else:
            for box in _KIND_BOX_ROLES:
                ground = _role_color(resolved_roles, values, box)
                if ground is None:
                    continue
                grounds.append((box, ink, ground))
                for kind, entry in kinds.items():
                    if "header" in entry.get("colorAlso", ()) and "color" in entry:
                        grounds.append((f"{kind}:{box}", entry["color"], ground))
        for name, text_ink, ground in grounds:
            contrast = _contrast(text_ink, ground)
            if contrast < _STATE_TEXT_CONTRAST_FLOORS[treatment]:
                raise ColorSchemeError("E_SCHEME_ANNOTATION_KIND_CONTRAST", f"{path}/fill",
                                       detail=f"{_shown(role)}:{_shown(name)}:{contrast:.2f}")


def _annotation_note_ground(*, declared_roles: Mapping[str, Any], resolved_roles: Mapping[str, Any],
                            values: Mapping[str, Any], color_bindings: Mapping[str, Any]) -> None:
    """Require the note box's resolved representative fill to be opaque and flat."""
    role = "annotation-note-box"
    declared = declared_roles.get(role)
    if (not isinstance(declared, Mapping) and role not in resolved_roles
            and "annotation-note-text" not in declared_roles
            and not any(isinstance(target, str) and target.startswith(f"{role}.")
                        for target in color_bindings)):
        return
    resolved = resolved_roles.get(role)
    if isinstance(resolved, Mapping):
        for property_name in ("gradientStart", "gradientEnd", "gradientAngle", "gradientFidelity", "pattern"):
            if property_name not in resolved:
                continue
            target = f"{role}.{property_name}"
            pointer = (f"/body/colorBindings/{target}" if target in color_bindings
                       else f"/body/roles/{role}/{property_name}")
            raise ColorSchemeError("E_SCHEME_ANNOTATION_NOTE_GROUND", pointer,
                                   f"role={_shown(role)}, property={_shown(property_name)}; note text requires flat opaque solid fill")
    fill_pointer = (f"/body/colorBindings/{role}.fill" if f"{role}.fill" in color_bindings
                    else f"/body/roles/{role}/fill")
    token = resolved.get("fill") if isinstance(resolved, Mapping) else None
    value = values.get(token) if isinstance(token, str) else None
    if (not isinstance(value, Mapping) or value.get("type") != "color"
            or not isinstance(value.get("value"), str)
            or fullmatch(r"#[0-9A-Fa-f]{6}", value["value"]) is None):
        raise ColorSchemeError("E_SCHEME_ANNOTATION_NOTE_GROUND", fill_pointer,
                               f"role={_shown(role)}, token={_shown(token)}, valueType={type(value).__name__}; expected opaque #RRGGBB color token")

    opacity_token = resolved.get("opacity") if isinstance(resolved, Mapping) else None
    if opacity_token is None:
        return
    opacity_value = values.get(opacity_token) if isinstance(opacity_token, str) else None
    if (not isinstance(opacity_value, Mapping) or opacity_value.get("type") != "number"
            or not isinstance(opacity_value.get("value"), (int, float))
            or isinstance(opacity_value.get("value"), bool)
            or float(opacity_value["value"]) != 1.0):
        raise ColorSchemeError("E_SCHEME_ANNOTATION_NOTE_GROUND", f"/body/roles/{role}/opacity",
                               f"role={_shown(role)}, token={_shown(opacity_token)}, valueType={type(opacity_value).__name__}; expected opacity 1")


def _canvas_texture(*, roles: Mapping[str, Any], values: Mapping[str, Any]) -> None:
    """Require the canvas texture role to name a finite repeating pattern (#587, #888).

    Fill (substrate) and stroke (ink) are checked with the other catalogue-pattern
    paint by resource closure. An inline pattern has no tile, so it cannot be a texture.
    Seeded patterns are Layout-completed from their explicit finite declaration.
    """
    binding = roles.get("canvas-texture")
    if not isinstance(binding, Mapping):
        return
    token_id = binding.get("pattern")
    pointer = "/body/roles/canvas-texture/pattern"
    if not isinstance(token_id, str):
        raise ColorSchemeError("E_THEME_ROLE_REQUIRED", pointer,
                               f"role='canvas-texture', pattern={_shown(token_id)}; expected catalog or seeded pattern token name")
    token = values.get(token_id)
    value = token.get("value") if isinstance(token, Mapping) else None
    if not isinstance(value, Mapping) or value.get("kind") not in {"catalog", "seeded"}:
        raise ColorSchemeError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", pointer,
                               f"role='canvas-texture', token={_shown(token_id)}, valueType={type(value).__name__}; expected catalog or seeded pattern")


def _contrast_policy(declared: Any) -> dict[str, str]:
    """Validate the Theme's `contrastPolicy` (#995, #1126) and return it, empty when it declares nothing.

    Contrast constraints are an opt-in design option: each member (`mark`, `stateText`, `groundText`,
    `decoration`, `unsupportedGround`) is `none`, `warning` or `error`; a member the Theme omits is `warning`
    at render. A structural gate is not a contrast constraint and has no member.
    """
    if declared is None:
        return {}
    if not isinstance(declared, Mapping):
        raise ColorSchemeError("E_THEME_CONTRAST_POLICY", "/body/contrastPolicy")
    for member, severity in declared.items():
        if member not in POLICY_MEMBERS:
            raise ColorSchemeError("E_THEME_CONTRAST_POLICY", f"/body/contrastPolicy/{member}")
        if severity not in POLICY_SEVERITIES:
            raise ColorSchemeError("E_THEME_CONTRAST_POLICY", f"/body/contrastPolicy/{member}",
                                   detail=f"expected one of {', '.join(POLICY_SEVERITIES)}")
    return dict(declared)


def _as_of_cone(*, roles: Mapping[str, Any]) -> None:
    """Require the as-of cone role to declare its ink, spread and extent (#890).

    Range limits are Layout's (it owns the geometry); a role that names none of them is no cone.
    """
    binding = roles.get("as-of-cone")
    if not isinstance(binding, Mapping):
        return
    for property_name in ("fill", "coneSpread", "coneExtent"):
        if not isinstance(binding.get(property_name), str):
            raise ColorSchemeError("E_THEME_ROLE_REQUIRED", f"/body/roles/as-of-cone/{property_name}")


def resolve_color_scheme(scheme: Mapping[str, Any], *, content_identity: str) -> dict[str, str]:
    body = scheme.get("body", {})
    colors = body.get("colors") if isinstance(body, Mapping) else None
    provenance = body.get("provenance") if isinstance(body, Mapping) else None
    if scheme.get("version") != "chrona/color-scheme/v0.2" or scheme.get("kind") != "color-scheme" or not isinstance(colors, Mapping):
        raise ColorSchemeError("E_SCHEME_SCHEMA", detail=f"kind={_shown(scheme.get('kind'))}, version={_shown(scheme.get('version'))}, colorsType={type(colors).__name__}; expected color-scheme v0.2 with color mapping")
    if not isinstance(provenance, Mapping) or not all(provenance.get(k) for k in ("kind", "source", "license")):
        missing = tuple(k for k in ("kind", "source", "license") if not isinstance(provenance, Mapping) or not provenance.get(k))
        raise ColorSchemeError("E_SCHEME_PROVENANCE", "/body/provenance",
                               f"missing or empty provenance fields={_shown(missing)}; expected kind, source, and license")
    if not _INTENTS.issubset(colors):
        raise ColorSchemeError("E_SCHEME_SCHEMA", "/body/colors",
                               f"missing intents={_shown(tuple(sorted(_INTENTS - set(colors))))}; expected all required color intents")
    if any(_contrast(str(colors["text"]), str(colors[surface])) < 4.5 for surface in ("surface", "surfaceRaised")):
        raise ColorSchemeError("E_SCHEME_CONTRAST", "/body/colors/text",
                               "text color must meet 4.5:1 against surface and surfaceRaised")
    result = {key: str(colors[key]) for key in _INTENTS}
    result.update({key: str(colors[key]) for key in _OPTIONAL_INTENTS if key in colors})
    categories = body.get("categories")
    if not isinstance(categories, Mapping) or not categories or any(not isinstance(slot, str) or not isinstance(color, str)
                                                                      for slot, color in categories.items()):
        invalid = next(((slot, type(color).__name__) for slot, color in categories.items()
                        if not isinstance(slot, str) or not isinstance(color, str)), None) if isinstance(categories, Mapping) else None
        raise ColorSchemeError("E_SCHEME_SCHEMA", "/body/categories",
                               f"categoriesType={type(categories).__name__}, invalidEntry={_shown(invalid)}; expected nonempty string-to-color mapping")
    result.update({f"category:{slot}": color for slot, color in categories.items()})
    return result


def resolve_theme(theme: Mapping[str, Any], scheme: Mapping[str, Any], *, scheme_content_identity: str) -> dict[str, Any]:
    """Produce the only concrete Theme value permitted to reach presentation adapters."""
    if theme.get("version") != "chrona/theme/v0.15" or theme.get("kind") != "theme":
        raise ColorSchemeError("E_SCHEME_THEME_BINDING", detail=f"kind={_shown(theme.get('kind'))}, version={_shown(theme.get('version'))}; expected theme v0.15")
    body = theme.get("body")
    if not isinstance(body, Mapping) or not isinstance(body.get("colorBindings"), Mapping):
        raise ColorSchemeError("E_SCHEME_THEME_BINDING", "/body/colorBindings",
                               f"bodyType={type(body).__name__}, colorBindingsType={type(body.get('colorBindings') if isinstance(body, Mapping) else None).__name__}; expected binding mapping")
    colors = resolve_color_scheme(scheme, content_identity=scheme_content_identity)
    values = dict(body.get("values", {}))
    roles = {name: dict(binding) for name, binding in body.get("roles", {}).items() if isinstance(binding, Mapping)}
    for role, binding in roles.items():
        for property_name in binding:
            if theme_role_property_consumer(role, property_name) is None:
                raise ColorSchemeError("E_THEME_ROLE_PROPERTY_UNSUPPORTED",
                                       f"/body/roles/{role}/{property_name}")
    for target, intent in body["colorBindings"].items():
        target_pointer = target if isinstance(target, str) and len(target) <= 120 else "<long-target>"
        if (not isinstance(target, str) or "." not in target or not isinstance(intent, str)
                or (intent not in _INTENTS and intent not in colors)):
            raise ColorSchemeError("E_SCHEME_INTENT_UNKNOWN", f"/body/colorBindings/{target_pointer}",
                                   f"target={_shown(target)}, intent={_shown(intent)}; expected role.property and a declared intent/category")
        role, property_name = target.rsplit(".", 1)
        if property_name not in {"fill", "stroke", "gradientStart", "gradientEnd", "shadowColor", "glowColor"}:
            raise ColorSchemeError("E_SCHEME_THEME_BINDING", f"/body/colorBindings/{target_pointer}",
                                   f"property={_shown(property_name)}; expected one of fill, stroke, gradientStart, gradientEnd, shadowColor, glowColor")
        if theme_role_property_consumer(role, property_name) is None:
            raise ColorSchemeError("E_THEME_ROLE_PROPERTY_UNSUPPORTED", f"/body/colorBindings/{target_pointer}")
        token = f"__scheme.{intent}.{target}"
        color = colors[intent]
        values[token] = {"type": "color", "value": color}
        roles.setdefault(role, {})[property_name] = token
    _horizontal_scales(declared_roles=body.get("roles", {}), values=values)
    _writing_modes(declared_roles=body.get("roles", {}), values=values)
    _state_text_contrast(declared_roles=body.get("roles", {}), resolved_roles=roles,
                         values=values, surface=colors["surface"])
    annotation_kinds = _annotation_kinds(declared=body.get("annotationKinds"), colors=colors)
    if any("heading" in entry for entry in annotation_kinds.values()) and "annotation-heading" not in roles:
        raise ColorSchemeError("E_THEME_ROLE_REQUIRED", "/body/roles/annotation-heading")
    _annotation_kind_text_contrast(declared_roles=body.get("roles", {}), resolved_roles=roles,
                                   values=values, kinds=annotation_kinds)
    _annotation_note_ground(declared_roles=body.get("roles", {}), resolved_roles=roles,
                            values=values, color_bindings=body["colorBindings"])
    _canvas_texture(roles=roles, values=values)
    _as_of_cone(roles=roles)
    contrast_policy = _contrast_policy(body.get("contrastPolicy"))
    inside_roles = set(_INSIDE_LABEL_HOSTS)
    if inside_roles & set(roles):
        for label_role, host_role in _INSIDE_LABEL_HOSTS.items():
            label_token = roles.get(label_role, {}).get("fill")
            host_token = roles.get(host_role, {}).get("fill")
            label_value = values.get(label_token) if isinstance(label_token, str) else None
            host_value = values.get(host_token) if isinstance(host_token, str) else None
            if (body["colorBindings"].get(f"{label_role}.fill") != _INSIDE_LABEL_INTENTS[label_role]
                    or not isinstance(label_value, Mapping) or label_value.get("type") != "color"
                    or not isinstance(host_value, Mapping) or host_value.get("type") != "color"
                    or _contrast(str(label_value.get("value")), str(host_value.get("value"))) < 4.5):
                raise ColorSchemeError("E_SCHEME_INSIDE_LABEL_CONTRAST", f"/body/colorBindings/{label_role}.fill",
                                       f"labelRole={_shown(label_role)}, hostRole={_shown(host_role)}, intent={_shown(body['colorBindings'].get(f'{label_role}.fill'))}; expected {_INSIDE_LABEL_INTENTS[label_role]} with contrast at least 4.5")
    declared_scales = body.get("colorScales", {})
    if not isinstance(declared_scales, Mapping):
        raise ColorSchemeError("E_SCHEME_THEME_BINDING", "/body/colorScales",
                               f"colorScalesType={type(declared_scales).__name__}; expected mapping of scale identifiers")
    resolved_scales: dict[str, dict[str, dict[str, str]]] = {}
    for scale_id, declaration in declared_scales.items():
        scale_pointer = scale_id if isinstance(scale_id, str) and len(scale_id) <= 120 else "<long-scale>"
        slots = declaration.get("slots") if isinstance(declaration, Mapping) else None
        palette = declaration.get("palette") if isinstance(declaration, Mapping) else None
        if isinstance(scale_id, str) and isinstance(palette, (list, tuple)) and palette:
            resolved_palette = [str(slot) for slot in palette]
            if any(f"category:{slot}" not in colors for slot in resolved_palette):
                missing = tuple(slot for slot in resolved_palette if f"category:{slot}" not in colors)
                raise ColorSchemeError("E_PRESENTATION_SCALE_MAPPING", f"/body/colorScales/{scale_pointer}/palette",
                                       f"missing category slots={_shown(missing)}; expected declared scheme categories")
            resolved_scales[scale_id] = {"palette": resolved_palette}
            continue
        if not isinstance(scale_id, str) or not isinstance(slots, Mapping):
            raise ColorSchemeError("E_PRESENTATION_SCALE_MAPPING", f"/body/colorScales/{scale_pointer}",
                                   f"scaleIdType={type(scale_id).__name__}, slotsType={type(slots).__name__}; expected scale id and slots mapping or palette")
        resolved_slots = {str(value): str(slot) for value, slot in slots.items()}
        if any(f"category:{slot}" not in colors for slot in resolved_slots.values()):
            missing = tuple(sorted({slot for slot in resolved_slots.values() if f"category:{slot}" not in colors}))
            raise ColorSchemeError("E_PRESENTATION_SCALE_MAPPING", f"/body/colorScales/{scale_pointer}/slots",
                                   f"missing category slots={_shown(missing)}; expected declared scheme categories")
        resolved_scales[scale_id] = {"slots": resolved_slots}
    suitability = scheme.get("body", {}).get("suitability", {}) if isinstance(scheme.get("body"), Mapping) else {}
    claimed = suitability.get("colorVision", ()) if isinstance(suitability, Mapping) else ()
    color_vision = [str(item) for item in claimed if item != "none-claimed"]
    return {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "id": theme.get("id"), "body": {"values": values, "roles": roles, "metrics": dict(body.get("metrics", {})), "colorScales": resolved_scales, **({"markStack": body["markStack"]} if "markStack" in body else {}), **({"annotationKinds": annotation_kinds} if annotation_kinds else {}), **({"contrastPolicy": contrast_policy} if contrast_policy else {}), "categorySlots": {key.removeprefix("category:"): value for key, value in colors.items() if key.startswith("category:")}, "colorVision": color_vision}}
