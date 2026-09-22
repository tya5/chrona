from hashlib import sha256
from types import SimpleNamespace

import yaml

import chrona.presentation.model.closure as closure
from chrona.storage.revision_store import LocalSnapshotReader


def _write(root, token, address, value):
    payload = yaml.safe_dump(value, sort_keys=True).encode()
    path = root / token / address
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"id": value.get("id", value.get("project", {}).get("id")), "kind": value.get("kind", "project"),
            "store": {"provider": "local", "identity": "test"}, "address": address,
            "revision": {"token": token}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}


def test_v06_closure_allows_named_snapshot_project_at_its_own_revision(tmp_path, monkeypatch):
    primary = {"version": "timeline/v0.1", "project": {"id": "p"}, "objects": {}}
    historic = {"version": "timeline/v0.1", "project": {"id": "p"}, "objects": {}}
    primary_ref = _write(tmp_path, "current", "project.yaml", primary)
    historic_ref = _write(tmp_path, "historic", "project.yaml", historic)
    snapshot = {"version": "chrona/snapshot-ref/v0.2", "kind": "snapshot-ref", "id": "q2", "body": {"project": historic_ref}}
    snapshot_ref = _write(tmp_path, "current", "snapshot.yaml", snapshot)
    resources = {}
    for name, kind in (("view", "view"), ("theme", "theme"), ("scheme", "color-scheme"), ("layout", "layout-profile")):
        versions = {
            "view": "chrona/view/v0.2", "theme": "chrona/theme/v0.2",
            "color-scheme": "chrona/color-scheme/v0.1", "layout-profile": "chrona/layout-profile/v0.2",
        }
        value = {"version": versions[kind], "kind": kind, "id": name, "body": {}}
        resources[name] = _write(tmp_path, "current", f"{name}.yaml", value)
    context = {"version": "chrona/render-context/v0.6", "kind": "render-context", "id": "ctx", "body": {
        "project": primary_ref, "view": resources["view"], "theme": resources["theme"],
        "colorScheme": resources["scheme"], "layout": resources["layout"],
        "inputs": {"snapshot": snapshot_ref}, "environment": {}, "target": {"capabilities": []}}}
    context_ref = _write(tmp_path, "current", "context.yaml", context)
    monkeypatch.setattr(closure.jsonschema, "Draft202012Validator", lambda _schema: type("V", (), {"iter_errors": lambda self, _value: iter(())})())
    monkeypatch.setattr(closure, "resolve_theme", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(closure, "parse_contract", lambda identity, value: SimpleNamespace(identity=identity, body=value.get("body", {}), document=value))

    resources = closure.resolve_render_context(context_ref, LocalSnapshotReader(tmp_path, "test")).resources

    assert [(item.kind, item.revision) for item in resources][-2:] == [("snapshot-ref", "current"), ("snapshot-project", "historic")]
