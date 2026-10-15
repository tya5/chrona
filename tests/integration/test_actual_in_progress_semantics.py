"""Started incomplete Actuals are rendered as Actual, with progress and an as-of delta (#1582)."""
from datetime import date

from tests.support import synthetic_review as sr


AS_OF = date(2026, 2, 10)


def _project():
    objects = {}
    observations = []
    for end_group, end in (("before", date(2026, 2, 20)), ("late", date(2026, 2, 5))):
        for progress in (0.0, 0.6, 1.0):
            object_id = f"{end_group}-{str(progress).replace('.', '')}"
            start = date(2026, 2, 1)
            objects[object_id] = sr.span(object_id, start, (end - start).days, title=object_id)
            observations.append({
                "id": f"{object_id}-observation", "sequence": 1, "projectObjectId": object_id,
                "actual": {"start": start.isoformat(), "progress": progress},
            })
    objects["no-start"] = sr.span("no-start", date(2026, 2, 1), 14, title="No start")
    observations.append({"id": "no-start-observation", "sequence": 1,
                         "projectObjectId": "no-start", "actual": {"progress": 0.6}})
    return sr.project(objects), {"version": "chrona/actual-set/v0.3", "kind": "actual-set",
        "id": "open-actuals", "body": {"asOf": AS_OF.isoformat(), "observations": observations}}


def _render(tmp_path):
    project, actual = _project()
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["tableColumns"] = [
        {"id": "Task", "source": "title", "missing": "em-dash", "align": "start",
         "width": "content", "headerOrientation": "horizontal"},
        {"id": "Delta", "source": {"comparisonFacet": "finishDelta"}, "format": "signedDays",
         "missing": "em-dash", "missingBy": {"inProgress": "blank"}, "align": "end",
         "width": "content", "headerOrientation": "horizontal"},
    ]
    return sr.render(tmp_path, project, presentation=parts, actual=actual)


def test_open_actuals_draw_with_declared_progress_and_known_delta_but_without_fake_finish(tmp_path):
    rendered = _render(tmp_path)
    primitives = rendered.surface.primitives
    actual_marks = {item.source_ref: item for item in primitives if item.purpose == "actual"}
    assert set(actual_marks) == {"before-00", "before-06", "before-10", "late-00", "late-06", "late-10"}
    assert all(item.bounds[2] > 0 for item in actual_marks.values())
    progress = {item.source_ref: item for item in primitives if item.purpose == "progress-fill"}
    assert set(progress) == {"before-06", "before-10", "late-06", "late-10"}
    assert progress["before-10"].bounds[2] > progress["before-06"].bounds[2] > 0
    assert progress["late-10"].bounds[2] > progress["late-06"].bounds[2] > 0
    cells = {item.source_ref: item.text for item in primitives
             if item.purpose == "table-cell" and item.table_column_id == "Delta"}
    assert {key: cells[key] for key in ("before-00", "before-06", "before-10")} == {
        "before-00": "", "before-06": "", "before-10": "",
    }
    assert {key: cells[key] for key in ("late-00", "late-06", "late-10")} == {
        "late-00": "+5d", "late-06": "+5d", "late-10": "+5d",
    }
    assert "W_LAYOUT_ACTUAL_INCOMPLETE:no-start" in rendered.scene.diagnostics

