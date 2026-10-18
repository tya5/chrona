"""Source-local hierarchy display names retained by ReviewItem (#1701 H1)."""
from datetime import date

from chrona.presentation.contracts.resources import (
    ViewComparison, ViewInput, ViewRows, ViewSelection, ViewVisibility, ViewWindow,
)
from chrona.presentation.model.projection import _snapshot_items, build_review_projection


def _view():
    return ViewInput(ViewSelection((), ()), None, None,
                     ViewWindow("selected-planned", None, None, 0),
                     ViewComparison(None, "optional", None, None, ()),
                     ViewVisibility(False, "none", "none"), (), (),
                     ViewRows("automatic", ()), None, (), None, None, None)


def _source_project(root_title, phase_title, task_title):
    return {
        "objects": {
            "root": {"type": "group", "title": root_title},
            "phase": {"type": "group", "title": phase_title, "parent": "root"},
            "task": {"type": "task", "title": task_title, "parent": "phase"},
        },
        "entities": {},
    }


def test_primary_snapshot_and_scenario_keep_hierarchy_titles_from_their_own_project():
    placement = {"task": {"start": date(2027, 3, 1), "end": date(2027, 3, 4)}}
    primary_project = _source_project("Primary root", "  ", "Primary task")
    snapshot_project = _source_project("Snapshot root", "Snapshot phase", "Snapshot task")
    scenario_project = _source_project("", "Scenario phase", "")

    primary = build_review_projection(primary_project, placement, _view(), None).items[0]
    snapshot = _snapshot_items(snapshot_project, placement, source_kind="snapshot")["task"]
    scenario = _snapshot_items(scenario_project, placement, source_kind="scenario")["task"]

    expected_path = ("root", "phase", "task")
    assert primary.hierarchy_path == snapshot.hierarchy_path == scenario.hierarchy_path == expected_path
    assert primary.hierarchy_titles == ("Primary root", "phase", "Primary task")
    assert snapshot.hierarchy_titles == ("Snapshot root", "Snapshot phase", "Snapshot task")
    assert scenario.hierarchy_titles == ("root", "Scenario phase", "task")
    assert (snapshot.source_kind, scenario.source_kind) == ("snapshot", "scenario")

    # Keep original item titles untouched; the fallback applies only to path labels.
    assert scenario.title == ""
    assert scenario.parent_id == "phase"
    assert scenario.hierarchy_depth == 2
    assert len(scenario.hierarchy_titles) == len(scenario.hierarchy_path)
