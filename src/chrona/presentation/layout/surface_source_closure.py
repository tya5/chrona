"""Close completed source demand inside one count trial, using fresh geometry."""
from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Callable, Any

from chrona.presentation.layout.model import LayoutError
from chrona.presentation.layout.source_use import CompletedSourceUse, SourceDestinationActivation
from chrona.presentation.layout.surface_render_plan import prepare_surface_render_plan

if TYPE_CHECKING:
    from chrona.presentation.layout.surface_render_plan import PreparedSurfaceRenderPlan, SurfaceRenderPlanInput


def _already_closed(plan: PreparedSurfaceRenderPlan, observed: CompletedSourceUse) -> bool:
    """Avoid replay when the initial source facts already prove exact demand.

    In particular, ordinary surfaces with no annotations or legend need no
    second composition. Equality of page size or entry count is not proof.
    Nonempty annotation consumers require their explicit completed witness.
    """
    measured = getattr(plan, "measured", None)
    if measured is None:
        return False
    annotation_input = measured.inputs.get("annotations")
    return (not observed.annotations and annotation_input is not None
            and not annotation_input.content_present
            and plan.content.legend_entries == observed.legend_entries
            and measured.legend_layout == observed.legend_layout)


def complete_source_render_plan(value: SurfaceRenderPlanInput, compose: Callable[..., Any], *,
                                initial: PreparedSurfaceRenderPlan | None = None):
    """Accept exact producer witnesses, or diagnose a repeating demand state.

    Every candidate starts from value.profile, never the previously pruned
    tree. Unrelated errors propagate to the count coordinator unchanged.
    """
    demand: CompletedSourceUse | None = None
    seen: list[tuple[object, ...]] = []
    activate_annotations = False
    plan = initial
    while True:
        events = []
        progress = getattr(value, "progress", None)
        candidate = (replace(value, progress=progress.buffered(events.append))
                     if progress is not None else value)
        if plan is None:
            plan = prepare_surface_render_plan(
                candidate, source_use=demand, activate_annotations=activate_annotations)
        elif progress is not None and plan.preparation is not None:
            inline = plan.preparation.inline
            plan = replace(plan, preparation=replace(plan.preparation, inline=replace(
                inline, request=replace(inline.request, progress=candidate.progress))))
        try:
            composition = compose(candidate, plan)
        except SourceDestinationActivation as activation:
            state = ("activate", activation.source, activation.consumer_id,
                     activation.candidate_id, demand.finite_state() if demand is not None else None)
            if activation.source != "annotations" or state in seen:
                raise LayoutError(
                    "E_LAYOUT_SOURCE_CONTENT_UNSTABLE", "/sources/" + activation.source,
                    detail=f"repeating destination activation: {state!r}") from activation
            seen.append(state)
            activate_annotations = True
            plan = None
            continue
        observed = getattr(composition, "source_use", None)
        # Dependency-network has no late legend/annotation source consumers.
        if (observed is None or (not activate_annotations and observed == demand)
                or (demand is None and not activate_annotations and _already_closed(plan, observed))):
            if progress is not None:
                for event in events:
                    progress.emit(event)
            return plan, composition
        state = observed.finite_state()
        if state in seen:
            raise LayoutError(
                "E_LAYOUT_SOURCE_CONTENT_UNSTABLE", "/sources",
                detail=f"completed source demand repeats without matching measurement; "
                       f"previous={demand!r}; observed={observed!r}")
        seen.append(state)
        demand = observed
        activate_annotations = False
        plan = None
