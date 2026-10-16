"""The prior Scene is an identity-pinned artifact, not a semantic resource."""
from dataclasses import fields

import pytest

from chrona.presentation.contracts import ArtifactPin, ClosureIdentity, SchemaContractError, parse_contract


def _context():
    store = {"provider": "local", "identity": "test-store"}
    ref = lambda identifier, kind, address: {
        "id": identifier, "kind": kind, "store": store, "address": address,
        "revision": {"token": "r1"},
    }
    return {
        "version": "chrona/render-context/v0.17", "kind": "render-context", "id": "context",
        "body": {
            "project": ref("project", "project", "projects/current.yaml"),
            "view": ref("view", "view", "views/current.yaml"),
            "theme": ref("theme", "theme", "themes/current.yaml"),
            "colorScheme": ref("scheme", "color-scheme", "schemes/current.yaml"),
            "layout": ref("layout", "layout-profile", "layouts/current.yaml"),
            "inputs": {},
            "environment": {
                "viewport": {"inlineSize": 800, "blockSize": 600},
                "locale": "en-US",
                "fontMetrics": {"algorithm": "declared-metrics-v3", "missingFont": "diagnose",
                                "fontSet": "chrona.noto-sans"},
                "scenePrecision": 3,
            },
            "target": {"kind": "svg", "capabilities": [],
                       "visualProfile": "chrona-output/visual/v0.5-baseline"},
        },
    }


def _identity(value):
    return ClosureIdentity("render-context", value["id"], "r1", "sha256:" + "b" * 64)


def _pin():
    return {"store": {"provider": "local", "identity": "scene-store"},
            "address": "scenes/previous.json", "revision": {"token": "scene-r1"},
            "contentIdentity": "sha256:" + "a" * 64}


def test_context_optional_previous_scene_decodes_to_neutral_artifact_pin():
    value = _context()
    assert parse_contract(_identity(value), value).previous_scene is None
    value["body"]["inputs"]["previousScene"] = _pin()

    context = parse_contract(_identity(value), value)

    assert context.previous_scene == ArtifactPin(
        value["body"]["inputs"]["previousScene"]["store"], "scenes/previous.json", "scene-r1",
        "sha256:" + "a" * 64,
    )
    assert tuple(field.name for field in fields(ArtifactPin)) == (
        "store", "address", "revision_token", "content_identity")
    assert not hasattr(context.previous_scene, "id")
    assert not hasattr(context.previous_scene, "kind")


@pytest.mark.parametrize("mutation", ["id", "kind", "bad-hash", "unsafe-address"])
def test_context_rejects_scene_pin_resource_identity_or_unpinned_bytes(mutation):
    value = _context()
    pin = _pin()
    if mutation == "id":
        pin["id"] = "invented-scene-resource"
    elif mutation == "kind":
        pin["kind"] = "scene"
    elif mutation == "bad-hash":
        pin["contentIdentity"] = "sha256:not-a-digest"
    else:
        pin["address"] = "../outside.json"
    value["body"]["inputs"]["previousScene"] = pin

    with pytest.raises(SchemaContractError):
        parse_contract(_identity(value), value)


def test_context_accepts_a_scene_pin_without_a_content_identity():
    value = _context()
    pin = _pin()
    del pin["contentIdentity"]
    value["body"]["inputs"]["previousScene"] = pin

    context = parse_contract(_identity(value), value)

    assert context.previous_scene.content_identity is None
    assert "contentIdentity" not in context.previous_scene.as_reader_reference()
