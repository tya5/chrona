"""Legend and source-content phases run after routing, in slot order, outside obstacle search (#592 I592-5a)."""
import inspect
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main
from chrona.presentation.layout import surface_composer, surface_content, surface_legend, surface_route_label_plan
from chrona.presentation.layout.obstacles import SurfaceObstacleIndex
from tests.support.draft_packages import stage_project_package_store

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_content_phases_follow_routes_and_relation_labels_in_source_order(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []

    def spy(name: str, original):
        def wrapper(*args, **kwargs):
            events.append(name)
            return original(*args, **kwargs)
        return wrapper

    monkeypatch.setattr(surface_route_label_plan, "compose_surface_routes",
                        spy("routes", surface_route_label_plan.compose_surface_routes))
    relation_label_owner = surface_route_label_plan.place_relation_labels

    def relation_label_spy(context, batch, *, terminal):
        assert isinstance(terminal, bool)
        name = "terminal-labels" if terminal else "ordinary-relation-labels"
        events.append(name)
        return relation_label_owner(context, batch, terminal=terminal)

    monkeypatch.setattr(surface_route_label_plan, "place_relation_labels", relation_label_spy)
    for attribute, name in (("reserve_potential_legend", "legend"), ("place_notes", "notes"),
                            ("complete_footer_band", "footer"), ("place_summary", "summary"),
                            ("recompose_realized_legend", "realized-legend")):
        monkeypatch.setattr(surface_composer, attribute, spy(name, getattr(surface_composer, attribute)))
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

    # A name-recovery retry may rehearse one additional route/label trial, but
    # each trial keeps its Layout-owned label phases before source-content phases.
    trials = events.count("routes")
    assert trials in {1, 2}
    route_phases = ["routes", "terminal-labels", "ordinary-relation-labels"] * trials
    assert events[:len(route_phases)] == route_phases
    assert events[len(route_phases):] == ["legend", "footer", "summary", "realized-legend"]


def test_source_content_phases_take_no_obstacle_index() -> None:
    for function in (surface_legend.place_legend, surface_content.place_notes, surface_content.place_summary):
        for parameter in inspect.signature(function).parameters.values():
            assert "obstacle" not in parameter.name.lower(), function
    context_fields = surface_legend.SurfaceLegendContext.__dataclass_fields__
    assert not any(field.type is SurfaceObstacleIndex or "Obstacle" in str(field.type) for field in context_fields.values())
