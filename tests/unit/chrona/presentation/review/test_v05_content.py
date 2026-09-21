from datetime import date

from chrona.presentation.model.projection import ReviewItem, ReviewProjection
from chrona.presentation.review.v05_content import normalize_v05_surface_content


def test_optional_content_is_selected_only_from_current_project_and_view():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 2)}, None, None, ()),), (date(2026, 1, 1), date(2026, 1, 2)), (), ())
    project = {"relations": ({"id": "r", "from": {"object": "a"}, "to": {"object": "a"}},), "annotations": {"n": {"text": "note"}}}
    view = {"body": {"tableColumns": ({"id": "Name", "source": "title", "missing": "blank"},), "visibility": {"relations": "semantic", "annotations": "none"}}}
    value = normalize_v05_surface_content(projection, project, view)
    assert value.table_cells == (("a", "Name", "A"),)
    assert value.relations[0]["id"] == "r"
    assert value.notes == (("n", "note"),)


def test_calendar_closures_come_only_from_project_calendar_exceptions():
    projection = ReviewProjection((ReviewItem("a", "A", "span", {"start": date(2026, 1, 1), "end": date(2026, 1, 5)}, None, None, ()),),
                                  (date(2026, 1, 1), date(2026, 1, 5)), (), ())
    project = {"project": {"calendar": "standard"},
               "calendars": {"standard": {"working_days": ["mon", "tue", "wed", "thu", "fri"],
                                           "exceptions": [{"date": "2026-01-01", "working": True}]}},
               "relations": (), "annotations": {}}
    view = {"body": {"tableColumns": (), "visibility": {"relations": "none", "annotations": "none"}}}

    value = normalize_v05_surface_content(projection, project, view)

    assert value.calendar_closed == (date(2026, 1, 3), date(2026, 1, 4))
