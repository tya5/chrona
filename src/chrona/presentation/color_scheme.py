"""Immutable Color Scheme validation and deterministic paint resolution."""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Mapping


class ColorSchemeError(ValueError):
    """Stable diagnostic emitted before Scene construction."""


_INTENTS = {"surface", "surfaceRaised", "text", "textMuted", "accent", "positive", "negative", "warning", "neutral"}


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
    result = {key: str(colors[key]) for key in _INTENTS}
    category = body.get("category")
    if category_key is not None:
        if not isinstance(category, list) or not category:
            raise ColorSchemeError("E_SCHEME_SCHEMA")
        result["category"] = str(category[category_index(content_identity, category_key, len(category))])
    return result
