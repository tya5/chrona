from datetime import date

from chrona.render import render_svg
from chrona.scene import scene_from_schedule
from chrona.scheduler import ScheduleResult


def test_render_svg_projects_placements_without_owning_them():
    project = {
        "project": {"title": "Demo"},
        "objects": {
            "task": {"title": "Build & Test"},
            "gate": {"title": "Release"},
        },
        "relations": [
            {
                "from": {"object": "task", "endpoint": "end"},
                "to": {"object": "gate", "endpoint": "at"},
            }
        ],
    }
    result = ScheduleResult(
        {
            "task": {"start": date(2026, 10, 1), "end": date(2026, 10, 8)},
            "gate": {"at": date(2026, 10, 9)},
        },
        [],
    )

    scene = scene_from_schedule(project, result)
    svg = render_svg(scene, {"marker", "metadata", "text-alternative"})

    assert '<svg ' in svg
    assert 'Build &amp; Test' in svg
    assert 'marker-end="url(#arrow)"' in svg
    assert '<rect ' in svg
    assert '<circle ' in svg


def test_svg_rejects_an_incapable_target_and_scene_is_deterministic():
    project = {"project": {"title": "Demo"}, "objects": {"task": {"title": "Task"}}, "relations": []}
    result = ScheduleResult({"task": {"at": date(2026, 10, 1)}}, [])
    scene = scene_from_schedule(project, result)
    assert render_svg(scene) == render_svg(scene)
    try:
        render_svg(scene, {"metadata", "text-alternative"})
    except ValueError as error:
        assert str(error) == "E_TARGET_CAPABILITY: marker"
    else:
        raise AssertionError("incapable target rendered SVG")
