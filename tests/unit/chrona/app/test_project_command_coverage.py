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
}
NOT_COVERED = {
    "version": "the format tag is a constant; create_project writes it and no edit may change it",
    "periods": "the skill does not teach periods; named date ranges are written with the file, a command type is a later additive item",
    "scenarios": "the skill does not teach scenarios; overlays reference objects by id and are authored with the file",
    "extensions": "package references are pinned revision and content identities resolved from files; an agent cannot compute them through a member command",
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


# The skill (references/*.md) shows this uncovered member; the reason above must therefore stay a deliberate one.
TAUGHT_BUT_NOT_COVERED = {"extensions"}


def test_an_uncovered_member_is_taught_by_the_skill_only_when_that_is_declared():
    from chrona.resources import skill_resource

    root = skill_resource()
    pages = [root.joinpath("SKILL.md"), *(page for page in root.joinpath("references").iterdir() if page.name.endswith(".md"))]
    text = "\n".join(page.read_text(encoding="utf-8") for page in pages)
    for member in set(NOT_COVERED) - {"version"}:
        shown = f"\n{member}:" in text or f"\n  {member}:" in text
        assert shown == (member in TAUGHT_BUT_NOT_COVERED), (
            f"the skill {'shows' if shown else 'no longer shows'} a {member} member: give it a command type or update TAUGHT_BUT_NOT_COVERED")
