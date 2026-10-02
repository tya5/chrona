"""The one dispatch of the revision-bound Store commands, shared by the command line and the agent tool core (#813).

``chrona command-check``, ``command-apply``, ``actual-intake``, ``actual-resolve`` and ``baseline-capture`` are one
engine (``operational.command_engine``) behind five names that differ only in the command type they require. This
module owns that dispatch so that a second front end calls the same code and a disagreement between the two is a
defect here: ``run_store_command`` maps a parsed Command Request to the Automation Result the command line writes.

It reads no file, writes no result file, prints nothing and exits nothing; the front end reads the command and the
Store configuration, and delivers the result. ``open_store_reader`` is the one way to open a workspace Store: with
``contained_in`` it refuses a configuration whose Store roots leave the directory (a Store configuration names its
own roots, and the engine writes below them).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Collection

from chrona.operational.command_engine import apply_actual_command, check_command
from chrona.operational.resources import parse_command, stamp_automation_result
from chrona.operational.store_config import ConfiguredStoreReader, load_store_config

OPERATIONS = ("command-check", "command-apply", "actual-intake", "actual-resolve", "baseline-capture")
"""The operation names, as the command line spells them."""

REQUIRED_TYPE = {
    "actual-intake": "applyActualIntakeBatch",
    "actual-resolve": "resolveActualObservation",
    "baseline-capture": "captureSnapshot",
}
"""The command type an operation accepts; ``command-check`` and ``command-apply`` accept any the engine supports."""

UNSUPPORTED = "E_AUTOMATION_OPERATION_UNSUPPORTED"


class StoreRootOutsideWorkspace(ValueError):
    """A Store configuration names a root that does not resolve strictly inside the allowed directory."""


def parse_command_request(text: str | bytes) -> dict[str, Any]:
    """Parse and validate one Command Request document, as ``chrona command-apply --command FILE`` does."""
    return parse_command(text)


def open_store_reader(config_path: str | Path, *, contained_in: str | Path | None = None) -> ConfiguredStoreReader:
    """Load a Store configuration; with ``contained_in`` every configured root must resolve strictly inside it.

    A root is resolved with symlinks followed, so an absolute path, a ``..`` path and a link that leaves the directory
    are all refused before any file is read from or written to a root. The directory itself is not a valid root.
    """
    reader = load_store_config(str(config_path))
    if contained_in is not None:
        base = Path(contained_in).resolve()
        for root in reader.roots.values():
            if base not in root.resolve().parents:
                raise StoreRootOutsideWorkspace(
                    "E_STORE_ROOT_OUTSIDE_WORKSPACE: a Store root in the configuration resolves outside the workspace")
    return reader


def run_store_command(
    operation: str, command: dict[str, Any], reader: Any, *, allowed_types: Collection[str] | None = None,
) -> dict[str, Any]:
    """The Automation Result of ``operation`` on one parsed Command Request.

    The result is ``rejected`` with ``E_AUTOMATION_OPERATION_UNSUPPORTED``, and nothing is read from or written to a
    Store, when the operation requires another command type or ``allowed_types`` (a narrowing a front end may add)
    does not contain the command's type.
    """
    required = REQUIRED_TYPE.get(operation)
    message = None
    if required is not None and command["type"] != required:
        message = f"{operation} needs a command of type {required!r}, got {command['type']!r}"
    elif allowed_types is not None and command["type"] not in allowed_types:
        message = f"{operation} accepts command types {', '.join(sorted(allowed_types))} here, got {command['type']!r}"
    if message is not None:
        return stamp_automation_result({
            "version": "chrona/automation-result/v0.2", "operation": operation, "status": "rejected",
            "requestContentIdentity": "sha256:" + "0" * 64, "inputs": [command["target"]],
            "diagnostics": [{"code": UNSUPPORTED, "message": message}], "artifacts": [],
        })
    result = check_command(reader, command) if operation == "command-check" else apply_actual_command(reader, command)
    result["operation"] = operation
    return result
