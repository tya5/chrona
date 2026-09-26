from pathlib import Path
from hashlib import sha256
import yaml
import pytest

from chrona.core.identity import content_identity
from chrona.presentation.model.theme_inheritance import ThemeInheritanceError, _resolve, resolve_draft_theme, resolve_snapshot_theme
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


def test_recursive_derived_theme_uses_effective_base_identity(tmp_path: Path):
    base = _base(); source = yaml.safe_dump(base).encode(); (tmp_path / "base.yaml").write_bytes(source)
    middle = _derived(base, source); middle_source = yaml.safe_dump(middle).encode()
    (tmp_path / "middle.yaml").write_bytes(middle_source)
    effective_middle = resolve_draft_theme(tmp_path / "middle.yaml")
    top = _derived(effective_middle, middle_source, path="middle.yaml")
    top["id"] = "top"; top["body"]["extends"]["id"] = "derived"
    top["body"]["values"]["spacing.m"]["value"] = 30
    (tmp_path / "top.yaml").write_text(yaml.safe_dump(top), encoding="utf-8")
    assert resolve_draft_theme(tmp_path / "top.yaml")["body"]["values"]["spacing.m"]["value"] == 30


def test_theme_source_cycle_rejects_before_attempting_an_untrusted_pin():
    source = _base(); raw = yaml.safe_dump(source).encode()
    derived = _derived(source, raw)
    with pytest.raises(ThemeInheritanceError) as error:
        _resolve(derived, "derived.yaml", lambda _key, _declaration: (derived, _pin(raw), "derived.yaml"))
    assert error.value.code == "E_THEME_INHERITANCE_CYCLE"


def test_draft_theme_rejects_symlink_escape(tmp_path: Path):
    inside = tmp_path / "inside"; inside.mkdir()
    outside = tmp_path / "outside.yaml"; base = _base(); source = yaml.safe_dump(base).encode()
    outside.write_bytes(source); (inside / "base.yaml").symlink_to(outside)
    (inside / "derived.yaml").write_text(yaml.safe_dump(_derived(base, source)), encoding="utf-8")
    with pytest.raises(ThemeInheritanceError) as error: resolve_draft_theme(inside / "derived.yaml")
    assert error.value.code == "E_THEME_INHERITANCE_PATH"


def test_draft_theme_distinguishes_missing_and_wrong_kind_base(tmp_path: Path):
    base = _base(); source = yaml.safe_dump(base).encode()
    path = tmp_path / "derived.yaml"
    path.write_text(yaml.safe_dump(_derived(base, source)), encoding="utf-8")
    with pytest.raises(ThemeInheritanceError) as error: resolve_draft_theme(path)
    assert error.value.code == "E_THEME_INHERITANCE_BASE_MISSING"
    wrong = {**base, "kind": "color-scheme"}; wrong_source = yaml.safe_dump(wrong).encode()
    (tmp_path / "base.yaml").write_bytes(wrong_source)
    path.write_text(yaml.safe_dump(_derived(wrong, wrong_source)), encoding="utf-8")
    with pytest.raises(ThemeInheritanceError) as error: resolve_draft_theme(path)
    assert error.value.code == "E_THEME_INHERITANCE_BASE_KIND"
