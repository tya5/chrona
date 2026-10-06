"""#1149 Theme syntax: alignment is role-local; stacks are closed ordered role groups."""
from pathlib import Path

import pytest
import yaml

from chrona.presentation.scene.capabilities import theme_role_property_consumer
from chrona.resources import validator_for_schema


SCHEMA = yaml.safe_load((Path(__file__).resolve().parents[5] / "schemas/theme-v0.15.schema.yaml").read_text())
VALIDATOR = validator_for_schema(SCHEMA)


def _theme(*, stack=None, role_align=None):
    roles = {"planned": {"align": role_align} if role_align else {}}
    body = {"values": {"gap": {"type": "number", "value": 3}}, "roles": roles,
            "colorBindings": {"planned.fill": "accent"}}
    if stack is not None:
        body["markStack"] = stack
    return {"version": "chrona/theme/v0.15", "kind": "theme", "id": "synthetic", "body": body}


def test_theme_schema_accepts_closed_stack_and_role_alignment():
    theme = _theme(stack={"members": [["planned", "missing-actual"], ["actual"]], "gap": "gap",
                          "frame": {"roles": ["snapshot", "scenario"], "padding": "gap"}},
                   role_align="end")
    assert not tuple(VALIDATOR.iter_errors(theme))


@pytest.mark.parametrize("stack", [
    {"members": [], "gap": "gap"},
    {"members": [["not-a-mark-role"]], "gap": "gap"},
    {"members": [["planned"]], "gap": 3},
    {"members": [["planned"]], "gap": "gap", "unknown": True},
    {"members": [["planned"]], "gap": "gap", "frame": {"roles": [], "padding": "gap"}},
])
def test_theme_schema_rejects_malformed_mark_stack_shapes(stack):
    assert tuple(VALIDATOR.iter_errors(_theme(stack=stack)))


def test_alignment_is_admitted_only_for_mark_roles_with_a_consumer():
    assert theme_role_property_consumer("planned", "align") is not None
    assert theme_role_property_consumer("missing-actual", "align") is not None
    assert theme_role_property_consumer("text", "align") is None
