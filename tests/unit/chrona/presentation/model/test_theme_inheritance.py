from copy import deepcopy
from pathlib import Path
from hashlib import sha256
import yaml
import pytest

from chrona.core.identity import content_identity
from chrona.presentation.model.theme_inheritance import ThemeInheritanceError, _resolve, resolve_draft_theme, resolve_snapshot_theme
from chrona.storage.revision_store import LocalSnapshotReader
from chrona.storage.snapshot_paths import snapshot_directory


def _base() -> dict:
    return {"version": "chrona/theme/v0.15", "kind": "theme", "id": "base",
            "body": {"values": {"spacing.m": {"type": "number", "value": 12}},
                     "roles": {"title": {"fontSize": "spacing.m"}},
                     "colorBindings": {"title.fill": "text"}}}


def _pin(payload: bytes) -> str:
    return "sha256:" + sha256(payload).hexdigest()


def _derived(base: dict, source: bytes, *, path: str = "base.yaml") -> dict:
    return {"version": "chrona/theme/v0.16", "kind": "theme", "id": "derived",
            "body": {"extends": {"id": "base", "path": path,
                                 "sourceContentIdentity": _pin(source), "contentIdentity": content_identity(base)},
                     "values": {"spacing.m": {"type": "number", "value": 24}}}}


def test_derived_theme_replaces_existing_whole_entries_and_has_canonical_base_pin(tmp_path: Path):
    base = _base(); source = yaml.safe_dump(base).encode(); (tmp_path / "base.yaml").write_bytes(source)
    derived = _derived(base, source)
    path = tmp_path / "derived.yaml"; path.write_text(yaml.safe_dump(derived), encoding="utf-8")
    effective = resolve_draft_theme(path)
    assert effective["version"] == "chrona/theme/v0.15"
    assert effective["id"] == "derived"
    assert effective["body"]["values"]["spacing.m"]["value"] == 24


