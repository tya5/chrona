"""A table column's absent value reads by the item's observation state (#991).

A Δ column showed one text for every absent value, so an unobserved item and an in-progress one could not differ
(blank against a dash). Synthetic Project through the packaged `executive-light` bundle; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest

from tests.support import synthetic_review as sr

AS_OF = date(2026, 3, 10)
ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed", "body": {
    "asOf": AS_OF.isoformat(), "observations": [
        {"id": "d", "sequence": 1, "projectObjectId": "done", "actual": {"start": "2026-02-02", "finish": "2026-02-20", "progress": 1}},
        {"id": "r", "sequence": 1, "projectObjectId": "running", "actual": {"start": "2026-03-02", "openUntil": "asOf"}}]}}


def _render(tmp_path, missing_by: dict | None):
    source = sr.project({
        "done": sr.span("done", date(2026, 2, 2), 14, title="Done"),
        "running": sr.span("running", date(2026, 3, 2), 30, title="Running"),
        "overdue": sr.span("overdue", date(2026, 2, 2), 10, title="Overdue"),
        "later": sr.span("later", date(2026, 5, 4), 10, title="Later")})
    parts = sr.bundle("executive-light")
    column = {"id": "Delta", "source": {"comparisonFacet": "finishDelta"}, "format": "signedDays", "missing": "em-dash",
              "align": "end", "width": "content", "headerOrientation": "horizontal"}
    if missing_by is not None:
        column["missingBy"] = missing_by
    title = {"id": "Task", "source": "title", "missing": "em-dash", "align": "start", "width": "content", "headerOrientation": "horizontal"}
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["tableColumns"] = [title, column]
    review = sr.render(tmp_path, source, presentation=parts, actual=ACTUAL)
    cells = {item.source_ref: item.text for item in review.surface.primitives
             if item.purpose == "table-cell" and item.table_column_id == "Delta"}
    return cells


def test_without_missing_by_every_absent_value_reads_the_columns_missing_text(tmp_path):
    cells = _render(tmp_path, None)
    assert cells == {"done": "+4d", "running": "—", "overdue": "—", "later": "—"}


def test_each_observation_state_reads_its_own_text_and_an_unnamed_state_keeps_missing(tmp_path):
    cells = _render(tmp_path, {"inProgress": "em-dash", "dueUnobserved": "blank", "notYetDue": "blank"})
    assert cells == {"done": "+4d", "running": "—", "overdue": "", "later": ""}


def test_a_state_not_named_keeps_the_columns_missing_text(tmp_path):
    cells = _render(tmp_path, {"dueUnobserved": "unknown"})
    assert cells == {"done": "+4d", "running": "—", "overdue": "unknown", "later": "—"}


def test_an_unknown_state_or_text_is_a_schema_error(tmp_path):
    with pytest.raises(Exception) as caught:
        _render(tmp_path, {"inprogress": "blank"})
    assert "E_" in str(caught.value)
