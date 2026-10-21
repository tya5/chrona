"""One projection-owned count producer for summary metrics and View figures (#927)."""
from collections import Counter
from collections.abc import Sequence
from datetime import date
from typing import Any

from chrona.core.figures import FigureCounts, FigureSpec
from chrona.presentation.model.projection import ObservationState, ReviewItem


def deferred_layout_figures(specs: Sequence[FigureSpec]) -> tuple[FigureSpec, ...]:
    """Only completed narrative counts are late; never defer unavailable date/state facts."""
    return tuple(item for item in specs if item.kind == "count" and item.source == "placedNotes")


def filtered_figure_counts(specs: Sequence[FigureSpec], items: Sequence[ReviewItem], *, as_of_available: bool,
                           grouping: Any = None) -> dict[str, FigureCounts]:
    """The count bundle of each restricted count figure, by figure id (#1880)."""
    return {spec.figure_id: projected_counts(items, as_of_available=as_of_available, spec=spec, grouping=grouping)
            for spec in specs if spec.kind == "count" and spec.filtered}


def _unassigned(item: ReviewItem, grouping: Any) -> bool:
    """True when the item sits in the group that collects objects with no grouping value."""
    if item.group_unassigned:
        return True
    return (grouping is not None and grouping.by == "field" and grouping.field is not None
            and grouping.field not in (item.fields or {}))


def projected_counts(items: Sequence[ReviewItem], *, as_of_available: bool, spec: FigureSpec | None = None,
                     grouping: Any = None) -> FigureCounts:
    """Count selected Primary facts, not row occurrences or comparison ghosts.

    A restricted count figure (``spec``) keeps only the selected objects of its object types and temporal kind;
    its group count also leaves out the unassigned group when asked.
    """
    selected_by_id = {}
    for item in items:
        if item.source_kind in {"primary", "combined"}:
            selected_by_id.setdefault(item.object_id, item)
    selected = tuple(selected_by_id.values())
    exclude_unassigned = False
    if spec is not None:
        selected = tuple(item for item in selected
                         if (not spec.object_types or item.object_type in spec.object_types)
                         and (spec.temporal_kind is None or item.source_type == spec.temporal_kind))
        exclude_unassigned = spec.exclude_unassigned
    states = Counter(item.observation_state for item in selected)
    deltas = tuple(item.finish_delta for item in selected if item.finish_delta is not None)
    due = states[ObservationState.DUE_UNOBSERVED]
    return FigureCounts(len(selected), states[ObservationState.RECORDED], due,
                        states[ObservationState.NOT_YET_DUE], states[ObservationState.UNAVAILABLE],
                        due if as_of_available else None, len(deltas),
                        sum(value > 0 for value in deltas), sum(value < 0 for value in deltas),
                        groups=len({item.group_id for item in selected if item.group_id
                    and not (exclude_unassigned and _unassigned(item, grouping))}))


def projected_last_planned_finish(items: Sequence[ReviewItem]) -> date | None:
    """Latest planned endpoint among distinct selected Primary items.

    Comparison ghosts and scenario/actual rows are not selected Project facts. A selected
    span contributes its planned end; a selected point contributes its planned at date.
    """
    selected_by_id = {}
    for item in items:
        if item.source_kind in {"primary", "combined"}:
            selected_by_id.setdefault(item.object_id, item)
    finishes = (item.planned.get("at" if item.source_type == "point" else "end")
                for item in selected_by_id.values())
    dates = tuple(value for value in finishes if value is not None)
    return max(dates) if dates else None
