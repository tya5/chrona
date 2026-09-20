from datetime import date
from pathlib import Path

from chrona.presentation.renderers.generic import render_svg
from chrona.presentation.model.surface_content import SurfaceContentInput
from chrona.presentation.model.settings import builtin_bases
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

    scene = scene_from_schedule(project, result)
    svg = render_svg(scene, {"marker", "metadata", "text-alternative"})

    assert '<svg ' in svg
    assert 'Build &amp; Test' in svg
    assert 'marker-end="url(#arrow)"' in svg
    assert '<rect ' in svg
    assert '<circle ' in svg
    assert 'E_PRESENTATION_LEGACY_ADAPTER' in svg
    assert '<text x="24" y="34"' in svg
    assert '<text x="24" y="81"' in svg
    assert 'font-size="10" fill="#6b6b6b">2026-10-01</text>' in svg


def test_controller_x_legacy_documentation_artifact_is_current():
    import yaml
    from chrona.scheduling.scheduler import schedule

    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    project = yaml.safe_load((root / "conformance/controller-x.yaml").read_text())
    scene = scene_from_schedule(project, schedule(project))
    generated = render_svg(scene, {"marker", "metadata", "text-alternative"})
    assert generated == (root / "conformance/controller-x.svg").read_text()


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
    svg = render_svg(scene, {"marker", "metadata", "text-alternative"}, settings)
    assert 'width="1600"' in svg
    assert 'data-purpose="milestone"' in svg and 'fill="#102B50"' in svg
    assert 'data-surface-id="minimal"' in svg
    assert 'data-scene-id=' in svg and '>Task</text>' in svg


def test_i3_f_minimal_svg_routes_scene_relations_from_completed_scene():
    project = {
        "project": {"title": "Demo"},
        "objects": {"task": {"title": "Task"}, "gate": {"title": "Gate"}},
        "relations": [{"id": "task-to-gate", "type": "dependency",
                       "from": {"object": "task", "endpoint": "end"},
                       "to": {"object": "gate", "endpoint": "at"}}],
    }
    scene = scene_from_schedule(project, ScheduleResult({
        "task": {"start": date(2026, 10, 1), "end": date(2026, 10, 8)},
        "gate": {"at": date(2026, 10, 10)},
    }, []))
    settings = builtin_bases()["executive-v0.2"]
    svg = render_svg(scene, {"marker", "metadata", "text-alternative"}, settings)
    assert 'data-surface-id="minimal"' in svg
    assert 'data-purpose="routed-connector"' in svg
    assert 'data-source-ref="task-to-gate"' in svg
    assert 'data-from-port-id=' in svg and 'data-to-port-id=' in svg


def test_i3_f_minimal_svg_accepts_normalized_annotation_input_before_scene_build():
    project = {
        "project": {"title": "Demo"},
        "objects": {"task": {"title": "Task"}},
        "relations": [],
    }
    scene = scene_from_schedule(project, ScheduleResult({
        "task": {"start": date(2026, 10, 1), "end": date(2026, 10, 8)},
    }, []))
    settings = builtin_bases()["executive-v0.2"]
    content = SurfaceContentInput(annotations=({
        "id": "risk", "purpose": "callout", "text": "Review risk",
        "anchor": {"kind": "object", "id": "task", "facet": "planned", "endpoint": "finish"},
    },))
    svg = render_svg(scene, {"marker", "metadata", "text-alternative"}, settings, content)
    assert 'data-surface-id="minimal"' in svg
    assert 'data-purpose="presentation-annotation"' in svg
    assert 'data-purpose="annotation-leader"' in svg
    assert 'Review risk' in svg
