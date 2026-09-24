"""Exercise installed-wheel behavior without reading repository resources."""
from __future__ import annotations

import sys
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch

from chrona.app.cli import main
from chrona.core.validation import validate_project
from chrona.resources import schema_resource
from chrona.scheduling.scheduler import schedule


PROJECT = {
    "version": "timeline/v0.6",
    "project": {"id": "wheel-smoke", "title": "Wheel smoke"},
    "objects": {
        "task": {
            "type": "task",
            "title": "Task",
            "schedule": {
                "mode": "fixed-span",
                "start": "2026-01-01",
                "end": "2026-01-02",
            },
        }
    },
}


def run() -> None:
    assert validate_project(PROJECT) == []
    assert schedule(PROJECT).ok
    assert schema_resource("layout-profile-v0.3.schema.yaml").is_file()
    try:
        with patch.object(sys, "argv", ["chrona", "--help"]):
            main()
    except SystemExit as error:
        assert error.code == 0
    else:
        raise AssertionError("CLI help did not terminate through argparse")
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        project, output = root / "my-chrona-project", root / "my-chrona-project" / "out"
        for command in (
            ["chrona", "init", str(project)],
            ["chrona", "materialize", str(project / "manifest.yaml"), "--slide", "mission-brief", "--output", str(output)],
        ):
            completed = subprocess.run(command, cwd=root, text=True, capture_output=True, check=False)
            if completed.returncode:
                raise AssertionError(f"documented fresh-project command failed: {' '.join(command)}\n{completed.stdout}\n{completed.stderr}")
        if not (output / "review.svg").is_file():
            raise AssertionError("documented materialize command did not create its artifact")
    print("Chrona installed-wheel smoke: PASS")


if __name__ == "__main__":
    run()
