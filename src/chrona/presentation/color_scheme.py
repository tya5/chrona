"""Immutable Color Scheme validation and deterministic paint resolution."""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping


class ColorSchemeError(ValueError):
    """Stable diagnostic emitted before Scene construction."""


_INTENTS = {"surface", "surfaceRaised", "text", "textMuted", "accent", "positive", "negative", "warning", "neutral"}


def _luminance(color: str) -> float:
    if not isinstance(color, str) or len(color) != 7 or not color.startswith("#"):
        raise ColorSchemeError("E_SCHEME_SCHEMA")
    try:
        channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    except ValueError as error:
        raise ColorSchemeError("E_SCHEME_SCHEMA") from error
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    low, high = sorted((_luminance(first), _luminance(second)))
    return (high + 0.05) / (low + 0.05)


def category_index(content_identity: str, key: str, count: int) -> int:
    if count < 1:
        raise ColorSchemeError("E_SCHEME_SCHEMA")
    digest = sha256((content_identity + "\0" + key).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % count


def resolve_color_scheme(scheme: Mapping[str, Any], *, content_identity: str, category_key: str | None = None) -> dict[str, str]:
    body = scheme.get("body", {})
    colors = body.get("colors") if isinstance(body, Mapping) else None
    provenance = body.get("provenance") if isinstance(body, Mapping) else None
    if scheme.get("version") != "chrona/color-scheme/v0.1" or scheme.get("kind") != "color-scheme" or not isinstance(colors, Mapping):
        raise ColorSchemeError("E_SCHEME_SCHEMA")
    if not isinstance(provenance, Mapping) or not all(provenance.get(k) for k in ("kind", "source", "license")):
        raise ColorSchemeError("E_SCHEME_PROVENANCE")
    if not _INTENTS.issubset(colors):
        raise ColorSchemeError("E_SCHEME_SCHEMA")
    if any(_contrast(str(colors["text"]), str(colors[surface])) < 4.5 for surface in ("surface", "surfaceRaised")):
        raise ColorSchemeError("E_SCHEME_CONTRAST")
    result = {key: str(colors[key]) for key in _INTENTS}
    category = body.get("category")
    if category_key is not None:
        if not isinstance(category, list) or not category:
            raise ColorSchemeError("E_SCHEME_SCHEMA")
        result["category"] = str(category[category_index(content_identity, category_key, len(category))])
    return result


def resolve_theme(theme: Mapping[str, Any], scheme: Mapping[str, Any], *, scheme_content_identity: str) -> dict[str, Any]:
    """Produce the only concrete Theme value permitted to reach presentation adapters."""
    if theme.get("version") != "chrona/theme/v0.2" or theme.get("kind") != "theme":
        raise ColorSchemeError("E_SCHEME_THEME_BINDING")
    body = theme.get("body")
    if not isinstance(body, Mapping) or not isinstance(body.get("colorBindings"), Mapping):
        raise ColorSchemeError("E_SCHEME_THEME_BINDING")
    colors = resolve_color_scheme(scheme, content_identity=scheme_content_identity)
    values = dict(body.get("values", {}))
    roles = {name: dict(binding) for name, binding in body.get("roles", {}).items() if isinstance(binding, Mapping)}
    for target, intent in body["colorBindings"].items():
        if not isinstance(target, str) or "." not in target or intent not in _INTENTS | {"category"}:
            raise ColorSchemeError("E_SCHEME_INTENT_UNKNOWN")
        role, property_name = target.rsplit(".", 1)
        if property_name not in {"fill", "stroke"}:
            raise ColorSchemeError("E_SCHEME_THEME_BINDING")
        token = f"__scheme.{intent}.{target}"
        color = colors[intent] if intent != "category" else resolve_color_scheme(scheme, content_identity=scheme_content_identity, category_key=target)["category"]
        values[token] = {"type": "color", "value": color}
        roles.setdefault(role, {})[property_name] = token
    return {"version": "chrona/resolved-theme/v0.2", "kind": "resolved-theme", "id": theme.get("id"), "body": {"values": values, "roles": roles, "metrics": dict(body.get("metrics", {}))}}
