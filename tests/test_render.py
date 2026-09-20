from datetime import date
from hashlib import sha256
from pathlib import Path
import subprocess

from chrona.render import render_svg
from chrona.presentation_settings import builtin_bases
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
    assert 'E_PRESENTATION_LEGACY_ADAPTER' in svg


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


def test_minimal_svg_consumes_resolved_presentation_settings():
    project = {"project": {"title": "Demo"}, "objects": {"task": {"title": "Task"}}, "relations": []}
    scene = scene_from_schedule(project, ScheduleResult({"task": {"at": date(2026, 10, 1)}}, []))
    settings = builtin_bases()["executive-v0.2"]
    for asset, style in zip(settings["context"]["fontMetrics"]["assets"], ("Regular", "Bold")):
        path = Path(subprocess.run(["fc-match", "-f", "%{file}", f"Nimbus Sans:style={style}"], capture_output=True, text=True, check=True).stdout)
        asset["contentIdentity"] = "sha256:" + sha256(path.read_bytes()).hexdigest()
    svg = render_svg(scene, {"marker", "metadata", "text-alternative"}, settings)
    assert 'width="1600"' in svg
    assert 'fill="#3986E6"' in svg
