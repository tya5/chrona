from pathlib import Path
from hashlib import sha256
import yaml
import pytest

from chrona.core.identity import content_identity
from chrona.presentation.model.theme_inheritance import ThemeInheritanceError, resolve_draft_theme, resolve_snapshot_theme
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory


def _base() -> dict:
    return {"version": "chrona/theme/v0.11", "kind": "theme", "id": "base",
            "body": {"values": {"spacing.m": {"type": "number", "value": 12}},
                     "roles": {"title": {"fontSize": "spacing.m"}},
                     "colorBindings": {"title.fill": "text"}}}


def _pin(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def _derived(base: dict, source: bytes, *, path: str = "base.yaml") -> dict:
    return {"version": "chrona/theme/v0.12", "kind": "theme", "id": "derived",
            "body": {"extends": {"id": "base", "path": path,
                                 "sourceContentIdentity": _pin(source), "contentIdentity": content_identity(base)},
                     "values": {"spacing.m": {"type": "number", "value": 24}}}}


def test_derived_theme_replaces_existing_whole_entries_and_has_canonical_base_pin(tmp_path: Path):
    base = _base(); source = yaml.safe_dump(base).encode(); (tmp_path / "base.yaml").write_bytes(source)
    derived = _derived(base, source)
    path = tmp_path / "derived.yaml"; path.write_text(yaml.safe_dump(derived), encoding="utf-8")
    effective = resolve_draft_theme(path)
    assert effective["version"] == "chrona/theme/v0.11"
    assert effective["id"] == "derived"
    assert effective["body"]["values"]["spacing.m"]["value"] == 24


@pytest.mark.parametrize("mutate, code", [
    (lambda value: value["body"]["extends"].update(path="../base.yaml"), "E_THEME_INHERITANCE_SCHEMA"),
    (lambda value: value["body"]["extends"].update(sourceContentIdentity="sha256:" + "0" * 64), "E_THEME_INHERITANCE_SOURCE_IDENTITY"),
    (lambda value: value["body"]["extends"].update(contentIdentity="sha256:" + "0" * 64), "E_THEME_INHERITANCE_BASE_IDENTITY"),
    (lambda value: value["body"]["values"].update(new={"type": "number", "value": 1}), "E_THEME_INHERITANCE_OVERRIDE_UNKNOWN"),
    (lambda value: value["body"]["values"].update({"spacing.m": {"type": "number", "value": []}}), "E_THEME_INHERITANCE_EFFECTIVE_SCHEMA"),
])
def test_derived_theme_rejects_invalid_pins_and_overrides(tmp_path: Path, mutate, code: str):
    base = _base(); source = yaml.safe_dump(base).encode(); (tmp_path / "base.yaml").write_bytes(source)
    derived = _derived(base, source); mutate(derived)
    path = tmp_path / "derived.yaml"; path.write_text(yaml.safe_dump(derived), encoding="utf-8")
    with pytest.raises(ThemeInheritanceError) as error: resolve_draft_theme(path)
    assert error.value.code == code


def test_derived_theme_resolves_from_same_immutable_snapshot(tmp_path: Path):
    base = _base(); source = yaml.safe_dump(base).encode(); derived = _derived(base, source)
    root = snapshot_directory(tmp_path, "revision-1"); (root / "themes").mkdir(parents=True)
    (root / "themes/base.yaml").write_bytes(source)
    reference = {"kind": "theme", "id": "derived", "store": {"provider": "local", "identity": "test"},
                 "address": "themes/derived.yaml", "revision": {"token": "revision-1"},
                 "contentIdentity": _pin(yaml.safe_dump(derived).encode())}
    reader = LocalSnapshotReader(tmp_path, "test")
    assert resolve_snapshot_theme(derived, reference, reader)["body"]["values"]["spacing.m"]["value"] == 24
    (root / "themes/base.yaml").write_text("changed", encoding="utf-8")
    with pytest.raises(ThemeInheritanceError) as error: resolve_snapshot_theme(derived, reference, reader)
    assert error.value.code == "E_THEME_INHERITANCE_SOURCE_IDENTITY"
