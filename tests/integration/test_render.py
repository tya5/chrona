from datetime import date
from pathlib import Path

from chrona.presentation.renderers.generic import render_svg
from chrona.presentation.scene.schedule import scene_from_schedule
from chrona.scheduling.scheduler import ScheduleResult


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

    scene = scene_from_schedule(project, result.placements)
    svg = render_svg(scene, {"marker", "metadata", "text-alternative"})

    assert '<svg ' in svg
    assert 'Build &amp; Test' in svg
    assert 'marker-end="url(#arrow)"' in svg
    assert '<rect ' in svg
    assert '<circle ' in svg
    assert 'data-presentation-scene="minimal"' in svg
    assert '<text x="24" y="34"' in svg
    assert '<text x="24" y="81"' in svg
    assert 'font-size="10" fill="#6b6b6b">2026-10-01</text>' in svg


def test_controller_x_legacy_documentation_artifact_is_current():
    import yaml
    from chrona.scheduling.scheduler import schedule

    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    project = yaml.safe_load((root / "conformance/controller-x.yaml").read_text())
    scene = scene_from_schedule(project, schedule(project).placements)
    generated = render_svg(scene, {"marker", "metadata", "text-alternative"})
    assert generated == (root / "conformance/controller-x.svg").read_text()


def test_svg_rejects_an_incapable_target_and_scene_is_deterministic():
    project = {"project": {"title": "Demo"}, "objects": {"task": {"title": "Task"}}, "relations": []}
    result = ScheduleResult({"task": {"at": date(2026, 10, 1)}}, [])
    scene = scene_from_schedule(project, result.placements)
    assert render_svg(scene) == render_svg(scene)
    try:
        render_svg(scene, {"metadata", "text-alternative"})
    except ValueError as error:
        assert str(error) == "E_TARGET_CAPABILITY: marker"
    else:
        raise AssertionError("incapable target rendered SVG")
