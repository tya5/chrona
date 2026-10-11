"""Public float records and every description carry the same explicit unit."""

from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

from chrona.app.agent_tools import tool_specs


def _spec():
    return next(spec for spec in tool_specs() if spec.name == "schedule_project")


@pytest.mark.parametrize("record", [
    {"value": 0, "unit": "calendar-days", "calendar": None},
    {"value": 21, "unit": "working-days", "calendar": "office"},
])
def test_explicit_float_basis_is_admitted(record):
    schema = _spec().output_schema["properties"]["analysis"]["properties"]["totalFloat"]["additionalProperties"]
    Draft202012Validator(schema).validate(record)


@pytest.mark.parametrize("record", [
    {"value": -1, "unit": "calendar-days", "calendar": None},
    {"value": True, "unit": "calendar-days", "calendar": None},
    {"value": 1, "unit": "working-days", "calendar": None},
    {"value": 1, "unit": "calendar-days", "calendar": "office"},
    {"value": 1, "unit": "working-days", "calendar": ""},
    {"value": 1, "unit": "days", "calendar": None},
    1,
])
def test_ambiguous_or_inconsistent_float_basis_is_rejected(record):
    schema = _spec().output_schema["properties"]["analysis"]["properties"]["totalFloat"]["additionalProperties"]
    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(record)


def test_specs_guide_and_tool_description_agree_with_the_output_schema():
    root = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
    schema = _spec().output_schema["properties"]["analysis"]["properties"]["totalFloat"]["additionalProperties"]
    units = schema["properties"]["unit"]["enum"]
    paths = ("docs/specification/57-public-schedule-analysis.md",
             "docs/specification/66-agent-interface.md", "docs/guides/agent-interface.md")
    texts = [*(root.joinpath(path).read_text(encoding="utf-8") for path in paths), _spec().description]
    for text in texts:
        assert all(unit in text for unit in units)
        assert "{value, unit, calendar}" in text
        assert "totalFloat` in calendar days" not in text
