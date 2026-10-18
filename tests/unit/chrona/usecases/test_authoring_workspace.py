from pathlib import Path

import pytest
import yaml

from chrona.operational.authoring_commands import read_authoring_workspace
from chrona.operational.workspace_initialization import publish_workspace_directory
from chrona.presentation.model.closure import ClosureError
from chrona.usecases.authoring_workspace import create_workspace, validate_workspace


def _project():
    return {
        "id": "日本語計画",
        "title": "基盤整備",
        "tasks": [{"id": "設計", "title": "要件整理", "planned": {
            "start": "2026-04-01", "finish": "2026-04-05",
        }}],
    }


def test_create_and_validate_workspace_preserves_unicode_and_binding_identity(tmp_path):
    destination = tmp_path / "workspace"

    created = create_workspace(destination, _project(), publish=publish_workspace_directory)

    workspace_path = destination / "workspace.yaml"
    raw = workspace_path.read_bytes()
    assert created.workspace == workspace_path
    assert r"\u65e5".encode() not in raw
    assert raw.decode("utf-8").index("version:") < raw.decode("utf-8").index("kind:") < raw.decode("utf-8").index("id:")
    document = yaml.safe_load(raw)
    assert document["id"] == "日本語計画-workspace"
    assert list(document["body"]) == ["project", "presentation"]
    assert list(document["body"]["project"]) == ["id", "title", "tasks"]
    assert document["body"]["project"] == _project()
    binding = document["body"]["presentation"]["binding"]["preset"]
    preset = yaml.safe_load((destination / binding["path"]).read_bytes())
    assert binding["id"] == preset["id"]
    assert binding["version"] == preset["body"]["package"]["version"]
    assert created.workspace_revision == validate_workspace(workspace_path, read_workspace=read_authoring_workspace)


def test_collision_is_rejected_before_reading_builtin_preset(tmp_path, monkeypatch):
    import chrona.usecases.authoring_workspace as owner

    destination = tmp_path / "occupied"
    destination.mkdir()
    sentinel = destination / "keep.txt"
    sentinel.write_text("untouched", encoding="utf-8")
    monkeypatch.setattr(owner, "copy_builtin_preset", lambda *_args: pytest.fail("preset read before collision check"))

    with pytest.raises(FileExistsError, match="E_AUTHORING_WORKSPACE_EXISTS"):
        owner.create_workspace(destination, _project(), publish=publish_workspace_directory)
    assert sentinel.read_text(encoding="utf-8") == "untouched"


def test_creation_detaches_nested_project_input_before_preset_preparation(tmp_path, monkeypatch):
    import chrona.usecases.authoring_workspace as owner

    project = _project()
    original_copy = owner.copy_builtin_preset

    def mutate_during_preset_copy(identifier, destination):
        project["tasks"][0]["title"] = "外部変更"
        return original_copy(identifier, destination)

    monkeypatch.setattr(owner, "copy_builtin_preset", mutate_during_preset_copy)
    created = owner.create_workspace(tmp_path / "workspace", project,
                                     publish=publish_workspace_directory)
    document = yaml.safe_load(created.workspace.read_bytes())
    assert document["body"]["project"]["tasks"][0]["title"] == "要件整理"


def test_invalid_project_never_calls_publisher_or_creates_destination(tmp_path):
    destination = tmp_path / "invalid"
    calls = []

    with pytest.raises(ClosureError, match="E_AUTHORING_WORKSPACE_SCHEMA"):
        create_workspace(destination, {"id": "bad", "tasks": [{"id": "broken", "title": "Missing dates"}]},
                         publish=lambda *_args: calls.append(True))
    assert not calls
    assert not destination.exists()


def test_publisher_rolls_back_only_new_destination_after_write_failure(tmp_path, monkeypatch):
    destination = tmp_path / "new"
    outside = tmp_path / "outside.txt"
    outside.write_text("leave", encoding="utf-8")
    original_open = Path.open

    def fail_workspace(path, *args, **kwargs):
        if path.name == "workspace.yaml" and path.parent == destination:
            assert (destination / "preset/preset.yaml").is_file()
            raise OSError("injected final write failure")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fail_workspace)
    with pytest.raises(OSError, match="injected final write failure"):
        publish_workspace_directory(destination, {"preset/preset.yaml": b"preset", "workspace.yaml": b"workspace"})
    assert not destination.exists()
    assert outside.read_text(encoding="utf-8") == "leave"


def test_publisher_refuses_destination_symlink_without_touching_target(tmp_path):
    target = tmp_path / "target"
    target.mkdir()
    sentinel = target / "keep.txt"
    sentinel.write_text("safe", encoding="utf-8")
    destination = tmp_path / "link"
    try:
        destination.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip("symlink creation is not available")

    with pytest.raises(FileExistsError, match="E_AUTHORING_WORKSPACE_EXISTS"):
        publish_workspace_directory(destination, {"workspace.yaml": b"{}"})
    assert sentinel.read_text(encoding="utf-8") == "safe"
