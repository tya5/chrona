"""A missing actual anchor retains the authored View pointer through render reporting."""
from datetime import date

import pytest

from chrona.usecases.failure_report import report_failure
from chrona.usecases.render_review import RenderFailed
from tests.support import synthetic_review as sr


@pytest.mark.parametrize("observed", [False, True], ids=["unobserved", "in-progress"])
def test_missing_actual_anchor_names_annotation_object_reason_and_view_pointer(tmp_path, observed):
    source = sr.project({"titlecard": sr.span("titlecard", date(2026, 2, 2), 40)})
    parts = sr.bundle()
    sr.add_notes(source, parts["view"], ("titlecard",), (sr.candidate("plot-near"),), words=1)
    parts["view"]["body"]["annotations"][0]["anchor"]["facet"] = "actual"
    observations = ([{"id": "started", "sequence": 1, "projectObjectId": "titlecard",
                      "actual": {"start": "2026-02-09", "progress": 0.4}}] if observed else [])
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "observed",
              "body": {"asOf": "2026-02-20", "observations": observations}}

    with pytest.raises(RenderFailed) as failed:
        sr.render(tmp_path, source, presentation=parts, actual=actual)

    assert failed.value.code == "E_PRESENTATION_ANCHOR_MISSING"
    assert failed.value.source_ref == "/body/annotations/0/anchor"
    report = report_failure(failed.value)
    assert report.status == "rejected" and report.exit_code == 1
    assert len(report.diagnostics) == 1
    row = report.diagnostics[0]
    assert row["code"] == "E_PRESENTATION_ANCHOR_MISSING"
    assert row["component"] == "presentation"
    assert row["sourceRef"] == "/body/annotations/0/anchor"
    assert "note-0" in row["message"]
    assert "titlecard" in row["message"]
    assert "actual" in row["message"]
    assert "completed" in row["message"] and "mark" in row["message"]
