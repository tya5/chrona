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


def package_providers(set_id: str) -> tuple[str, ...]:
    """The separately installed package providers (not `chrona.resources`) whose assets a set names, in declared order."""
    found: list[str] = []
    for asset in _sets()[set_id]:
        for part in ("metrics", "font"):
            locator = asset[part]["locator"]
            identity = locator.get("identity")
            if locator.get("provider") == "package" and identity != "chrona.resources" and identity not in found:
                found.append(str(identity))
    return tuple(found)


def draft_font_metrics(set_ids: tuple[str, ...], base: Mapping[str, Any],
                       unavailable: frozenset[str] = frozenset()) -> dict[str, Any]:
    """The draft font descriptor a preset's `fontSets` stand for (#429): `base` with its assets replaced by the union of the sets.

    A set adds candidates, it is not a requirement: an asset served by a provider named in `unavailable` is left out, so
    the Theme family list continues on installed fonts. Assets are deduplicated by (family, weight) and keep the declared
    order; an unknown id is refused by the schema, so it cannot reach here.
    """
    assets: list[Any] = []
    seen: set[tuple[str, int]] = set()
    for set_id in set_ids:
        for asset in _sets()[set_id]:
            if unavailable and any(asset[part]["locator"].get("identity") in unavailable for part in ("metrics", "font")):
                continue
            key = (str(asset["family"]).casefold(), int(asset["weight"]))
            if key not in seen:
                seen.add(key)
                assets.append(deepcopy(asset))
    return {**{key: deepcopy(value) for key, value in base.items() if key not in {"assets", "fontSet"}}, "assets": assets}
