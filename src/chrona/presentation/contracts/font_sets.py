"""Packaged font sets: a Render Context's `fontMetrics.fontSet` expands to its asset list (#1345).

A set is a name for an exact, identity-pinned asset list (`resources/fonts/font-sets.yaml`), so a Context that says
`fontSet: chrona.noto-sans` is the Context that lists those assets. Explicit `assets` stay valid; a Context states one or the
other. The sets are the declared closure; installed fonts (#1281) remain a fallback behind it, not part of it.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from functools import cache
from importlib.resources import files
from typing import Any

from chrona.resources import safe_load


@cache
def _sets() -> Mapping[str, Any]:
    value = safe_load(files("chrona.resources").joinpath("fonts", "font-sets.yaml").read_bytes())
    return value["sets"]


def font_set_ids() -> tuple[str, ...]:
    return tuple(_sets())


def expand_font_set(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """The Render Context value with a `fontMetrics.fontSet` replaced by the asset list it names (unchanged without one)."""
    body = value.get("body") if isinstance(value, Mapping) else None
    environment = body.get("environment") if isinstance(body, Mapping) else None
    metrics = environment.get("fontMetrics") if isinstance(environment, Mapping) else None
    if not isinstance(metrics, Mapping) or "fontSet" not in metrics or "assets" in metrics:
        return value
    assets = _sets().get(metrics["fontSet"])
    if assets is None:  # unchanged: the schema's enum refuses an unknown name with its pointer
        return value
    expanded = deepcopy(dict(value))
    target = expanded["body"]["environment"]["fontMetrics"]
    del target["fontSet"]
    target["assets"] = deepcopy(assets)
    return expanded
