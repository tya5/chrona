"""A heading part can require an Actual Set or a Snapshot and is omitted when the render has none (#1880 row 2)."""
from datetime import date

import pytest

from chrona.presentation.model.closure import ClosureError
from tests.integration.test_heading_omit_when_zero import _subtitle_role
from tests.integration.test_heading_counts import _parts
from tests.support import synthetic_review as sr

ACTUAL = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
          "body": {"asOf": "2026-02-04", "observations": []}}
SUBTITLE = [{"text": "SCHEDULE"}, {"text": " / ACTUAL", "presentWhen": "actualSet"},
            {"text": " / BASELINE", "presentWhen": "snapshot"}, {"text": " / END"}]


def _source():
    return sr.project({"a": sr.span("a", date(2026, 2, 2), 5)})


def _subtitle(tmp_path, *, actual=None, snapshot=None, parts=None):
    parts = parts or _parts()
    _subtitle_role(parts)
    parts["view"]["body"]["grouping"] = {"by": "none", "missing": "ungrouped"}
    parts["view"]["body"]["heading"] = {"title": "Plan", "subtitle": SUBTITLE}
    rendered = sr.render(tmp_path, _source(), presentation=parts, actual=actual, snapshot_project=snapshot)
    return [p.text for p in rendered.surface.primitives if p.scene_id == "subtitle"], rendered


@pytest.mark.parametrize(("actual", "snapshot", "expected"), [
    (None, None, "SCHEDULE / END"),
    (ACTUAL, None, "SCHEDULE / ACTUAL / END"),
    (None, "snapshot", "SCHEDULE / BASELINE / END"),
    (ACTUAL, "snapshot", "SCHEDULE / ACTUAL / BASELINE / END"),
], ids=["neither", "actual", "snapshot", "both"])
def test_a_part_is_kept_only_when_its_data_is_supplied(tmp_path, actual, snapshot, expected):
    texts, _ = _subtitle(tmp_path, actual=actual, snapshot=_source() if snapshot else None)
    assert texts == [expected]


def test_an_omitted_part_reports_no_missing_fact(tmp_path):
    parts = _parts()
    _subtitle_role(parts)
    parts["view"]["body"]["heading"] = {"title": "Plan", "subtitle": [
        {"text": "AS OF {asOf}", "presentWhen": "actualSet"}, {"text": "Plan"}]}
    rendered = sr.render(tmp_path, _source(), presentation=parts)
    assert not [item for item in rendered.warning_records if "HEADING_FACT" in item.payload["code"]]
    assert [p.text for p in rendered.surface.primitives if p.scene_id == "subtitle"] == ["Plan"]


def test_an_unknown_condition_is_refused(tmp_path):
    parts = _parts()
    parts["view"]["body"]["heading"] = {"title": [{"text": "x", "presentWhen": "forecast"}]}
    with pytest.raises(ClosureError) as caught:
        sr.render(tmp_path, _source(), presentation=parts)
    assert str(caught.value) == "E_VIEW_SCHEMA"
