"""One obstacle index and one phase order across label, route and relation-label placement (#592 I592-4)."""
import sys
from pathlib import Path

import pytest

from chrona.app.cli import main
from chrona.presentation.layout import surface_composer

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def test_labels_routes_and_relation_labels_share_one_growing_obstacle_index(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[tuple[str, int, int]] = []
    place_member_labels = surface_composer.place_member_labels
    compose_surface_routes = surface_composer.compose_surface_routes
    place_relation_labels = surface_composer.place_relation_labels
    requested: list[frozenset[str]] = []

    def record(name: str, obstacles) -> None:
        events.append((name, id(obstacles), len(obstacles.all())))

    def labels(context, requests, obstacles):
        requested.append(frozenset(item.placement_id for item in requests))
        record("member-labels", obstacles)
        return place_member_labels(context, requests, obstacles)

    def routes(context):
        record("routes", context.obstacles)
        return compose_surface_routes(context)

    def relation_labels(context, batch):
        record("relation-labels", context.obstacles)
        return place_relation_labels(context, batch)

    monkeypatch.setattr(surface_composer, "place_member_labels", labels)
    monkeypatch.setattr(surface_composer, "compose_surface_routes", routes)
    monkeypatch.setattr(surface_composer, "place_relation_labels", relation_labels)
    example = ROOT / "examples/halcyon-1"
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(example / "project.yaml"),
                                      "--actual", str(example / "actual.yaml"),
                                      "--output", str(tmp_path / "out.svg")])
    main()

    assert [name for name, _, _ in events] == ["member-labels", "routes", "member-labels", "relation-labels"]
    assert len({identity for _, identity, _ in events}) == 1  # the same index object in every phase
    counts = [count for _, _, count in events]
    assert counts == sorted(counts)  # monotone: nothing is ever removed
    assert counts[2] > counts[1]  # routes registered their paths before the later labels ran
    before_routes, after_routes = requested
    assert before_routes.isdisjoint(after_routes)  # each request is placed in exactly one phase
    assert "as-of-label" in before_routes  # required text is placed before routes
