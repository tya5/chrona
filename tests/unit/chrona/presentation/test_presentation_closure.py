from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from chrona.presentation import ClosureError, resolve_render_context
from chrona.revision_store import LocalSnapshotReader


def _ref(kind, identifier, address, payload, token="snapshot-1"):
    return {"id": identifier, "kind": kind, "store": {"provider": "local", "identity": "closure-test"}, "address": address, "revision": {"token": token}, "contentIdentity": f"sha256:{sha256(payload).hexdigest()}"}


def _write(root: Path, address: str, value: dict, token="snapshot-1"):
    payload = yaml.safe_dump(value, sort_keys=True).encode()
    path = root / token / address
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return payload


def test_closure_is_ordered_pinned_and_rejects_identity_or_revision_mismatch(tmp_path):
    project = {"version": "timeline/v0.1", "project": {"id": "p"}, "objects": {"a": {"type": "task", "schedule": {"mode": "fixed", "start": "2026-10-01", "end": "2026-10-02"}}}}
    bodies = {"view": {"version": "chrona/presentation/v0.1", "kind": "view", "id": "v", "body": {}}, "style": {"version": "chrona/presentation/v0.1", "kind": "style", "id": "s", "body": {}}, "theme": {"version": "chrona/presentation/v0.1", "kind": "theme", "id": "t", "body": {}}, "scene": {"version": "chrona/presentation/v0.1", "kind": "scene-profile", "id": "sp", "body": {}}}
    project_bytes = _write(tmp_path, "project.yaml", project)
    refs = {"project": _ref("project", "p", "project.yaml", project_bytes)}
    for name, kind, identifier in (("view", "view", "v"), ("style", "style", "s"), ("theme", "theme", "t"), ("scene", "scene-profile", "sp")):
        data = _write(tmp_path, f"{name}.yaml", bodies[name]); refs[name] = _ref(kind, identifier, f"{name}.yaml", data)
    context = {"version": "chrona/presentation/v0.1", "kind": "render-context", "id": "ctx", "body": {"project": refs["project"], "view": refs["view"], "style": refs["style"], "theme": refs["theme"], "sceneProfile": refs["scene"], "evaluation": {"locale": "ja-JP"}, "viewport": {}, "target": {}, "layoutMetrics": {}}}
    context_bytes = _write(tmp_path, "context.yaml", context)
    reader = LocalSnapshotReader(tmp_path, "closure-test")
    _, closure = resolve_render_context(_ref("render-context", "ctx", "context.yaml", context_bytes), reader)
    assert [(item.kind, item.id) for item in closure] == [("project", "p"), ("view", "v"), ("style", "s"), ("theme", "t"), ("scene-profile", "sp")]
    _write(tmp_path, "theme.yaml", bodies["theme"], token="snapshot-2")
    context["body"]["theme"] = context["body"]["theme"] | {"revision": {"token": "snapshot-2"}}
    bad_context = _write(tmp_path, "bad-context.yaml", context)
    with pytest.raises(ClosureError, match="E_CLOSURE_MIXED_REVISION"):
        resolve_render_context(_ref("render-context", "ctx", "bad-context.yaml", bad_context), reader)


def test_closure_rejects_path_escape_before_reading_snapshot(tmp_path):
    reader = LocalSnapshotReader(tmp_path, "closure-test")
    with pytest.raises(ClosureError, match="E_IMMUTABLE_SNAPSHOT_REQUIRED"):
        resolve_render_context({"id": "ctx", "kind": "render-context", "store": {"provider": "local", "identity": "closure-test"}, "address": "../context.yaml", "revision": {"token": "snapshot-1"}, "contentIdentity": "sha256:" + "0" * 64}, reader)
