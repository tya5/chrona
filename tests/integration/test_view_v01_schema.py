from datetime import date
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import jsonschema
import pytest
import yaml

from chrona.resources import schema_resource


ROOT = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def _json_value(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    return value


def _validator() -> jsonschema.Draft202012Validator:
    schema = yaml.safe_load(schema_resource("view-v0.9.schema.yaml").read_text(encoding="utf-8"))
    foundation = yaml.safe_load(schema_resource("presentation-resource-v0.1.schema.yaml").read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(
        schema, resolver=jsonschema.RefResolver.from_schema(schema, store={foundation["$id"]: foundation})
    )


@pytest.mark.parametrize("path", sorted(ROOT.glob("examples/**/views/*.yaml")))
def test_declared_public_v03_view_validates(path: Path):
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if value.get("version") != "chrona/view/v0.9":
        pytest.skip("not a v0.3 View")
    assert next(_validator().iter_errors(_json_value(value)), None) is None, path


def test_v03_relation_visibility_object_rejects_unsupported_policy():
    value = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    value["body"]["visibility"]["relations"] = {"mode": "all", "overflow": "truncate"}
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_v04_rejects_unimplemented_relation_fallback_contract():
    value = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    value["body"]["visibility"]["fallback"] = {"relations": ["above", "suppress"]}
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_view_admits_inside_at_each_member_label_side_ingress():
    value = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    value["body"]["visibility"]["labels"] = {
        "placement": "plot", "content": ["title"], "side": "inside", "overflow": "suppress",
    }
    value["body"]["visibility"]["fallback"] = {"labels": ["inside", "end", "suppress"]}
    assert next(_validator().iter_errors(_json_value(value)), None) is None
    schema = yaml.safe_load(schema_resource("view-v0.9.schema.yaml").read_text(encoding="utf-8"))
    assert "inside" in schema["$defs"]["presentationIntent"]["properties"]["label"]["properties"]["side"]["enum"]


def test_v07_scenario_table_source_is_closed_to_id_or_title():
    value = yaml.safe_load((ROOT / "examples/halcyon-1/views/02-programme-board.yaml").read_text(encoding="utf-8"))
    value["body"]["tableColumns"][0]["source"] = {"scenario": "title"}
    assert next(_validator().iter_errors(_json_value(value)), None) is None
    value["body"]["tableColumns"][0]["source"] = {"scenario": "unknown"}
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


@pytest.mark.parametrize("key", ("entityIds", "profiles"))
def test_v03_selection_rejects_undefined_capability(key: str):
    value = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    value["body"]["selection"]["include"][key] = ["undefined"]
    assert next(_validator().iter_errors(_json_value(value)), None) is not None


def test_dependency_network_keeps_common_window_and_rejects_timeline_authoring():
    value = yaml.safe_load((ROOT / "examples/aster-ssd/views/01-overview.yaml").read_text(encoding="utf-8"))
    body = value["body"]
    body["surface"] = "dependency-network"
    forbidden = ("tableColumns", "axis", "markers", "shading", "timePresentation", "annotations", "annotationPresentation")
    saved = {name: body.pop(name) for name in forbidden if name in body}
    assert "window" in body
    assert next(_validator().iter_errors(_json_value(value)), None) is None
    for name, item in saved.items():
        candidate = deepcopy(value)
        candidate["body"][name] = item
        assert next(_validator().iter_errors(_json_value(candidate)), None) is not None, name
