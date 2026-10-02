"""The View-to-projection errors name the row, item, object or value at fault (#829 S4)."""
from dataclasses import replace
from datetime import date

import pytest

from chrona.presentation.contracts.resources import (
    ViewComparison, ViewGrouping, ViewInput, ViewLaneKeys, ViewRow, ViewRowItem, ViewRows, ViewVisibility, ViewWindow,
    freeze,
)
from chrona.presentation.model.projection import build_review_projection
from chrona.usecases.diagnostic_messages import is_bare

PROJECT = {"objects": {
    "programme": {"title": "Programme", "schedule": {"mode": "rollup"}},
    "task": {"title": "Task", "parent": "programme", "schedule": {"mode": "fixed"}},
    "gate": {"title": "Gate", "fields": {"owner": "delivery"}},
}, "entities": {}}
PLACEMENTS = {"programme": {"start": date(2026, 1, 1), "end": date(2026, 1, 3)},
              "task": {"start": date(2026, 1, 1), "end": date(2026, 1, 2)},
              "gate": {"at": date(2026, 1, 2)}}


FLAT = {"objects": {"task": {"title": "Task", "schedule": {"mode": "fixed"}},
                    "gate": {"title": "Gate", "fields": {"owner": "delivery"}}}, "entities": {}}
FLAT_PLACEMENTS = {name: PLACEMENTS[name] for name in FLAT["objects"]}


def _view(rows, *, window=("selected-planned", None, None, 0), actual="optional", grouping=None, labels=False) -> ViewInput:
    return ViewInput(None, grouping, None, ViewWindow(*window), ViewComparison(None, actual, None, None, ()),
                     ViewVisibility(labels, "none", "none"), (), (), rows, None, (), None, None, None)


def _explicit(*rows: ViewRow) -> ViewInput:
    return _view(ViewRows("explicit", tuple(rows)))


def _row(row_id, items, *, depth=0, parent=None, subject=None):
    return ViewRow(row_id, None, depth, parent, None, subject, tuple(items))


def _item(item_id, kind="primary", obj="task", track="stacked"):
    return ViewRowItem(item_id, kind, obj, track)


def _say(view: ViewInput, **kwargs) -> str:
    with pytest.raises(ValueError) as caught:
        build_review_projection(kwargs.pop("project", FLAT), kwargs.pop("placements", FLAT_PLACEMENTS), view,
                                kwargs.pop("actual_set", None), **kwargs)
    text = str(caught.value)
    code = text.split(":", 1)[0]
    assert code.startswith("E_REVIEW_") or code == "E_ACTUAL_REQUIRED", text
    assert not is_bare(code, text), text
    return text


def test_a_required_actual_that_was_not_given_says_what_to_pass():
    assert "--actual FILE" in _say(_view(ViewRows("automatic", ()), actual="required"))


def test_an_empty_selection_and_a_reversed_window_say_what_they_found():
    assert "selects no object" in _say(_view(ViewRows("automatic", ())), project={"objects": {}, "entities": {}}, placements={})
    text = _say(_view(ViewRows("automatic", ()), window=("explicit", "2026-03-01", "2026-02-01", 0)))
    assert "2026-03-01" in text and "2026-02-01" in text


def test_duplicate_ids_name_the_duplicate():
    assert "'r'" in _say(_explicit(_row("r", [_item("i")]), _row("r", [_item("j")])))
    text = _say(_explicit(_row("r", [_item("i"), _item("i")])))
    assert "'r'" in text and "'i'" in text


def test_an_item_source_that_cannot_be_read_names_item_row_and_object():
    unknown_kind = _say(_explicit(_row("r", [_item("i", kind="mystery")])))
    assert "'i'" in unknown_kind and "'r'" in unknown_kind and "'mystery'" in unknown_kind
    missing = _say(_explicit(_row("r", [_item("i", kind="snapshot", obj="task")])))
    assert "snapshot" in missing and "'task'" in missing
    no_actual = _say(_explicit(_row("r", [_item("i", kind="actual", obj="task")])))
    assert "no actual observation" in no_actual


def test_a_bad_track_and_a_foreign_table_subject_name_their_value():
    assert "'sideways'" in _say(_explicit(_row("r", [_item("i", track="sideways")])))
    text = _say(_explicit(_row("r", [_item("i")], subject="elsewhere")))
    assert "'elsewhere'" in text and "'r'" in text


def test_row_parent_errors_name_the_rows_and_objects():
    kw = {"project": PROJECT, "placements": PLACEMENTS}
    missing = _say(_explicit(_row("a", [_item("a", obj="programme")]), _row("b", [_item("b")], parent="ghost")), **kw)
    assert "'b'" in missing and "'ghost'" in missing
    root = _say(_explicit(_row("a", [_item("a", obj="programme")]), _row("b", [_item("b", obj="gate")], parent="a")), **kw)
    assert "'gate'" in root and "root" in root
    mismatch = _say(_explicit(_row("a", [_item("a", obj="task")]), _row("b", [_item("b", obj="task")], parent="a")), **kw)
    assert "'programme'" in mismatch and "'task'" in mismatch


def test_lane_key_target_and_value_name_what_is_wrong():
    lanes = ViewRows("lanes", (), packing=("explicit",), lane_keys=ViewLaneKeys(None, freeze({"absent": "k"})))
    assert "'absent'" in _say(_view(lanes))
    field = ViewRows("lanes", (), packing=("explicit",), lane_keys=ViewLaneKeys("owner", None))
    project = {"objects": {"gate": {"title": "Gate", "fields": {"owner": 7}}}, "entities": {}}
    text = _say(_view(field), project=project, placements={"gate": {"at": date(2026, 1, 2)}})
    assert "'gate'" in text and "7" in text


def test_point_policy_errors_say_which_setting_is_missing():
    grouping = ViewGrouping("field", "owner", (), "ungrouped", None, None, None)
    needs_header = _say(_view(ViewRows("automatic", (), "group-header"), grouping=grouping))
    assert "presentation header" in needs_header
    header = ViewGrouping("field", "owner", (), "ungrouped", "header", None, None)
    assert "visibility.labels" in _say(_view(ViewRows("automatic", (), "group-header"), grouping=header))
    assert "'bogus'" in _say(_view(ViewRows("automatic", (), "bogus")))
