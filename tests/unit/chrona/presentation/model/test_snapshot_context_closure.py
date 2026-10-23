from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import yaml
import pytest

import chrona.presentation.contracts.diagnostics as contract_diagnostics
import chrona.presentation.model.closure as closure
import chrona.resources as chrona_resources
from chrona.core.identity import content_identity
from chrona.presentation.contracts import (
    ProfilePackageContract, ProjectContract, RenderContextContract,
    RenderEnvironment, RenderTarget, ResourceReference, freeze,
)
from chrona.presentation.model.closure import ClosureError
from chrona.core.ports import SnapshotReadError
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory
from tests.support.deck_contexts import context_document, snapshot_resource_document


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
                return ProjectContract(identity, value["version"], freeze(value),
                                       tuple(freeze(item) for item in value.get("extensions", ())))
            if identity.kind == "profile-package":
                return ProfilePackageContract(identity, value["version"], value["packageId"], freeze(value))
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

    assert [(item.kind, item.revision) for item in resources if item.kind in {"snapshot-ref", "snapshot-project"}] == [
        ("snapshot-ref", "current"), ("snapshot-project", "historic")]


def _resolve_projects_with_packages(tmp_path, monkeypatch, *, primary_extensions, snapshot_extensions):
    primary = {"version": "timeline/v0.7", "project": {"id": "p"}, "objects": {},
               "extensions": primary_extensions}
    historic = {"version": "timeline/v0.7", "project": {"id": "p"}, "objects": {},
                "extensions": snapshot_extensions}
    primary_ref = _write(tmp_path, "current", "project.yaml", primary)
    historic_ref = _write(tmp_path, "historic", "project.yaml", historic)
    snapshot = {"version": "chrona/snapshot-ref/v0.2", "kind": "snapshot-ref", "id": "snapshot",
                "body": {"project": historic_ref}}
    snapshot_ref = _write(tmp_path, "current", "snapshot.yaml", snapshot)
    resources = {}
    versions = {
        "view": "chrona/view/v0.26", "theme": "chrona/theme/v0.15",
        "color-scheme": "chrona/color-scheme/v0.2", "layout-profile": "chrona/layout-profile/v0.10",
    }
    for name, kind in (("view", "view"), ("theme", "theme"), ("scheme", "color-scheme"), ("layout", "layout-profile")):
        value = {"version": versions[kind], "kind": kind, "id": name, "body": {}}
        resources[name] = _write(tmp_path, "current", f"{name}.yaml", value)
    context = {"version": "chrona/render-context/v0.17", "kind": "render-context", "id": "ctx", "body": {
        "project": primary_ref, "view": resources["view"], "theme": resources["theme"],
        "colorScheme": resources["scheme"], "layout": resources["layout"],
        "inputs": {"snapshot": snapshot_ref}, "environment": {"fontMetrics": {"missingFont": "diagnose"}},
        "target": {"capabilities": []}}}
    context_ref = _write(tmp_path, "current", "context.yaml", context)
    monkeypatch.setattr(chrona_resources, "Draft202012Validator",
                        lambda _schema, **_kwargs: type("V", (), {"iter_errors": lambda self, _value: iter(())})())
    chrona_resources.schema_validator.cache_clear()
    monkeypatch.setattr(closure, "resolve_theme", lambda *_args, **_kwargs: {})

    def fake_parse(identity, value):
        if identity.kind != "render-context":
            if identity.kind == "project":
                return ProjectContract(identity, value["version"], freeze(value),
                                       tuple(freeze(item) for item in value.get("extensions", ())))
            if identity.kind == "profile-package":
                return ProfilePackageContract(identity, value["version"], value["packageId"], freeze(value))
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
            None, RenderEnvironment(1, 1, "en-US", freeze({"missingFont": "diagnose"}), 0, None),
            RenderTarget("svg", ()),
        )

    monkeypatch.setattr(closure, "parse_contract", fake_parse)
    monkeypatch.setattr(contract_diagnostics, "parse_contract", fake_parse)
    return closure.resolve_render_context(context_ref, LocalSnapshotReader(tmp_path, "test"))


def _package_extension(tmp_path, token, *, declared_id="kit", package_id="kit", address="extensions/kit.yaml"):
    value = {"version": "chrona/profile/v0.3", "packageId": package_id, "profiles": {}}
    payload = yaml.safe_dump(value, sort_keys=True).encode()
    path = snapshot_directory(tmp_path, token) / address
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return {"packageId": declared_id, "resource": {
        "id": "kit", "kind": "profile-package", "store": {"provider": "local", "identity": "test"},
        "address": address, "revision": {"token": token},
        "contentIdentity": "sha256:" + sha256(payload).hexdigest(),
    }}


