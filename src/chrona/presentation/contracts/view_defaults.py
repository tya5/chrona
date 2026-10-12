"""The View members a Layout profile supplies by default (`viewDefaults`, #1341 slice 1).

The View is the thin connector between a project and a design: what names the project's ids stays in it, how the surface
looks and is laid out can live in the Layout profile. `viewDefaults` is a View body fragment holding the design members; this
ingress step overlays it by the View, member by member, before any resource is validated, so the merged View is validated as the
View it is. Pure and project-independent: it reads two mappings and returns a mapping.

Rule (the reviewer-approved design note on #1341, decision 2): a member the View declares replaces the design's whole member;
a member it omits takes the design's. The three members whose sub-members split between connection and design (`comparison`,
`rows`, `window`) merge one level down, creating omitted members from design sub-members only. A Layout profile without `viewDefaults`, or a
View that declares every member, is untouched.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import replace
from typing import Any

from chrona.presentation.contracts.diagnostics import PresentationResourceSource

WHOLE_MEMBERS = ("visibility", "axis", "deadlines", "shading", "timePresentation", "annotationPresentation",
                 "backgroundDecoration", "progressFill", "annotationPlacement")
SPLIT_MEMBERS: Mapping[str, tuple[str, ...]] = {
    "comparison": ("baselineMarks", "missingActualScope", "deltaUnit", "facets"),
    "rows": ("mode", "trackAllocation", "packing", "laneTable", "points", "items"),
    "window": ("marginDays",),
}


def merge_view_defaults(view: Mapping[str, Any], defaults: Mapping[str, Any]) -> dict[str, Any]:
    """The View with the design's defaults filled in under it (the View's own members win)."""
    merged = deepcopy(dict(view))
    body = merged.get("body")
    if not isinstance(body, dict):
        return merged
    for name in WHOLE_MEMBERS:
        if name in defaults and name not in body:
            body[name] = deepcopy(defaults[name])
    for name, members in SPLIT_MEMBERS.items():
        declared, offered = body.get(name), defaults.get(name)
        if not isinstance(offered, Mapping):
            continue
        if name not in body:
            supplied = {member: deepcopy(offered[member]) for member in members if member in offered}
            if supplied:
                body[name] = supplied
        elif isinstance(declared, dict):
            for member in members:
                if member in offered and member not in declared:
                    declared[member] = deepcopy(offered[member])
    return merged


def apply_view_defaults(sources: Sequence[PresentationResourceSource]) -> list[PresentationResourceSource]:
    """The sources with the first View overlaid on the first Layout profile's `viewDefaults`; unchanged without them."""
    layout = next((item for item in sources if item.identity.kind == "layout-profile" and isinstance(item.value, Mapping)), None)
    defaults = layout.value.get("viewDefaults") if layout is not None else None
    if not isinstance(defaults, Mapping) or not defaults:
        return list(sources)
    result = []
    done = False
    for item in sources:
        if not done and item.identity.kind == "view" and isinstance(item.value, Mapping):
            merged = merge_view_defaults(item.value, defaults)
            item = replace(item, value=merged)  # the identity stays the View file's: the Layout it pairs with is pinned too
            done = True
        result.append(item)
    return result
