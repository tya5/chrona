import yaml

from chrona.usecases import preset_library


def test_builtin_preset_copy_includes_optional_style_member(tmp_path, monkeypatch):
    members = {
        "view": {"id": "view-id", "kind": "view", "sourceRoot": "source", "sourcePath": "view.yaml"},
        "theme": {"id": "theme-id", "kind": "theme", "sourceRoot": "source", "sourcePath": "theme.yaml"},
        "colorScheme": {"id": "scheme-id", "kind": "color-scheme", "sourceRoot": "source", "sourcePath": "scheme.yaml"},
        "layout": {"id": "layout-id", "kind": "layout-profile", "sourceRoot": "source", "sourcePath": "layout.yaml"},
        "style": {"id": "style-id", "kind": "style", "sourceRoot": "source", "sourcePath": "style.yaml"},
    }
    entry = {"id": "styled", "members": members}
    documents = {
        "view-id": {"version": "v", "kind": "view", "id": "view-id"},
        "theme-id": {"version": "v", "kind": "theme", "id": "theme-id"},
        "scheme-id": {"version": "v", "kind": "color-scheme", "id": "scheme-id"},
        "layout-id": {"version": "v", "id": "layout-id"},
        "style-id": {"version": "chrona/style/v0.2", "kind": "style", "id": "style-id", "body": {"rules": []}},
    }
    monkeypatch.setattr(preset_library, "_library", lambda: [entry])
    monkeypatch.setattr(
        preset_library,
        "_read_member",
        lambda member: yaml.safe_dump(documents[member["id"]], sort_keys=False).encode(),
    )

    target = preset_library.copy_builtin_preset("styled", tmp_path / "styled")

    preset = yaml.safe_load(target.read_text(encoding="utf-8"))
    assert preset["body"]["resources"]["style"] == {"id": "style-id", "kind": "style", "path": "style.yaml"}
    assert yaml.safe_load((target.parent / "style.yaml").read_text(encoding="utf-8")) == documents["style-id"]
