"""The forecast display flag is an optional, identity-bearing Context input."""
from copy import deepcopy

import pytest

from chrona.presentation.contracts import ClosureIdentity, SchemaContractError, parse_contract


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


def _identity(content_identity):
    return ClosureIdentity("render-context", "context", "r1", content_identity)


def test_forecast_defaults_false_and_explicit_false_remains_identity_bearing():
    omitted = _context()
    explicit_false = deepcopy(omitted)
    explicit_false["body"]["forecast"] = False

    default_contract = parse_contract(_identity("sha256:" + "a" * 64), omitted)
    explicit_contract = parse_contract(_identity("sha256:" + "b" * 64), explicit_false)

    assert default_contract.forecast is False
    assert explicit_contract.forecast is False
    assert "forecast" not in omitted["body"]
    assert explicit_false["body"]["forecast"] is False
    assert default_contract.identity.content_identity != explicit_contract.identity.content_identity


def test_forecast_true_is_admitted_without_a_context_version_change():
    value = _context()
    value["body"]["forecast"] = True

    contract = parse_contract(_identity("sha256:" + "c" * 64), value)

    assert contract.version == "chrona/render-context/v0.17"
    assert contract.forecast is True


@pytest.mark.parametrize("invalid", [None, 0, "true", []])
def test_forecast_requires_a_boolean(invalid):
    value = _context()
    value["body"]["forecast"] = invalid

    with pytest.raises(SchemaContractError):
        parse_contract(_identity("sha256:" + "d" * 64), value)
