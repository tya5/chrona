from pathlib import Path

import yaml

from chrona.presentation.contracts import ClosureIdentity, StyleContract, parse_contract
from chrona.presentation.model.authoring import normalize_authoring_workspace


ROOT = Path(__file__).resolve().parents[5]


def _resource(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def _contract(kind: str, document: dict):
    return parse_contract(ClosureIdentity(kind, document["id"], "draft", "sha256:" + "a" * 64), document)


def test_guided_authoring_copies_optional_preset_style_as_typed_resource():
    resources = {
        "view.yaml": _resource("examples/aster-ssd/views/01-overview.yaml"),
        "theme.yaml": _resource("examples/aster-ssd/themes/executive-light.yaml"),
        "scheme.yaml": _resource("examples/aster-ssd/schemes/executive-light.yaml"),
        "layout.yaml": _resource("conformance/layout-profile-intent-v0.2.yaml"),
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
        "view.yaml": _resource("examples/aster-ssd/views/01-overview.yaml"),
        "theme.yaml": _resource("examples/aster-ssd/themes/executive-light.yaml"),
        "scheme.yaml": _resource("examples/aster-ssd/schemes/executive-light.yaml"),
        "layout.yaml": _resource("conformance/layout-profile-intent-v0.2.yaml"),
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
