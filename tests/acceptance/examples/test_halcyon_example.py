"""The HALCYON-1 example reproduces byte-for-byte through the public materializer."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

from chrona.core.validation import load_yaml, validate_project
from chrona.scheduling.scheduler import schedule
from tools.materialize_example import materialize

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
EXAMPLE = ROOT / "examples/halcyon-1"
MANIFEST = yaml.safe_load((EXAMPLE / "manifest.yaml").read_text(encoding="utf-8"))


def test_project_validates_and_schedules_the_mission_story():
    project = load_yaml(EXAMPLE / "project.yaml")
    assert validate_project(project) == []
    result = schedule(project)
    assert result.ok, result.diagnostics
    placed = result.placements
    assert len(placed) == 26 and len(project["relations"]) == 24
    assert placed["integration"]["start"] > placed["payload-delivery"]["at"]
    assert placed["launch"]["at"] == date(2027, 10, 22)
    assert placed["emc"]["end"] <= date(2027, 9, 8)


@pytest.mark.parametrize("slide", [item["id"] for item in MANIFEST["slides"]])
def test_each_slide_reproduces_from_its_context(tmp_path, slide):
    materialize(EXAMPLE / "manifest.yaml", slide, tmp_path / slide, write=False)


def test_each_context_binds_its_own_view_theme_layout_and_scheme():
    for entry in MANIFEST["slides"]:
        context = yaml.safe_load((EXAMPLE / entry["context"]).read_text(encoding="utf-8"))["body"]
        stem = Path(entry["context"]).stem
        assert context["view"]["address"] == f"views/{stem}.yaml"
        addresses = {context[key]["address"] for key in ("theme", "colorScheme", "layout")}
        assert len(addresses) == 3
        svg = (EXAMPLE / entry["expectedSvg"]).read_text(encoding="utf-8")
        view = yaml.safe_load((EXAMPLE / context["view"]["address"]).read_text(encoding="utf-8"))
        for object_id in view["body"]["selection"]["include"].get("ids", ["launch"]):
            assert f'data-source-ref="{object_id}"' in svg
