"""Immutable Color Scheme validation and deterministic paint resolution."""
from __future__ import annotations

from typing import Any, Mapping

from chrona.presentation.model.semantic_registry import ContrastClass, contrast_bindings
from chrona.presentation.scene.paint_analysis import composited_contrast


class ColorSchemeError(ValueError):
    """Stable diagnostic emitted before Scene construction."""

    def __init__(self, diagnostic_id: str, source_ref: str = "/", detail: str | None = None):
        super().__init__(diagnostic_id)
        self.diagnostic_id = diagnostic_id
        self.source_ref = source_ref
        self.detail = detail


_INTENTS = {"surface", "surfaceRaised", "text", "textMuted", "accent", "positive", "negative", "warning", "neutral",
            "insideLabelPlanned", "insideLabelActual", "insideLabelSnapshot", "insideLabelScenario"}
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
        raise ColorSchemeError("E_SCHEME_SCHEMA") from error


_STATE_TEXT_CONTRAST_FLOORS = {"required": 4.5, "deemphasized": 3.0}


def _state_text_contrast(*, declared_roles: Mapping[str, Any], resolved_roles: Mapping[str, Any],
                         values: Mapping[str, Any], surface: str) -> None:
    """Enforce the finite state-text policy at Theme/Scheme closure.

    The check intentionally reads the declared treatment while resolving its
    colour from the completed Theme role: Scheme bindings must not sidestep a
    role's author-visible contrast declaration.
    """
    for binding in contrast_bindings(ContrastClass.STATE_TEXT):
        role = binding.theme_role
        path = f"/body/roles/{role}"
        declared = declared_roles.get(role)
        treatment = declared.get("contrastTreatment") if isinstance(declared, Mapping) else None
        if treatment not in _STATE_TEXT_CONTRAST_FLOORS:
            raise ColorSchemeError("E_SCHEME_STATE_TEXT_TREATMENT", path)
        if role == "variance-behind" and treatment != "required":
            raise ColorSchemeError("E_SCHEME_STATE_TEXT_TREATMENT", path)
        resolved = resolved_roles.get(role)
        token = resolved.get("fill") if isinstance(resolved, Mapping) else None
        value = values.get(token) if isinstance(token, str) else None
        if not isinstance(value, Mapping) or value.get("type") != "color" or not isinstance(value.get("value"), str):
            raise ColorSchemeError("E_SCHEME_STATE_TEXT_CONTRAST", f"{path}/fill")
        opacity = 1.0
        opacity_token = resolved.get("opacity") if isinstance(resolved, Mapping) else None
        if opacity_token is not None:
            opacity_value = values.get(opacity_token) if isinstance(opacity_token, str) else None
            if (not isinstance(opacity_value, Mapping) or opacity_value.get("type") != "number"
                    or not isinstance(opacity_value.get("value"), (int, float))):
                raise ColorSchemeError("E_SCHEME_STATE_TEXT_CONTRAST", f"{path}/opacity")
            opacity = float(opacity_value["value"])
        try:
            contrast = composited_contrast(fill=value["value"], opacity=opacity, ground=surface)
        except ValueError as error:
            raise ColorSchemeError("E_SCHEME_STATE_TEXT_CONTRAST", f"{path}/fill") from error
        if contrast < _STATE_TEXT_CONTRAST_FLOORS[treatment]:
            raise ColorSchemeError("E_SCHEME_STATE_TEXT_CONTRAST", f"{path}/fill",
                                   detail=f"{role}:{contrast:.2f}")


