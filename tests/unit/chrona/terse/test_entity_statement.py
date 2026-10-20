"""`entity ID "Title" PROFILE` declares a minimal entity so a terse plan can reference it (#1842 row 1, Spec 65 section 12.4)."""
from __future__ import annotations

import pytest
import yaml

from chrona.terse import compile_terse, emit_project
from chrona.usecases.project_checks import schedule_project_mapping
from chrona.usecases.terse_compile import compile_plan

REVISION = "git:0123456789abcdef0123456789abcdef01234567"
PACKAGE = {
    "version": "chrona/profile/v0.3", "packageId": "atlas-delivery",
    "requires": {"projectFormat": "timeline/v0.7"},
    "profiles": {
        "atlas.deliverable": {"extends": "entity"},
        "atlas.other": {"extends": "entity"},
        "atlas.work": {"extends": "task", "fields": {
            "deliverable": {"type": "objectReference", "targetProfiles": ["atlas.deliverable"]}}},
    },
}
HEAD = f'project atlas "Atlas" calendar standard extension atlas-delivery "atlas.yaml" {REVISION}\ncalendar standard mon-fri\n'
WORK = 'hotfix "Hotfix" task profile atlas.work 4wd from 2026-12-15 deliverable=del-portal\n'
ENTITY = 'entity del-portal "Partner portal" atlas.deliverable\n'


def _compile(text, tmp_path):
    (tmp_path / "atlas.yaml").write_text(yaml.safe_dump(PACKAGE), encoding="utf-8")
    return compile_plan(text.encode(), "plan.chrona", resource_origin=tmp_path)


def test_entity_is_emitted_between_calendars_and_objects_with_type_and_title():
    result = compile_terse("project p\ncalendar standard mon-fri\n" + ENTITY + 'a "A" task 2d\n')
    assert result.ok, result.diagnostics
    assert list(result.project) == ["version", "project", "calendars", "entities", "objects"]
    assert result.project["entities"] == {"del-portal": {"type": "atlas.deliverable", "title": "Partner portal"}}
    assert result.entity_profile_bindings == ("del-portal",) and result.profile_bindings == ()
    assert "entities:\n  del-portal:\n    type: 'atlas.deliverable'\n    title: Partner portal\nobjects:" in emit_project(result.project)


def test_source_map_ranges_cover_the_statement_profile_and_title():
    result = compile_terse("project p\n" + ENTITY + 'a "A" task 2d\n')
    line = ENTITY.rstrip("\n")
    ranges = {key: result.source_map[key].as_dict() for key in ("/entities/del-portal", "/entities/del-portal/type", "/entities/del-portal/title")}
    assert ranges["/entities/del-portal"] == {"line": 2, "column": 1, "endLine": 2, "endColumn": len(line) + 1}
    assert ranges["/entities/del-portal/type"]["column"] == line.index("atlas.deliverable") + 1
    assert ranges["/entities/del-portal/title"]["column"] == line.index('"Partner') + 1


def test_a_plan_without_entities_is_unchanged_and_emits_no_entities_section():
    result = compile_terse("project p\na task 2d\n")
    assert result.ok and "entities" not in result.project and result.entity_profile_bindings == ()


@pytest.mark.parametrize("line", ['entity task 5d', 'entity "Entity" task 5d', 'entity "Entity" gate 2026-12-01'])
def test_an_object_may_still_be_named_entity(line):
    result = compile_terse("project p\n" + line + "\n")
    assert result.ok, result.diagnostics
    assert list(result.project["objects"]) == ["entity"] and "entities" not in result.project


def _codes(text):
    result = compile_terse(text)
    assert result.project is None
    return [(item.id, item.range.line, item.range.column) for item in result.diagnostics]


