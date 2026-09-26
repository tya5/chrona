"""Executable evidence for the #378 Project learning ladder."""
from pathlib import Path

import yaml

from chrona.presentation.model.closure import resolve_draft_render
from chrona.resources import default_preset_resource, default_preset_root
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.usecases.local_authoring import initialize_project
from chrona.usecases.render_review import RenderRequest, render_review


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
STAGES = ("01-spans", "02-gate", "03-relations", "04-calendar", "05-constraints", "06-rollup", "07-actuals")


def _render(project: Path, actual: Path | None = None, view: Path | None = None):
    draft = resolve_draft_render(project_path=project, actual_path=actual,
                                 view_path=view,
                                 preset_path=Path(str(default_preset_resource())),
                                 preset_root=Path(str(default_preset_root())))
    return render_review(RenderRequest(draft.closure, draft.asset_root, ReferenceScheduler(),
                                       asset_root=draft.asset_root, draft_auto_block=draft.auto_block))


def test_each_small_tutorial_stage_renders_and_introduces_its_own_concept():
    sources = {stage: ROOT / "examples/onboarding" / stage / "project.yaml" for stage in STAGES}
    projects = {stage: yaml.safe_load(path.read_bytes()) for stage, path in sources.items()}
    assert all(project["version"] == "timeline/v0.7" for project in projects.values())
    assert len(projects["01-spans"]["objects"]) == 2
    assert projects["02-gate"]["objects"]["release"]["type"] == "gate"
    assert projects["03-relations"]["relations"][0]["lag"] == "2d"
    assert projects["04-calendar"]["objects"]["build"]["schedule"]["amount"] == "5wd"
    assert projects["04-calendar"]["calendars"]["team-week"]["exceptions"]
    assert projects["05-constraints"]["objects"]["build"]["schedule"]["constraints"]
    assert projects["05-constraints"]["objects"]["release"]["deadline"]
    assert projects["06-rollup"]["objects"]["phase"]["schedule"]["mode"] == "rollup"
    assert projects["06-rollup"]["objects"]["design"]["parent"] == "phase"
    for stage, project_path in sources.items():
        actual = project_path.parent / "actual.yaml" if stage == "07-actuals" else None
        view = project_path.parent / "view.yaml" if stage == "07-actuals" else None
        rendered = _render(project_path, actual, view)
        assert rendered.artifact.content.startswith(b"<svg ")
        if actual is not None:
            assert b'data-purpose="progress-fill"' in rendered.artifact.content


def test_editing_the_first_tutorial_project_changes_the_render(tmp_path: Path):
    source = ROOT / "examples/onboarding/01-spans/project.yaml"
    edited = yaml.safe_load(source.read_bytes())
    edited["objects"]["design"]["title"] = "Design, revised by the reader"
    edited_path = tmp_path / "project.yaml"
    edited_path.write_text(yaml.safe_dump(edited, sort_keys=False), encoding="utf-8")
    assert _render(source).artifact.content != _render(edited_path).artifact.content


def test_adding_a_task_to_initialized_project_changes_its_render(tmp_path: Path):
    starter = tmp_path / "demo"
    initialize_project(starter)
    project_path = starter / "project.yaml"
    before = _render(project_path).artifact.content
    edited = yaml.safe_load(project_path.read_bytes())
    edited["objects"]["verification"] = {
        "type": "task", "title": "Verification added by the reader",
        "schedule": {"mode": "fixed-span", "start": "2026-12-16", "end": "2026-12-17"},
    }
    project_path.write_text(yaml.safe_dump(edited, sort_keys=False), encoding="utf-8")
    after = _render(project_path).artifact.content
    assert after != before
    assert b'data-source-ref="verification"' in after


def test_advanced_tutorial_examples_select_their_declared_closure_edges():
    halcyon = ROOT / "examples/halcyon-1"
    project = yaml.safe_load((halcyon / "project.yaml").read_bytes())
    scenario_view = yaml.safe_load((halcyon / "views/06-flight-readiness.yaml").read_bytes())
    snapshot_view = yaml.safe_load((halcyon / "views/07-replan-baseline.yaml").read_bytes())
    context = yaml.safe_load((halcyon / "contexts/07-replan-baseline.yaml").read_bytes())
    assert scenario_view["body"]["comparison"]["scenario"] in project["scenarios"]
    assert scenario_view["body"]["comparison"]["baseline"] == "scenario"
    assert snapshot_view["body"]["comparison"]["baseline"] == "snapshot"
    assert context["body"]["inputs"]["snapshot"]["kind"] == "snapshot-ref"
    orion = ROOT / "examples/orion-asic"
    extended = yaml.safe_load((orion / "project.yaml").read_bytes())
    package = extended["extensions"][0]["resource"]
    assert package["kind"] == "profile-package"
    assert (orion / package["address"]).is_file()
