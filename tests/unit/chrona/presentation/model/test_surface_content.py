from datetime import date

import pytest

from chrona.presentation.model.projection import ObservationState, ReviewItem
from chrona.presentation.model.surface_content import display_value, table_value
from chrona.presentation.table_presentation import BooleanPresencePresentation


def test_declared_table_missing_values_are_normalized_before_scene_construction():
    assert display_value(None, "blank") == ""
    assert display_value(None, "em-dash") == "—"
    assert display_value(None, "unknown") == "unknown"


def test_declared_table_value_is_not_replaced_by_a_missing_policy():
    assert display_value("ready", "blank") == "ready"
    assert display_value(4, "em-dash") == "4"
    assert display_value(4, "em-dash", "signedDays") == "+4d"


def test_typed_table_facets_are_formatted_by_the_view_contract():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
                      {"start": date(2026, 1, 2), "finish": date(2026, 1, 8)}, 3, ())
    assert display_value(table_value(item, {}, {"facet": "planned"}), "blank", "dateRange") == "01 Jan – 05 Jan"
    assert display_value(table_value(item, {}, {"facet": "actual"}), "in-progress", "date") == "2026-01-08"
    assert display_value(table_value(item, {}, {"facet": "finishDelta"}), "blank", "signedDays") == "+3d"


def test_in_flight_actual_renders_as_an_open_date_range():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
                      {"start": date(2026, 1, 2), "progress": 0.5}, None, ())
    assert display_value(table_value(item, {}, {"facet": "actual"}), "in-progress", "dateRange") == "02 Jan 2026 –"


def test_missing_actual_uses_the_declared_in_progress_policy_without_context():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)}, None, None, ())
    assert display_value(table_value(item, {}, {"facet": "actual"}), "in-progress", "dateRange") == "in progress"


@pytest.mark.parametrize("state,expected", (
    (ObservationState.DUE_UNOBSERVED, True),
    (ObservationState.RECORDED, False),
    (ObservationState.NOT_YET_DUE, None),
    (ObservationState.UNAVAILABLE, None),
))
def test_missing_actual_table_fact_follows_observation_state(state, expected):
    item = ReviewItem("a", "A", "span", {"start": date(2027, 8, 1), "end": date(2027, 8, 20)},
                      None, None, (), observation_state=state)
    assert table_value(item, {}, {"comparisonFacet": "missingActual"}) is expected


def test_boolean_table_values_require_and_use_a_declared_presence_presentation():
    presence = BooleanPresencePresentation("Missing", "Recorded")
    assert display_value(True, "blank", presence) == "Missing"
    assert display_value(False, "blank", presence) == "Recorded"
    with pytest.raises(ValueError, match="E_VIEW_BOOLEAN_PRESENTATION"):
        display_value(True, "blank", "text")
