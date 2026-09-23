from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from chrona.presentation.packages import PackageError, PackageMember, package_content_identity, verify_presentation_package
from chrona.presentation.package_acquisition import AcquisitionError, acquire_local_package, verify_locked_package


ROOT = Path(__file__).parents[4]


def _digest(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _package(root: Path) -> Path:
    source = ROOT / "examples/controller-z"
    files = {"views/executive.yaml": source / "views/executive.yaml", "themes/executive-light.yaml": source / "themes/executive-light.yaml",
             "schemes/executive-light.yaml": source / "schemes/executive-light.yaml", "layouts/executive-review.yaml": source / "layouts/executive-review.yaml"}
    for relative, original in files.items():
        target = root / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(original.read_bytes())
    preset = {"version": "chrona/presentation-preset/v0.1", "kind": "presentation-preset", "id": "executive-light", "body": {
        "package": {"version": "1.0.0"}, "resources": {
            "view": {"id": "controller-z-executive", "kind": "view", "path": "views/executive.yaml"},
            "theme": {"id": "executive-light", "kind": "theme", "path": "themes/executive-light.yaml"},
            "colorScheme": {"id": "executive-light", "kind": "color-scheme", "path": "schemes/executive-light.yaml"},
            "layout": {"id": "executive-review", "kind": "layout-profile", "path": "layouts/executive-review.yaml"}},
        "compatibleColorSchemes": [{"id": "executive-light", "kind": "color-scheme", "path": "schemes/executive-light.yaml"}]}}
    preset_path = root / "presets/executive-light.yaml"; preset_path.parent.mkdir(); preset_path.write_text(yaml.safe_dump(preset, sort_keys=False))
    resources = [{"id": "controller-z-executive", "kind": "view", "path": "views/executive.yaml", "contentIdentity": _digest(root / "views/executive.yaml")},
                 {"id": "executive-light", "kind": "theme", "path": "themes/executive-light.yaml", "contentIdentity": _digest(root / "themes/executive-light.yaml")},
                 {"id": "executive-light", "kind": "color-scheme", "path": "schemes/executive-light.yaml", "contentIdentity": _digest(root / "schemes/executive-light.yaml")},
                 {"id": "executive-review", "kind": "layout-profile", "path": "layouts/executive-review.yaml", "contentIdentity": _digest(root / "layouts/executive-review.yaml")}]
    manifest = {"format": "chrona/presentation-package/v0.1", "kind": "presentation-package", "id": "acme/executive-review",
        "package": {"release": "1.0.0", "contentIdentity": "sha256:" + "0" * 64, "license": "CC-BY-4.0", "publisher": {"id": "acme", "displayName": "Acme"}},
        "members": {"presets": [{"id": "executive-light", "path": "presets/executive-light.yaml", "contentIdentity": _digest(preset_path)}], "resources": resources},
        "compatibility": {"chrona": ">=0.1.0a0 <0.2.0", "targets": ["chrona-output/svg/v0.5"]}, "provenance": {}}
    members = (PackageMember("executive-light", "presentation-preset", "presets/executive-light.yaml", _digest(preset_path)),
               *(PackageMember(item["id"], item["kind"], item["path"], item["contentIdentity"]) for item in resources))
    manifest["package"]["contentIdentity"] = package_content_identity(manifest, root, members)
    (root / "package.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False))
    return root


def test_package_verifies_complete_single_source_tree(tmp_path):
    package = verify_presentation_package(_package(tmp_path / "executive-review"))
    assert package.id == "acme/executive-review"
    assert package.member("views/executive.yaml").kind == "view"  # type: ignore[union-attr]


def test_package_rejects_tampered_member_before_any_consumer(tmp_path):
    root = _package(tmp_path / "executive-review")
    (root / "themes/executive-light.yaml").write_text("tampered")
    with pytest.raises(PackageError, match="E_PACKAGE_MEMBER_IDENTITY"):
        verify_presentation_package(root)


def test_package_rejects_undeclared_or_executable_authority(tmp_path):
    root = _package(tmp_path / "executive-review")
    (root / "plugin.py").write_text("raise SystemExit")
    with pytest.raises(PackageError, match="E_PACKAGE_UNDECLARED_FILE"):
        verify_presentation_package(root)


def test_explicit_acquisition_writes_provider_neutral_lock_and_verifies_offline_bytes(tmp_path):
    source = _package(tmp_path / "source")
    lock_path = tmp_path / "workspace/chrona.lock.yaml"
    acquired = acquire_local_package(source_root=source, cache_root=tmp_path / "cache", preset_id="executive-light", lock_path=lock_path)
    assert lock_path.is_file()
    assert "cache" not in lock_path.read_text()
    locked = verify_locked_package(cache_root=tmp_path / "cache", lock=acquired.lock,
                                   package_id="acme/executive-review", preset_id="executive-light")
    assert locked.package.content_identity == acquired.package.content_identity


def test_locked_package_diagnoses_missing_offline_bytes(tmp_path):
    source = _package(tmp_path / "source")
    acquired = acquire_local_package(source_root=source, cache_root=tmp_path / "cache", preset_id="executive-light", lock_path=tmp_path / "chrona.lock.yaml")
    import shutil
    shutil.rmtree(tmp_path / "cache")
    with pytest.raises(AcquisitionError, match="E_PACKAGE_OFFLINE_UNAVAILABLE"):
        verify_locked_package(cache_root=tmp_path / "cache", lock=acquired.lock,
                              package_id="acme/executive-review", preset_id="executive-light")
