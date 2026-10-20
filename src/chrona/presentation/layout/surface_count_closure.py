"""Owns count-bound planning/composition and accepted facts; reads closed programs and typed narrative receipts."""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Literal

from chrona.core.figures import FigureSpec, resolve_figures
from chrona.presentation.count_text import CountTextError
from chrona.presentation.figure_text import FigureTextError, FigureTextProgram, FigureTextReadError, compile_figure_text
from chrona.presentation.heading_text import ClosedHeadingProgram, HeadingTextPrograms
from chrona.presentation.layout.dependency_network import DependencyNetworkLayout, compose_dependency_network_surface
from chrona.presentation.layout.model import CountDependentHeadingFitError, LayoutError
from chrona.presentation.layout.slot_heading import compile_slot_heading_programs, source_has_content
from chrona.presentation.layout.surface_composer import compose_surface_layout
from chrona.presentation.layout.surface_completion import SurfaceLayoutComposition
from chrona.presentation.layout.surface_quality import SurfaceLayoutRequest
from chrona.presentation.layout.temporal_capacity import TemporalInlineCapacity
from chrona.presentation.layout.surface_render_plan import PreparedSurfaceRenderPlan, SurfaceRenderPlanInput, prepare_surface_render_plan
from chrona.presentation.model.presentation_contract import normalize_presentation_input
from chrona.presentation.model.projection import ReviewProjection
from chrona.presentation.model.theme_tokens import ThemeTokenView
from chrona.presentation.review.figure_facts import deferred_layout_figures, projected_counts


@dataclass(frozen=True)
class CountReadInput:
    value: SurfaceRenderPlanInput
    figures: tuple[FigureSpec, ...]
    active: bool


@dataclass(frozen=True)
class CountTrial:
    count: int | None
    outcome: Literal["ordinary", "accepted", "mismatch", "range", "text-fit"]
    actual: int | None = None
    path: str | None = None
    figure_ids: frozenset[str] = frozenset()
    detail: str = ""
    supported_range: tuple[int, int] | None = None


@dataclass(frozen=True)
class CompletedSurfaceRenderPlan:
    plan: PreparedSurfaceRenderPlan
    projection: ReviewProjection
    composition: SurfaceLayoutComposition | DependencyNetworkLayout
    trials: tuple[CountTrial, ...]


class CountClosureError(LayoutError):
    def __init__(self, upper: int, trials: tuple[CountTrial, ...]):
        self.upper, self.trials = upper, trials
        evidence = "; ".join(f"{t.count}:{t.outcome}:actual={t.actual}:path={t.path}:"
                             f"figures={','.join(sorted(t.figure_ids))}:{t.detail}" for t in trials)
        super().__init__("E_LAYOUT_FIGURE_COUNT_UNSTABLE", "/body/figures",
                         detail=f"domain=0..{upper}; trials={len(trials)}; {evidence}")


def inspect_count_reads(value: SurfaceRenderPlanInput) -> CountReadInput:
    """Semantic admission and active-read selection, without metrics or geometry."""
    figures = deferred_layout_figures(value.view.figures)
    if not figures:
        return CountReadInput(value, (), False)
    late = {item.figure_id for item in figures}
    root = value.profile.get("root", {})
    parts = set()

    def visit(node):
        source = node.get("source") if node.get("kind") == "slot" else None
        if source in {"title", "heading"}:
            parts.update(("title", "subtitle", "kicker"))
        elif source in {"heading.title", "heading.subtitle", "heading.kicker"}:
            parts.add(source.split(".", 1)[1])
        for child in node.get("children", ()):
            visit(child)

    visit(root)
    heading = value.heading
    if isinstance(heading, HeadingTextPrograms):
        heading = replace(heading,
            title=heading.title if "title" in parts else compile_figure_text(""),
            subtitle=heading.subtitle if "subtitle" in parts else None,
            kicker=heading.kicker if "kicker" in parts else None)
        value = replace(value, heading=heading)
    active = isinstance(heading, HeadingTextPrograms) and bool(heading.figure_ids & late)
    for item in compile_slot_heading_programs(root, value.view.figures):
        present = source_has_content(value.content, item.source)
        if item.source in {"heading.title", "heading.subtitle", "heading.kicker", "title", "heading"}:
            part = {"title": "title", "heading": "title", "heading.title": "title",
                    "heading.subtitle": "subtitle", "heading.kicker": "kicker"}[item.source]
            text = getattr(heading, part, None)
            present = text is not None
            if isinstance(text, (FigureTextProgram, ClosedHeadingProgram)) and not text.figure_ids & late:
                try:
                    present = bool(text.bind(dict(value.projection.figures), value.view.figure_formats))
                except (CountTextError, FigureTextError) as error:
                    raise FigureTextReadError(error, f"/body/heading/{part}") from error
            elif text is not None and not isinstance(heading, HeadingTextPrograms):
                present = bool(text)
        if (item.node_id not in (value.view.slot_heading_text or {}) and present
                and item.program.figure_ids & late):
            active = True
    return CountReadInput(value, figures, active)


