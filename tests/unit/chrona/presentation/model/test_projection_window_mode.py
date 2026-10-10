"""ReviewProjection retains the View's declared temporal-window mode."""
from dataclasses import replace
from datetime import date

from chrona.presentation.model.projection import ReviewProjection, WindowMode, build_review_projection
from tests.unit.chrona.presentation.model.test_projection_rows import typed_view


def _projection(mode: str) -> ReviewProjection:
    project = {"objects": {"task": {"title": "Task", "fields": {}}}, "entities": {}}
    placements = {"task": {"start": date(2026, 1, 1), "end": date(2026, 1, 10)}}
    window = {"mode": mode}
    if mode == "explicit":
        window.update(start="2026-01-01", end="2026-01-10")
    view = typed_view({"body": {
        "comparison": {"actual": "optional", "facets": []},
        "window": window,
        "rows": {"mode": "automatic"},
    }})
    actuals = {"body": {"asOf": "2026-01-10", "observations": [{
        "id": "obs-task", "projectObjectId": "task", "sequence": 1,
        "actual": {"start": "2026-01-01", "finish": "2026-01-10"},
    }]}}
    return build_review_projection(project, placements, view, actuals)


def test_projection_retains_declared_window_mode_even_when_date_windows_match():
    projections = {
        mode: _projection(mode)
        for mode in ("selected-planned", "selected-comparison", "explicit")
    }

    assert {mode: projection.window_mode for mode, projection in projections.items()} == {
        "selected-planned": WindowMode.SELECTED_PLANNED,
        "selected-comparison": WindowMode.SELECTED_COMPARISON,
        "explicit": WindowMode.EXPLICIT,
    }
    assert {projection.window for projection in projections.values()} == {
        (date(2026, 1, 1), date(2026, 1, 10)),
    }

    # Mode is the only changed projection fact for these equal-window inputs.
    planned = projections["selected-planned"]
    for projection in projections.values():
        assert replace(projection, window_mode=WindowMode.SELECTED_PLANNED) == planned


def test_legacy_projection_construction_and_replace_keep_typed_window_mode():
    window = (date(2026, 1, 1), date(2026, 1, 10))
    legacy = ReviewProjection((), window, (), ())
    assert legacy.window_mode is WindowMode.SELECTED_PLANNED

    explicit = _projection("explicit")
    changed = replace(explicit, window_mode=WindowMode.SELECTED_COMPARISON)
    assert changed.window == explicit.window
    assert changed.items == explicit.items
    assert changed.window_mode is WindowMode.SELECTED_COMPARISON
