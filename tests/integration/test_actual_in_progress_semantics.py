"""Started incomplete Actuals are rendered as Actual, with progress and an as-of delta (#1582)."""
from datetime import date

import pytest

from chrona.resources import builtin_preset_source_root, safe_load

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


def _assert_fill_measures_planned_span(primitives, fills, progress_of):
    """#1869: an open Actual's fill is progress x the planned span from the observed start, clipped to the Actual."""
    actual = {item.source_ref: item for item in primitives if item.purpose == "actual"}
    planned = {item.source_ref: item for item in primitives if item.purpose == "planned"}
    for ref, fill in fills.items():
        expected = min(actual[ref].bounds[2], progress_of[ref] * planned[ref].bounds[2])
        assert fill.bounds[2] == pytest.approx(expected, rel=0.02, abs=0.5), ref
    # before-*: the plan is longer than the elapsed span, so both fractions are clipped to the Actual mark.
    assert fills["before-10"].bounds[2] == pytest.approx(fills["before-06"].bounds[2])
    # late-*: the plan is shorter, so the fractions of the planned span differ.
    assert fills["late-10"].bounds[2] > fills["late-06"].bounds[2] > 0


def test_open_actuals_draw_with_declared_progress_and_known_delta_but_without_fake_finish(tmp_path):
    rendered = _render(tmp_path)
    primitives = rendered.surface.primitives
    actual_marks = {item.source_ref: item for item in primitives if item.purpose == "actual"}
    assert set(actual_marks) == {"before-00", "before-06", "before-10", "late-00", "late-06", "late-10"}
    assert all(item.bounds[2] > 0 for item in actual_marks.values())
    progress = {item.source_ref: item for item in primitives if item.purpose == "progress-fill"}
    assert set(progress) == {"before-06", "before-10", "late-06", "late-10"}
    _assert_fill_measures_planned_span(
        primitives, progress, {"before-06": 0.6, "before-10": 1.0, "late-06": 0.6, "late-10": 1.0})
    cells = {item.source_ref: item.text for item in primitives
             if item.purpose == "table-cell" and item.table_column_id == "Delta"}
    assert {key: cells[key] for key in ("before-00", "before-06", "before-10")} == {
        "before-00": "", "before-06": "", "before-10": "",
    }
    assert {key: cells[key] for key in ("late-00", "late-06", "late-10")} == {
        "late-00": "+5d", "late-06": "+5d", "late-10": "+5d",
    }
    assert "W_LAYOUT_ACTUAL_INCOMPLETE:no-start" in rendered.scene.diagnostics


@pytest.mark.parametrize("design", ("target-b", "sunday"))
def test_shared_design_defaults_fill_open_actual_fraction_and_authored_view_wins(tmp_path, design):
    project, actual = _project()
    # Exercise fractional fractions alongside the boundary controls 0 and 1.
    next(item for item in actual["body"]["observations"]
         if item["projectObjectId"] == "late-06")["actual"]["progress"] = 0.3
    project["objects"]["before-06"]["plannedProgress"] = 0.25
    parts = sr.bundle("executive-light")
    design_root = builtin_preset_source_root(f"designs/{design}")
    design_layout = safe_load(design_root.joinpath("layout.yaml").read_bytes())
    assert design_layout["viewDefaults"]["progressFill"] == {"source": "actual"}
    # Exercise the published design default through the generic View while
    # retaining this synthetic fixture's compatible Theme and Layout geometry.
    parts["layout"]["viewDefaults"] = {
        "progressFill": design_layout["viewDefaults"]["progressFill"],
    }
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    # The generic View does not select a fill; the shared design defaults do.
    parts["view"]["body"].pop("progressFill", None)

    directory = tmp_path / design
    directory.mkdir()
    rendered = sr.render(directory, project, presentation=parts, actual=actual)
    fills = {item.source_ref: item for item in rendered.surface.primitives
             if item.purpose == "progress-fill"}
    assert set(fills) == {"before-06", "before-10", "late-06", "late-10"}
    assert fills["before-06"].scene_id.startswith("progress-fill:actual:")
    assert fills["late-06"].scene_id.startswith("progress-fill:actual:")
    _assert_fill_measures_planned_span(
        rendered.surface.primitives, fills,
        {"before-06": 0.6, "before-10": 1.0, "late-06": 0.3, "late-10": 1.0})

    # An authored source remains authoritative over the design's actual default.
    parts["view"]["body"]["progressFill"] = {"source": "planned"}
    override_directory = tmp_path / f"{design}-override"
    override_directory.mkdir()
    overridden = sr.render(override_directory, project,
                           presentation=parts, actual=actual)
    override_fills = {item.source_ref: item for item in overridden.surface.primitives
                      if item.purpose == "progress-fill"}
    assert set(override_fills) == {"before-06"}
    assert override_fills["before-06"].scene_id.startswith("progress-fill:planned:")


def test_actual_point_progress_is_completed_inside_multipart_glyph_without_scene_clip_alias(tmp_path):
    project, actual = _project()
    project["objects"]["gate"] = sr.point("gate", date(2026, 2, 3), title="Gate")
    actual["body"]["observations"].append({
        "id": "gate-observation", "sequence": 1, "projectObjectId": "gate",
        "actual": {"at": "2026-02-04", "progress": 0.6},
    })
    parts = sr.bundle("executive-light")
    parts["view"]["body"]["rows"] = {"mode": "automatic"}
    parts["view"]["body"]["progressFill"] = {"source": "actual"}
    parts["theme"]["body"]["values"]["milestone-symbol"]["value"] = {
        "shape": "glyph", "viewBox": [10, 10], "parts": [
            {"d": "M0 0L7 0L7 10L0 10Z", "paint": "fill"},
            {"d": "M5 0L10 0L10 10L5 10Z", "paint": "fill"},
        ],
    }
    rendered = sr.render(tmp_path, project, presentation=parts, actual=actual)
    actual_parts = [primitive for primitive in rendered.surface.primitives
                    if primitive.purpose == "actual" and primitive.source_ref == "gate"]
    progress = next(primitive for primitive in rendered.surface.primitives
                    if primitive.purpose == "progress-fill" and primitive.source_ref == "gate")
    assert {primitive.scene_id for primitive in actual_parts} == {
        "actual:gate:gate:part0", "actual:gate:gate:part1", "actual:gate:gate:part2",
    }
    assert progress.kind == "Symbol" and progress.symbol is not None
    assert progress.clip_source_id is None
    points = tuple(point for command in progress.symbol.outline for point in command.points)
    left, _, width, _ = actual_parts[0].bounds
    assert max(x for x, _ in points) <= left + width * 0.6 + 1e-5