def resolve_color_scheme(scheme: Mapping[str, Any], *, content_identity: str) -> dict[str, str]:
    body = scheme.get("body", {})
    colors = body.get("colors") if isinstance(body, Mapping) else None
    provenance = body.get("provenance") if isinstance(body, Mapping) else None
    if scheme.get("version") != "chrona/color-scheme/v0.2" or scheme.get("kind") != "color-scheme" or not isinstance(colors, Mapping):
        raise ColorSchemeError("E_SCHEME_SCHEMA")
    if not isinstance(provenance, Mapping) or not all(provenance.get(k) for k in ("kind", "source", "license")):
        raise ColorSchemeError("E_SCHEME_PROVENANCE")
    if not _INTENTS.issubset(colors):
        raise ColorSchemeError("E_SCHEME_SCHEMA")
    if any(_contrast(str(colors["text"]), str(colors[surface])) < 4.5 for surface in ("surface", "surfaceRaised")):
        raise ColorSchemeError("E_SCHEME_CONTRAST")
    result = {key: str(colors[key]) for key in _INTENTS}
    categories = body.get("categories")
    if not isinstance(categories, Mapping) or not categories or any(not isinstance(slot, str) or not isinstance(color, str)
                                                                      for slot, color in categories.items()):
        raise ColorSchemeError("E_SCHEME_SCHEMA")
    result.update({f"category:{slot}": color for slot, color in categories.items()})
    return result


def resolve_theme(theme: Mapping[str, Any], scheme: Mapping[str, Any], *, scheme_content_identity: str) -> dict[str, Any]:
    """Produce the only concrete Theme value permitted to reach presentation adapters."""
    if theme.get("version") != "chrona/theme/v0.11" or theme.get("kind") != "theme":
        raise ColorSchemeError("E_SCHEME_THEME_BINDING")
    body = theme.get("body")
    if not isinstance(body, Mapping) or not isinstance(body.get("colorBindings"), Mapping):
        raise ColorSchemeError("E_SCHEME_THEME_BINDING")
    colors = resolve_color_scheme(scheme, content_identity=scheme_content_identity)
    values = dict(body.get("values", {}))
    roles = {name: dict(binding) for name, binding in body.get("roles", {}).items() if isinstance(binding, Mapping)}
    for target, intent in body["colorBindings"].items():
        if (not isinstance(target, str) or "." not in target or not isinstance(intent, str)
                or (intent not in _INTENTS and intent not in colors)):
            raise ColorSchemeError("E_SCHEME_INTENT_UNKNOWN")
        role, property_name = target.rsplit(".", 1)
        if property_name not in {"fill", "stroke", "gradientStart", "gradientEnd", "shadowColor"}:
            raise ColorSchemeError("E_SCHEME_THEME_BINDING")
        token = f"__scheme.{intent}.{target}"
        color = colors[intent]
        values[token] = {"type": "color", "value": color}
        roles.setdefault(role, {})[property_name] = token
    _state_text_contrast(declared_roles=body.get("roles", {}), resolved_roles=roles,
                         values=values, surface=colors["surface"])
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
                raise ColorSchemeError("E_SCHEME_INSIDE_LABEL_CONTRAST")
    declared_scales = body.get("colorScales", {})
    if not isinstance(declared_scales, Mapping):
        raise ColorSchemeError("E_SCHEME_THEME_BINDING")
    resolved_scales: dict[str, dict[str, dict[str, str]]] = {}
    for scale_id, declaration in declared_scales.items():
        slots = declaration.get("slots") if isinstance(declaration, Mapping) else None
        if not isinstance(scale_id, str) or not isinstance(slots, Mapping):
            raise ColorSchemeError("E_PRESENTATION_SCALE_MAPPING")
        resolved_slots = {str(value): str(slot) for value, slot in slots.items()}
        if any(f"category:{slot}" not in colors for slot in resolved_slots.values()):
            raise ColorSchemeError("E_PRESENTATION_SCALE_MAPPING")
        resolved_scales[scale_id] = {"slots": resolved_slots}
    return {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "id": theme.get("id"), "body": {"values": values, "roles": roles, "metrics": dict(body.get("metrics", {})), "colorScales": resolved_scales, "categorySlots": {key.removeprefix("category:"): value for key, value in colors.items() if key.startswith("category:")}}}
