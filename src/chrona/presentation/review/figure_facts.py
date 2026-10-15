"""One projection-owned count producer for summary metrics and View figures (#927)."""
from collections import Counter
from collections.abc import Sequence
from datetime import date

from chrona.core.figures import FigureCounts, FigureSpec
from chrona.presentation.model.projection import ObservationState, ReviewItem


def deferred_layout_figures(specs: Sequence[FigureSpec]) -> tuple[FigureSpec, ...]:
    """Only completed narrative counts are late; never defer unavailable date/state facts."""
    return tuple(item for item in specs if item.kind == "count" and item.source == "placedNotes")


def projected_counts(items: Sequence[ReviewItem], *, as_of_available: bool) -> FigureCounts:
    """Count selected Primary facts, not row occurrences or comparison ghosts."""
    selected_by_id = {}
    for item in items:
        if item.source_kind in {"primary", "combined"}:
            selected_by_id.setdefault(item.object_id, item)
    selected = tuple(selected_by_id.values())
    states = Counter(item.observation_state for item in selected)
    deltas = tuple(item.finish_delta for item in selected if item.finish_delta is not None)
    due = states[ObservationState.DUE_UNOBSERVED]
    return FigureCounts(len(selected), states[ObservationState.RECORDED], due,
                        states[ObservationState.NOT_YET_DUE], states[ObservationState.UNAVAILABLE],
                        due if as_of_available else None, len(deltas),
                        sum(value > 0 for value in deltas), sum(value < 0 for value in deltas),
                        groups=len({item.group_id for item in selected if item.group_id}))


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
