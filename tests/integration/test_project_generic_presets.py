"""The five catalogue presets carry no project-specific values (#479 I479-3)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
import yaml

from chrona.app.cli import main
from chrona.usecases.local_authoring import initialize_project

ROOT = Path(__file__).resolve().parents[2]
BUNDLES = ROOT / "src/chrona/resources/presets/bundles"
PRESETS = [entry["id"] for entry in yaml.safe_load(
    (ROOT / "src/chrona/resources/presets/library.yaml").read_text(encoding="utf-8"))["entries"]
    if entry["id"] != "chrona-default-draft"]  # the bundled default is the "default" case; its bundle is editorial-readable-default (#1305)


def _project_values(path: Path) -> set[str]:
    """Group-field values and entity ids an example project names."""
    project = yaml.safe_load(path.read_text(encoding="utf-8"))
    values = {str(value) for obj in project["objects"].values() for key, value in obj.get("fields", {}).items()
              if key == "owner"}
    return values | set(project.get("entities", {}))


def test_no_bundle_file_names_an_example_projects_group_values():
    values = _project_values(ROOT / "examples/halcyon-1/project.yaml") | _project_values(ROOT / "examples/controller-z/project.yaml")
    for path in BUNDLES.glob("*/*.yaml"):
        text = path.read_text(encoding="utf-8")
        tokens = {token.strip(" :,[]{}'\"") for line in text.splitlines() for token in line.replace(".", " ").split()}
        assert not tokens & values, (path.name, path.parent.name, sorted(tokens & values))


def _render(tmp_path: Path, monkeypatch, preset_id: str, project: Path) -> tuple[dict, bytes]:
    preset = tmp_path / preset_id
    monkeypatch.setattr(sys, "argv", ["chrona", "preset", "copy", preset_id, "--output", str(preset)])
    main()
    scene_path, svg_path = tmp_path / f"{preset_id}.json", tmp_path / f"{preset_id}.svg"
    monkeypatch.setattr(sys, "argv", ["chrona", "render", str(project), "--preset", str(preset / "preset.yaml"),
                                      "--output", str(svg_path), "--emit-scene", str(scene_path)])
    main()
    return json.loads(scene_path.read_text(encoding="utf-8"))["surfaces"][0], svg_path.read_bytes()


@pytest.mark.parametrize("preset_id", PRESETS)
def test_each_preset_renders_halcyon_and_the_starter(tmp_path, monkeypatch, preset_id):
    (tmp_path / "halcyon").mkdir()
    halcyon, _ = _render(tmp_path / "halcyon", monkeypatch, preset_id, ROOT / "examples/halcyon-1/project.yaml")
    view = yaml.safe_load((BUNDLES / preset_id / "view.yaml").read_text(encoding="utf-8"))["body"]
    if (view.get("grouping") or {}).get("presentation") == "header":
        assert any(item["id"].startswith("group-header:") for item in halcyon["primitives"])
    starter = tmp_path / "starter"
    initialize_project(starter)
    (tmp_path / "out").mkdir()
    surface, _ = _render(tmp_path / "out", monkeypatch, preset_id, starter / "project.yaml")
    assert not any(item["id"].startswith("group-header:") for item in surface["primitives"])
    if (BUNDLES / preset_id / "detail.yaml").is_file():
        assert any(item["id"].startswith("legend:") for item in halcyon["primitives"])
    labels = view["visibility"]["labels"]
    if isinstance(labels, dict) and labels.get("placement") in {"plot", "both"} and any(
            column.get("source") == "title" for column in view.get("tableColumns", ())):
        assert labels["placement"] == "both"  # names in both places is the declared placement


def test_elevated_light_paints_its_gradient_without_a_flag(tmp_path, monkeypatch):
    _, svg = _render(tmp_path, monkeypatch, "elevated-light", ROOT / "examples/controller-z/project.yaml")
    assert b"<linearGradient" in svg
