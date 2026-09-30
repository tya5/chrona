"""Legend and source-content phases run after routing, in slot order, outside obstacle search (#592 I592-5a)."""
import inspect
import sys
from pathlib import Path

import pytest

from chrona.app.cli import main
from chrona.presentation.layout import surface_composer, surface_content, surface_legend
from chrona.presentation.layout.obstacles import SurfaceObstacleIndex

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_content_phases_follow_routes_and_relation_labels_in_source_order(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    def spy(name: str, original):
        def wrapper(*args, **kwargs):
            events.append(name)
            return original(*args, **kwargs)
        return wrapper

    for attribute, name in (("compose_surface_routes", "routes"), ("place_relation_labels", "relation-labels"),
                            ("place_legend", "legend"), ("place_notes", "notes"),
                            ("complete_footer_band", "footer"), ("place_summary", "summary")):
        monkeypatch.setattr(surface_composer, attribute, spy(name, getattr(surface_composer, attribute)))
    example = ROOT / "examples/halcyon-1"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render", str(example / "project.yaml"), "--actual", str(example / "actual.yaml"),
        "--view", str(example / "views/02-programme-board.yaml"), "--theme", str(example / "themes/wallboard.yaml"),
        "--scheme", str(example / "schemes/control-room-dark.yaml"), "--layout", str(example / "layouts/wallboard.yaml"),
        "--summary", str(example / "profiles/summary.yaml"), "--detail", str(example / "profiles/detail.yaml"),
        "--output", str(tmp_path / "out.svg"),
    ])
    main()

    # Every phase ran exactly once, in the published order: relations, legend, notes, footer completion, summary.
    assert events == ["routes", "relation-labels", "legend", "notes", "footer", "summary"]


def test_source_content_phases_take_no_obstacle_index() -> None:
    for function in (surface_legend.place_legend, surface_content.place_notes, surface_content.place_summary):
        for parameter in inspect.signature(function).parameters.values():
            assert "obstacle" not in parameter.name.lower(), function
    context_fields = surface_legend.SurfaceLegendContext.__dataclass_fields__
    assert not any(field.type is SurfaceObstacleIndex or "Obstacle" in str(field.type) for field in context_fields.values())
