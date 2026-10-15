"""An Actual interval's exclusive `finish` must be after its `start`; CSV `actual_finish` is inclusive (#1565).

Synthetic Projects only; no test reads `examples/`.
"""
from __future__ import annotations

from datetime import date

import pytest
import yaml

from chrona.presentation.model.closure import ClosureError
from chrona.usecases.table_import import import_table
from tests.support import synthetic_review as sr


def _actual(start: str, finish: str) -> dict:
    return {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed", "body": {
        "asOf": "2026-10-14", "observations": [
            {"id": "ok", "sequence": 1, "projectObjectId": "other", "actual": {"start": "2026-10-01", "finish": "2026-10-02"}},
            {"id": "review-observed", "sequence": 1, "projectObjectId": "review", "actual": {"start": start, "finish": finish}}]}}


def _source() -> dict:
    return sr.project({"review": sr.span("review", date(2026, 10, 12), 1), "other": sr.span("other", date(2026, 10, 1), 2)})


@pytest.mark.parametrize("finish", ["2026-10-12", "2026-10-11"])
def test_a_same_day_or_backwards_actual_is_rejected_at_read_naming_the_observation(tmp_path, finish):
    with pytest.raises(ClosureError) as caught:
        sr.render(tmp_path, _source(), presentation=sr.bundle("executive-light"), actual=_actual("2026-10-12", finish))
    error = caught.value
    assert error.diagnostic_id == "E_ACTUAL_FINISH_NOT_AFTER_START"
    assert "'review-observed'" in error.detail and "exclusive end" in error.detail and "finish: 2026-10-13" in error.detail
    assert error.source_ref == "/body/observations/1/actual/finish"


def test_csv_actuals_round_trip_to_a_render_with_the_one_day_task_visible(tmp_path):
    table = ("id,title,start,finish,actual_start,actual_finish\n"
             "a,Design,2026-10-05,2026-10-09,2026-10-05,2026-10-09\n"
             "b,Review,2026-10-12,2026-10-12,2026-10-12,2026-10-12\n")
    result = import_table(table, project_id="p", as_of="2026-10-14")
    assert result.ok
    project, actual = yaml.safe_load(result.project_yaml), yaml.safe_load(result.actual_yaml)
    assert [o["actual"]["finish"] for o in actual["body"]["observations"]] == ["2026-10-10", "2026-10-13"]
    source = sr.project({"a": sr.span("a", date(2026, 10, 5), 5), "b": sr.span("b", date(2026, 10, 12), 1)})
    assert project["objects"]["a"]["schedule"]["end"] == "2026-10-10"
    rendered = sr.render(tmp_path, source, presentation=sr.bundle("executive-light"), actual=actual)
    marks = {p.scene_id for p in rendered.surface.primitives if p.scene_id.startswith("actual:")}
    assert any(m.endswith(":a") for m in marks) and any(m.endswith(":b") for m in marks)
