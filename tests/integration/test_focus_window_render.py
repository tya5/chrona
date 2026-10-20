"""Three PM focus rules through native Scene and the public PNG pipeline."""
from datetime import date

import pytest

from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.failure_report import report_failure
from chrona.usecases.render_review import RenderFailed
from tests.integration.test_window_row_admission_render import _parts
from tests.support import synthetic_review as sr


def focus_case(rule):
    source = sr.project({
        "done": sr.span("done", date(2026, 3, 12), 4, title="Finished review"),
        "ongoing": sr.span("ongoing", date(2026, 3, 18), 7, title="Next delivery"),
        "future": sr.span("future", date(2026, 5, 1), 4, title="Later delivery"),
    })
    actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "focus-facts",
              "body": {"asOf": "2026-03-15", "observations": [
                  {"id": "done-fact", "projectObjectId": "done", "sequence": 1,
                   "actual": {"start": "2026-03-12", "finish": "2026-03-14"}},
              ]}}
    parts = _parts(lanes=False)
    body = parts["view"]["body"]
    body["window"] = {"mode": "selected-planned"}
    if rule in {"finished", "focus"}:
        body["selection"] = {"include": {}, "exclude": {"state": ["finished"]}}
    if rule in {"relative", "focus"}:
        body["window"] = {"mode": "relative", "before": "1w", "after": "6w"}
    if rule == "focus":
        body["window"]["outside"] = "omit"
    return source, parts, actual


def render_focus_png(directory, rule):
    source, parts, actual = focus_case(rule)
    scene = sr.render(directory, source, presentation=parts, actual=actual)
    png = render_draft(DraftRenderRequest(
        directory / "project.yaml", "png", view=directory / "view.yaml",
        theme=directory / "theme.yaml", scheme=directory / "scheme.yaml",
        layout=directory / "layout.yaml", actual=directory / "actual.yaml",
        viewport="1600x900",
    )).artifact.content
    return scene, png


@pytest.mark.parametrize("rule,rows", [("finished", 2), ("relative", 3), ("focus", 1)])
def test_focus_rules_produce_expected_rows_and_real_png(tmp_path, rule, rows):
    rendered, png = render_focus_png(tmp_path, rule)
    assert len(rendered.surface.rows) == rows
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    if rule in {"finished", "focus"}:
        assert not any(item.source_ref == "done" for item in rendered.surface.primitives)
    if rule == "focus":
        assert not any(item.source_ref == "future" for item in rendered.surface.primitives)


@pytest.mark.parametrize("lanes", [False, True], ids=["automatic", "fixed-lanes"])
def test_default_keep_and_explicit_keep_have_identical_completed_output(tmp_path, lanes):
    source, _parts_unused, actual = focus_case("relative")
    parts = _parts(lanes=lanes)
    parts["view"]["body"]["window"].pop("outside")
    implicit_dir, explicit_dir = tmp_path / "implicit", tmp_path / "explicit"
    implicit_dir.mkdir()
    explicit_dir.mkdir()
    implicit = sr.render(implicit_dir, source, presentation=parts, actual=actual)
    parts["view"]["body"]["window"]["outside"] = "keep"
    explicit = sr.render(explicit_dir, source, presentation=parts, actual=actual)
    assert explicit.surface == implicit.surface
    assert explicit.artifact.content == implicit.artifact.content


def test_relative_window_without_actual_reports_the_declared_window_pointer(tmp_path):
    source, parts, _actual = focus_case("relative")
    parts["view"]["body"]["comparison"]["actual"] = "optional"
    with pytest.raises(RenderFailed) as failure:
        sr.render(tmp_path, source, presentation=parts)
    report = report_failure(failure.value)
    diagnostic = report.diagnostics[0]
    assert diagnostic["code"] == "E_VIEW_WINDOW_AS_OF_REQUIRED"
    assert diagnostic["sourceRef"] == "/body/window"
    assert diagnostic["component"] == "view"
