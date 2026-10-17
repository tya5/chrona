"""Draft extension package ingress: config discovery, lazy reads, and MCP containment."""
from __future__ import annotations

from argparse import Namespace
from hashlib import sha256
import json
from pathlib import Path
from datetime import date

import pytest
import yaml

from chrona.app.agent_tools import call_tool
from chrona.app.agent_workspace import WorkspaceScope
from chrona.app.cli import _draft_package_reader
from chrona.core.identity import content_identity
from chrona.core.validation import validate_project
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory
from tests.support import synthetic_review as sr
from tests.support.store_workspace import STORE_IDENTITY, StoreWorkspace, run_cli
from chrona.usecases.failure_report import StableFailure


def _identity(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def _local_package_reference(payload: bytes, *, identity: str = STORE_IDENTITY, token: str = "package-r1") -> dict:
    return {
        "id": "kit-reference", "kind": "profile-package",
        "store": {"provider": "local", "identity": identity},
        "address": "packages/kit.yaml", "revision": {"token": token},
        "contentIdentity": _identity(payload),
    }


def _write_package(work: StoreWorkspace, payload: bytes, *, token: str = "package-r1") -> dict:
    target = snapshot_directory(work.store, token) / "packages" / "kit.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    return _local_package_reference(payload, token=token)


PACKAGE_ID = "synthetic-neutral-profile"
PACKAGE_TOKEN = "neutral-profile-r1"


def _write_profile_package(work: StoreWorkspace, *, token: str = PACKAGE_TOKEN) -> tuple[bytes, dict]:
    package = {
        "version": "chrona/profile/v0.3", "packageId": PACKAGE_ID,
        "requires": {"projectFormat": "timeline/v0.7"},
        "profiles": {"synthetic-neutral-profile.neutral": {"extends": "milestone"}},
    }
    package["contentIdentity"] = content_identity(package)
    payload = yaml.safe_dump(package, sort_keys=False, allow_unicode=True).encode("utf-8")
    target = snapshot_directory(work.store, token) / "packages" / "neutral-profile.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    reference = {
        "id": PACKAGE_ID, "kind": "profile-package",
        "store": {"provider": "local", "identity": STORE_IDENTITY},
        "address": "packages/neutral-profile.yaml", "revision": {"token": token},
        "contentIdentity": _identity(payload),
    }
    return payload, reference


