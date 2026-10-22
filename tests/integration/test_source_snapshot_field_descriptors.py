"""Native review projection keeps snapshot package field declarations source-local."""
from __future__ import annotations

from hashlib import sha256
from pathlib import Path

import yaml

from chrona.core.identity import content_identity
from chrona.presentation.model.closure import resolve_render_context
from chrona.presentation.model.field_roles import FieldDescriptor
from chrona.scheduling.scheduler import ReferenceScheduler
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases import render_review as render_review_usecase
from chrona.usecases.render_review import RenderRequest, render_review
from tests.unit.chrona.presentation.model.test_snapshot_context_closure import _real_package_ref
from tests.support.deck_contexts import context_document, stage_theme_bases


_ORIGINAL_BUILD_REVIEW_PROJECTION = render_review_usecase.build_review_projection


def _real_ingress_with_actual_and_package_stores(tmp_path, primary_extensions, snapshot_extensions,
                                                  package_values):
    """Close the snapshot-package fixture with the real Context's required actual input."""
    root = Path(__file__).resolve().parents[2]
    example_root = root / "examples/halcyon-1"

    def write_local(token, address, value, kind):
        payload = yaml.safe_dump(value, sort_keys=False).encode()
        path = snapshot_directory(tmp_path, token) / address
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        identifier = value.get("project", {}).get("id") if kind == "project" else value.get("id")
        return {"id": identifier, "kind": kind,
                "store": {"provider": "local", "identity": "test"}, "address": address,
                "revision": {"token": token}, "contentIdentity": "sha256:" + sha256(payload).hexdigest()}

    primary_project = yaml.safe_load((example_root / "project.yaml").read_text(encoding="utf-8"))
    primary_project["extensions"] = primary_extensions
    primary_ref = write_local("primary", "project.yaml", primary_project, "project")
    historic_project = yaml.safe_load((example_root / "project.yaml").read_text(encoding="utf-8"))
    historic_project["extensions"] = snapshot_extensions
    historic_ref = write_local("historic", "project.yaml", historic_project, "project")
    context = context_document(example_root, "programme-board")
    body = context["body"]
    references = {"project": primary_ref}
    for key, kind in (("view", "view"), ("theme", "theme"),
                      ("colorScheme", "color-scheme"), ("layout", "layout-profile")):
        original = body[key]
        value = yaml.safe_load((example_root / original["address"]).read_text(encoding="utf-8"))
        references[key] = write_local("primary", original["address"], value, kind)
        if kind == "theme":
            stage_theme_bases(example_root, original["address"], snapshot_directory(tmp_path, "primary"))
    actual_value = yaml.safe_load((example_root / "actual.yaml").read_text(encoding="utf-8"))
    actual_ref = write_local("primary", "actual.yaml", actual_value, "actual-set")
    snapshot_ref = write_local("primary", "snapshot-ref.yaml", {
        "version": "chrona/snapshot-ref/v0.2", "kind": "snapshot-ref", "id": "snapshot",
        "body": {"project": historic_ref}}, "snapshot-ref")
    body.update({key: references[key] for key in ("project", "view", "theme", "colorScheme", "layout")})
    body["inputs"] = {"actual": actual_ref, "snapshot": snapshot_ref}
    context_ref = write_local("primary", "context.yaml", context, "render-context")

    class Reader:
        def read(self, reference):
            if reference.get("kind") == "profile-package":
                key = (reference["store"]["identity"], reference["address"])
                try:
                    return package_values[key]
                except KeyError as error:
                    from chrona.core.ports import SnapshotReadError
                    raise SnapshotReadError("E_STORE_REFERENCE", f"unresolved package pin {key!r}") from error
            return LocalSnapshotReader(tmp_path, "test").read(reference)

    return resolve_render_context(context_ref, Reader())


def test_native_render_uses_snapshot_package_descriptors_for_snapshot_projection(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[2]
    package = yaml.safe_load((root / "examples/halcyon-1/extensions/semiconductor-development.yaml")
                             .read_text(encoding="utf-8"))
    package["packageId"] = "kit"
    package["contentIdentity"] = content_identity(
        {key: value for key, value in package.items() if key != "contentIdentity"})
    historic = yaml.safe_load(yaml.safe_dump(package))
    historic["profiles"]["PDR"]["fields"]["approval"]["enumValues"].append("deferred")
    historic["profiles"]["PDR"]["fields"]["approval"]["required"] = False
    historic["contentIdentity"] = content_identity(
        {key: value for key, value in historic.items() if key != "contentIdentity"})
    primary_ref = _real_package_ref("store-a", "packages/kit.yaml")
    snapshot_ref = _real_package_ref("store-b", "packages/kit.yaml")
    resolved = _real_ingress_with_actual_and_package_stores(
        tmp_path, [primary_ref], [snapshot_ref],
        {("store-a", "packages/kit.yaml"): yaml.safe_dump(package, sort_keys=False).encode(),
         ("store-b", "packages/kit.yaml"): yaml.safe_dump(historic, sort_keys=False).encode()},
    )
    primary_package, = resolved.profile_packages_for(resolved.project)
    snapshot_package, = resolved.profile_packages_for(resolved.snapshot_project)
    assert primary_package.identity.revision == snapshot_package.identity.revision == "shared-token"
    assert primary_package.identity.content_identity != snapshot_package.identity.content_identity
    captured = []

    def capture_projection(*args, **kwargs):
        projection = _ORIGINAL_BUILD_REVIEW_PROJECTION(*args, **kwargs)
        captured.append((kwargs, projection))
        return projection

    monkeypatch.setattr(render_review_usecase, "build_review_projection", capture_projection)
    rendered = render_review(RenderRequest(
        closure=resolved, snapshot_root=tmp_path, scheduler=ReferenceScheduler()))

    assert rendered.surface.primitives
    assert len(captured) == 1
    kwargs, projection = captured[0]
    primary_bindings = kwargs["field_bindings"]
    snapshot_bindings = kwargs["snapshot_field_bindings"]
    assert primary_bindings is not snapshot_bindings
    assert primary_bindings.descriptor_for("pdr", "approval") == FieldDescriptor(
        "approval", "enum", "one", ("pending", "approved", "rejected"))
    assert snapshot_bindings.descriptor_for("pdr", "approval") == FieldDescriptor(
        "approval", "enum", "one", ("pending", "approved", "rejected", "deferred"))
    assert projection.items
