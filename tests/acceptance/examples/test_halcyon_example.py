"""The HALCYON-1 example reproduces byte-for-byte from its authoring resources."""
from __future__ import annotations

import subprocess
import sys
from datetime import date
from pathlib import Path

import yaml

from chrona.core.validation import load_yaml, validate_project
from chrona.scheduling.scheduler import schedule

ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
EXAMPLE = ROOT / "examples/halcyon-1"


def test_project_validates_and_schedules_the_mission_story():
    project = load_yaml(EXAMPLE / "project.yaml")
    assert validate_project(project) == []
    result = schedule(project)
    assert result.ok, result.diagnostics
    placed = result.placements
    assert len(placed) == 26 and len(project["relations"]) == 24
    assert placed["integration"]["start"] > placed["payload-delivery"]["at"]  # three-way convergence
    assert placed["campaign"]["start"].weekday() < 6  # range calendar works Saturdays
    assert placed["launch"]["at"] == date(2027, 10, 22)
    assert placed["emc"]["end"] <= date(2027, 9, 8)  # upper-bound constraint respected


def test_every_slide_reproduces_from_the_manifest():
    completed = subprocess.run(
        [sys.executable, str(ROOT / "tools/materialize_example.py"), str(EXAMPLE / "manifest.yaml"), "--check"],
        capture_output=True, text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr


def test_slides_carry_source_ids_and_their_own_bindings():
    manifest = yaml.safe_load((EXAMPLE / "manifest.yaml").read_text())
    for slide in manifest["slides"]:
        svg = (EXAMPLE / slide["output"]).read_text()
        view = yaml.safe_load((EXAMPLE / slide["view"]).read_text())
        for object_id in view["body"]["selection"]["include"].get("ids", ["launch"]):
            assert f'data-source-ref="{object_id}"' in svg
        context = yaml.safe_load((EXAMPLE / "contexts" / f"{Path(slide['view']).stem}.yaml").read_text())
        assert context["body"]["layout"]["address"] == slide["layout"]
        assert context["body"]["colorScheme"]["address"] == slide["colorScheme"]
        assert context["body"]["environment"]["viewport"] == slide["viewport"]
