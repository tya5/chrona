"""Shared authoring ends before the immutable Context/render boundary."""
from hashlib import sha256
from pathlib import Path
import shutil

import pytest
import yaml

from chrona.storage.snapshot_paths import snapshot_directory
from chrona.usecases.deck_context import resolve_deck_context
from chrona.usecases.materialize import (
    MaterializationError, _OverlayBuilder, copy_context_closure, materialize,
)


ROOT = Path(__file__).resolve().parents[2]


def _deck(tmp_path: Path) -> Path:
    root = tmp_path / "deck"
    shutil.copytree(ROOT / "tests/fixtures/aster-ssd", root)
    document = yaml.safe_load((root / "contexts/01-overview.yaml").read_bytes())
    manifest = {
        "version": "chrona/example-materializer/v0.1", "id": "synthetic-deck",
        "role": "regression-corpus", "contextDefaults": document["body"],
        "slides": [{"id": "overview", "contextOverrides": {"id": document["id"]},
                    "evidence": "Equivalent shared and explicit Contexts.",
                    "expectedSvg": "generated/overview.svg",
                    "expectedScene": "generated/overview.scene.json"}],
    }
    (root / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    return root


def test_shared_and_explicit_real_materialization_is_byte_identical(tmp_path):
    shared = _deck(tmp_path)
    selected = resolve_deck_context(shared / "manifest.yaml", "overview")
    explicit = tmp_path / "explicit"
    shutil.copytree(shared, explicit)
    manifest = yaml.safe_load((explicit / "manifest.yaml").read_bytes())
    manifest.pop("contextDefaults")
    manifest["slides"][0].pop("contextOverrides")
    manifest["slides"][0]["context"] = selected.address
    context_file = explicit / selected.address
    context_file.parent.mkdir(parents=True)
    context_file.write_bytes(selected.payload)
    (explicit / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")

    a = materialize(shared / "manifest.yaml", "overview", tmp_path / "a", write=True)
    b = materialize(explicit / "manifest.yaml", "overview", tmp_path / "b", write=True)
    assert a.closure_reference == b.closure_reference
    assert a.closure_reference["contentIdentity"] == "sha256:" + sha256(selected.payload).hexdigest()
    for artifact in ("review.svg", "review.scene.json", "closure.yaml"):
        assert (tmp_path / "a" / artifact).read_bytes() == (tmp_path / "b" / artifact).read_bytes()
    assert not (shared / selected.address).exists()


def test_composed_context_cannot_shadow_an_authored_file(tmp_path):
    root = _deck(tmp_path)
    selected = resolve_deck_context(root / "manifest.yaml", "overview")
    authored = root / selected.address
    authored.parent.mkdir(parents=True)
    authored.write_bytes(b"authored content")
    snapshot = tmp_path / "snapshot"
    with pytest.raises(MaterializationError, match="E_MATERIALIZER_OVERLAY_COLLISION"):
        copy_context_closure(root, selected, snapshot)
    assert authored.read_bytes() == b"authored content"
    assert not snapshot.exists()


def test_composed_context_reference_pins_are_not_repaired(tmp_path):
    root = _deck(tmp_path)
    manifest = yaml.safe_load((root / "manifest.yaml").read_bytes())
    manifest["contextDefaults"]["project"]["contentIdentity"] = "sha256:" + "0" * 64
    (root / "manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    selected = resolve_deck_context(root / "manifest.yaml", "overview")
    with pytest.raises(ValueError, match="E_CONTENT_IDENTITY"):
        copy_context_closure(root, selected, tmp_path / "snapshot")


@pytest.mark.parametrize("address,owned_address", [
    ("resource.yaml", "resource.yaml"),
    ("resource.yaml", "resource.yaml/child"),
    ("resource.yaml/child", "resource.yaml"),
])
def test_reserved_context_path_is_rejected_before_resource_write(tmp_path, address, owned_address):
    from chrona.usecases.materialize import _copy_reference

    source = tmp_path / "source"
    source.mkdir()
    resource = source / address
    resource.parent.mkdir(parents=True, exist_ok=True)
    resource.write_bytes(b"resource")
    snapshot = tmp_path / "snapshot"
    target = snapshot_directory(snapshot, "r1") / address
    builder = _OverlayBuilder(tmp_path / "overlay")
    builder.reserve_context_path(snapshot_directory(snapshot, "r1") / owned_address)
    reference = {"id": "resource", "kind": "project", "address": address,
                 "revision": {"token": "r1"}, "store": {"provider": "local", "identity": "test"}}
    with pytest.raises(MaterializationError, match="E_MATERIALIZER_OVERLAY_COLLISION"):
        _copy_reference(source, reference, snapshot, overlay=builder)
    assert not target.exists()


def test_composed_init_copies_package_closure_without_overlay_internals(tmp_path, monkeypatch):
    from chrona.presentation.model.closure import resolve_render_context
    from chrona.storage.package_store import read_package_reference
    from chrona.storage.revision_store import LocalSnapshotReader
    from chrona.usecases import local_authoring
    from chrona.usecases.deck_context import resolve_deck_context

    source = _deck(tmp_path)
    monkeypatch.setattr(local_authoring, "template_resource", lambda _name: source)
    manifest_path = source / "manifest.yaml"
    selected = resolve_deck_context(manifest_path, "overview")
    destination = tmp_path / "initialized"

    result = local_authoring.initialize_project(destination, example="aster-ssd")

    assert result.available_slides == ("overview",)
    store_root = destination / ".chrona" / "store"
    token = selected.body["project"]["revision"]["token"]
    revision = store_root / f"revision-{token}"
    context_path = revision / selected.address
    assert context_path.is_file()
    context = yaml.safe_load(context_path.read_bytes())
    context_reference = {
        "id": context["id"], "kind": "render-context",
        "store": context["body"]["project"]["store"], "address": selected.address,
        "revision": {"token": token},
        "contentIdentity": "sha256:" + sha256(context_path.read_bytes()).hexdigest(),
    }
    closure = resolve_render_context(
        context_reference,
        LocalSnapshotReader(store_root, "aster-ssd-example", require_content_identity=False),
    )
    assert closure.context.identity.id == context["id"]

    package_assets = [
        asset[key]["locator"]
        for asset in selected.body["environment"]["fontMetrics"]["assets"]
        for key in ("metrics",)
    ]
    assert package_assets
    for locator in package_assets:
        staged_asset = revision / locator["address"]
        assert staged_asset.is_file()
        assert staged_asset.read_bytes() == read_package_reference({
            "store": {"provider": "package", "identity": locator["identity"]},
            "address": locator["address"],
        })
    assert not any(path.name == "materialized-overlay" for path in store_root.rglob("*"))