@pytest.mark.parametrize("mutate, code", [
    (lambda value: value["body"]["extends"].update(path="../base.yaml"), "E_THEME_INHERITANCE_SCHEMA"),
    (lambda value: value["body"]["extends"].update(sourceContentIdentity="sha256:" + "0" * 64), "E_THEME_INHERITANCE_SOURCE_IDENTITY"),
    (lambda value: value["body"]["extends"].update(contentIdentity="sha256:" + "0" * 64), "E_THEME_INHERITANCE_BASE_IDENTITY"),
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


@pytest.mark.parametrize("mutate, needle", [
    (lambda value: value["body"]["extends"].update(path="../base.yaml"), "derived Theme does not satisfy"),
    (lambda value: value["body"]["extends"].update(sourceContentIdentity="sha256:" + "0" * 64), "sha256:" + "0" * 64),
    (lambda value: value["body"]["extends"].update(contentIdentity="sha256:" + "0" * 64), "sha256:" + "0" * 64),
    (lambda value: value["body"]["values"].update({"spacing.m": {"type": "number", "value": []}}), "resolved Theme does not satisfy"),
])
def test_every_inheritance_failure_says_what_it_found(tmp_path: Path, mutate, needle: str):
    base = _base(); source = yaml.safe_dump(base).encode(); (tmp_path / "base.yaml").write_bytes(source)
    derived = _derived(base, source); mutate(derived)
    path = tmp_path / "derived.yaml"; path.write_text(yaml.safe_dump(derived), encoding="utf-8")
    with pytest.raises(ThemeInheritanceError) as error: resolve_draft_theme(path)
    assert needle in error.value.detail


def test_cycle_missing_base_and_wrong_kind_name_the_themes(tmp_path: Path):
    source = _base(); raw = yaml.safe_dump(source).encode(); derived = _derived(source, raw)
    with pytest.raises(ThemeInheritanceError) as cycle:
        _resolve(derived, "dir/derived.yaml", lambda _key, _declaration: (derived, _pin(raw), "dir/derived.yaml"))
    assert "derived.yaml -> derived.yaml" in cycle.value.detail
    path = tmp_path / "derived.yaml"; path.write_text(yaml.safe_dump(derived), encoding="utf-8")
    with pytest.raises(ThemeInheritanceError) as missing: resolve_draft_theme(path)
    assert "base.yaml" in missing.value.detail
    wrong = {**source, "kind": "color-scheme"}; wrong_raw = yaml.safe_dump(wrong).encode()
    (tmp_path / "base.yaml").write_bytes(wrong_raw)
    path.write_text(yaml.safe_dump(_derived(wrong, wrong_raw)), encoding="utf-8")
    with pytest.raises(ThemeInheritanceError) as kind: resolve_draft_theme(path)
    assert "color-scheme" in kind.value.detail and "'base'" in kind.value.detail


def test_derived_theme_adds_tokens_roles_bindings_scales_and_kinds_the_base_lacks_and_equals_the_hand_merged_theme(tmp_path: Path):
    """#1401: addition is as allowed as replacement; the resolved Theme is the non-derived Theme written by hand."""
    base = _base(); source = yaml.safe_dump(base).encode(); (tmp_path / "base.yaml").write_bytes(source)
    added = {
        "values": {"spacing.l": {"type": "number", "value": 20}, "spacing.m": {"type": "number", "value": 24}},
        "roles": {"subtitle": {"fontSize": "spacing.l"}},
        "colorBindings": {"subtitle.fill": "text"},
        "colorScales": {"phase": {"slots": {"design": "surface"}}},
        "annotationKinds": {"risk": {"label": "Risk"}},
        "metrics": {"text.body.size": "spacing.m"},
    }
    derived = _derived(base, source)
    derived["body"].update(deepcopy(added))
    path = tmp_path / "derived.yaml"; path.write_text(yaml.safe_dump(derived), encoding="utf-8")

    effective = resolve_draft_theme(path)

    by_hand = deepcopy(base)
    by_hand["id"] = "derived"
    for name, entries in added.items():
        by_hand["body"].setdefault(name, {}).update(deepcopy(entries))
    assert effective == by_hand
    assert "subtitle" in effective["body"]["roles"] and "title" in effective["body"]["roles"]  # nothing is removed


def test_a_redeclared_role_replaces_members_and_keeps_omitted_members(tmp_path: Path):
    base = _base(); base["body"]["roles"]["title"] = {"fontSize": "spacing.m", "fontWeight": "w"}
    base["body"]["values"]["w"] = {"type": "fontWeight", "value": "700"}
    source = yaml.safe_dump(base).encode(); (tmp_path / "base.yaml").write_bytes(source)
    derived = _derived(base, source)
    derived["body"]["values"]["spacing.l"] = {"type": "number", "value": 30}
    derived["body"]["roles"] = {"title": {"fontSize": "spacing.l"}}
    path = tmp_path / "derived.yaml"; path.write_text(yaml.safe_dump(derived), encoding="utf-8")

    assert resolve_draft_theme(path)["body"]["roles"]["title"] == {"fontSize": "spacing.l", "fontWeight": "w"}


def test_derived_role_adds_a_member_without_mutating_its_inputs():
    base = _base()
    base["body"]["values"]["w"] = {"type": "fontWeight", "value": "700"}
    source = yaml.safe_dump(base).encode()
    derived = _derived(base, source)
    derived["body"]["roles"] = {"title": {"fontWeight": "w"}}
    before_base, before_derived = deepcopy(base), deepcopy(derived)

    effective = _resolve(derived, "derived.yaml", lambda *_: (base, _pin(source), "base.yaml"))
    expected = deepcopy(base)
    expected["id"] = "derived"
    expected["body"]["values"]["spacing.m"]["value"] = 24
    expected["body"]["roles"]["title"]["fontWeight"] = "w"
    assert effective == expected
    assert base == before_base and derived == before_derived
    effective["body"]["roles"]["title"]["fontWeight"] = "changed"
    assert base == before_base and derived == before_derived


def test_empty_derived_role_does_not_remove_inherited_members():
    base = _base(); source = yaml.safe_dump(base).encode()
    derived = _derived(base, source)
    derived["body"]["roles"] = {"title": {}}

    effective = _resolve(derived, "derived.yaml", lambda *_: (base, _pin(source), "base.yaml"))
    assert effective["body"]["roles"]["title"] == base["body"]["roles"]["title"]


@pytest.mark.parametrize("members", [None, 3, {"fontSize": None}])
def test_malformed_derived_role_uses_effective_schema_diagnostic(members):
    base = _base(); source = yaml.safe_dump(base).encode()
    derived = _derived(base, source)
    derived["body"]["roles"] = {"title": members}

    with pytest.raises(ThemeInheritanceError) as error:
        _resolve(derived, "derived.yaml", lambda *_: (base, _pin(source), "base.yaml"))
    assert error.value.code == "E_THEME_INHERITANCE_EFFECTIVE_SCHEMA"
