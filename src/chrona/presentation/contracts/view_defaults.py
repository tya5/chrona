"""Close a Layout profile's project-independent presentation beneath the View.

The View is the thin connector between a project and a design: what names the project's ids stays in it, how the surface
looks and is laid out can live in the Layout profile. `viewDefaults` is a View body fragment holding the design members; this
ingress step overlays it by the View, member by member, before any resource is validated, so the merged View is validated as the
View it is. Pure and project-independent: it reads two mappings and returns a mapping.

Rule (the reviewer-approved design note on #1341, decision 2): a member the View declares replaces the design's whole member;
a member it omits takes the design's. Split connection/design members merge one level down,
creating omitted members from design sub-members only. Named styles supply column presentation.
A Layout profile without `viewDefaults`, or a
View that declares every member, is untouched.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import replace
from typing import Any

from chrona.presentation.contracts.diagnostics import PresentationDiagnostic, PresentationResourceSource
from chrona.presentation.contracts.resources import DesignMergedView

WHOLE_MEMBERS = ("visibility", "axis", "deadlines", "shading", "timePresentation", "annotationPresentation",
                 "backgroundDecoration", "progressFill", "annotationPlacement", "figureFormats", "heading")
# View v0.28's dependency-network branch prohibits these presentation members.
# A Layout may still carry them for its table-timeline use; they are inapplicable
# defaults on a network surface, not authored network View declarations.
NETWORK_INAPPLICABLE_MEMBERS = frozenset({
    "tableColumns", "hierarchyColumn", "backgroundDecoration", "axis", "markers", "periods", "shading",
    "timePresentation", "annotations", "annotationPresentation", "annotationBindings", "annotationPlacement",
})
SPLIT_MEMBERS: Mapping[str, tuple[str, ...]] = {
    "comparison": ("baselineMarks", "baselineLabels", "missingActualScope", "deltaUnit", "facets"),
    "rows": ("mode", "trackAllocation", "packing", "laneTable", "points", "items"),
    "window": ("marginDays",),
    "grouping": ("presentation", "header", "headerPlacement", "tint"),
    "colorEncoding": ("scale", "target"),
}
COLUMN_PRESENTATION_MEMBERS = (
    "format", "missing", "missingBy", "affixes", "zero", "textRole", "align",
    "headerOrientation", "width", "endDisplay", "text",
)
MARKER_PRESENTATION_MEMBERS = ("kind", "label", "placement", "date")
PERIOD_LABEL_PRESENTATION_MEMBERS = ("placement", "overflow")
VISUAL_PRESENTATION_MEMBERS = ("ref", "side", "decorative")


def _fill_presentation(target: dict[str, Any], offered: Mapping[str, Any], members: Sequence[str]) -> None:
    for member in members:
        if member in offered and member not in target:
            target[member] = deepcopy(offered[member])


def _close_array_presentation(body: dict[str, Any], defaults: Mapping[str, Any]) -> None:
    """Fill existing occurrences only; never infer a project selection or new occurrence."""
    offered = defaults.get("markerPresentation")
    markers = body.get("markers")
    if isinstance(offered, Mapping) and isinstance(markers, list):
        for marker in markers:
            if isinstance(marker, dict):
                _fill_presentation(marker, offered, MARKER_PRESENTATION_MEMBERS)
    offered = defaults.get("periodLabelPresentation")
    periods = body.get("periods")
    if isinstance(offered, Mapping) and isinstance(periods, (list, Mapping)):
        selections = periods if isinstance(periods, list) else [periods]
        for period in selections:
            label = period.get("label") if isinstance(period, Mapping) else None
            if isinstance(label, dict):
                _fill_presentation(label, offered, PERIOD_LABEL_PRESENTATION_MEMBERS)
    offered_by_kind = defaults.get("visualPresentation")
    visuals = body.get("visuals")
    if isinstance(offered_by_kind, Mapping) and isinstance(visuals, list):
        for visual in visuals:
            if not isinstance(visual, dict):
                continue
            target = visual.get("target")
            kind = target.get("kind") if isinstance(target, Mapping) else None
            offered = offered_by_kind.get(kind) if isinstance(kind, str) else None
            if isinstance(offered, Mapping):
                members = ("side", "decorative") if "encoding" in visual else VISUAL_PRESENTATION_MEMBERS
                _fill_presentation(visual, offered, members)


def _column_source_kind(source: object) -> str | None:
    if isinstance(source, str):
        return source
    if isinstance(source, Mapping) and len(source) == 1:
        kind = next(iter(source))
        return "field" if kind == "fieldRole" else kind
    return None


def _declares_value_bearing_grouping(body: Mapping[str, Any]) -> bool:
    """Whether the View's own grouping connection can produce values for a tint."""
    grouping = body.get("grouping")
    by = grouping.get("by") if isinstance(grouping, Mapping) else None
    return (isinstance(by, str) and by in {"field", "objectType"}
            or isinstance(by, Mapping) and "fieldRole" in by)


