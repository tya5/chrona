from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from chrona.presentation.model.closure import ClosureError, resolve_render_context
from chrona.storage.revision_store import LocalSnapshotReader


def _ref(kind, identifier, address, payload, token="snapshot-1"):
    return {"id": identifier, "kind": kind, "store": {"provider": "local", "identity": "closure-test"}, "address": address, "revision": {"token": token}, "contentIdentity": f"sha256:{sha256(payload).hexdigest()}"}


def _write(root: Path, address: str, value: dict, token="snapshot-1"):
    payload = yaml.safe_dump(value, sort_keys=True).encode()
    path = root / token / address
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def test_closure_rejects_path_escape_before_reading_snapshot(tmp_path):
    reader = LocalSnapshotReader(tmp_path, "closure-test")
    with pytest.raises(ClosureError, match="E_IMMUTABLE_SNAPSHOT_REQUIRED"):
        resolve_render_context({"id": "ctx", "kind": "render-context", "store": {"provider": "local", "identity": "closure-test"}, "address": "../context.yaml", "revision": {"token": "snapshot-1"}, "contentIdentity": "sha256:" + "0" * 64}, reader)


def test_v04_closure_binds_theme_and_layout_separately(tmp_path):
    project = {"version": "timeline/v0.1", "project": {"id": "p"}, "objects": {}}
    view = {"version": "chrona/presentation/v0.1", "kind": "view", "id": "v", "body": {}}
    theme = {"version": "chrona/presentation/v0.1", "kind": "theme", "id": "t", "body": {"values": {}, "roles": {}}}
    layout = {"version": "chrona/layout-profile/v0.2", "id": "l", "writingMode": "horizontal-tb", "root": {}}
    refs = {}
    for name, kind, identifier, value in (
        ("project", "project", "p", project), ("view", "view", "v", view),
        ("theme", "theme", "t", theme), ("layout", "layout-profile", "l", layout),
    ):
        payload = _write(tmp_path, f"{name}.yaml", value)
        refs[name] = _ref(kind, identifier, f"{name}.yaml", payload)
    identity = "sha256:" + "a" * 64
    context = {
        "version": "chrona/presentation/v0.4", "kind": "render-context", "id": "ctx",
        "body": {
            **refs, "inputs": {},
            "environment": {"viewport": {"inlineSize": 1000, "blockSize": 600}, "locale": "en-US", "fontMetrics": {"algorithm": "declared-metrics-v1", "assets": [{"family": "Noto Sans", "weight": 400, "revision": "font-v1", "contentIdentity": identity, "path": "fonts/noto.json"}], "missingFont": "diagnose"}, "scenePrecision": 3},
            "target": {"kind": "svg", "capabilities": ["accessibleText"]},
        },
    }
    payload = _write(tmp_path, "context-v04.yaml", context)
    _, closure = resolve_render_context(_ref("render-context", "ctx", "context-v04.yaml", payload), LocalSnapshotReader(tmp_path, "closure-test"))
    assert [(item.kind, item.id) for item in closure] == [("project", "p"), ("view", "v"), ("theme", "t"), ("layout-profile", "l")]
