"""The network View member closes only node-label authoring (#416)."""

import pytest

from chrona.presentation.contracts import ClosureIdentity, parse_contract
from chrona.presentation.contracts.resources import FrozenDict, SchemaContractError, ViewNetworkIntent
from tests.support import synthetic_review as sr


def _network_view():
    value = sr.bundle("executive-light")["view"]
    value["version"] = "chrona/view/v0.28"
    body = value["body"]
    body["surface"] = "dependency-network"
    body["rows"] = {"mode": "automatic"}
    for name in ("tableColumns", "hierarchyColumn", "backgroundDecoration", "axis", "markers",
                 "periods", "shading", "timePresentation", "annotations", "annotationPresentation",
                 "annotationBindings", "annotationPlacement"):
        body.pop(name, None)
    return value


def _parse(value):
    return parse_contract(ClosureIdentity("view", value["id"], "draft", "sha256:" + "a" * 64), value).view


def test_network_is_none_when_absent_and_title_is_the_typed_default():
    value = _network_view()
    assert _parse(value).network is None

    value["body"]["network"] = {}
    intent = _parse(value).network
    assert intent == ViewNetworkIntent("title")

    value["body"]["network"] = {"nodeLabel": {}}
    assert _parse(value).network == ViewNetworkIntent("title")


@pytest.mark.parametrize(("source", "expected"), [
    (None, None),
    ("title", "title"),
    ("id", "id"),
    ({"field": "owner"}, FrozenDict({"field": "owner"})),
    ({"fieldRole": "responsible"}, FrozenDict({"fieldRole": "responsible"})),
])
def test_network_node_label_source_is_typed_and_field_references_are_frozen(source, expected):
    value = _network_view()
    value["body"]["network"] = {"nodeLabel": {"source": source}}

    intent = _parse(value).network

    assert intent is not None
    assert intent.node_label_source == expected
    if isinstance(source, dict):
        assert isinstance(intent.node_label_source, FrozenDict)


@pytest.mark.parametrize("network", [None, {"extra": True}, {"nodeLabel": None},
                                      {"nodeLabel": {"extra": True}},
                                      {"nodeLabel": {"source": {"field": "owner", "fieldRole": "responsible"}}}])
def test_network_schema_is_closed(network):
    value = _network_view()
    value["body"]["network"] = network

    with pytest.raises(SchemaContractError):
        _parse(value)


def test_timeline_refuses_even_an_empty_network_member_at_its_pointer():
    value = sr.bundle("executive-light")["view"]
    value["version"] = "chrona/view/v0.28"
    value["body"]["network"] = {}

    with pytest.raises(SchemaContractError) as error:
        _parse(value)

    assert error.value.source_ref == "/body/network"
    assert "dependency-network" in str(error.value)