def merge_view_defaults(view: Mapping[str, Any], defaults: Mapping[str, Any]) -> dict[str, Any]:
    """The View with the design's defaults filled in under it (the View's own members win)."""
    merged = DesignMergedView(deepcopy(dict(view)))
    body = merged.get("body")
    if not isinstance(body, dict):
        return merged
    effective_defaults = defaults
    if body.get("surface") == "dependency-network":
        effective_defaults = {name: value for name, value in defaults.items()
                              if name not in NETWORK_INAPPLICABLE_MEMBERS}
    grouping_defaults = effective_defaults.get("grouping")
    if isinstance(grouping_defaults, Mapping) and not _declares_value_bearing_grouping(body):
        # Tint is a paint default only; it cannot supply the grouping connection
        # that gives it values. Preserve other grouping presentation defaults.
        effective_defaults = dict(effective_defaults)
        effective_defaults["grouping"] = {name: value for name, value in grouping_defaults.items()
                                          if name != "tint"}
    supplied: set[str] = set()
    origins: list[tuple[str, str]] = []
    for name in WHOLE_MEMBERS:
        if name in effective_defaults and name not in body:
            body[name] = deepcopy(effective_defaults[name])
            supplied.add(name)
            origins.append((f"/body/{name}", f"/viewDefaults/{name}"))
    for name, members in SPLIT_MEMBERS.items():
        declared, offered = body.get(name), effective_defaults.get(name)
        if not isinstance(offered, Mapping):
            continue
        if name not in body:
            fragment = {member: deepcopy(offered[member]) for member in members if member in offered}
            if fragment:
                body[name] = fragment
                supplied.add(name)
                origins.extend((f"/body/{name}/{member}", f"/viewDefaults/{name}/{member}")
                               for member in fragment)
        elif isinstance(declared, dict):
            for member in members:
                if member in offered and member not in declared:
                    declared[member] = deepcopy(offered[member])
                    origins.append((f"/body/{name}/{member}", f"/viewDefaults/{name}/{member}"))
    styles = effective_defaults.get("columnStyles")
    columns = body.get("tableColumns")
    if isinstance(styles, Mapping) and isinstance(columns, list):
        for column in columns:
            if not isinstance(column, dict):
                continue
            name = column.get("style") if "style" in column else _column_source_kind(column.get("source"))
            style = styles.get(name) if isinstance(name, str) else None
            if isinstance(style, Mapping):
                _fill_presentation(column, style, COLUMN_PRESENTATION_MEMBERS)
    _close_array_presentation(body, effective_defaults)
    merged.design_supplied = frozenset(supplied)
    merged.design_origins = tuple(origins)
    return merged


def inherited_layout_origin(view: Mapping[str, Any], source_ref: str) -> str | None:
    """Map a semantic error path to its exact Layout-default pointer, if inherited.

    Only whole and split members recorded while closing ``viewDefaults`` are
    considered. Array-entry presentation and authored View paths are untouched.
    """
    origins = getattr(view, "design_origins", ())
    matches = [(view_path, layout_path) for view_path, layout_path in origins
               if source_ref == view_path or source_ref.startswith(view_path + "/")]
    if not matches:
        return None
    view_path, layout_path = max(matches, key=lambda item: len(item[0]))
    return layout_path + source_ref[len(view_path):]


def collect_column_style_diagnostics(
    sources: Sequence[PresentationResourceSource],
) -> tuple[PresentationDiagnostic, ...]:
    """Resolve explicit style names without making the View-only parser read a Layout.

    Inspect original pointers and collect every unknown name; structural mistakes
    remain schema findings. Optional source-kind defaults need no reference finding.
    """
    layout = next((item for item in sources if item.identity.kind == "layout-profile"
                   and isinstance(item.value, Mapping)), None)
    defaults = layout.value.get("viewDefaults", {}) if layout is not None else {}
    if not isinstance(defaults, Mapping):
        return ()
    styles = defaults.get("columnStyles", {})
    if not isinstance(styles, Mapping):
        return ()
    view = next((item for item in sources if item.identity.kind == "view"
                 and isinstance(item.value, Mapping)), None)
    body = view.value.get("body") if view is not None else None
    columns = body.get("tableColumns") if isinstance(body, Mapping) else None
    if not isinstance(columns, list):
        return ()
    findings = []
    for index, column in enumerate(columns):
        if not isinstance(column, Mapping):
            continue
        name = column.get("style")
        if isinstance(name, str) and name and name not in styles:
            findings.append(PresentationDiagnostic(
                "E_VIEW_COLUMN_STYLE_UNKNOWN", "view", view.identity.id,
                f"/body/tableColumns/{index}/style", None,
                f"Column style {name!r} is not declared by the selected Layout profile", "contract",
            ))
    return tuple(findings)


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
