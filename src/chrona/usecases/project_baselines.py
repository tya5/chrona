"""The file-route baseline of a Project: an immutable byte copy ``baselines/<name>.yaml`` beside it (#1892 row 2).

``update-a-plan.md`` step 1 keeps a baseline with ``cp project.yaml baseline.yaml`` and ``render --snapshot`` draws
the plan against it. ``save_baseline`` is that copy as one call: the bytes are copied unchanged, never edited, and a
name is never overwritten with other content. The Store route (``captureSnapshot``) is a separate mechanism.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml

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
    return _save(project_path, project_path.read_bytes(), name, publish)


def workspace_baseline_payload(workspace: Mapping[str, Any]) -> bytes:
    """The bytes of the ordinary Project a guided workspace's inline ``body.project`` normalizes to (#1921).

    It is the Project ``render_workspace`` draws, written as the file that ``snapshot`` takes. The same workspace
    Project always yields the same bytes, so saving twice under one name replays.
    """
    from chrona.presentation.model.authoring import workspace_project_document
    return yaml.safe_dump(workspace_project_document(workspace["body"]["project"]), allow_unicode=True,
                          sort_keys=False).encode("utf-8")


def save_workspace_baseline(workspace_path: Path, name: str, payload: bytes, *,
                            publish: Callable[[Path, bytes], None]) -> SavedBaseline:
    """Write the workspace Project ``payload`` to ``baselines/<name>.yaml`` beside ``workspace.yaml``."""
    return _save(workspace_path, payload, name, publish)


def _save(source: Path, payload: bytes, name: str, publish: Callable[[Path, bytes], None]) -> SavedBaseline:
    directory = source.parent / BASELINE_DIRECTORY
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
