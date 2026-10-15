"""Project-declared object-field roles stay typed while Views bind them (#1559)."""
import pytest
from datetime import date

from chrona.presentation.contracts import ClosureIdentity, ContractError, parse_contract
from chrona.presentation.contracts.resources import FrozenDict, ProjectContract, ViewContract
from tests.support import synthetic_review as sr


def _project():
    return sr.project({"task": sr.span("task", date(2026, 2, 1), 5, owner="engineering")})


def _view(*, lanes=False):
    view = sr.bundle("executive-light")["view"]
    body = view["body"]
    body["rows"] = {"mode": "lanes"} if lanes else {"mode": "automatic"}
    body.pop("hierarchyColumn", None)
    if lanes:
        body.pop("tableColumns", None)
        body["rows"].update({"packing": ["explicit", "attached"], "laneTable": {
            "label": "group", "columns": [{"id": "Task", "source": "label"}],
        }})
    else:
        body["tableColumns"] = [
            {"id": "Task", "source": "title", "missing": "em-dash", "align": "start",
             "width": {"fr": 1}, "headerOrientation": "horizontal"},
        ]
    return view


def _parse(kind: str, value: dict):
    identity = value.get("id") or value.get("project", {}).get("id")
    return parse_contract(ClosureIdentity(kind, identity, "draft", "sha256:" + "a" * 64), value)


def test_project_roles_are_optional_closed_and_frozen():
    project = _project()
    assert isinstance(_parse("project", project), ProjectContract)

    project["fieldRoles"] = {"responsible": "owner", "phase": "phase"}
    contract = _parse("project", project)
    assert contract.field_roles == {"responsible": "owner", "phase": "phase"}
    assert isinstance(contract.field_roles, FrozenDict)
    with pytest.raises(TypeError):
        contract.field_roles["responsible"] = "late-change"
    assert contract.scheduler_input["fieldRoles"] == contract.field_roles

    project["fieldRoles"]["unlisted"] = "other"
    with pytest.raises(ContractError, match="E_RESOURCE_SCHEMA"):
        _parse("project", project)
    project["fieldRoles"] = {"responsible": "   "}
    with pytest.raises(ContractError, match="E_RESOURCE_SCHEMA"):
        _parse("project", project)


def test_view_role_grouping_columns_color_icon_and_group_presentation_are_typed():
    view = _view()
    body = view["body"]
    body["grouping"] = {
        "by": {"fieldRole": "responsible"}, "fallback": "objectType",
        "missing": "Unassigned", "presentation": "header",
        "tint": {"scale": "responsible"},
    }
    body["tableColumns"].append({
        "id": "Phase", "source": {"fieldRole": "phase"}, "missing": "em-dash",
        "align": "start", "width": "content", "headerOrientation": "horizontal",
        "transform": "initials",
    })
    body["colorEncoding"] = {
        "scale": "owner", "target": "planned", "source": {"fieldRole": "responsible"},
        "domain": "firstAppearance",
    }
    body["visuals"] = [{
        "target": {"kind": "cell", "object": "firmware", "column": "Workstream"}, "encoding": {
            "fieldRole": "phase", "domain": {"design": "material:flag-outline-rounded"},
        },
    }]

    contract = _parse("view", view)
    assert isinstance(contract, ViewContract)
    assert contract.view.grouping.by == "field"
    assert contract.view.grouping.field is None
    assert contract.view.grouping.field_role == "responsible"
    assert contract.view.grouping.fallback == "objectType"
    assert isinstance(contract.view.table_columns[-1].source, FrozenDict)
    assert contract.view.table_columns[-1].source == {"fieldRole": "phase"}
    assert isinstance(contract.view.color_encoding, FrozenDict)
    assert contract.view.color_encoding["source"] == {"fieldRole": "responsible"}
    assert isinstance(contract.view.visuals[0].encoding, FrozenDict)
    assert contract.view.visuals[0].encoding["fieldRole"] == "phase"


def test_lane_key_and_lane_table_role_references_remain_frozen():
    view = _view(lanes=True)
    view["body"]["rows"]["laneKeys"] = {"fieldRole": "responsible"}
    view["body"]["rows"]["laneTable"]["columns"] = [
        {"id": "Lane", "source": "label"},
        {"id": "Phase", "source": {"fieldRole": "phase"}, "transform": "initials"},
    ]
    contract = _parse("view", view)
    assert isinstance(contract, ViewContract)
    assert contract.view.rows.lane_keys.field is None
    assert contract.view.rows.lane_keys.field_role == "responsible"
    source = contract.view.rows.lane_table.columns[1].source
    assert isinstance(source, FrozenDict)
    assert source == {"fieldRole": "phase"}


def test_legacy_field_references_keep_their_existing_nonempty_string_grammar():
    view = _view()
    view["body"]["tableColumns"][0]["source"] = {"field": " "}
    contract = _parse("view", view)
    assert contract.view.table_columns[0].source == {"field": " "}


@pytest.mark.parametrize("change", [
    lambda body: body["grouping"].update(by={"fieldRole": "unlisted"}, fallback="none"),
    lambda body: body["grouping"].update(by={"fieldRole": "responsible"}),
    lambda body: body["grouping"].update(by={"fieldRole": "responsible"}, fallback="none",
                                         field="owner", missing="Unset"),
    lambda body: body["grouping"].update(by="field", field="owner", missing="none", fallback="none"),
    lambda body: body["tableColumns"][0].update(source={"field": "owner", "fieldRole": "phase"}),
    lambda body: body.update(colorEncoding={"scale": "x", "target": "planned",
                                           "source": {"fieldRole": "unlisted"}, "domain": "firstAppearance"}),
    lambda body: body.update(visuals=[{"target": {"kind": "mark"}, "encoding": {
        "field": "owner", "fieldRole": "phase", "domain": {"x": "material:flag-outline-rounded"}}}]),
])
def test_role_forms_reject_closed_vocabulary_and_ambiguous_or_incomplete_sources(change):
    view = _view()
    body = view["body"]
    change(body)
    with pytest.raises(ContractError, match="E_RESOURCE_SCHEMA"):
        _parse("view", view)
