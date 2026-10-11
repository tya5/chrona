"""A Layout profile's `viewDefaults` supply the design members of a View (#1341, slice 1).

Synthetic Project through the packaged `executive-light` bundle; the committed corpus is not read.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from chrona.presentation.contracts.view_defaults import SPLIT_MEMBERS, WHOLE_MEMBERS, merge_view_defaults
from tests.support import synthetic_review as sr


def _source() -> dict:
    return sr.with_calendar(sr.project({"a": sr.span("a", date(2026, 2, 2), 30), "g": sr.point("g", date(2026, 3, 9))}))


def _move_design_to_the_layout(parts: dict, members=WHOLE_MEMBERS) -> dict:
    """Take the design members out of the View and put them, unchanged, in the Layout profile's `viewDefaults`."""
    body, moved = parts["view"]["body"], {}
    for name in members:
        if name in body:
            moved[name] = body.pop(name)
    parts["layout"]["viewDefaults"] = moved
    return moved


def _render(tmp_path, parts):
    return sr.render(tmp_path, _source(), presentation=parts)


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def test_a_view_without_the_design_members_renders_as_the_view_that_declares_them(tmp_path):
    full = sr.bundle("executive-light")
    thin = deepcopy(full)
    moved = _move_design_to_the_layout(thin)

    assert moved and set(moved) <= set(WHOLE_MEMBERS) and not set(moved) & set(thin["view"]["body"])
    assert _render(_sub(tmp_path, "full"), full).artifact.content == _render(_sub(tmp_path, "thin"), thin).artifact.content


def test_a_member_the_view_declares_wins_over_the_design_whole(tmp_path):
    parts = sr.bundle("executive-light")
    declared = deepcopy(parts["view"]["body"]["axis"])
    parts["layout"]["viewDefaults"] = {"axis": {"tiers": []}, "shading": {"nonWorking": False, "exceptions": False}}

    merged = merge_view_defaults(parts["view"], parts["layout"]["viewDefaults"])

    assert merged["body"]["axis"] == declared  # the View's own member, not the default
    assert merged["body"]["shading"] == parts["view"]["body"].get("shading", {"nonWorking": False, "exceptions": False})


def test_without_viewdefaults_or_when_the_view_declares_every_member_nothing_changes(tmp_path):
    plain = sr.bundle("executive-light")
    full = deepcopy(plain)
    full["layout"]["viewDefaults"] = {name: deepcopy(plain["view"]["body"][name]) for name in WHOLE_MEMBERS if name in plain["view"]["body"]}

    assert _render(_sub(tmp_path, "plain"), plain).artifact.content == _render(_sub(tmp_path, "full"), full).artifact.content


def test_split_members_merge_one_level_down_and_only_into_a_member_the_view_declares():
    view = {"version": "chrona/view/v0.28", "kind": "view", "id": "v", "body": {
        "surface": "table-timeline", "comparison": {"baseline": "snapshot", "deltaUnit": "working-days"}}}
    defaults = {"comparison": {"deltaUnit": "calendar-days", "baselineMarks": "ghost-when-changed"},
                "rows": {"mode": "lanes"}, "window": {"marginDays": 7}}

    merged = merge_view_defaults(view, defaults)

    assert merged["body"]["comparison"] == {"baseline": "snapshot", "deltaUnit": "working-days", "baselineMarks": "ghost-when-changed"}
    assert "rows" not in merged["body"] and "window" not in merged["body"]  # the View declares neither: no connection to merge into
    assert view["body"]["comparison"] == {"baseline": "snapshot", "deltaUnit": "working-days"}  # the input is not mutated


def test_the_merged_view_is_validated_as_the_view_it_is(tmp_path):
    parts = sr.bundle("executive-light")
    parts["layout"]["viewDefaults"] = {"deadlines": {"show": "never-heard-of"}}

    with pytest.raises(Exception) as raised:
        _render(tmp_path, parts)
    assert "E_VIEW_SCHEMA" in str(raised.value)  # a View error, found after the merge


def test_the_member_lists_are_the_design_half_of_the_reviewed_classification():
    assert set(WHOLE_MEMBERS) == {"visibility", "axis", "deadlines", "shading", "timePresentation", "annotationPresentation",
                                  "backgroundDecoration", "progressFill"}
    assert {name: set(members) for name, members in SPLIT_MEMBERS.items()} == {
        "comparison": {"baselineMarks", "missingActualScope", "deltaUnit", "facets"},
        "rows": {"mode", "trackAllocation", "packing", "laneTable", "points", "items"}, "window": {"marginDays"}}
