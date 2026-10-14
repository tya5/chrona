"""#1134: the Theme schema shape of `contrastPolicy.exceptions`."""
from pathlib import Path

import pytest
import yaml

from chrona.resources import validator_for_schema

SCHEMA = yaml.safe_load((Path(__file__).resolve().parents[5] / "schemas/theme-v0.15.schema.yaml").read_text())
VALIDATOR = validator_for_schema(SCHEMA)
ENTRY = {"purpose": "as-of-label", "over": "as-of-label-chip", "minimum": 3.5, "reason": "Owner-approved white on amber"}


def _theme(policy):
    body = {"values": {}, "roles": {"planned": {}}, "colorBindings": {"planned.fill": "accent"}}
    if policy is not None:
        body["contrastPolicy"] = policy
    return {"version": "chrona/theme/v0.15", "kind": "theme", "id": "synthetic", "body": body}


@pytest.mark.parametrize("policy", [None, {"mark": "error"}, {"groundText": "error", "exceptions": [ENTRY]},
                                    {"exceptions": [{**{k: v for k, v in ENTRY.items() if k != "purpose"}, "role": "actual"}]}])
def test_valid_policies_and_absent_exceptions_are_accepted(policy):
    assert not tuple(VALIDATOR.iter_errors(_theme(policy)))


def _without(key):
    return {k: v for k, v in ENTRY.items() if k != key}


@pytest.mark.parametrize("entry, pointer", [
    (_without("minimum"), "/body/contrastPolicy/exceptions/0"),
    (_without("reason"), "/body/contrastPolicy/exceptions/0"),
    (_without("over"), "/body/contrastPolicy/exceptions/0"),
    (_without("purpose"), "/body/contrastPolicy/exceptions/0"),
    ({**ENTRY, "role": "text"}, "/body/contrastPolicy/exceptions/0"),
    ({**ENTRY, "reason": ""}, "/body/contrastPolicy/exceptions/0/reason"),
    ({**ENTRY, "minimum": 0}, "/body/contrastPolicy/exceptions/0/minimum"),
    ({**ENTRY, "floor": 3}, "/body/contrastPolicy/exceptions/0")])
def test_a_malformed_entry_is_refused_at_its_pointer(entry, pointer):
    errors = list(VALIDATOR.iter_errors(_theme({"exceptions": [entry]})))
    assert errors and all("/" + "/".join(str(p) for p in e.absolute_path) == pointer for e in errors[:1])


def test_an_empty_list_is_refused():
    assert tuple(VALIDATOR.iter_errors(_theme({"exceptions": []})))
