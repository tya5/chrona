from datetime import date

from chrona.core.forecast import ForecastItem
from chrona.presentation.model.projection import (
    FoldedPointProjection, ForecastComparisonFact, ReviewItem, ReviewProjection, ReviewRowProjection,
    forecast_deadline_placements,
)


def _item(object_id, *, source_kind="primary", temporal_paint=True, forecast=True):
    fact = (ForecastComparisonFact(ForecastItem({"end": date(2026, 2, 1)}, completed=False), 1)
            if forecast else None)
    return ReviewItem(object_id, object_id, "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
                      None, None, (), item_id=object_id, source_kind=source_kind,
                      temporal_paint=temporal_paint, forecast=fact)


def _projection(*, rows=(), folded_points=(), items=()):
    return ReviewProjection(tuple(items), (date(2026, 1, 1), date(2026, 1, 2)), (), (),
                            rows=tuple(rows), folded_points=tuple(folded_points))


def test_forecast_selection_uses_painted_primary_occurrences_and_deduplicates_object_identity():
    primary = _item("task")
    combined = _item("task", source_kind="combined")
    excluded = (
        _item("task", source_kind="actual"),
        _item("task", source_kind="snapshot"),
        _item("task", source_kind="scenario"),
        _item("hidden-rollup", temporal_paint=False),
        _item("without-forecast", forecast=False),
    )
    row = ReviewRowProjection("row", "Row", "", "task", (primary, combined, *excluded))

    selected = forecast_deadline_placements(_projection(rows=(row,)))

    assert selected == {"task": {"end": date(2026, 2, 1)}}


def test_folded_occurrences_are_selected_but_context_only_projection_items_are_not():
    folded = _item("folded")
    folded_member = _item("folded-member")
    point = FoldedPointProjection(folded, "group", members=(folded_member, _item("other", source_kind="snapshot")))
    context_header = _item("context-only-header")
    projection = _projection(folded_points=(point,), items=(context_header,))

    selected = forecast_deadline_placements(projection)

    assert selected == {
        "folded": {"end": date(2026, 2, 1)},
        "folded-member": {"end": date(2026, 2, 1)},
    }


def test_forecast_selection_is_independent_of_window_and_does_not_mutate_projection_facts():
    primary = _item("outside-window")
    row = ReviewRowProjection("row", "Row", "", "outside-window", (primary,))
    projection = _projection(rows=(row,))

    selected = forecast_deadline_placements(projection)
    selected["outside-window"]["end"] = date(2030, 1, 1)

    assert projection.rows[0].items[0].forecast.schedule.placement["end"] == date(2026, 2, 1)
