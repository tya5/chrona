from pathlib import Path
import yaml
import pytest

from chrona.core.identity import content_identity
from chrona.presentation.model.theme_inheritance import ThemeInheritanceError, resolve_draft_theme


def _base() -> dict:
    return {"version": "chrona/theme/v0.11", "kind": "theme", "id": "base",
            "body": {"values": {"spacing.m": {"type": "number", "value": 12}},
                     "roles": {"title": {"fontSize": "spacing.m"}}, "colorBindings": {}}}


def test_derived_theme_replaces_existing_whole_entries_and_has_canonical_base_pin(tmp_path: Path):
    base = _base(); (tmp_path / "base.yaml").write_text(yaml.safe_dump(base), encoding="utf-8")
    derived = {"version": "chrona/theme/v0.12", "kind": "theme", "id": "derived",
               "body": {"extends": {"id": "base", "path": "base.yaml", "contentIdentity": content_identity(base)},
                        "values": {"spacing.m": {"type": "number", "value": 24}},
                        "roles": {"title": {"fontSize": "spacing.m"}}}}
    path = tmp_path / "derived.yaml"; path.write_text(yaml.safe_dump(derived), encoding="utf-8")
    effective = resolve_draft_theme(path)
    assert effective["version"] == "chrona/theme/v0.11"
    assert effective["id"] == "derived"
    assert effective["body"]["values"]["spacing.m"]["value"] == 24


@pytest.mark.parametrize("body, code", [
    ({"extends": {"id": "base", "path": "../base.yaml", "contentIdentity": "sha256:" + "0" * 64}}, "E_THEME_INHERITANCE_SCHEMA"),
    ({"extends": {"id": "base", "path": "base.yaml", "contentIdentity": "sha256:" + "0" * 64}}, "E_THEME_INHERITANCE_BASE_IDENTITY"),
    ({"extends": {"id": "base", "path": "base.yaml", "contentIdentity": "sha256:" + "0" * 64}, "values": {"new": {"type": "number", "value": 1}}}, "E_THEME_INHERITANCE_BASE_IDENTITY"),
])
def test_derived_theme_rejects_invalid_pins(tmp_path: Path, body: dict, code: str):
    (tmp_path / "base.yaml").write_text(yaml.safe_dump(_base()), encoding="utf-8")
    path = tmp_path / "derived.yaml"; path.write_text(yaml.safe_dump({"version": "chrona/theme/v0.12", "kind": "theme", "id": "derived", "body": body}), encoding="utf-8")
    with pytest.raises(ThemeInheritanceError) as error: resolve_draft_theme(path)
    assert error.value.code == code
