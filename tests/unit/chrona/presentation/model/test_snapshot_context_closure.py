from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import yaml
import pytest

import chrona.presentation.contracts.diagnostics as contract_diagnostics
import chrona.presentation.model.closure as closure
import chrona.resources as chrona_resources
from chrona.presentation.contracts import RenderContextContract, RenderEnvironment, RenderTarget, ResourceReference, freeze
from chrona.presentation.model.closure import ClosureError
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory


def _write(root, token, address, value):
    payload = yaml.safe_dump(value, sort_keys=True).encode()
    path = snapshot_directory(root, token) / address
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"id": value.get("id", value.get("project", {}).get("id")), "kind": value.get("kind", "project"),
            "store": {"provider": "local", "identity": "test"}, "address": address,
            "revision": {"token": token}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}


def test_v06_closure_allows_named_snapshot_project_at_its_own_revision(tmp_path, monkeypatch, request):
    primary = {"version": "timeline/v0.7", "project": {"id": "p"}, "objects": {}}
    historic = {"version": "timeline/v0.7", "project": {"id": "p"}, "objects": {}}
    primary_ref = _write(tmp_path, "current", "project.yaml", primary)
    historic_ref = _write(tmp_path, "historic", "project.yaml", historic)
    snapshot = {"version": "chrona/snapshot-ref/v0.2", "kind": "snapshot-ref", "id": "q2", "body": {"project": historic_ref}}
    snapshot_ref = _write(tmp_path, "current", "snapshot.yaml", snapshot)
    resources = {}
    for name, kind in (("view", "view"), ("theme", "theme"), ("scheme", "color-scheme"), ("layout", "layout-profile")):
        versions = {
            "view": "chrona/view/v0.26", "theme": "chrona/theme/v0.15",
            "color-scheme": "chrona/color-scheme/v0.2", "layout-profile": "chrona/layout-profile/v0.10",
        }
        value = {"version": versions[kind], "kind": kind, "id": name, "body": {}}
        resources[name] = _write(tmp_path, "current", f"{name}.yaml", value)
    context = {"version": "chrona/render-context/v0.17", "kind": "render-context", "id": "ctx", "body": {
        "project": primary_ref, "view": resources["view"], "theme": resources["theme"],
        "colorScheme": resources["scheme"], "layout": resources["layout"],
        "inputs": {"snapshot": snapshot_ref}, "environment": {"fontMetrics": {"missingFont": "diagnose"}}, "target": {"capabilities": []}}}
    context_ref = _write(tmp_path, "current", "context.yaml", context)
    monkeypatch.setattr(chrona_resources, "Draft202012Validator", lambda _schema, **_kwargs: type("V", (), {"iter_errors": lambda self, _value: iter(())})())
    chrona_resources.schema_validator.cache_clear()
    request.addfinalizer(chrona_resources.schema_validator.cache_clear)
    monkeypatch.setattr(closure, "resolve_theme", lambda *_args, **_kwargs: {})
    def fake_parse(identity, value):
        if identity.kind != "render-context":
            if identity.kind == "project":
                return SimpleNamespace(identity=identity, scheduler_input=value, extensions=())
            if identity.kind == "snapshot-ref":
                return SimpleNamespace(identity=identity, project=ResourceReference.from_value(freeze(value["body"]["project"])))
            if identity.kind == "theme":
                return SimpleNamespace(identity=identity, theme_input=value)
            if identity.kind == "color-scheme":
                return SimpleNamespace(identity=identity, scheme_input=value)
            return SimpleNamespace(identity=identity, layout_input=value)
        body = value["body"]
        reference = lambda name: ResourceReference.from_value(freeze(body[name]))
        return RenderContextContract(
            identity, value["version"], reference("project"), reference("view"), reference("theme"),
            reference("colorScheme"), reference("layout"), None,
            ResourceReference.from_value(freeze(body["inputs"]["snapshot"])), None, None,
            None,
            RenderEnvironment(1, 1, "en-US", freeze({"missingFont": "diagnose"}), 0, None), RenderTarget("svg", ()),
        )

    monkeypatch.setattr(closure, "parse_contract", fake_parse)
    monkeypatch.setattr(contract_diagnostics, "parse_contract", fake_parse)

    resources = closure.resolve_render_context(context_ref, LocalSnapshotReader(tmp_path, "test")).resources

    assert [(item.kind, item.revision) for item in resources][-2:] == [("snapshot-ref", "current"), ("snapshot-project", "historic")]


@pytest.mark.parametrize(
    ("resource_kind", "context_key", "stale_version"),
    (
        ("layout-profile", "layout", "chrona/layout-profile/v0.8"),
        ("review-detail-profile", "detailProfile", "chrona/review-detail-profile/v0.0"),
    ),
)
def test_snapshot_stale_special_profile_versions_keep_version_diagnostic_after_identity_checks(
    tmp_path, resource_kind, context_key, stale_version,
):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    example_root = root / "examples/halcyon-1"
    context = yaml.safe_load((example_root / "contexts/02-programme-board.yaml").read_text(encoding="utf-8"))
    token = "stale-profile"
    refs = {}
    for key in ("project", "view", "theme", "colorScheme", "layout"):
        original = context["body"][key]
        resource_path = example_root / original["address"]
        value = yaml.safe_load(resource_path.read_text(encoding="utf-8"))
        kind = original["kind"]
        if key == context_key:
            value["version"] = stale_version
        ref = _write(tmp_path, token, original["address"], value)
        ref["kind"] = kind
        refs[key] = ref
    for key, original in context["body"]["inputs"].items():
        if key != "detailProfile" or context_key == "detailProfile":
            resource_path = example_root / original["address"]
            value = yaml.safe_load(resource_path.read_text(encoding="utf-8"))
            if key == context_key:
                value["version"] = stale_version
            ref = _write(tmp_path, token, original["address"], value)
            ref["kind"] = original["kind"]
            refs[key] = ref

    context["id"] = "stale-profile-context"
    context["body"]["project"] = refs["project"]
    context["body"]["view"] = refs["view"]
    context["body"]["theme"] = refs["theme"]
    context["body"]["colorScheme"] = refs["colorScheme"]
    context["body"]["layout"] = refs["layout"]
    context["body"]["inputs"] = ({"detailProfile": refs["detailProfile"]}
                                   if context_key == "detailProfile" else {})
    context_ref = _write(tmp_path, token, "context.yaml", context)
    reader = LocalSnapshotReader(tmp_path, "test")

    with pytest.raises(ClosureError) as error:
        closure.resolve_render_context(context_ref, reader)

    assert (error.value.diagnostic_id, error.value.source_ref) == (
        "E_RESOURCE_VERSION_UNSUPPORTED", "/version")

    # The special handling may defer version parsing, but a mismatched pinned id
    # still fails before contract parsing.
    wrong_id_context = yaml.safe_load(yaml.safe_dump(context))
    wrong_id_reference = (wrong_id_context["body"]["inputs"][context_key]
                          if context_key == "detailProfile" else wrong_id_context["body"][context_key])
    wrong_id_reference["id"] = "different-resource"
    wrong_id_ref = _write(tmp_path, token, "wrong-id-context.yaml", wrong_id_context)
    with pytest.raises(ClosureError) as identity_error:
        closure.resolve_render_context(wrong_id_ref, reader)
    assert identity_error.value.diagnostic_id == "E_CLOSURE_ID"
