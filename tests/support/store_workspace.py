"""A scratch workspace with a local Store, an Actual set, a Project and Command Requests (#813).

The Store lives at ``<root>/.chrona/store`` and is named by ``<root>/.chrona/store.yaml``, so a workspace root is also a
project directory the command line and the MCP tools can both use. ``apply`` is stateful, so a test that compares the
command line with a tool builds the fixture twice.
"""
from __future__ import annotations

import json
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from chrona.app.cli import main
from chrona.commands.actual_commands import LocalActualStore
from chrona.storage.snapshot_paths import snapshot_directory

STORE_IDENTITY = "test"
PROJECT = {
    "version": "timeline/v0.7", "project": {"id": "p"}, "extensions": [],
    "objects": {"firmware": {"type": "milestone", "schedule": {"mode": "fixed-point", "at": "2026-01-01"}}},
    "relations": [],
}


class StoreWorkspace:
    def __init__(self, root: Path, *, integrity: str = "required"):
        self.root = root
        self.store = root / ".chrona" / "store"
        self.config = root / ".chrona" / "store.yaml"
        self.store.mkdir(parents=True)
        self.config.write_text(yaml.safe_dump({
            "version": "chrona/store-config/v0.1",
            "stores": [{"provider": "local", "identity": STORE_IDENTITY, "root": "store", "integrity": integrity}],
        }, sort_keys=False), encoding="utf-8")
        actual = {"version": "chrona/actual-set/v0.3", "kind": "actual-set", "id": "actuals", "body": {"observations": []}}
        self.initial_revision, _ = LocalActualStore(self.store, actual).read()
        self.target = self.actual_reference(self.initial_revision)
        self.project_ref = self.write_resource("project-r1", "project.yaml", PROJECT, "project", "p")

    # --- resources of the Store -----------------------------------------------------------------------------
    def write_resource(self, token: str, address: str, value: dict[str, Any], kind: str, identifier: str) -> dict[str, Any]:
        payload = yaml.safe_dump(value, sort_keys=True).encode()
        path = snapshot_directory(self.store, token) / address
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        return {"id": identifier, "kind": kind, "store": {"provider": "local", "identity": STORE_IDENTITY},
                "address": address, "revision": {"token": token}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}

    def actual_reference(self, revision: str) -> dict[str, Any]:
        payload = (snapshot_directory(self.store, revision) / "actuals" / "actuals.yaml").read_bytes()
        return {"id": "actuals", "kind": "actual-set", "store": {"provider": "local", "identity": STORE_IDENTITY},
                "address": "actuals/actuals.yaml", "revision": {"token": revision},
                "contentIdentity": "sha256:" + sha256(payload).hexdigest()}

    def batch(self, name: str, finish: str = "2026-01-02", key: str = "42") -> dict[str, Any]:
        body = {"source": {"system": "supplier", "contentIdentity": "sha256:" + "a" * 64},
                "records": [{"externalKey": key, "projectObjectId": "firmware", "actual": {"finish": finish}}]}
        document = {"version": "chrona/actual-intake-batch/v0.2", "kind": "actual-intake-batch", "id": name, "body": body}
        return self.write_resource(f"{name}-r1", f"{name}.yaml", document, "actual-intake-batch", name)

    # --- Command Requests -----------------------------------------------------------------------------------
    def intake(self, command_id: str, batch: dict[str, Any], *, target: dict[str, Any] | None = None,
               base: str | None = None) -> dict[str, Any]:
        target = target or self.target
        return {"version": "chrona/command/v0.3", "commandId": command_id, "type": "applyActualIntakeBatch",
                "target": target, "baseRevision": base or target["revision"]["token"],
                "expectedContentIdentity": target["contentIdentity"],
                "payload": {"batch": batch, "project": self.project_ref}}

    def capture(self, command_id: str, snapshot_id: str) -> dict[str, Any]:
        return {"version": "chrona/command/v0.3", "commandId": command_id, "type": "captureSnapshot",
                "target": self.project_ref, "baseRevision": "project-r1",
                "expectedContentIdentity": self.project_ref["contentIdentity"],
                "payload": {"snapshotId": snapshot_id, "registry": {"provider": "local", "identity": STORE_IDENTITY}}}

    def write_command(self, name: str, command: dict[str, Any]) -> str:
        """Write a Command Request below ``commands/`` and return its workspace path."""
        path = self.root / "commands" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(command, sort_keys=True), encoding="utf-8")
        return f"commands/{name}"

    # --- observation ----------------------------------------------------------------------------------------
    def tip(self) -> dict[str, Any]:
        return json.loads((self.store / "actual-tips" / "actuals.json").read_text(encoding="utf-8"))

    def snapshot(self) -> dict[str, bytes]:
        """Every file of the Store by relative path: equal before and after means nothing was written."""
        return {path.relative_to(self.store).as_posix(): path.read_bytes()
                for path in sorted(self.store.rglob("*")) if path.is_file()}


def run_cli(monkeypatch, capsys, cwd: Path, *arguments: str) -> tuple[int, str]:
    """Run ``chrona ARGUMENTS`` in ``cwd`` in this process; return the exit code and standard output."""
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["chrona", *arguments])
    code = 0
    try:
        main()
    except SystemExit as error:
        code = error.code if isinstance(error.code, int) else 0
    return code, capsys.readouterr().out
