from pathlib import Path
from typing import Mapping

import pytest
import yaml

from chrona.presentation.model.closure import ClosureError, resolve_guided_draft_render
from chrona.usecases.authoring_workspace import create_workspace
from chrona.usecases.guided_render import WorkspaceRenderRequest, render_workspace


def _publish(directory: Path, files: Mapping[str, bytes]) -> None:
    directory.mkdir()
    for name, payload in files.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


@pytest.mark.parametrize("preset", ["chrona-default-draft", "target-b"])
def test_render_workspace_renders_copied_builtin_preset(preset: str, tmp_path: Path):
    created = create_workspace(
        tmp_path / preset,
        {"id": "guided-test", "title": "Guided test", "tasks": [
            {"id": "task", "title": "Task", "planned": {"start": "2027-01-04", "finish": "2027-01-09"}},
        ]},
        preset,
        publish=_publish,
    )

    result = render_workspace(WorkspaceRenderRequest(created.workspace, "svg"))

    assert result.artifact.content.startswith(b"<svg")
    assert result.provenance.workspace_identity
    assert result.provenance.preset_identity.startswith("sha256:")


def test_guided_closure_preserves_preset_identity_diagnostic_envelope(tmp_path: Path):
    created = create_workspace(
        tmp_path / "identity-mismatch",
        {"id": "guided-test", "tasks": [
            {"id": "task", "title": "Task", "planned": {"start": "2027-01-04", "finish": "2027-01-09"}},
        ]},
        "target-b",
        publish=_publish,
    )
    workspace = yaml.safe_load(created.workspace.read_text(encoding="utf-8"))
    workspace["body"]["presentation"]["binding"]["preset"]["version"] = "wrong-version"
    created.workspace.write_text(yaml.safe_dump(workspace, sort_keys=False), encoding="utf-8")

    with pytest.raises(ClosureError) as raised:
        resolve_guided_draft_render(workspace_path=created.workspace)

    error = raised.value
    assert error.diagnostic_id == "E_AUTHORING_PRESET_IDENTITY"
    assert error.source_ref == "/body/presentation/binding/preset"
    assert "bound preset id/version='chrona-builtin-target-b'/'wrong-version'" in error.detail
    assert "selected='chrona-builtin-target-b'/'1'" in error.detail
