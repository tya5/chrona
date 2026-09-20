#!/usr/bin/env python3
"""Validate the M23 Review Detail Profile structure and semantic invariants."""
from copy import deepcopy
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator


DOCS = Path(__file__).resolve().parents[1]


def diagnostics(profile):
    body = profile.get("body", {})
    result = []
    groups = [entry.get("groupId") for entry in body.get("groupDetails", [])]
    if len(groups) != len(set(groups)):
        result.append("E_DETAIL_DUPLICATE_GROUP")
    observations = body.get("observations", {})
    columns = [entry.get("id") for entry in observations.get("columns", [])]
    if len(columns) != len(set(columns)):
        result.append("E_DETAIL_DUPLICATE_COLUMN")
    rows = [entry.get("id") for entry in observations.get("rows", [])]
    if len(rows) != len(set(rows)):
        result.append("E_DETAIL_DUPLICATE_ROW")
    column_set = set(columns)
    if any(set(row.get("cells", {})) != column_set for row in observations.get("rows", [])):
        result.append("E_DETAIL_OBSERVATION_CELLS")
    return tuple(result)


def main():
    schema = yaml.safe_load((DOCS / "schemas/review-detail-profile-v0.1.schema.yaml").read_text())
    fixture = yaml.safe_load((DOCS / "fixtures/review-detail-profile-v0.1.yaml").read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    validator.validate(fixture)
    assert diagnostics(fixture) == ()

    negative = []
    duplicate_group = deepcopy(fixture)
    duplicate_group["body"]["groupDetails"].append(deepcopy(duplicate_group["body"]["groupDetails"][0]))
    negative.append((duplicate_group, "E_DETAIL_DUPLICATE_GROUP"))
    duplicate_column = deepcopy(fixture)
    duplicate_column["body"]["observations"]["columns"].append(
        deepcopy(duplicate_column["body"]["observations"]["columns"][0]))
    negative.append((duplicate_column, "E_DETAIL_DUPLICATE_COLUMN"))
    duplicate_row = deepcopy(fixture)
    duplicate_row["body"]["observations"]["rows"].append(
        deepcopy(duplicate_row["body"]["observations"]["rows"][0]))
    negative.append((duplicate_row, "E_DETAIL_DUPLICATE_ROW"))
    missing_cell = deepcopy(fixture)
    del missing_cell["body"]["observations"]["rows"][0]["cells"]["status"]
    negative.append((missing_cell, "E_DETAIL_OBSERVATION_CELLS"))
    for value, expected in negative:
        validator.validate(value)
        assert expected in diagnostics(value)

    missing_source = deepcopy(fixture)
    del missing_source["body"]["observations"]["rows"][0]["source"]
    assert not validator.is_valid(missing_source)
    print("Review Detail Profile conformance: PASS (1 positive, 5 negative)")


if __name__ == "__main__":
    main()
