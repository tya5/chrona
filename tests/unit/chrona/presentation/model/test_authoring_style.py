from chrona.presentation.contracts import ClosureIdentity, StyleContract, parse_contract
from chrona.presentation.model.authoring import normalize_authoring_workspace
from chrona.resources import builtin_preset_source_root, safe_load


def _resource(name: str) -> dict:
    return safe_load(builtin_preset_source_root("presets/bundles/executive-light").joinpath(name).read_bytes())


def _contract(kind: str, document: dict):
    return parse_contract(ClosureIdentity(kind, document["id"], "draft", "sha256:" + "a" * 64), document)


def test_guided_authoring_copies_optional_preset_style_as_typed_resource():
    resources = {
        "view.yaml": _resource("view.yaml"),
        "theme.yaml": _resource("theme.yaml"),
        "scheme.yaml": _resource("scheme.yaml"),
        "layout.yaml": _resource("layout.yaml"),
        "style.yaml": {
            "version": "chrona/style/v0.2", "kind": "style", "id": "guide-style",
            "body": {"rules": [{"id": "emphasis", "when": {"roles": ["critical"]},
                                  "then": {"role": "emphasis"}}]},
        },
    }
    preset = {
        "version": "chrona/presentation-preset/v0.1", "kind": "presentation-preset", "id": "starter",
        "body": {"package": {"version": "1"}, "resources": {
            "view": {"id": resources["view.yaml"]["id"], "kind": "view", "path": "view.yaml"},
            "style": {"id": "guide-style", "kind": "style", "path": "style.yaml"},
            "theme": {"id": resources["theme.yaml"]["id"], "kind": "theme", "path": "theme.yaml"},
            "colorScheme": {"id": resources["scheme.yaml"]["id"], "kind": "color-scheme", "path": "scheme.yaml"},
            "layout": {"id": resources["layout.yaml"]["id"], "kind": "layout-profile", "path": "layout.yaml"},
        }, "compatibleColorSchemes": [{"id": resources["scheme.yaml"]["id"], "kind": "color-scheme", "path": "scheme.yaml"}]},
    }
    workspace = {
        "version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "guide",
        "body": {"project": {"id": "guide", "tasks": []}, "presentation": {
            "mode": "guided", "binding": {"preset": {"id": "starter", "version": "1", "path": "preset.yaml"}}}},
    }

    normalized = normalize_authoring_workspace(
        _contract("authoring-workspace", workspace), _contract("presentation-preset", preset), resources,
    )

    assert isinstance(normalized.style, StyleContract)
    assert normalized.style.identity.id == "guide-style"
    sources = dict(normalized.draft_sources())
    assert sources["style"] == resources["style.yaml"]


def test_guided_authoring_rejects_preset_style_kind_or_id_mismatch():
    resources = {
        "view.yaml": _resource("view.yaml"),
        "theme.yaml": _resource("theme.yaml"),
        "scheme.yaml": _resource("scheme.yaml"),
        "layout.yaml": _resource("layout.yaml"),
        "style.yaml": {"version": "chrona/style/v0.2", "kind": "theme", "id": "wrong"},
    }
    preset = {
        "version": "chrona/presentation-preset/v0.1", "kind": "presentation-preset", "id": "starter",
        "body": {"package": {"version": "1"}, "resources": {
            "view": {"id": resources["view.yaml"]["id"], "kind": "view", "path": "view.yaml"},
            "style": {"id": "guide-style", "kind": "style", "path": "style.yaml"},
            "theme": {"id": resources["theme.yaml"]["id"], "kind": "theme", "path": "theme.yaml"},
            "colorScheme": {"id": resources["scheme.yaml"]["id"], "kind": "color-scheme", "path": "scheme.yaml"},
            "layout": {"id": resources["layout.yaml"]["id"], "kind": "layout-profile", "path": "layout.yaml"},
        }, "compatibleColorSchemes": [{"id": resources["scheme.yaml"]["id"], "kind": "color-scheme", "path": "scheme.yaml"}]},
    }
    workspace = {
        "version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "guide",
        "body": {"project": {"id": "guide", "tasks": []}, "presentation": {
            "mode": "guided", "binding": {"preset": {"id": "starter", "version": "1", "path": "preset.yaml"}}}},
    }

    try:
        normalize_authoring_workspace(_contract("authoring-workspace", workspace), _contract("presentation-preset", preset), resources)
    except ValueError as error:
        assert str(error).startswith("E_AUTHORING_PRESET_RESOURCE")
    else:
        raise AssertionError("wrong preset Style identity must be rejected")
