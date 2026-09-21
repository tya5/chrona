from datetime import date\n\nfrom chrona.presentation.model.projection import ReviewItem\nfrom chrona.presentation.model.surface_content import display_value, table_value


def test_declared_table_missing_values_are_normalized_before_scene_construction():
    assert display_value(None, "blank") == ""
    assert display_value(None, "em-dash") == "—"
    assert display_value(None, "unknown") == "unknown"


def test_declared_table_value_is_not_replaced_by_a_missing_policy():
    assert display_value("ready", "blank") == "ready"
    assert display_value(4, "em-dash") == "+4d"


def test_typed_table_facets_are_formatted_by_the_view_contract():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)},
                      {"start": date(2026, 1, 2), "finish": date(2026, 1, 8)}, 3, ())
    assert display_value(table_value(item, {}, {"facet": "planned"}), "blank", "dateRange") == "2026-01-01 – 2026-01-05"
    assert display_value(table_value(item, {}, {"facet": "actual"}), "in-progress", "date") == "2026-01-08"
    assert display_value(table_value(item, {}, {"facet": "finishDelta"}), "blank", "signedDays") == "+3d"


def test_missing_actual_uses_the_declared_in_progress_policy():
    item = ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)}, None, None, ())
    assert display_value(table_value(item, {}, {"facet": "actual"}), "in-progress", "dateRange") == "in progress"
