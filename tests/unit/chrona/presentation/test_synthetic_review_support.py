"""#575: the synthetic review support renders a small project with no corpus input."""
from __future__ import annotations

from datetime import date

import pytest

import chrona.resources as resources
from tests.support import synthetic_review as sr


@pytest.fixture
def no_examples(monkeypatch):
    """Fail if anything resolves a resource under the examples corpus."""
    real_files = resources.files

    def guarded(package, *args, **kwargs):
        if str(package).split(".")[0] == "examples":
            raise AssertionError("the examples corpus was requested")
        return real_files(package, *args, **kwargs)

    monkeypatch.setattr(resources, "files", guarded)


def test_project_builds_owners_tasks_gates_and_relations():
    value = sr.project(
        {"a": sr.span("a", date(2026, 1, 5), 10, owner="x"), "g": sr.point("g", date(2026, 1, 20), owner="x")},
        [{"id": "a-g", "type": "dependency", "from": {"object": "a", "endpoint": "end"},
          "to": {"object": "g", "endpoint": "at"}}])
    assert value["entities"] == {"x": {"type": "team", "title": "Team x"}}
    assert value["objects"]["a"]["schedule"] == {"mode": "fixed-span", "start": "2026-01-05", "end": "2026-01-15"}
    assert value["objects"]["g"]["schedule"] == {"mode": "fixed-point", "at": "2026-01-20"}
    assert [item["id"] for item in value["relations"]] == ["a-g"]


def test_chain_project_holds_one_relation_less_than_its_tasks_per_group():
    value = sr.chain_project(groups=2, per_group=3)
    assert len(value["objects"]) == 6 and len(value["relations"]) == 4


def test_bundle_returns_fresh_copies_of_the_four_packaged_resources():
    first, second = sr.bundle(), sr.bundle()
    assert set(first) == {"view", "theme", "scheme", "layout"}
    first["view"]["body"]["surface"] = "changed"
    assert second["view"]["body"]["surface"] != "changed"


def test_a_synthetic_project_renders_one_lane_row_per_overlapping_task(tmp_path, no_examples):
    parts = sr.bundle()
    parts["view"] = sr.lane_view(parts["view"])
    rendered = sr.render(tmp_path, sr.bunched_project(groups=2, per_group=3), presentation=parts)
    assert rendered.surface.lane_mode == "lanes"
    assert len(rendered.surface.rows) == 6
    assert rendered.artifact.content.startswith(b"<svg")
