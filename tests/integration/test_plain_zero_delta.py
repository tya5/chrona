"""A signed table column can draw a zero delta without its sign (#1289).

The Sunday Strip shows `0` for an on-time column, `+3!` for a slip and `-3` for an early finish.
Synthetic Project through the packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from tests.support import synthetic_review as sr

ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed", "body": {
    "asOf": "2026-03-10", "observations": [
        {"id": "late", "sequence": 1, "projectObjectId": "late", "actual": {"start": "2026-02-02", "finish": "2026-02-14", "progress": 1}},
        {"id": "ontime", "sequence": 1, "projectObjectId": "ontime", "actual": {"start": "2026-02-02", "finish": "2026-02-11", "progress": 1}},
        {"id": "early", "sequence": 1, "projectObjectId": "early", "actual": {"start": "2026-02-02", "finish": "2026-02-05", "progress": 1}}]}}


def _cells(tmp_path, *, format="signedNumber", zero=None, affixes=None):
    source = sr.project({
        "late": sr.span("late", date(2026, 2, 2), 10, title="Late"),
        "ontime": sr.span("ontime", date(2026, 2, 2), 9, title="On time"),
        "early": sr.span("early", date(2026, 2, 2), 7, title="Early")})
    parts = sr.bundle("executive-light")
    column = {"id": "Delta", "source": {"comparisonFacet": "finishDelta"}, "format": format, "missing": "blank",
              "align": "end", "width": "content", "headerOrientation": "horizontal"}
    if zero is not None:
        column["zero"] = zero
    if affixes is not None:
        column["affixes"] = affixes
    title = {"id": "Task", "source": "title", "missing": "em-dash", "align": "start", "width": "content",
             "headerOrientation": "horizontal"}
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["tableColumns"] = [title, column]
    review = sr.render(tmp_path, source, presentation=parts, actual=ACTUAL)
    return {item.source_ref: item.text for item in review.surface.primitives
            if item.purpose == "table-cell" and item.table_column_id == "Delta"}


def _sub(tmp_path, name):
    path = tmp_path / name
    path.mkdir()
    return path


def test_the_default_keeps_the_sign_at_zero(tmp_path):
    cells = _cells(tmp_path)

    assert cells["ontime"] == "+0" and cells["early"].startswith("-") and cells["late"].startswith("+")


def test_plain_zero_draws_zero_without_a_sign_and_keeps_every_other_sign(tmp_path):
    default = _cells(_sub(tmp_path, "default"))
    plain = _cells(_sub(tmp_path, "plain"), zero="plain")

    assert plain["ontime"] == "0"
    assert plain["late"] == default["late"] and plain["early"] == default["early"]


def test_plain_zero_for_days_is_zero_d(tmp_path):
    days = _cells(tmp_path, format="signedDays", zero="plain")

    assert days["ontime"] == "0d" and days["late"].endswith("d") and days["late"].startswith("+")
    assert days["early"].startswith("-")


def test_an_explicit_signed_zero_is_the_default_output(tmp_path):
    assert _cells(_sub(tmp_path, "a")) == _cells(_sub(tmp_path, "b"), zero="signed")


def test_an_on_time_affix_still_wraps_the_plain_zero(tmp_path):
    cells = _cells(tmp_path, zero="plain", affixes={"onTime": {"suffix": "*"}})

    assert cells["ontime"] == "0*"


def test_zero_on_a_column_that_is_not_signed_is_refused(tmp_path):
    with pytest.raises(Exception) as caught:
        _cells(tmp_path, format="text", zero="plain")

    assert "E_VIEW_COLUMN_ZERO" in str(caught.value) + repr(getattr(caught.value, "__cause__", ""))


def test_an_unknown_zero_spelling_is_a_schema_error(tmp_path):
    with pytest.raises(Exception) as caught:
        _cells(tmp_path, zero="blank")

    assert "E_" in str(caught.value)
