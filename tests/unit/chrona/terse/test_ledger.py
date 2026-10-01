"""The ledger test (design 5.3): every authorable Project property is decided, mapped or yaml-only (#148).

A property added to `schemas/project-v0.7.schema.yaml` fails this test until someone classifies it in
`chrona.terse.ledger`. The decision is forced, not the construct.
"""
from __future__ import annotations

import copy
from typing import Any

from chrona.resources import schema_document
from chrona.terse.ledger import LEDGER, MAPPED, YAML_ONLY


def _resolve(node: dict[str, Any], defs: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in node and node["$ref"].startswith("#/$defs/"):
        node = defs[node["$ref"].removeprefix("#/$defs/")]
    return node


def _walk(node: dict[str, Any], prefix: str, defs: dict[str, Any], stop: frozenset[str], found: set[str]) -> None:
    """Add `prefix.property` for every property of an object schema, recursing into nested objects, items and unions."""
    node = _resolve(node, defs)
    branches = [node] + [_resolve(branch, defs) for branch in node.get("oneOf", [])]
    for branch in branches:
        for key, value in branch.get("properties", {}).items():
            path = f"{prefix}.{key}"
            found.add(path)
            if path in stop:
                continue
            nested = _resolve(value, defs)
            if "items" in nested:
                _walk(nested["items"], path, defs, stop, found)
            _walk(value, path, defs, stop, found)


def authorable_paths(schema: dict[str, Any]) -> set[str]:
    defs = schema["$defs"]
    found = {f"top.{key}" for key in schema["properties"]}
    _walk(schema["properties"]["project"], "project", defs, frozenset(), found)
    _walk(defs["calendar"], "calendar", defs, frozenset(), found)
    _walk(defs["object"], "object", defs, frozenset({"object.schedule"}), found)
    for branch in defs["schedule"]["oneOf"]:
        form = _resolve(branch, defs)["properties"]["mode"]["const"]
        _walk(branch, f"schedule.{form}", defs, frozenset({"schedule.scheduled.constraints"}), found)
    _walk(defs["constraints"], "constraints", defs, frozenset(), found)
    _walk(defs["relation"], "relation", defs, frozenset(), found)
    return found


def _live_schema() -> dict[str, Any]:
    return schema_document("project-v0.7.schema.yaml")


def test_every_authorable_property_is_classified_and_no_entry_is_stale():
    paths = authorable_paths(_live_schema())
    assert paths - set(LEDGER) == set(), "unclassified Project properties: decide mapped or yaml-only in chrona/terse/ledger.py"
    assert set(LEDGER) - paths == set(), "ledger entries for properties that no longer exist"


def test_every_entry_is_mapped_or_yaml_only_with_a_reason():
    for path, (classification, reason) in LEDGER.items():
        assert classification in {MAPPED, YAML_ONLY} and reason.strip(), path


def test_the_scope_rule_keeps_free_maps_and_other_sections_out_of_the_grammar():
    for path in ("object.fields", "top.entities", "top.annotations", "top.scenarios", "top.extensions", "object.link", "object.wbsCode",
                 "object.deadline", "object.plannedProgress", "object.attachesTo", "calendar.fiscalStartMonth"):
        assert LEDGER[path][0] == YAML_ONLY, path
    for path in ("project.id", "object.type", "object.parent", "object.schedule", "relation.lag.calendar", "calendar.exceptions.working"):
        assert LEDGER[path][0] == MAPPED, path


def test_a_property_added_to_the_schema_turns_the_ledger_test_red():
    schema = copy.deepcopy(_live_schema())
    schema["$defs"]["object"]["properties"]["costCode"] = {"type": "string"}
    schema["$defs"]["relation"]["properties"]["rationale"] = {"type": "string"}
    schema["$defs"]["scheduled"]["properties"]["buffer"] = {"type": "string"}
    schema["properties"]["risks"] = {"type": "object"}
    schema["$defs"]["bounds"]["properties"]["target"] = {"type": "string"}
    assert authorable_paths(schema) - set(LEDGER) == {
        "object.costCode", "relation.rationale", "schedule.scheduled.buffer", "top.risks", "constraints.start.target", "constraints.end.target",
        "schedule.scheduled-point.constraints.at.target"}
