"""Annotations place after all source content, share the one obstacle index and register their own geometry (#592 I592-5b)."""
import sys
from pathlib import Path

import pytest

from chrona.app.cli import main
from chrona.presentation.layout import surface_annotations, surface_composer

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_annotations_follow_source_content_and_extend_the_same_obstacle_index(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    seen: dict[str, tuple[int, int]] = {}
    call: dict[str, object] = {}

    def spy(name: str, original):
        def wrapper(*args, **kwargs):
            events.append(name)
            return original(*args, **kwargs)
        return wrapper

    for attribute, name in (("compose_surface_routes", "routes"), ("place_relation_labels", "relation-labels"),
                            ("place_legend", "legend"), ("place_notes", "notes"), ("place_summary", "summary")):
        monkeypatch.setattr(surface_composer, attribute, spy(name, getattr(surface_composer, attribute)))
    routes = surface_composer.compose_surface_routes

    def routes_spy(context):
        seen["routes"] = (id(context.obstacles), len(context.obstacles.all()))
        return routes(context)

    monkeypatch.setattr(surface_composer, "compose_surface_routes", routes_spy)
    original = surface_composer.place_annotations

    def annotations_spy(context):
        events.append("annotations")
        index = context.surface_obstacles
        seen["annotations-before"] = (id(index), len(index.all()))
        batch = original(context)
        seen["annotations-after"] = (id(index), len(index.all()))
        call["batch"] = batch
        return batch

    monkeypatch.setattr(surface_composer, "place_annotations", annotations_spy)
    example = ROOT / "examples/halcyon-1"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(example / "project.yaml"), "--actual", str(example / "actual.yaml"),
        "--view", str(example / "views/02-programme-board.yaml"), "--theme", str(example / "themes/wallboard.yaml"),
        "--scheme", str(example / "schemes/control-room-dark.yaml"), "--layout", str(example / "layouts/wallboard.yaml"),
        "--summary", str(example / "profiles/summary.yaml"), "--detail", str(example / "profiles/detail.yaml"),
        "--output", str(tmp_path / "out.svg"),
    ])
    main()

    assert events == ["routes", "relation-labels", "legend", "notes", "summary", "annotations"]
    assert seen["routes"][0] == seen["annotations-before"][0] == seen["annotations-after"][0]  # one index object
    assert seen["annotations-before"][1] >= seen["routes"][1]  # nothing was removed before annotations ran
    batch = call["batch"]
    assert batch.text and batch.relations  # this slide has annotation text and leaders
    assert seen["annotations-after"][1] > seen["annotations-before"][1]  # annotations registered their own geometry


def test_annotation_module_owns_its_paint_order_and_anchor_helpers() -> None:
    assert surface_annotations.ANNOTATION_PAINT_ORDER == 400
    assert not hasattr(surface_composer, "ANNOTATION_PAINT_ORDER")
    assert callable(surface_annotations.comparison_marks) and callable(surface_annotations.annotation_anchor_bounds)
