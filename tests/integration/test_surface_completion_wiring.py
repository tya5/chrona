"""The composer hands every completed batch to one completion phase, after annotations (#592 I592-6)."""
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main
from chrona.presentation.layout import surface_annotations, surface_completion, surface_composer
from tests.support.draft_packages import stage_project_package_store

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_completion_runs_once_after_annotations_with_every_batch(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    captured: dict[str, object] = {}
    annotations = surface_annotations.place_annotations
    route_options = surface_composer.compose_routes_and_member_labels
    select_options = surface_composer.complete_route_label_options
    completion = surface_composer.complete_surface_layout

    def annotations_spy(context):
        events.append("annotation-option")
        captured.setdefault("option_contexts", []).append(context)
        batch = annotations(context)
        captured.setdefault("option_batches", []).append(batch)
        return batch

    def route_options_spy(context):
        captured["options"] = route_options(context)
        return captured["options"]

    def select_options_spy(options, context):
        plan, batch = select_options(options, context)
        captured["selected_plan"] = plan
        captured["selected_batch"] = batch
        return plan, batch

    def completion_spy(context):
        events.append("completion")
        captured["context"] = context
        return completion(context)

    monkeypatch.setattr(surface_composer, "compose_routes_and_member_labels", route_options_spy)
    monkeypatch.setattr(surface_composer, "complete_route_label_options", select_options_spy)
    monkeypatch.setattr(surface_annotations, "place_annotations", annotations_spy)
    monkeypatch.setattr(surface_composer, "complete_surface_layout", completion_spy)
    example = ROOT / "examples/halcyon-1"
    project_path = example / "project.yaml"
    project = yaml.safe_load(project_path.read_bytes())
    store_config = stage_project_package_store(tmp_path / "project-store", project, example)
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(project_path), "--actual", str(example / "actual.yaml"),
        "--store-config", str(store_config),
        "--view", str(example / "views/02-programme-board.yaml"), "--theme", str(example / "themes/wallboard.yaml"),
        "--scheme", str(example / "schemes/control-room-dark.yaml"), "--layout", str(example / "layouts/wallboard.yaml"),
        "--summary", str(example / "profiles/summary.yaml"), "--detail", str(example / "profiles/detail.yaml"),
        "--output", str(tmp_path / "out.svg"),
    ])
    main()

    options = captured["options"]
    expected_options = 1 + (options.retry is not None)
    assert events == ["annotation-option"] * expected_options + ["completion"]
    assert len(captured["option_contexts"]) == len(captured["option_batches"]) == expected_options
    indexes = [context.surface_obstacles for context in captured["option_contexts"]]
    assert indexes[0] is options.first.obstacles
    if options.retry is not None:
        assert indexes[1] is options.retry.obstacles
    assert len({id(index) for index in indexes}) == expected_options
    context = captured["context"]
    batch = captured["selected_batch"]
    assert batch in captured["option_batches"]
    assert any(captured["selected_plan"].obstacles is option.obstacles
               for option in (options.first, options.retry) if option is not None)
    assert isinstance(context, surface_completion.SurfaceCompletionContext)
    # Annotation geometry reached the completion phase, and nothing from it was dropped.
    placed_ids = {item.placement_id for item in context.text} | {item.placement_id for item in context.shapes}
    assert {item.placement_id for item in batch.text} <= placed_ids
    assert {item.placement_id for item in batch.shapes} <= placed_ids


def test_the_composer_keeps_its_public_surface() -> None:
    assert surface_composer.SurfaceLayoutComposition is surface_completion.SurfaceLayoutComposition
    assert callable(surface_composer.compose_surface_layout)
    assert callable(surface_composer.timeline_content_block_requirement)
