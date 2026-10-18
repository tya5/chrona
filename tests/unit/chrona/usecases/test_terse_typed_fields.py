"""Inline typed fields use the same package rules and source map as YAML."""
from __future__ import annotations

import pytest
import yaml

from chrona.usecases.terse_compile import compile_plan
from chrona.usecases.project_checks import schedule_project_mapping

REVISION = "git:" + "0123456789abcdef" * 2 + "01234567"
PACKAGE = {
    "version": "chrona/profile/v0.3", "packageId": "team-delivery",
    "requires": {"projectFormat": "timeline/v0.7"},
    "profiles": {"work": {"extends": "task", "fields": {
        "risk": {"type": "enum", "enumValues": ["low", "high"], "required": True},
        "count": {"type": "integer"}, "note": {"type": "string"},
    }}},
}


def _plan(fields="risk=high", *, profile="work", path="team.yaml", revision=REVISION):
    return (f'project demo extension team-delivery "{path}" {revision}\n'
            f'build "Build" task profile {profile} 2026-11-02..2026-11-09 {fields}\n').encode()


def _package(root, package=PACKAGE, name="team.yaml"):
    data = yaml.safe_dump(package).encode()
    (root / name).write_bytes(data)
    return data


def test_valid_typed_fields_retain_exact_package_bytes(tmp_path):
    content = _package(tmp_path)
    result = compile_plan(_plan(), "plan.chrona", resource_origin=tmp_path)
    assert result.ok, result.diagnostics
    assert result.project["objects"]["build"]["fields"] == {"risk": "high"}
    assert result.project["objects"]["build"]["type"] == "work"
    assert result.extension_snapshots[0].content == content
    assert result.extension_snapshots[0].path == "team.yaml"
    assert yaml.safe_load(result.yaml) == result.project


@pytest.mark.parametrize("fields,code,key", [
    ("risk=high extra=oops", "E_PROFILE_FIELD_UNKNOWN", "extra"),
    ("risk=high count=oops", "E_PROFILE_FIELD_TYPE", "count"),
    ("risk=extreme", "E_PROFILE_FIELD_ENUM", "risk"),
])
def test_field_rejections_are_positioned_on_the_complete_assignment(tmp_path, fields, code, key):
    _package(tmp_path)
    data = _plan(fields)
    result = compile_plan(data, "plan.chrona", resource_origin=tmp_path)
    assert result.yaml is None and result.project is None
    (finding,) = result.diagnostics
    assert finding.id == code and finding.path == f"/objects/build/fields/{key}"
    assignment = next(word for word in fields.split() if word.startswith(key + "="))
    line = data.decode().splitlines()[1]
    assert finding.range.as_dict() == {"line": 2, "column": line.index(assignment) + 1,
                                      "endLine": 2, "endColumn": line.index(assignment) + len(assignment) + 1}


def test_unknown_explicit_profile_is_positioned_even_without_fields(tmp_path):
    _package(tmp_path)
    result = compile_plan(_plan("", profile="missing"), "plan.chrona", resource_origin=tmp_path)
    (finding,) = result.diagnostics
    assert finding.id == "E_TERSE_PROFILE_UNKNOWN"
    assert finding.path == "/objects/build/type" and finding.range.line == 2
    assert result.yaml is None


def test_required_field_points_to_the_profile_context(tmp_path):
    _package(tmp_path)
    result = compile_plan(_plan(""), resource_origin=tmp_path)
    (finding,) = result.diagnostics
    assert finding.id == "E_PROFILE_FIELD_REQUIRED" and finding.range.line == 2


@pytest.mark.parametrize("path,revision", [("../outside.yaml", REVISION), ("team.yaml", "main")])
def test_authored_extension_schema_errors_are_not_compiler_defects(tmp_path, path, revision):
    _package(tmp_path)
    result = compile_plan(_plan(path=path, revision=revision), "plan.chrona", resource_origin=tmp_path)
    assert not result.ok and not result.defect
    assert all(item.id == "E_SCHEMA" and item.range.line == 1 for item in result.diagnostics)


def test_missing_resource_origin_never_reads_the_working_directory(tmp_path, monkeypatch):
    _package(tmp_path)
    monkeypatch.chdir(tmp_path)
    result = compile_plan(_plan(), "plan.chrona")
    assert [item.id for item in result.diagnostics] == ["E_EXTENSION_UNRESOLVED"]
    assert result.yaml is None


def test_invalid_package_does_not_cascade_unknown_profile(tmp_path):
    _package(tmp_path, {"invalid": True})
    result = compile_plan(_plan(profile="missing"), resource_origin=tmp_path)
    assert [item.id for item in result.diagnostics] == ["E_PROFILE_PACKAGE_INVALID"]


def test_ambiguous_package_does_not_cascade_unknown_profile(tmp_path):
    _package(tmp_path)
    second = {**PACKAGE, "packageId": "other-delivery"}
    _package(tmp_path, second, "other.yaml")
    data = _plan().replace(b"\nbuild", f' extension other-delivery "other.yaml" {REVISION}\nbuild'.encode())
    result = compile_plan(data, resource_origin=tmp_path)
    assert [item.id for item in result.diagnostics] == ["E_PROFILE_ID_DUPLICATE"]


def test_explicit_group_profile_retains_rollup_and_parent_semantics(tmp_path):
    package = {**PACKAGE, "profiles": {**PACKAGE["profiles"], "phase": {"extends": "group", "fields": {}}}}
    _package(tmp_path, package)
    data = (f'project demo extension team-delivery "team.yaml" {REVISION}\n'
            'phase group profile phase\n'
            '  child task profile work 2026-11-02..2026-11-09 risk=high\n').encode()
    result = compile_plan(data, resource_origin=tmp_path)
    assert result.ok, result.diagnostics
    assert result.project["objects"]["phase"]["schedule"] == {"mode": "rollup"}
    assert result.project["objects"]["child"]["parent"] == "phase"
    schedule = schedule_project_mapping(result.project, base_dir=tmp_path)
    assert schedule.ok, schedule.diagnostics
    assert schedule.placements["phase"] == schedule.placements["child"]
