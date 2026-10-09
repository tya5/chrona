"""Synthetic annotation-kind fixtures for the #584 rules.

A Project with Project annotations of two kinds goes through the packaged preset bundle with a Theme
that dresses those kinds. Nothing here reads `examples/`.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

from chrona.presentation.model.closure import resolve_draft_render
from chrona.presentation.renderers.v05_svg import V05SvgRenderer
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.render_review import RenderRequest, RenderedReview, render_review
from tests.support import synthetic_review as sr

TARGET_PARTS = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file()
                    ) / "src/chrona/resources/icons/chrona-target-parts-v2026-10-09.yaml"
STAMPS = {"risk": "chrona-target-parts:seal-risk", "note": "chrona-target-parts:seal-note"}
KIND_COLORS = {"kind-alert": "#8E1B12", "kind-report": "#1D3F73"}
KINDS = {
    "risk": {"label": "RISK", "secondary": "WARNING", "title": "{label} · {subject}", "color": "category:kind-alert"},
    "note": {"label": "NOTE", "secondary": "REPORT", "color": "category:kind-report"},
}
_TEXT_PROPERTIES = {"fontFamily": "editorial", "fontWeight": "text-weight", "letterSpacing": "letter-spacing",
                    "textTransform": "text-transform", "numericSpacing": "numeric-spacing"}


def render(directory: Path, source: Mapping[str, Any], parts: Mapping[str, Mapping[str, Any]], *,
           visual_profile: str = "chrona-output/visual/v0.6-svg", viewport: tuple[int, int | None] = (1600, 900),
           catalogs: tuple[Path, ...] | None = None) -> RenderedReview:
    """Render through the packaged target-parts catalogue under a rich profile: a stamp glyph's stroked
    parts carry a required line cap and join, which the baseline profile does not admit."""
    paths = {kind: sr._write(directory / f"{kind}.yaml", value) for kind, value in parts.items()}
    draft = resolve_draft_render(
        project_path=sr._write(directory / "project.yaml", source), view_path=paths["view"], theme_path=paths["theme"],
        scheme_path=paths["scheme"], layout_path=paths["layout"], icon_catalog_paths=catalogs if catalogs is not None else (TARGET_PARTS,),
        viewport=viewport, visual_profile=visual_profile)
    return render_review(RenderRequest(
        closure=draft.closure, snapshot_root=draft.asset_root, asset_root=draft.asset_root,
        scheduler=ReferenceScheduler(), renderer=V05SvgRenderer(), draft_auto_block=draft.auto_block))


def project(kinds: Iterable[str] = ("risk", "note"), text: str | None = None) -> dict[str, Any]:
    """At least three tasks and one Project annotation per requested kind, anchored on the first tasks."""
    kinds = tuple(kinds)
    objects = {f"t{index}": sr.span(f"t{index}", date(2026, 1, 5) + timedelta(days=index * 40), 28, owner="a",
                                    title=f"Task {index}") for index in range(max(3, len(kinds)))}
    source = sr.project(objects)
    source["annotations"] = {}
    for index, kind in enumerate(kinds):
        source["annotations"][f"n{index}"] = {"kind": kind, "text": text or f"A {kind} note on task {index} with a few words.",
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
                    bar: bool = True, border_side: str | None = None, border_width: float = 6, secondary: bool = True,
                    label_fill: str = "surface", padding: float = 0.6, stamp: str | None = None,
                    stamp_size: float = 2.0, stamps: Mapping[str, str] | None = None) -> None:
    """Declare the header, bar, kind-painted border and optional stamp."""
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
    if border_side is not None:
        for box_role in ("annotation-note-box", "annotation-callout-box",
                         "annotation-highlight-box", "annotation-arrow-box"):
            if box_role not in roles:
                continue
            container_ref = roles[box_role].get("annotationContainer")
            container = deepcopy(values[container_ref]["value"]) if container_ref else {
                "outline": "rectangle", "cornerRadius": 0}
            container.setdefault("border", {})[border_side] = {"width": border_width, "paint": "kind"}
            token_id = f"kind-border-container:{box_role}"
            values[token_id] = {"type": "annotationContainer", "value": container}
            roles[box_role]["annotationContainer"] = token_id
        roles["annotation-kind-accent"] = {}
        bindings["annotation-kind-accent.fill"] = "accent"
    if stamp is not None:
        for kind, glyph in (STAMPS if stamps is None else stamps).items():
            if kind in theme["annotationKinds"]:
                theme["annotationKinds"][kind]["stamp"] = glyph
        values["kind-stamp-placement"] = {"type": "stampPlacement", "value": {"corner": stamp, "size": stamp_size}}
        roles["annotation-kind-stamp"] = {"stampPlacement": "kind-stamp-placement"}
        bindings["annotation-kind-stamp.fill"] = "text"
        bindings["annotation-kind-stamp.stroke"] = "text"


def with_tilt(parts: dict[str, dict[str, Any]], degrees: Any, *,
              roles: Iterable[str] = ("annotation-note-box",), outline: str = "rectangle") -> None:
    """Give the note box role(s) an `annotationContainer` token that declares a tilt cycle."""
    theme = parts["theme"]["body"]
    for role in roles:
        binding = theme["roles"].setdefault(role, {})
        previous = binding.get("annotationContainer")
        container = deepcopy(theme["values"][previous]["value"]) if previous else {
            "outline": outline, "cornerRadius": 0}
        container["outline"] = outline
        container["tiltDegrees"] = list(degrees) if isinstance(degrees, (list, tuple)) else degrees
        token_id = f"tilt-container:{role}"
        theme["values"][token_id] = {"type": "annotationContainer", "value": container}
        binding["annotationContainer"] = token_id
