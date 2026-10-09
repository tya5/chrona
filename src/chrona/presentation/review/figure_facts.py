"""One projection-owned count producer for summary metrics and View figures (#927)."""
from collections import Counter
from collections.abc import Sequence

from chrona.core.figures import FigureCounts
from chrona.presentation.model.projection import ObservationState, ReviewItem


def projected_counts(items: Sequence[ReviewItem], *, as_of_available: bool) -> FigureCounts:
    """Count selected Primary facts, not row occurrences or comparison ghosts."""
    selected = tuple(item for item in items if item.source_kind == "primary")
    states = Counter(item.observation_state for item in selected)
    deltas = tuple(item.finish_delta for item in selected if item.finish_delta is not None)
    due = states[ObservationState.DUE_UNOBSERVED]
    return FigureCounts(len(selected), states[ObservationState.RECORDED], due,
                        states[ObservationState.NOT_YET_DUE], states[ObservationState.UNAVAILABLE],
                        due if as_of_available else None, len(deltas),
                        sum(value > 0 for value in deltas), sum(value < 0 for value in deltas))