def test_snapshot_project_resolves_same_package_id_at_its_own_pin(tmp_path, monkeypatch, request):
    current_package = _package_extension(tmp_path, "current")
    historic_package = _package_extension(tmp_path, "historic")
    closure_value = _resolve_projects_with_packages(
        tmp_path, monkeypatch, primary_extensions=[current_package], snapshot_extensions=[historic_package])
    request.addfinalizer(chrona_resources.schema_validator.cache_clear)

    assert [(item.id, item.revision) for item in closure_value.resources if item.kind == "profile-package"] == [
        ("kit", "current"), ("kit", "historic")]
    assert [item.identity.revision for item in closure_value.profile_packages_for(closure_value.project)] == ["current"]
    assert [item.identity.revision for item in closure_value.profile_packages_for(closure_value.snapshot_project)] == ["historic"]


def test_snapshot_project_reuses_an_exact_shared_package_pin(tmp_path, monkeypatch, request):
    shared_package = _package_extension(tmp_path, "current")
    closure_value = _resolve_projects_with_packages(
        tmp_path, monkeypatch, primary_extensions=[shared_package], snapshot_extensions=[shared_package])
    request.addfinalizer(chrona_resources.schema_validator.cache_clear)

    assert len([item for item in closure_value.resources if item.kind == "profile-package"]) == 1
    assert closure_value.profile_packages_for(closure_value.project) == closure_value.profile_packages_for(
        closure_value.snapshot_project)


def test_snapshot_project_missing_package_pin_is_rejected(tmp_path, monkeypatch, request):
    missing = {"packageId": "kit", "resource": {
        "id": "kit", "kind": "profile-package", "store": {"provider": "local", "identity": "test"},
        "address": "extensions/missing.yaml", "revision": {"token": "historic"},
    }}
    with pytest.raises(ClosureError) as error:
        _resolve_projects_with_packages(tmp_path, monkeypatch, primary_extensions=[], snapshot_extensions=[missing])
    request.addfinalizer(chrona_resources.schema_validator.cache_clear)

    assert error.value.diagnostic_id == "E_STORE_REFERENCE"


def test_snapshot_project_package_declaration_must_match_its_pinned_package(tmp_path, monkeypatch, request):
    package = _package_extension(tmp_path, "historic", declared_id="not-kit")
    with pytest.raises(ClosureError) as error:
        _resolve_projects_with_packages(tmp_path, monkeypatch, primary_extensions=[], snapshot_extensions=[package])
    request.addfinalizer(chrona_resources.schema_validator.cache_clear)

    assert error.value.diagnostic_id == "E_CLOSURE_ID"


def _real_ingress_with_package_stores(tmp_path, primary_extensions, snapshot_extensions, package_values):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    example_root = root / "examples/halcyon-1"

    def write_local(token, address, value, kind):
        payload = yaml.safe_dump(value, sort_keys=False).encode()
        path = snapshot_directory(tmp_path, token) / address
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        identifier = value.get("project", {}).get("id") if kind == "project" else value.get("id")
        return {"id": identifier, "kind": kind,
                "store": {"provider": "local", "identity": "test"}, "address": address,
                "revision": {"token": token},
                "contentIdentity": "sha256:" + sha256(payload).hexdigest()}

    primary_project = yaml.safe_load((example_root / "project.yaml").read_text(encoding="utf-8"))
    primary_project["extensions"] = primary_extensions
    primary_ref = write_local("primary", "project.yaml", primary_project, "project")
    historic_project = yaml.safe_load((example_root / "project.yaml").read_text(encoding="utf-8"))
    historic_project["extensions"] = snapshot_extensions
    historic_ref = write_local("historic", "project.yaml", historic_project, "project")

    original_context = context_document(example_root, "programme-board")
    body = original_context["body"]
    references = {"project": primary_ref}
    for key, kind in (("view", "view"), ("theme", "theme"),
                      ("colorScheme", "color-scheme"), ("layout", "layout-profile")):
        original = body[key]
        value = snapshot_resource_document(example_root, original)
        references[key] = write_local("primary", original["address"], value, kind)
    snapshot_ref = write_local("primary", "snapshot-ref.yaml", {
        "version": "chrona/snapshot-ref/v0.2", "kind": "snapshot-ref", "id": "snapshot",
        "body": {"project": historic_ref}}, "snapshot-ref")
    body.update({key: references[key] for key in ("project", "view", "theme", "colorScheme", "layout")})
    body["inputs"] = {"snapshot": snapshot_ref}
    context_ref = write_local("primary", "context.yaml", original_context, "render-context")

    class Reader:
        def read(self, reference):
            if reference.get("kind") == "profile-package":
                key = (reference["store"]["identity"], reference["address"])
                try:
                    return package_values[key]
                except KeyError as error:
                    raise SnapshotReadError("E_STORE_REFERENCE", f"unresolved package pin {key!r}") from error
            return LocalSnapshotReader(tmp_path, "test").read(reference)

    return closure.resolve_render_context(context_ref, Reader())


