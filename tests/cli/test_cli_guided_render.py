from pathlib import Path
from typing import Mapping
import json
import sys

import pytest

from chrona.app.cli import main
from chrona.usecases.authoring_workspace import create_workspace


def _publish(directory: Path, files: Mapping[str, bytes]) -> None:
    directory.mkdir()
    for name, payload in files.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)


@pytest.mark.parametrize("preset", ["chrona-default-draft", "target-b"])
def test_render_workspace_cli_uses_copied_builtin_preset(preset: str, tmp_path: Path, monkeypatch, capsys):
    created = create_workspace(
        tmp_path / preset,
        {"id": "guided-cli-test", "title": "Guided CLI test", "tasks": [
            {"id": "task", "title": "Task", "planned": {"start": "2027-01-04", "finish": "2027-01-09"}},
        ]},
        preset,
        publish=_publish,
    )
    output = tmp_path / f"{preset}.svg"
    monkeypatch.setattr(sys, "argv", [
        "chrona", "render-workspace", str(created.workspace), "--output", str(output),
    ])

    main()

    assert output.read_bytes().startswith(b"<svg")
    assert json.loads(capsys.readouterr().out)["status"] == "ok"