@pytest.mark.parametrize("text,expected", [
    ('project p\na "A" task 2d\n' + ENTITY, [("E_TERSE_DIRECTIVE_ORDER", 3, 1)]),
    ('project p\n' + ENTITY + 'calendar standard mon-fri\n', [("E_TERSE_DIRECTIVE_ORDER", 3, 1)]),
    (ENTITY + "project p\n", [("E_TERSE_DIRECTIVE_ORDER", 1, 1)]),
    ('project p\n' + ENTITY + ENTITY, [("E_TERSE_NAME_DUPLICATE", 3, 8)]),
    ('project p\n' + ENTITY + 'del-portal "Dup" task 2d\n', [("E_TERSE_NAME_DUPLICATE", 3, 1)]),
    ('project p\nentity Del-Portal "T" atlas.x\n', [("E_TERSE_NAME_INVALID", 2, 8)]),
    ('project p\nentity d "" atlas.x\n', [("E_TERSE_TITLE_EMPTY", 2, 10)]),
    ('project p\nentity d Title atlas.x\n', [("E_TERSE_TITLE_UNQUOTED", 2, 10)]),
    ('project p\nentity d\n', [("E_TERSE_LINE_INCOMPLETE", 2, 9)]),
    ('project p\nentity d "T"\n', [("E_TERSE_LINE_INCOMPLETE", 2, 13)]),
    ('project p\nentity d "T" atlas.x extra\n', [("E_TERSE_TOKEN_UNEXPECTED", 2, 22)]),
    ('project p\n  entity d "T" atlas.x\n', [("E_TERSE_INDENT", 2, 1)]),
    ('project p\nentity d "T" atlas.x\na task 2d after d\n', [("E_TERSE_REFERENCE_UNKNOWN", 3, 17)]),
])
def test_entity_statement_errors_are_positioned(text, expected):
    assert _codes(text) == expected


def test_after_naming_an_entity_says_it_is_an_entity():
    result = compile_terse('project p\nentity d "T" atlas.x\na task 2d after d\n')
    assert "entity" in result.diagnostics[0].hint


def test_trial_12_addition_compiles_validates_and_schedules_with_a_declared_entity(tmp_path):
    result = _compile(HEAD + ENTITY + WORK, tmp_path)
    assert result.ok, [item.as_dict() for item in result.diagnostics]
    assert result.project["objects"]["hotfix"]["fields"] == {"deliverable": "del-portal"}
    assert schedule_project_mapping(result.project).ok


def test_the_same_reference_without_the_entity_still_fails_in_the_shared_validator(tmp_path):
    result = _compile(HEAD + WORK, tmp_path)
    (finding,) = result.diagnostics
    assert finding.id == "E_PROFILE_FIELD_TYPE" and finding.path == "/objects/hotfix/fields/deliverable"


def test_an_entity_of_the_wrong_profile_does_not_satisfy_the_reference(tmp_path):
    result = _compile(HEAD + 'del-portal-x "X" atlas.other\n'.replace("del-portal-x", "entity del-portal") + WORK, tmp_path)
    (finding,) = result.diagnostics
    assert finding.id == "E_PROFILE_FIELD_TYPE"


def test_unknown_entity_profile_is_positioned_on_the_profile_token(tmp_path):
    text = HEAD + 'entity del-portal "Partner portal" atlas.missing\n' + 'a "A" task 2d\n'
    result = _compile(text, tmp_path)
    (finding,) = result.diagnostics
    assert finding.id == "E_TERSE_PROFILE_UNKNOWN" and finding.path == "/entities/del-portal/type"
    line = text.splitlines()[2]
    assert (finding.range.line, finding.range.column) == (3, line.index("atlas.missing") + 1)
    assert result.yaml is None


def test_an_entity_with_no_package_is_unknown_profile_not_a_silent_open_type():
    result = compile_plan(('project p\n' + ENTITY + 'a "A" task 2d\n').encode(), "plan.chrona")
    assert [item.id for item in result.diagnostics] == ["E_TERSE_PROFILE_UNKNOWN"]


def test_compiled_bytes_are_deterministic_and_round_trip(tmp_path):
    first, second = (_compile(HEAD + ENTITY + WORK, tmp_path) for _ in range(2))
    assert first.yaml == second.yaml
    assert yaml.safe_load(first.yaml) == first.project
