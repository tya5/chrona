"""First-hour CLI defects (#1585): import validation, calendar hint, cycle names, undrawn snapshot, preset descriptions, --role."""
from __future__ import annotations

import re
import subprocess
import sys

import pytest
import yaml

from chrona.resources import schema_document
from chrona.core.source_ranges import locate
from chrona.usecases.draft_render import DraftRenderRequest, render_draft
from chrona.usecases.preset_library import PRESET_DESCRIPTIONS, _library, _read_member, list_builtin_presets
from chrona.usecases.project_checks import validate_project_file
from chrona.usecases.table_import import import_table

CALENDAR = ["standard mon-fri"]
CYCLE = ("id,title,type,start,duration,predecessors\n"
         "auth,Auth,task,2027-03-01,5wd,payments\n"
         "payments,Payments,task,,5wd,auth\n")


def _codes(result):
    return [item.code for item in result.diagnostics]


def test_import_rejects_a_dependency_cycle_at_the_predecessors_cell_naming_the_relation_by_ids():
    result = import_table(CYCLE, project_id="p", calendars=CALENDAR)

    assert not result.ok and _codes(result) == ["E_UNSUPPORTED_CYCLE"]
    found = result.diagnostics[0]
    assert (found.row, found.column, found.header) == (3, 6, "predecessors")
    record = found.as_dict()
    assert record["sourceRef"] == "/relations/auth -> payments"
    assert record["cell"] == {"row": 3, "column": 6, "header": "predecessors"}
    assert "predecessors of `payments`" in record["hint"]


def test_validate_names_the_cycle_relation_by_object_ids_and_still_finds_its_line(tmp_path):
    table = import_table(CYCLE.replace(",payments\n", ",\n"), project_id="p", calendars=CALENDAR)
    project = yaml.safe_load(table.project_yaml)
    project["relations"] = [
        {"id": "r1", "type": "dependency", "from": {"object": "payments", "endpoint": "end"}, "to": {"object": "auth", "endpoint": "start"}, "lag": "0d"},
        {"id": "r2", "type": "dependency", "from": {"object": "auth", "endpoint": "end"}, "to": {"object": "payments", "endpoint": "start"}, "lag": "0d"}]
    path = tmp_path / "cycle.yaml"
    path.write_text(yaml.safe_dump(project, sort_keys=False), encoding="utf-8")

    found = validate_project_file(path).diagnostics

    assert [item.path for item in found] == ["/relations/auth -> payments"]
    assert found[0].source_range is not None
    line = path.read_text(encoding="utf-8").splitlines()[found[0].source_range["line"] - 1]
    assert "id: r2" in line


def test_locate_resolves_a_relation_reference_by_ids_to_its_entry():
    root = yaml.compose("relations:\n  - {id: a, from: {object: x}, to: {object: y}}\n  - {id: b, from: {object: y}, to: {object: z}}\n")

    assert locate(root, "/relations/y -> z")["line"] == 3
    assert locate(root, "/relations/z -> y")["line"] == 1  # no such relation: the deepest node that exists


def test_import_rejects_a_reversed_actual_at_the_actual_finish_cell():
    table = ("id,title,type,start,end,actual_start,actual_finish\n"
             "a,A,task,2027-03-01,2027-03-10,2027-03-05,2027-03-02\n")

    result = import_table(table, project_id="p", as_of="2027-03-15")

    assert not result.ok and _codes(result) == ["E_ACTUAL_FINISH_NOT_AFTER_START"]
    found = result.diagnostics[0]
    assert (found.row, found.column, found.header) == (2, 7, "actual_finish")
    assert "before actual_start" in found.message


def test_import_reports_a_cycle_and_a_reversed_actual_in_one_run():
    table = ("id,type,start,duration,predecessors,actual_start,actual_finish\n"
             "a,task,2027-03-01,5wd,b,2027-03-05,2027-03-02\n"
             "b,task,,5wd,a,,\n")

    result = import_table(table, project_id="p", calendars=CALENDAR)

    assert sorted(_codes(result)) == ["E_ACTUAL_FINISH_NOT_AFTER_START", "E_UNSUPPORTED_CYCLE"]


def test_a_missing_calendar_is_one_hint_in_the_calendar_option_form():
    table = "id,type,duration\n" + "".join(f"t{n},task,5wd\n" for n in range(11))

    result = import_table(table, project_id="p")

    missing = [item for item in result.diagnostics if item.code == "E_CALENDAR_REQUIRED"]
    assert len(missing) == 11
    hints = [item.hint for item in missing if item.hint]
    assert len(hints) == 1
    assert '--calendar "standard mon-fri"' in hints[0] and "project line" not in hints[0]


def _team_table(headers="id,title,type,start,end,team,owner", **row):
    return (f"{headers}\n"
            "a,A,task,2027-03-01,2027-03-05,platform,ana\n"
            "b,B,task,2027-03-05,2027-03-09,payments,bo\n")


