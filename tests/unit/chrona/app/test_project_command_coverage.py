"""Every top-level Project member has a project-command type, or a reason it has none (#1892 row 1, item 3)."""
from __future__ import annotations

from chrona.resources import safe_load, schema_validator

COMMANDS = {
    "project": ("setProjectMeta",),
    "calendars": ("setCalendar", "removeCalendar"),
    "entities": ("setEntity", "removeEntity"),
    "objects": ("setObject", "removeObject"),
    "relations": ("setRelation", "removeRelation"),
    "fieldRoles": ("setFieldRole", "removeFieldRole"),
    "annotations": ("setAnnotation", "removeAnnotation"),
    "periods": ("setPeriod", "removePeriod"),
    "scenarios": ("setScenario", "removeScenario"),
    "extensions": ("setExtension", "removeExtension"),
}
NOT_COVERED = {
    "version": "the format tag is a constant; create_project writes it and no edit may change it",
}


def _members() -> set[str]:
    return set(schema_validator("project-v0.7.schema.yaml").schema["properties"])


def _command_types() -> set[str]:
    return set(schema_validator("project-command-v0.1.schema.yaml").schema["properties"]["type"]["enum"])


def test_every_project_member_has_a_command_type_or_a_stated_reason():
    members = _members()
    assert members == set(COMMANDS) | set(NOT_COVERED), (
        "a Project schema member is neither covered by a command type nor listed with a reason: "
        f"{sorted(members - set(COMMANDS) - set(NOT_COVERED))}; stale entries: {sorted((set(COMMANDS) | set(NOT_COVERED)) - members)}")
    assert not set(COMMANDS) & set(NOT_COVERED)
    assert all(reason.strip() for reason in NOT_COVERED.values())


def test_every_listed_command_type_exists_and_every_type_is_listed():
    listed = {name for names in COMMANDS.values() for name in names}
    assert listed == _command_types()