def _write_draft(work: StoreWorkspace, *, extension: dict | None = None, nested: bool = True) -> Path:
    source = sr.project({
        "task": sr.span("task", date(2026, 10, 1), 5, owner="team-a", title="Synthetic task"),
    })
    if extension is not None:
        source["extensions"] = [extension]
    diagnostics = validate_project(source)
    assert diagnostics == [], diagnostics
    target = work.root / ("draft/project.yaml" if nested else "project.yaml")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(yaml.safe_dump(source, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return target


def _assert_scene_has_package_and_vocabulary(scene_path: Path, reference: dict) -> None:
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    resources = scene["provenance"]["resources"]
    assert {
        "kind": "profile-package", "id": reference["id"],
        "revision": reference["revision"]["token"], "contentIdentity": reference["contentIdentity"],
    } in resources
    assert any(item["kind"] == "semantic-vocabulary" and item["id"] == "chrona-core"
               and item["revision"] == "v0.1" and item["contentIdentity"].startswith("sha256:")
               for item in resources)


def test_cli_package_reader_uses_an_explicit_store_config_for_a_pinned_snapshot(tmp_path):
    work = StoreWorkspace(tmp_path / "workspace")
    payload = b"version: chrona/profile/v0.3\npackageId: kit\nprofiles: {}\n"
    reference = _write_package(work, payload)
    source = work.root / "draft" / "project.yaml"
    source.parent.mkdir()
    source.write_text("version: timeline/v0.7\nproject: {id: draft}\nobjects: {}\nrelations: []\n")

    reader = _draft_package_reader(Namespace(store_config=str(work.config)), source)

    assert reader.read(reference) == payload


def test_cli_package_reader_discovers_store_config_from_source_ancestors(tmp_path):
    work = StoreWorkspace(tmp_path / "workspace")
    payload = b"version: chrona/profile/v0.3\npackageId: kit\nprofiles: {}\n"
    reference = _write_package(work, payload)
    source = work.root / "nested" / "draft" / "project.yaml"
    source.parent.mkdir(parents=True)
    source.write_text("version: timeline/v0.7\nproject: {id: draft}\nobjects: {}\nrelations: []\n")

    reader = _draft_package_reader(Namespace(store_config=None), source)

    assert reader.read(reference) == payload


def test_cli_package_reader_requires_config_only_when_a_local_pin_is_read(tmp_path):
    work = StoreWorkspace(tmp_path / "workspace")
    payload = b"version: chrona/profile/v0.3\npackageId: kit\nprofiles: {}\n"
    reference = _local_package_reference(payload)
    source = work.root / "draft.yaml"
    source.write_text("version: timeline/v0.7\nproject: {id: draft}\nobjects: {}\nrelations: []\n")
    work.config.unlink()
    reader = _draft_package_reader(Namespace(store_config=None), source)

    with pytest.raises(StableFailure) as raised:
        reader.read(reference)
    assert raised.value.code == "E_STORE_CONFIG_REQUIRED"


def test_cli_package_reader_reads_a_wheel_package_without_any_store_config(tmp_path):
    source = tmp_path / "project.yaml"
    source.write_text("version: timeline/v0.7\nproject: {id: draft}\nobjects: {}\nrelations: []\n")
    reference = {
        "id": "default-font-metrics", "kind": "profile-package",
        "store": {"provider": "package", "identity": "chrona.resources"},
        "address": "fonts/default-font-metrics.yaml", "revision": {"token": "v0.1"},
    }
    reader = _draft_package_reader(Namespace(store_config=None), source)

    assert reader.read(reference).startswith(b"algorithm:")


@pytest.mark.parametrize("explicit_config", [True, False], ids=["explicit-store-config", "ancestor-discovery"])
def test_cli_renders_a_project_with_a_pinned_profile_package_and_emits_scene_provenance(
    tmp_path, monkeypatch, capsys, explicit_config,
):
    work = StoreWorkspace(tmp_path / "workspace")
    payload, reference = _write_profile_package(work)
    project = _write_draft(work, extension={"packageId": PACKAGE_ID, "resource": reference})
    output, scene_path = work.root / "draft/output.svg", work.root / "draft/scene.json"
    arguments = ["render", project.relative_to(work.root).as_posix(), "--output", output.relative_to(work.root).as_posix(),
                 "--emit-scene", scene_path.relative_to(work.root).as_posix()]
    if explicit_config:
        arguments.extend(("--store-config", work.config.relative_to(work.root).as_posix()))

    code, stdout = run_cli(monkeypatch, capsys, work.root, *arguments)

    result = json.loads(stdout)
    assert code == 0 and result["status"] == "ok", result
    assert output.is_file()
    assert output.read_bytes().startswith((b"<?xml", b"<svg"))
    assert payload == (snapshot_directory(work.store, PACKAGE_TOKEN) / "packages/neutral-profile.yaml").read_bytes()
    _assert_scene_has_package_and_vocabulary(scene_path, reference)


def test_cli_rejects_a_profile_package_pin_hash_mismatch_before_writing_artifacts(tmp_path, monkeypatch, capsys):
    work = StoreWorkspace(tmp_path / "workspace")
    _payload, reference = _write_profile_package(work)
    reference["contentIdentity"] = "sha256:" + "0" * 64
    project = _write_draft(work, extension={"packageId": PACKAGE_ID, "resource": reference})
    output, scene_path = work.root / "draft/output.svg", work.root / "draft/scene.json"

    code, stdout = run_cli(monkeypatch, capsys, work.root, "render", project.relative_to(work.root).as_posix(),
                           "--store-config", work.config.relative_to(work.root).as_posix(),
                           "--output", output.relative_to(work.root).as_posix(),
                           "--emit-scene", scene_path.relative_to(work.root).as_posix())

    result = json.loads(stdout)
    assert code != 0 and result["status"] == "rejected", result
    assert any(item["code"] == "E_CONTENT_IDENTITY" for item in result["diagnostics"]), result
    assert not output.exists() and not scene_path.exists()


def test_mcp_renders_a_project_with_a_pinned_profile_package_from_the_workspace_store(tmp_path):
    work = StoreWorkspace(tmp_path / "workspace")
    _payload, reference = _write_profile_package(work)
    project = _write_draft(work, extension={"packageId": PACKAGE_ID, "resource": reference})

    result = call_tool(WorkspaceScope(work.root), "render_draft", {
        "project": project.relative_to(work.root).as_posix(), "inline": "none",
    })

    assert result.structured["status"] == "ok", result.structured
    assert result.structured["byteLength"] > 0 and result.structured["contentIdentity"].startswith("sha256:")
    assert result.attachments == ()


def test_mcp_render_draft_refuses_outside_store_root_before_reading_a_package_pin(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside_store = tmp_path / "outside-store"
    outside_store.mkdir()
    work = StoreWorkspace(workspace)
    package, reference = _write_profile_package(work)
    # Move only the pinned package bytes outside the workspace; the config names its actual location.
    external_path = snapshot_directory(outside_store, PACKAGE_TOKEN) / "packages" / "neutral-profile.yaml"
    external_path.parent.mkdir(parents=True)
    external_path.write_bytes(package)
    source = _write_draft(work, extension={"packageId": PACKAGE_ID, "resource": reference})
    config = workspace / "outside.yaml"
    config.write_text(yaml.safe_dump({
        "version": "chrona/store-config/v0.1",
        "stores": [{"provider": "local", "identity": STORE_IDENTITY,
                    "root": str(outside_store), "integrity": "required"}],
    }), encoding="utf-8")
    reads: list[Path] = []

    def record_store_read(self, requested):
        reads.append(Path(requested))
        raise AssertionError("the outside Store must not be read")

    monkeypatch.setattr("chrona.storage.revision_store.LocalSnapshotReader.read", record_store_read)

    result = call_tool(WorkspaceScope(workspace), "render_draft", {"project": source.relative_to(workspace).as_posix(),
                                                                    "storeConfig": "outside.yaml", "inline": "none"})

    assert result.structured["status"] == "failed"
    assert [item["code"] for item in result.structured["diagnostics"]] == ["E_MCP_PATH_CONTAINMENT"]
    assert result.structured["diagnostics"][0]["sourceRef"] == "/storeConfig"
    assert reads == []
    assert external_path.read_bytes() == package


def test_mcp_render_draft_without_extensions_renders_without_a_store_config(tmp_path):
    work = StoreWorkspace(tmp_path / "workspace")
    work.config.unlink()
    source = _write_draft(work)
    result = call_tool(WorkspaceScope(work.root), "render_draft", {"project": source.relative_to(work.root).as_posix(),
                                                                       "inline": "none"})

    assert result.structured["status"] == "ok"
    assert result.attachments == ()