def test_role_binds_responsible_to_an_extra_column_without_changing_fields():
    result = import_table(_team_table(), project_id="p", roles=["responsible=team"])

    assert result.ok, [item.as_dict() for item in result.diagnostics]
    project = yaml.safe_load(result.project_yaml)
    assert project["fieldRoles"] == {"responsible": "team"}
    assert project["objects"]["a"]["fields"] == {"team": "platform", "owner": "ana"}
    plain = yaml.safe_load(import_table(_team_table(), project_id="p").project_yaml)
    assert "fieldRoles" not in plain
    del project["fieldRoles"]
    assert project == plain


def test_role_is_a_closed_vocabulary_read_from_the_schema():
    vocabulary = schema_document("vocabulary-v0.1.schema.yaml")["$defs"]["projectFieldRole"]["enum"]
    for role in vocabulary:
        assert import_table(_team_table(), project_id="p", roles=[f"{role}=team"]).ok


@pytest.mark.parametrize("roles, code", [
    (["boss=team"], "E_IMPORT_ROLE_UNKNOWN"),
    (["responsible=team", "responsible=owner"], "E_IMPORT_ROLE_DUPLICATE"),
    (["responsible=squad"], "E_IMPORT_ROLE_HEADER_ABSENT"),
    (["responsible=title"], "E_IMPORT_ROLE_COLUMN_RESERVED"),
    (["responsible=id"], "E_IMPORT_ROLE_COLUMN_RESERVED"),
    (["responsible"], "E_IMPORT_ROLE_SYNTAX"),
    (["=team"], "E_IMPORT_ROLE_SYNTAX"),
])
def test_role_rejections(roles, code):
    result = import_table(_team_table(), project_id="p", roles=roles)

    assert not result.ok and code in _codes(result)
    assert result.project_yaml is None


def _snapshot_files(tmp_path):
    table = "id,title,type,start,end\na,A,task,2027-03-01,2027-03-10\nb,B,task,2027-03-10,2027-03-20\n"
    earlier = "id,title,type,start,end\na,A,task,2027-03-01,2027-03-08\nb,B,task,2027-03-08,2027-03-18\n"
    (tmp_path / "plan.yaml").write_bytes(import_table(table, project_id="p").project_yaml)
    (tmp_path / "base.yaml").write_bytes(import_table(earlier, project_id="p").project_yaml)
    return tmp_path / "plan.yaml", tmp_path / "base.yaml"


@pytest.mark.parametrize("preset, drawn", [("chrona-default-draft", False), ("executive-light", False), ("target-b", True)])
def test_a_snapshot_the_view_does_not_draw_is_warned_about(tmp_path, preset, drawn):
    plan, base = _snapshot_files(tmp_path)

    result = render_draft(DraftRenderRequest(project=plan, target_kind="svg", preset=preset, snapshot=base))

    codes = [item["code"] for item in result.notes]
    assert (codes == []) is drawn
    if not drawn:
        assert result.notes[0]["severity"] == "warning" and "--snapshot" in result.notes[0]["message"]


def test_no_snapshot_no_warning(tmp_path):
    plan, _base = _snapshot_files(tmp_path)

    assert render_draft(DraftRenderRequest(project=plan, target_kind="svg")).notes == ()


def test_every_builtin_preset_has_a_one_line_description():
    listed = list_builtin_presets()
    ids = [entry["id"] for entry in _library()]

    assert [item["id"] for item in listed] == ids and len(ids) == 15
    assert set(PRESET_DESCRIPTIONS) == set(ids)
    for item in listed:
        text = item["description"]
        assert text and "\n" not in text and len(text) < 160, item["id"]


@pytest.mark.parametrize("entry", _library(), ids=lambda entry: entry["id"])
def test_a_preset_description_matches_its_own_resources(entry, tmp_path):
    text = PRESET_DESCRIPTIONS[entry["id"]]
    scheme = yaml.safe_load(_read_member(entry["members"]["colorScheme"]))
    background = re.search(r"background: (\w+)", yaml.safe_dump(scheme)).group(1)
    assert text.split("; ")[0].endswith(f", {background}"), text
    assert "draws actuals" in text


@pytest.mark.parametrize("entry", _library(), ids=lambda entry: entry["id"])
def test_a_preset_description_says_whether_a_snapshot_baseline_is_drawn(entry, tmp_path):
    plan, base = _snapshot_files(tmp_path)

    notes = render_draft(DraftRenderRequest(project=plan, target_kind="svg", preset=entry["id"], snapshot=base)).notes

    says_drawn = "baseline drawn from --snapshot" in PRESET_DESCRIPTIONS[entry["id"]]
    assert says_drawn == (not notes), entry["id"]


def _chrona(tmp_path, *args):
    return subprocess.run([sys.executable, "-c", "from chrona.app.cli import main; main()", *args], cwd=tmp_path,
                          capture_output=True, text=True)


def test_render_output_help_matches_the_behaviour_an_existing_file_is_replaced(tmp_path):
    flat = " ".join(_chrona(tmp_path, "render", "--help").stdout.split())
    assert "an existing file is replaced" in flat and "an existing file is not replaced" not in flat

    plan, _base = _snapshot_files(tmp_path)
    target = tmp_path / "out.svg"
    target.write_text("stale", encoding="utf-8")
    result = _chrona(tmp_path, "render", str(plan), "--output", str(target))
    assert result.returncode == 0, result.stdout
    assert target.read_text(encoding="utf-8").startswith("<svg")
