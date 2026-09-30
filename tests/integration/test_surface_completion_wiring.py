"""The composer hands every completed batch to one completion phase, after annotations (#592 I592-6)."""
import sys
from pathlib import Path

import pytest

from chrona.app.cli import main
from chrona.presentation.layout import surface_completion, surface_composer

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_completion_runs_once_after_annotations_with_every_batch(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    captured: dict[str, object] = {}
    annotations = surface_composer.place_annotations
    completion = surface_composer.complete_surface_layout

    def annotations_spy(context):
        events.append("annotations")
        captured["annotation_batch"] = annotations(context)
        return captured["annotation_batch"]

    def completion_spy(context):
        events.append("completion")
        captured["context"] = context
        return completion(context)

    monkeypatch.setattr(surface_composer, "place_annotations", annotations_spy)
    monkeypatch.setattr(surface_composer, "complete_surface_layout", completion_spy)
    example = ROOT / "examples/halcyon-1"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(example / "project.yaml"), "--actual", str(example / "actual.yaml"),
        "--view", str(example / "views/02-programme-board.yaml"), "--theme", str(example / "themes/wallboard.yaml"),
        "--scheme", str(example / "schemes/control-room-dark.yaml"), "--layout", str(example / "layouts/wallboard.yaml"),
        "--summary", str(example / "profiles/summary.yaml"), "--detail", str(example / "profiles/detail.yaml"),
        "--output", str(tmp_path / "out.svg"),
    ])
    main()

    assert events == ["annotations", "completion"]
    context = captured["context"]
    batch = captured["annotation_batch"]
    assert isinstance(context, surface_completion.SurfaceCompletionContext)
    # Annotation geometry reached the completion phase, and nothing from it was dropped.
    placed_ids = {item.placement_id for item in context.text} | {item.placement_id for item in context.shapes}
    assert {item.placement_id for item in batch.text} <= placed_ids
    assert {item.placement_id for item in batch.shapes} <= placed_ids


def test_the_composer_keeps_its_public_surface() -> None:
    assert surface_composer.SurfaceLayoutComposition is surface_completion.SurfaceLayoutComposition
    assert callable(surface_composer.compose_surface_layout)
    assert callable(surface_composer.timeline_content_block_requirement)