def _with_count(value: SurfaceRenderPlanInput, count: int) -> Any:
    specs = deferred_layout_figures(value.view.figures)
    if not specs:
        return value.projection
    actual_body = (value.actual or {}).get("body", {})
    counts = replace(projected_counts(value.projection.items, as_of_available=actual_body.get("asOf") is not None),
                     placed_notes=count)
    resolved = resolve_figures(specs, as_of=None, placements={}, periods=(), calendars={},
                              default_calendar=None, counts=counts)
    assert not resolved.diagnostics, "closed Layout count facts must resolve"
    values = {**dict(value.projection.figures), **resolved.values}
    unavailable_ids = {finding.details["figure"] for finding in value.projection.unavailable_figures}
    return replace(value.projection, figures=tuple((item.figure_id, values[item.figure_id])
        for item in value.view.figures if item.scope == "global"
        and item.figure_id not in unavailable_ids))


def _compose(value: SurfaceRenderPlanInput, plan: PreparedSurfaceRenderPlan):
    request = (plan.preparation.inline.request if plan.preparation is not None else SurfaceLayoutRequest(
        projection=value.projection, surface_content=plan.content,
        presentation_contract=normalize_presentation_input(plan.content),
        layout_manifest=plan.manifest, measured_sources=plan.measured,
        temporal_capacity=(TemporalInlineCapacity.from_manifest(plan.manifest, plan.measured)
                           if value.view.surface == "table-timeline" else None),
        theme_tokens=ThemeTokenView(value.theme), font_metrics=value.font_metrics,
        capabilities=dict(value.capabilities), icon_assets=value.icon_assets,
        paint_capabilities=value.paint_capabilities,
        visual_requests=value.visual_requests, capacity_short_sources=plan.capacity_short_sources,
        declared_viewport=plan.declared_viewport, auto_block_limit=plan.profile.distances.get("/reviewSurface/maxBlockSize"),
        progress=value.progress, previous_route_hints=value.previous_route_hints))
    if value.view.surface == "dependency-network":
        return compose_dependency_network_surface(request)
    return compose_surface_layout(request, prepared=plan.preparation)


def complete_surface_render_plan(seed: CountReadInput, *, initial: PreparedSurfaceRenderPlan | None = None) -> CompletedSurfaceRenderPlan:
    """Accept the highest consistent count, or one ordinary completion when no late read exists."""
    value = seed.value
    if not seed.active:
        plan = initial if initial is not None else prepare_surface_render_plan(value)
        composition = _compose(value, plan)
        receipts = composition.placement.narrative_receipts if value.view.surface == "table-timeline" else ()
        projection = _with_count(value, len(receipts))
        return CompletedSurfaceRenderPlan(plan, projection, composition, (CountTrial(None, "ordinary", len(receipts)),))
    if initial is not None:
        raise ValueError("active count closure cannot reuse mutable prepared candidate state")
    upper = len(value.content.annotations) + len(value.content.notes)
    late = frozenset(item.figure_id for item in seed.figures)
    trials = []
    for count in range(upper, -1, -1):
        events = []
        candidate = replace(value, projection=_with_count(value, count),
                            progress=value.progress.buffered(events.append) if value.progress is not None else None)
        try:
            plan = prepare_surface_render_plan(candidate)
            composition = _compose(candidate, plan)
        except FigureTextReadError as error:
            failure = error.failure
            if (not isinstance(failure, CountTextError) or failure.supported_range is None
                    or failure.figure_id not in late):
                raise
            trials.append(CountTrial(count, "range", path=error.path,
                figure_ids=frozenset((failure.figure_id,)), detail=failure.detail, supported_range=failure.supported_range))
            continue
        except CountDependentHeadingFitError as error:
            if not error.figure_ids & late:
                raise
            trials.append(CountTrial(count, "text-fit", path=error.path,
                                     figure_ids=error.figure_ids, detail=error.detail))
            continue
        actual = len(composition.placement.narrative_receipts)
        if actual != count:
            trials.append(CountTrial(count, "mismatch", actual))
            continue
        trials.append(CountTrial(count, "accepted", actual))
        if value.progress is not None:
            for event in events:
                value.progress.emit(event)
        return CompletedSurfaceRenderPlan(plan, candidate.projection, composition, tuple(trials))
    raise CountClosureError(upper, tuple(trials))
