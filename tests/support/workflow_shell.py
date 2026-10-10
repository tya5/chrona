"""Select the Actions-compatible Bash for workflow execution tests."""
from pathlib import Path
import shutil
import sys

import pytest


def workflow_bash() -> str:
    if sys.platform != "win32":
        return "bash"
    git = shutil.which("git")
    assert git is not None
    for parent in Path(git).resolve().parents:
        candidate = parent / "bin" / "bash.exe"
        if candidate.is_file():
            return str(candidate)
    pytest.fail("Git Bash is required for workflow shell tests")
