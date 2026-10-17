"""Optional Style resource ingress is admitted by the live schemas."""
from copy import deepcopy

from chrona.resources import schema_validator


def _reference(kind="style"):
    return {"id": "treatment", "kind": kind, "store": {"provider": "local", "identity": "test"},
            "address": "styles/treatment.yaml", "revision": {"token": "r1"}}


def _context():
    ref = lambda identifier, kind, address: {
        "id": identifier, "kind": kind, "store": {"provider": "local", "identity": "test"},
        "address": address, "revision": {"token": "r1"},
    }
    return {
        "version": "chrona/render-context/v0.17", "kind": "render-context", "id": "context",
        "body": {
            "project": ref("project", "project", "projects/main.yaml"),
            "view": ref("view", "view", "views/main.yaml"),
            "theme": ref("theme", "theme", "themes/main.yaml"),
            "colorScheme": ref("scheme", "color-scheme", "schemes/main.yaml"),
            "layout": ref("layout", "layout-profile", "layouts/main.yaml"),
            "inputs": {},
            "environment": {"viewport": {"inlineSize": 800, "blockSize": 600}, "locale": "en-US",
                             "fontMetrics": {"algorithm": "declared-metrics-v3", "missingFont": "diagnose",
                                             "fontSet": "chrona.noto-sans"}, "scenePrecision": 3},
            "target": {"kind": "svg", "capabilities": [],
                       "visualProfile": "chrona-output/visual/v0.5-baseline"},
        },
    }


def test_render_context_accepts_optional_pinned_style_and_rejects_other_kind():
    validator = schema_validator("render-context-v0.17.schema.yaml")
    plain = _context()
    with_style = deepcopy(plain)
    with_style["body"]["style"] = _reference()

    assert validator.is_valid(plain)
    assert validator.is_valid(with_style)
    with_style["body"]["style"]["kind"] = "theme"
    assert not validator.is_valid(with_style)


def test_presentation_preset_accepts_optional_style_resource():
    validator = schema_validator("presentation-preset-v0.1.schema.yaml")
    value = {"version": "chrona/presentation-preset/v0.1", "kind": "presentation-preset", "id": "starter",
             "body": {"package": {"version": "1"}, "resources": {
                 "view": {"id": "view", "kind": "view", "path": "view.yaml"},
                 "theme": {"id": "theme", "kind": "theme", "path": "theme.yaml"},
                 "colorScheme": {"id": "scheme", "kind": "color-scheme", "path": "scheme.yaml"},
                 "layout": {"id": "layout", "kind": "layout-profile", "path": "layout.yaml"},
                 "style": {"id": "style", "kind": "style", "path": "style.yaml"}},
                 "compatibleColorSchemes": [{"id": "scheme", "kind": "color-scheme", "path": "scheme.yaml"}]}}

    assert validator.is_valid(value)
    del value["body"]["resources"]["style"]
    assert validator.is_valid(value)
    value["body"]["resources"]["style"] = {"id": "style", "kind": "style", "path": "style.yaml"}
    value["body"]["resources"]["style"]["kind"] = "theme"
    assert not validator.is_valid(value)


def test_preset_library_accepts_optional_style_member():
    validator = schema_validator("preset-library-v0.2.schema.yaml")
    value = {"version": "chrona/preset-library/v0.2", "entries": [{"id": "starter", "members": {
        "view": {"id": "view", "kind": "view", "sourceRoot": "bundles/starter", "sourcePath": "view.yaml"},
        "theme": {"id": "theme", "kind": "theme", "sourceRoot": "bundles/starter", "sourcePath": "theme.yaml"},
        "colorScheme": {"id": "scheme", "kind": "color-scheme", "sourceRoot": "bundles/starter", "sourcePath": "scheme.yaml"},
        "layout": {"id": "layout", "kind": "layout-profile", "sourceRoot": "bundles/starter", "sourcePath": "layout.yaml"},
        "style": {"id": "style", "kind": "style", "sourceRoot": "bundles/starter", "sourcePath": "style.yaml"}}}]}

    assert validator.is_valid(value)
    del value["entries"][0]["members"]["style"]
    assert validator.is_valid(value)
    value["entries"][0]["members"]["style"] = {
        "id": "style", "kind": "style", "sourceRoot": "bundles/starter", "sourcePath": "style.yaml"}
    value["entries"][0]["members"]["style"]["kind"] = "theme"
    assert not validator.is_valid(value)


def test_authoring_workspace_allows_optional_explicit_style_reference():
    validator = schema_validator("authoring-workspace-v0.1.schema.yaml")
    pin = "sha256:" + "a" * 64
    ref = lambda identifier, kind: {"id": identifier, "kind": kind, "path": f"{identifier}.yaml",
                                    "contentIdentity": pin}
    value = {"version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "workspace",
             "body": {"project": {"id": "project", "tasks": []}, "presentation": {
                 "mode": "explicit", "resources": {
                     "view": ref("view", "view"), "theme": ref("theme", "theme"),
                     "colorScheme": ref("scheme", "color-scheme"), "layout": ref("layout", "layout-profile"),
                     "renderContext": ref("context", "render-context"), "style": ref("style", "style")},
                 "receipt": ref("receipt", "presentation-materialization-receipt")}}}

    assert validator.is_valid(value)
    del value["body"]["presentation"]["resources"]["style"]
    assert validator.is_valid(value)
    value["body"]["presentation"]["resources"]["style"] = ref("style", "style")
    value["body"]["presentation"]["resources"]["style"]["kind"] = "theme"
    assert not validator.is_valid(value)