def _real_package_ref(store_identity, address):
    return {"packageId": "kit", "resource": {
        "id": "kit", "kind": "profile-package",
        "store": {"provider": "local", "identity": store_identity},
        "address": address, "revision": {"token": "shared-token"},
    }}


def test_real_ingress_keeps_same_id_and_token_source_package_edges_distinct(tmp_path):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    package = yaml.safe_load((root / "examples/halcyon-1/extensions/semiconductor-development.yaml").read_text(encoding="utf-8"))
    package["packageId"] = "kit"
    package["contentIdentity"] = content_identity({key: value for key, value in package.items() if key != "contentIdentity"})
    other = yaml.safe_load(yaml.safe_dump(package))
    other["profiles"]["PDR"]["fields"]["approval"]["required"] = False
    other["contentIdentity"] = content_identity({key: value for key, value in other.items() if key != "contentIdentity"})
    first_payload = yaml.safe_dump(package, sort_keys=False).encode()
    other_payload = yaml.safe_dump(other, sort_keys=False).encode()
    primary_ref = _real_package_ref("store-a", "packages/kit.yaml")
    snapshot_ref = _real_package_ref("store-b", "packages/kit.yaml")

    resolved = _real_ingress_with_package_stores(
        tmp_path, [primary_ref], [snapshot_ref],
        {("store-a", "packages/kit.yaml"): first_payload,
         ("store-b", "packages/kit.yaml"): other_payload})

    primary_package, = resolved.profile_packages_for(resolved.project)
    snapshot_package, = resolved.profile_packages_for(resolved.snapshot_project)
    assert primary_package.identity.revision == snapshot_package.identity.revision == "shared-token"
    assert primary_package.identity.content_identity != snapshot_package.identity.content_identity
    assert primary_package.profile_input["profiles"]["PDR"]["fields"]["approval"]["required"] is True
    assert snapshot_package.profile_input["profiles"]["PDR"]["fields"]["approval"]["required"] is False
    assert len(resolved.profile_packages) == 2


def test_real_ingress_rejects_conflicting_same_source_package_declarations(tmp_path):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    package_value = yaml.safe_load((root / "examples/halcyon-1/extensions/semiconductor-development.yaml").read_text(encoding="utf-8"))
    package_value["packageId"] = "kit"
    package_value["contentIdentity"] = content_identity({key: value for key, value in package_value.items()
                                                          if key != "contentIdentity"})
    package = yaml.safe_dump(package_value, sort_keys=False).encode()
    first = _real_package_ref("store-a", "packages/kit-a.yaml")
    second = _real_package_ref("store-b", "packages/kit-b.yaml")
    # The Project schema accepts both declarations; closure rejects their conflict.
    with pytest.raises(ClosureError) as error:
        _real_ingress_with_package_stores(
            tmp_path, [first, second], [],
            {("store-a", "packages/kit-a.yaml"): package,
             ("store-b", "packages/kit-b.yaml"): package})

    assert error.value.diagnostic_id == "E_CLOSURE_ID"


def test_real_ingress_rejects_snapshot_package_id_mismatch(tmp_path):
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    package_value = yaml.safe_load((root / "examples/halcyon-1/extensions/semiconductor-development.yaml").read_text(encoding="utf-8"))
    package_value["packageId"] = "kit"
    package_value["contentIdentity"] = content_identity({key: value for key, value in package_value.items()
                                                          if key != "contentIdentity"})
    payload = yaml.safe_dump(package_value, sort_keys=False).encode()
    extension = {"packageId": "another-id", "resource": _real_package_ref("snapshot-store", "packages/kit.yaml")["resource"]}

    with pytest.raises(ClosureError) as error:
        _real_ingress_with_package_stores(
            tmp_path, [], [extension], {("snapshot-store", "packages/kit.yaml"): payload})

    assert error.value.diagnostic_id == "E_CLOSURE_ID"


def test_real_ingress_rejects_unresolved_snapshot_package_pin(tmp_path):
    reference = _real_package_ref("missing-store", "packages/missing.yaml")

    with pytest.raises(ClosureError) as error:
        _real_ingress_with_package_stores(tmp_path, [], [reference], {})

    assert error.value.diagnostic_id == "E_STORE_REFERENCE"


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
    context = context_document(example_root, "programme-board")
    token = "stale-profile"
    refs = {}
    for key in ("project", "view", "theme", "colorScheme", "layout"):
        original = context["body"][key]
        value = snapshot_resource_document(example_root, original)
        kind = original["kind"]
        for extension in value.get("extensions", ()) if key == "project" else ():
            # The Project's pinned profile packages move into the test store byte for byte.
            package = extension["resource"]
            package_path = snapshot_directory(tmp_path, package["revision"]["token"]) / package["address"]
            package_path.parent.mkdir(parents=True, exist_ok=True)
            package_path.write_bytes((example_root / package["address"]).read_bytes())
            package["store"] = {"provider": "local", "identity": "test"}
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
