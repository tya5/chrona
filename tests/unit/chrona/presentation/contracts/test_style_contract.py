"""Style ingress admits one typed contract; rule evaluation is a later owner."""
from copy import deepcopy
from datetime import date

import pytest

from chrona.presentation.contracts import (
    ClosureIdentity, ContractError, SchemaContractError, StyleContract, parse_contract,
)
from chrona.presentation.style import StyleEncodingOutcome, StyleRoleOutcome
from chrona.resources import safe_load


def _document():
    return {"version": "chrona/style/v0.2", "kind": "style", "id": "treatment",
            "body": {"rules": [{"id": "critical", "when": {"roles": ["critical"]},
                                 "then": {"role": "emphasis"}}]}}


def _parse(value):
    return parse_contract(ClosureIdentity("style", "treatment", "r1", "sha256:" + "a" * 64), value)


def test_style_is_a_schema_registered_detached_typed_contract():
    value = _document()
    contract = _parse(value)
    value["body"]["rules"][0]["when"]["roles"].append("planned")
    assert isinstance(contract, StyleContract)
    assert contract.rules[0].selector.roles == ("critical",)
    assert contract.rules[0].outcome == StyleRoleOutcome("emphasis")


def test_empty_style_has_no_implicit_assignment():
    value = _document()
    value["body"]["rules"] = []
    assert _parse(value).rules == ()


def test_scoped_fill_retains_author_title_and_opt_in_scope_qualifier():
    value = _document()
    value["body"]["rules"][0] = {
        "id": "risk", "when": {"purpose": "planned", "roles": ["critical"]},
        "then": {"encode": {"channel": "fill", "source": {"field": "risk"},
                            "scale": "risk", "domain": ["low", "high"],
                            "legend": {"title": "Critical risk", "showScope": True}}},
    }
    outcome = _parse(value).rules[0].outcome
    assert isinstance(outcome, StyleEncodingOutcome)
    assert outcome.legend.title == "Critical risk"
    assert outcome.legend.show_scope is True


def test_unquoted_yaml_date_field_literal_matches_quoted_iso_scalar():
    unquoted = safe_load(b"""
version: chrona/style/v0.2
kind: style
id: treatment
body:
  rules:
    - id: date
      when:
        fields:
          - source: {field: dueDate}
            equals: 2026-02-01
      then: {role: emphasis}
""")
    quoted = deepcopy(unquoted)
    quoted["body"]["rules"][0]["when"]["fields"][0]["equals"] = "2026-02-01"

    assert unquoted["body"]["rules"][0]["when"]["fields"][0]["equals"] == date(2026, 2, 1)
    assert _parse(unquoted).rules[0].selector.fields[0].equals == "2026-02-01"
    assert _parse(unquoted).rules == _parse(quoted).rules


@pytest.mark.parametrize("selector", [{"facet": "planned"}, {"sourceType": "span"},
                                      {"relationKind": "FS"}, {"roles": ["unknown"]},
                                      {"columnSource": "finishDelta"}, {}])
def test_initial_selector_vocabulary_is_closed(selector):
    value = _document()
    value["body"]["rules"][0]["when"] = selector
    with pytest.raises(SchemaContractError):
        _parse(value)


def test_rule_cannot_assign_both_role_and_encoding_in_one_outcome():
    value = _document()
    value["body"]["rules"][0]["then"]["encode"] = {
        "channel": "fill", "source": {"field": "risk"}, "scale": "risk", "domain": ["low"]}
    with pytest.raises(SchemaContractError):
        _parse(value)


def test_duplicate_rule_failure_crosses_contract_boundary_with_pointer():
    value = _document()
    value["body"]["rules"].append(deepcopy(value["body"]["rules"][0]))
    with pytest.raises(ContractError) as error:
        _parse(value)
    assert error.value.diagnostic_id == "E_STYLE_RULE_ID_DUPLICATE"
    assert error.value.source_ref == "/body/rules/1/id"


def test_scoped_title_failure_crosses_contract_boundary_with_pointer():
    value = _document()
    value["body"]["rules"][0]["then"] = {"encode": {
        "channel": "fill", "source": {"field": "risk"}, "scale": "risk", "domain": ["low"]}}
    with pytest.raises(ContractError) as error:
        _parse(value)
    assert error.value.diagnostic_id == "E_STYLE_LEGEND_TITLE_REQUIRED"
    assert error.value.source_ref == "/body/rules/0/then/encode/legend/title"
