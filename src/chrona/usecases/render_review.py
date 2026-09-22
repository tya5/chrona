"""Render one immutable Render Context closure into a review surface.

This is the whole render use case: it owns the order of the pipeline —
closure, schedule, projection, content, measurement, layout, scene, render —
so that no adapter has to know it. A caller supplies an already-resolved
closure and receives an SVG or a stable diagnostic; nothing here reads
command-line arguments, writes files, or prints.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from chrona.core.diagnostics import Diagnostic
from chrona.extensions.profiles import validate_profiles
from chrona.presentation.layout.engine import solve_layout
from chrona.presentation.layout.profile import resolve_layout_profile
from chrona.presentation.layout.sources import SourceInput, measure_sources
from chrona.presentation.model.closure import RenderClosure
from chrona.presentation.model.font_metrics import resolve_font_metrics
from chrona.presentation.model.projection import build_review_projection
from chrona.presentation.renderers.v05_svg import render_v05_svg
from chrona.presentation.review.v05_content import normalize_v05_surface_content
from chrona.presentation.scene.model import SceneSurface
from chrona.presentation.scene.v05_builder import build_scene_input, compose_review_surface
from chrona.scheduling.scheduler import schedule

# Consumed through ``context["resolvedTheme"]`` rather than through the closure
# accessor, so they are read by construction.
_IMPLICITLY_READ = frozenset({"color-scheme", "theme"})


class RenderRejected(Exception):
    """The closure is valid but its Project cannot be scheduled."""

    def __init__(self, diagnostics: list[Diagnostic], component: str = "core"):
        super().__init__(component)
        self.diagnostics = diagnostics
        self.component = component


class RenderFailed(Exception):
    """The render cannot proceed, reported as one stable diagnostic code."""

    def __init__(self, code: str, message: str, component: str):
        super().__init__(code)
        self.code = code
        self.message = message
        self.component = component


@dataclass(frozen=True)
class RenderRequest:
    """One resolved closure and the store it was read from."""

    closure: RenderClosure
    snapshot_root: Path
    require_all_inputs_read: bool = False


@dataclass(frozen=True)
class RenderedReview:
    """The rendered surface and the closure inputs the render actually read."""

    svg: str
    surface: SceneSurface
    read_inputs: frozenset[str] = field(default_factory=frozenset)


class _Closure:
    """Resource access that records which declared inputs the render reads."""

    def __init__(self, closure: RenderClosure):
        self._closure = closure
        self.read: set[str] = set()

    def get(self, kind: str) -> dict[str, Any] | None:
        self.read.add(kind)
        item = self._closure.resource(kind)
        return item.contract.document if item is not None else None

    def all_of(self, kind: str) -> tuple[dict[str, Any], ...]:
        values = tuple(item.contract.document for item in self._closure.resources if item.kind == kind)
        if values:
            self.read.add(kind)
        return values

    def unused(self) -> tuple[str, ...]:
        declared = {item.kind for item in self._closure.resources}
        return tuple(sorted(declared - self.read - _IMPLICITLY_READ))


def render_review(request: RenderRequest) -> RenderedReview:
    """Render one closure, in the one order the pipeline has."""
    render_closure, closure = request.closure, _Closure(request.closure)
    project, view, layout = (render_closure.project.facts, render_closure.view.document,
                             render_closure.layout_profile.profile)
    theme = render_closure.resolved_theme.document
    closure.read.update({"project", "view", "layout-profile", "theme", "color-scheme"})

    manifests = {item.document["packageId"]: item.document for item in render_closure.profile_packages}
    if manifests:
        closure.read.add("profile-package")
    projection = _project_review(project, view, render_closure, manifests)
    if render_closure.actual_set is not None:
        closure.read.add("actual-set")
    if render_closure.snapshot is not None:
        closure.read.update({"snapshot-ref", "snapshot-project"})

    environment = render_closure.context.body["environment"]
    font_metrics = _font_metrics(theme, environment, request.snapshot_root / render_closure.context.body["theme"]["revision"]["token"])
    source_inputs = _source_inputs(project, view, projection)
    measured = measure_sources(source_inputs, theme, font_metrics=font_metrics)
    resolved_layout = resolve_layout_profile(layout, available_sources=set(source_inputs), theme=theme)
    viewport = environment["viewport"]
    manifest = solve_layout(
        resolved_layout,
        viewport_inline=viewport["inlineSize"],
        viewport_block=viewport["blockSize"],
        measurements=_slot_measurements(resolved_layout.profile["root"], measured),
    )

    surface_content = normalize_v05_surface_content(
        projection, project, view,
        actual_set=render_closure.actual_set.document if render_closure.actual_set else None,
        detail=render_closure.detail_profile.document if render_closure.detail_profile else None,
    )
    if render_closure.detail_profile is not None:
        closure.read.add("review-detail-profile")
    scene_input = build_scene_input(
        projection=projection, surface_content=surface_content, layout_manifest=manifest,
        resolved_theme=theme, font_metrics=font_metrics, measured_sources=measured,
        capabilities={name: True for name in render_closure.context.body["target"]["capabilities"]},
        locale=environment["locale"],
    )

    unused = closure.unused()
    if request.require_all_inputs_read and unused:
        raise RenderFailed("E_CLOSURE_INPUT_UNUSED",
                           "closure inputs loaded but never read: " + ", ".join(unused), "closure")

    surface = compose_review_surface(scene_input)
    svg = render_v05_svg(surface, viewport=(float(viewport["inlineSize"]), float(viewport["blockSize"])),
                         tokens=scene_input.theme_tokens)
    return RenderedReview(svg, surface, frozenset(closure.read))


def _project_review(project: dict[str, Any], view: dict[str, Any], closure: RenderClosure,
                    manifests: dict[str, dict[str, Any]]) -> Any:
    """Schedule the Project, and its Snapshot when one is bound, then project the review."""
    result = schedule(project, extension_diagnostics=validate_profiles(project, manifests))
    if not result.ok:
        raise RenderRejected(result.diagnostics)
    actual = closure.actual_set.document if closure.actual_set is not None else None
    snapshot_project = closure.snapshot_project.facts if closure.snapshot_project is not None else None
    snapshot_result = schedule(snapshot_project) if snapshot_project is not None else None
    if snapshot_result is not None and not snapshot_result.ok:
        raise RenderRejected(snapshot_result.diagnostics)
    return build_review_projection(
        project, result.placements, view, actual,
        snapshot_project=snapshot_project,
        snapshot_placements=snapshot_result.placements if snapshot_result is not None else None,
    )


def _font_metrics(theme: dict[str, Any], environment: dict[str, Any], asset_root: Path) -> Any:
    body = theme["body"]
    family_token = body.get("roles", {}).get("text", {}).get("fontFamily")
    family = body.get("values", {}).get(family_token, {}).get("value")
    if not isinstance(family, str):
        raise RenderFailed("E_THEME_ROLE_REQUIRED", "text.fontFamily is required", "theme")
    return resolve_font_metrics(family, environment["fontMetrics"], asset_root=asset_root)


def _source_inputs(project: dict[str, Any], view: dict[str, Any], projection: Any) -> dict[str, SourceInput]:
    """Declare what each slot will hold, for measurement before layout."""
    rows = projection.rows or ()
    row_count = len(rows) or len(projection.items)
    span_days = max(1, (projection.window[1] - projection.window[0]).days)
    notes = tuple(str(item.get("text", "")) for item in project.get("annotations", {}).values())
    return {
        "title": SourceInput((project["project"].get("title", "Chrona"),), typography_role="heading"),
        "table": SourceInput(
            tuple(row.label for row in rows) or tuple(item.title for item in projection.items),
            row_count, len(view.get("body", {}).get("tableColumns", ())) or 1),
        "timeline": SourceInput(item_count=row_count, span_days=span_days),
        "timeline-axis": SourceInput(span_days=span_days, typography_role="axis"),
        "summary": SourceInput(("summary",)),
        "legend": SourceInput(("legend",), typography_role="legend"),
        "group-details": SourceInput(("group details",)),
        "observations": SourceInput(("observations",)),
        "milestones": SourceInput(("milestones",)),
        "annotations": SourceInput(("annotations",), typography_role="annotation"),
        "notes": SourceInput(notes or ("notes",), typography_role="annotation"),
    }


def _slot_measurements(root: Mapping[str, Any], measured: Any) -> dict[str, Any]:
    measurements: dict[str, Any] = {}

    def bind(node: Mapping[str, Any]) -> None:
        if node["kind"] == "slot":
            measurements[node["id"]] = measured.measurements[node["source"]]
        for child in node.get("children", ()):
            bind(child)

    bind(root)
    return measurements
