"""Synthetic annotation-kind fixtures for the #584 rules.

A Project with Project annotations of two kinds goes through the packaged preset bundle with a Theme
that dresses those kinds. Nothing here reads `examples/`.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from typing import Any, Iterable, Mapping

from tests.support import synthetic_review as sr

KIND_COLORS = {"kind-alert": "#8E1B12", "kind-report": "#1D3F73"}
KINDS = {
    "risk": {"label": "RISK", "secondary": "WARNING", "title": "{label} · {subject}", "color": "category:kind-alert"},
    "note": {"label": "NOTE", "secondary": "REPORT", "color": "category:kind-report"},
}
_TEXT_PROPERTIES = {"fontFamily": "editorial", "fontWeight": "text-weight", "letterSpacing": "letter-spacing",
                    "textTransform": "text-transform", "numericSpacing": "numeric-spacing"}


def project(kinds: Iterable[str] = ("risk", "note")) -> dict[str, Any]:
    """Three tasks and one Project annotation per requested kind, anchored on the first tasks."""
    objects = {f"t{index}": sr.span(f"t{index}", date(2026, 1, 5) + timedelta(days=index * 40), 28, owner="a",
                                    title=f"Task {index}") for index in range(3)}
    source = sr.project(objects)
    source["annotations"] = {}
    for index, kind in enumerate(kinds):
        source["annotations"][f"n{index}"] = {"kind": kind, "text": f"A {kind} note on task {index} with a few words.",
                                              "anchor": {"object": f"t{index}"}}
    return source


def with_view_notes(parts: dict[str, dict[str, Any]], source: Mapping[str, Any], *, purpose: str = "note",
                    connector: str = "none") -> None:
    """One View annotation per Project annotation, each referencing it and offering one plot candidate."""
    body = parts["view"]["body"]
    body["annotations"] = []
    body["visibility"]["annotations"] = {"mode": "presentation", "marker": "numbered"}
    for key, note in source["annotations"].items():
        body["annotations"].append({
            "id": f"view-{key}", "purpose": purpose, "projectAnnotation": key,
            "anchor": {"kind": "object", "id": note["anchor"]["object"], "facet": "planned", "endpoint": "body"},
            "candidates": [deepcopy(sr.candidate("plot-near", connector=connector))]})


def _role(prefix: str, size: str, line: str, treatment: bool = True) -> dict[str, Any]:
    role = {"fontSize": size, "lineHeight": line, **_TEXT_PROPERTIES}
    if treatment:
        role["contrastTreatment"] = "required"
    return role


def with_kind_theme(parts: dict[str, dict[str, Any]], *, kinds: Mapping[str, Mapping[str, Any]] | None = None,
                    bar: bool = True, accent: str | None = None, accent_size: float = 6, secondary: bool = True,
                    label_fill: str = "surface", padding: float = 0.6) -> None:
    """Declare `annotationKinds` and the roles that draw the header, bar and accent."""
    scheme, theme = parts["scheme"]["body"], parts["theme"]["body"]
    scheme["categories"].update(KIND_COLORS)
    theme["annotationKinds"] = deepcopy(dict(KINDS if kinds is None else kinds))
    values, roles, bindings = theme["values"], theme["roles"], theme["colorBindings"]
    values.update({"kind-label-size": {"type": "number", "value": 16}, "kind-label-line": {"type": "number", "value": 1.2},
                   "kind-secondary-size": {"type": "number", "value": 11},
                   "kind-secondary-line": {"type": "number", "value": 1.2},
                   "kind-bar-padding": {"type": "number", "value": padding}})
    roles["annotation-kind-label"] = _role("label", "kind-label-size", "kind-label-line")
    bindings["annotation-kind-label.fill"] = label_fill
    if secondary:
        roles["annotation-kind-secondary"] = _role("secondary", "kind-secondary-size", "kind-secondary-line")
        bindings["annotation-kind-secondary.fill"] = label_fill
    if bar:
        roles["annotation-kind-bar"] = {"chipPadding": "kind-bar-padding"}
        bindings["annotation-kind-bar.fill"] = "category:kind-alert"
    if accent is not None:
        values["kind-accent-edge"] = {"type": "edge", "value": {"side": accent, "size": accent_size}}
        roles["annotation-kind-accent"] = {"edge": "kind-accent-edge"}
        bindings["annotation-kind-accent.fill"] = "accent"
