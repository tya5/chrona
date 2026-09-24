from pathlib import Path

import pytest
import yaml

from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract
from chrona.presentation.model.authoring import AuthoringError, normalize_authoring_workspace


ROOT = Path(__file__).resolve().parents[5]


def _resource(path: str) -> dict:
    return yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))


def _preset(resources: dict) -> dict:
    return {
        "version": "chrona/presentation-preset/v0.1", "kind": "presentation-preset", "id": "plan-actual",
        "body": {"package": {"version": "1"}, "resources": {
            "view": {"id": resources["views/review.yaml"]["id"], "kind": "view", "path": "views/review.yaml"},
            "theme": {"id": resources["themes/theme.yaml"]["id"], "kind": "theme", "path": "themes/theme.yaml"},
            "colorScheme": {"id": resources["schemes/scheme.yaml"]["id"], "kind": "color-scheme", "path": "schemes/scheme.yaml"},
            "layout": {"id": resources["layouts/layout.yaml"]["id"], "kind": "layout-profile", "path": "layouts/layout.yaml"},
        }, "compatibleColorSchemes": [{"id": resources["schemes/scheme.yaml"]["id"], "kind": "color-scheme", "path": "schemes/scheme.yaml"}]},
    }


def _workspace() -> dict:
    return {
        "version": "chrona/authoring-workspace/v0.1", "kind": "authoring-workspace", "id": "controller",
        "body": {"project": {"id": "controller", "title": "Controller", "tasks": [{
            "id": "firmware", "title": "Firmware", "planned": {"start": "2026-04-01", "finish": "2026-04-10"},
        }]}, "actuals": [{"taskId": "firmware", "actual": {"start": "2026-04-02", "finish": "2026-04-12"}, "progress": 0.5}],
        "presentation": {"mode": "guided", "binding": {"preset": {"id": "plan-actual", "version": "1", "path": "presets/plan-actual.yaml"},
        "overrides": {"view": {"window": {"start": "2026-04-01", "end": "2026-04-30"}, "visibility": {"relations": "none"}}}}}},
    }


def _resources() -> dict:
    return {
        "views/review.yaml": _resource("examples/aster-ssd/views/01-overview.yaml"),
        "themes/theme.yaml": _resource("examples/aster-ssd/themes/executive-light.yaml"),
        "schemes/scheme.yaml": _resource("examples/aster-ssd/schemes/executive-light.yaml"),
        "layouts/layout.yaml": _resource("examples/halcyon-1/layouts/wallboard.yaml"),
    }


def _contract(kind: str, document: dict):
    return parse_contract(ClosureIdentity(kind, document["id"], "draft", "sha256:" + "a" * 64), document)


def test_workspace_normalizes_to_existing_typed_contracts_only():
    resources = _resources()
    result = normalize_authoring_workspace(_contract("authoring-workspace", _workspace()), _contract("presentation-preset", _preset(resources)), resources)

    assert result.project.scheduler_input["project"]["id"] == "controller"
    assert result.project.scheduler_input["objects"]["firmware"]["schedule"]["start"] == "2026-04-01"
    assert result.actual_set is not None
    assert result.actual_set.observations_input["body"]["observations"][0]["projectObjectId"] == "firmware"
    assert result.view.view.window.mode == "explicit"
    assert result.view.view.visibility.relations == "none"


def test_workspace_rejects_duplicate_task_and_unknown_actual_task():
    document = _workspace()
    document["body"]["project"]["tasks"].append(document["body"]["project"]["tasks"][0].copy())
    with pytest.raises(ContractError, match="E_AUTHORING_TASK_ID"):
        _contract("authoring-workspace", document)

    document = _workspace()
    document["body"]["actuals"][0]["taskId"] = "missing"
    with pytest.raises(ContractError, match="E_AUTHORING_ACTUAL_TASK"):
        _contract("authoring-workspace", document)


def test_workspace_rejects_scheme_not_declared_by_preset():
    resources = _resources()
    document = _workspace()
    document["body"]["presentation"]["binding"]["overrides"] = {"theme": {"colorScheme": "not-admitted"}}
    with pytest.raises(AuthoringError, match="E_AUTHORING_COLOR_SCHEME"):
        normalize_authoring_workspace(_contract("authoring-workspace", document), _contract("presentation-preset", _preset(resources)), resources)


def test_workspace_schema_rejects_geometry_override():
    document = _workspace()
    document["body"]["presentation"]["binding"]["overrides"]["view"]["offset"] = {"x": 1}
    with pytest.raises(ContractError, match="E_RESOURCE_SCHEMA"):
        _contract("authoring-workspace", document)


def test_explicit_workspace_has_no_binding_and_bypasses_guided_normalization():
    document = _workspace()
    digest = "sha256:" + "a" * 64
    document["body"]["presentation"] = {"mode": "explicit", "resources": {
        name: {"id": name, "kind": name, "path": f"presentation/{name}.yaml", "contentIdentity": digest}
        for name in ("view", "theme", "colorScheme", "layout", "renderContext")
    }, "receipt": {"id": "receipt", "kind": "presentation-materialization-receipt", "path": "presentation/receipt.yaml", "contentIdentity": digest}}
    workspace = _contract("authoring-workspace", document)
    assert workspace.mode == "explicit"
    assert workspace.binding is None
    with pytest.raises(AuthoringError, match="E_AUTHORING_EXPLICIT_MODE"):
        normalize_authoring_workspace(workspace, _contract("presentation-preset", _preset(_resources())), _resources())
