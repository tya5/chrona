from datetime import date

from chrona.presentation.model.projection import _snapshot_items, build_review_projection
from chrona.presentation.contracts.resources import (
    ViewComparison, ViewInput, ViewRows, ViewSelection, ViewVisibility, ViewWindow,
)


def _view():
    return ViewInput(ViewSelection((), ()), None, None, ViewWindow("selected-planned", None, None, 0),
                     ViewComparison(None, "optional", None, None, ()),
                     ViewVisibility(False, "none", "none"), (), (), ViewRows("automatic", ()),
                     None, (), None, None, None)


def test_primary_keeps_declared_host_separate_from_derived_row_attachment_and_parent():
    project = {"objects": {
        "span": {"type": "task", "title": "Span"},
        "point": {"type": "milestone", "title": "Point", "parent": "span", "attachesTo": "other"},
        "other": {"type": "task", "title": "Other"},
    }, "entities": {}}
    projection = build_review_projection(project, {
        "span": {"start": date(2026, 1, 1), "end": date(2026, 1, 10)},
        "point": {"at": date(2026, 1, 5)},
        "other": {"start": date(2026, 1, 1), "end": date(2026, 1, 10)},
    }, _view(), None)
    point = next(item for item in projection.items if item.object_id == "point")
    assert point.parent_id == "span"
    assert point.declared_attaches_to == "other"
    # This default table projection does not derive a row attachment.
    assert point.attached_to is None


def test_snapshot_and_scenario_items_keep_their_own_project_links_and_parents():
    project = {"objects": {
        "parent": {"type": "task", "title": "Parent"},
        "point": {"type": "milestone", "title": "Point", "parent": "parent", "attachesTo": "parent"},
    }, "entities": {}}
    items = _snapshot_items(project, {"point": {"at": date(2026, 1, 5)}}, source_kind="scenario")
    point = items["point"]
    assert point.source_kind == "scenario"
    assert point.parent_id == "parent"
    assert point.declared_attaches_to == "parent"
