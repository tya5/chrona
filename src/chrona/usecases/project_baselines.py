"""The file-route baseline of a Project: an immutable byte copy ``baselines/<name>.yaml`` beside it (#1892 row 2).

``update-a-plan.md`` step 1 keeps a baseline with ``cp project.yaml baseline.yaml`` and ``render --snapshot`` draws
the plan against it. ``save_baseline`` is that copy as one call: the bytes are copied unchanged, never edited, and a
name is never overwritten with other content. The Store route (``captureSnapshot``) is a separate mechanism.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

BASELINE_DIRECTORY = "baselines"
BASELINE_NAME_PATTERN = "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$"


class BaselineConflict(Exception):
    """A refusal carrying its stable code: the name holds other content, or ``baselines`` is not a real directory."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class SavedBaseline:
    path: Path
    identity: str
    replayed: bool


def save_project_baseline(project_path: Path, name: str, *, publish: Callable[[Path, bytes], None]) -> SavedBaseline:
    """Copy the Project file's bytes to ``baselines/<name>.yaml`` beside it, or replay an identical earlier copy."""
    payload = project_path.read_bytes()
    directory = project_path.parent / BASELINE_DIRECTORY
    if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
        raise BaselineConflict("E_BASELINE_DIRECTORY", f"{BASELINE_DIRECTORY} beside the Project is not a real directory; "
                               "remove or rename it before saving a baseline")
    directory.mkdir(exist_ok=True)
    destination = directory / f"{name}.yaml"
    identity = "sha256:" + hashlib.sha256(payload).hexdigest()
    try:
        publish(destination, payload)
    except FileExistsError:
        if destination.is_symlink() or not destination.is_file() or destination.read_bytes() != payload:
            raise BaselineConflict(
                "E_BASELINE_FILE_EXISTS",
                f"{BASELINE_DIRECTORY}/{name}.yaml already holds other content; a baseline is never overwritten, "
                "so save under a new name") from None
        return SavedBaseline(destination, identity, True)
    return SavedBaseline(destination, identity, False)
