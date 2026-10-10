"""The SDK-free agent tool core (#142, I142-S3): registry, result contract, scoping, determinism, cross-surface equality.

Every scenario goes through ``call_tool`` with a ``WorkspaceScope`` over a scratch directory and no SDK. Results
are checked against the registry's own output schemas, and the CLI is the oracle for verdicts and bytes.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from types import SimpleNamespace

import pytest
from jsonschema import Draft202012Validator, FormatChecker

from chrona.app import agent_tools
from chrona.app.agent_tools import (
    InvalidArgumentsError, UnknownToolError, call_tool, registry_document, tool_specs,
)
from chrona.app.agent_workspace import WorkspaceScope
from chrona.app.cli import main
from chrona.core.diagnostics import Diagnostic
from chrona.core.ports import RenderArtifact
from chrona.usecases.preset_library import copy_builtin_preset
from chrona.usecases.project_checks import ProjectValidation

REPO = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())
LAUNCH = (REPO / "skills" / "chrona" / "examples" / "launch.yaml").read_text(encoding="utf-8")

SMALL = """\
version: timeline/v0.7
project: {id: tool-unit, title: Tool unit}
objects:
  design: {type: task, title: Design, schedule: {mode: fixed-span, start: '2026-10-01', end: '2026-10-31'}}
  release: {type: gate, title: Release, schedule: {mode: fixed-point, at: '2026-12-18'}}
relations: []
"""
CYCLE = """\
version: timeline/v0.7
project: {id: cyc, title: Cycle}
objects:
  a: {type: task, title: A, schedule: {mode: scheduled, amount: 3d}}
  b: {type: task, title: B, schedule: {mode: scheduled, amount: 3d}}
relations:
  - {id: r1, type: dependency, from: {object: a, endpoint: end}, to: {object: b, endpoint: start}, lag: 0d}
  - {id: r2, type: dependency, from: {object: b, endpoint: end}, to: {object: a, endpoint: start}, lag: 0d}
"""
BAD_SCHEDULE = "version: timeline/v0.7\nobjects: {a: {type: task, title: A, schedule: {mode: scheduled}}}\n"
FILES = {
    "small.yaml": SMALL, "launch.yaml": LAUNCH, "cycle.yaml": CYCLE, "bad.yaml": BAD_SCHEDULE,
    "broken.yaml": "a: [\n", "not-a-mapping.yaml": "- a\n- b\n", "empty.yaml": "",
    "plans/nested.yaml": SMALL,
}
SPECS = {spec.name: spec for spec in tool_specs()}
VALIDATORS = {name: Draft202012Validator(spec.output_schema, format_checker=FormatChecker()) for name, spec in SPECS.items()}


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    root = tmp_path / "ws"
    for name, text in FILES.items():
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_text(text, encoding="utf-8")
    return root


@pytest.fixture
def scope(workspace: Path) -> WorkspaceScope:
    return WorkspaceScope(workspace)


def run(scope: WorkspaceScope, name: str, **arguments):
    result = call_tool(scope, name, arguments)
    VALIDATORS[name].validate(result.structured)
    assert json.loads(result.text()) == result.structured
    assert result.is_error == (result.structured["status"] == "failed")
    return result


def codes(result) -> list[str]:
    return [item["code"] for item in result.structured["diagnostics"]]


def cli(monkeypatch, capsys, cwd: Path, *arguments: str) -> tuple[int, str, str]:
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(sys, "argv", ["chrona", *arguments])
    code = 0
    try:
        main()
    except SystemExit as error:
        code = error.code if isinstance(error.code, int) else 0
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- the registry --------------------------------------------------------------------------------------------

def test_the_tool_set_is_seven_read_only_tools_and_one_writer_in_order():
    assert [spec.name for spec in tool_specs()] == ["validate_project", "schedule_project", "render_draft", "list_presets", "render_review", "compare_baseline", "check_command", "apply_command"]
    document = registry_document()
    assert document["toolSet"] == "chrona/agent-tools/v0.4"
    assert [tool["name"] for tool in document["tools"]] == list(SPECS)
    for tool in document["tools"]:
        writes = tool["name"] == "apply_command"
        assert tool["annotations"] == {"readOnlyHint": not writes, "destructiveHint": writes, "idempotentHint": True,
                                       "openWorldHint": False}
        assert tool["description"] and tool["title"]


def test_every_schema_is_a_valid_closed_json_schema():
    for spec in tool_specs():
        Draft202012Validator.check_schema(spec.input_schema)
        Draft202012Validator.check_schema(spec.output_schema)
        assert spec.input_schema["type"] == "object" and spec.input_schema["additionalProperties"] is False
        assert spec.output_schema["additionalProperties"] is False
        assert spec.output_schema["required"] == ["status", "diagnostics"]


def test_no_tool_accepts_an_integrity_font_or_filesystem_override():
    # The tool set offers exactly these inputs: nothing that lowers Store integrity, consults host fonts,
    # reads an arbitrary descriptor, names an output path or a Store root, or names a typesetter.
    assert {name: set(spec.input_schema["properties"]) for name, spec in SPECS.items()} == {
        "validate_project": {"project"}, "schedule_project": {"project"}, "list_presets": set(),
        "check_command": {"command", "storeConfig"}, "apply_command": {"command", "storeConfig"},
        "render_review": {"contextReference", "storeConfig", "inline"},
        "compare_baseline": {"baselineReference", "candidateReference", "storeConfig"},
        "render_draft": {"project", "actual", "preset", "view", "theme", "scheme", "layout", "viewport", "locale",
                         "format", "inline"},
    }


def test_the_registry_document_is_deterministic_and_json():
    first = json.dumps(registry_document(), sort_keys=False)
    assert first == json.dumps(registry_document(), sort_keys=False)
    assert json.loads(first) == registry_document()


def test_the_registry_document_is_a_copy_not_the_live_schemas():
    registry_document()["tools"][0]["inputSchema"]["properties"]["project"]["maxLength"] = 1
    assert SPECS["validate_project"].input_schema["properties"]["project"]["maxLength"] == 512


# --- protocol errors: unknown names and malformed arguments are not envelopes ---------------------------------

def test_an_unknown_tool_is_a_protocol_error(scope):
    with pytest.raises(UnknownToolError):
        call_tool(scope, "approve_command", {})


@pytest.mark.parametrize(("name", "arguments"), [
    ("validate_project", {}), ("validate_project", {"project": 3}), ("validate_project", {"project": ""}),
    ("validate_project", {"project": "a" * 513}), ("validate_project", {"project": "small.yaml", "extra": 1}),
    ("validate_project", [1]), ("list_presets", {"x": 1}),
    ("render_draft", {"project": "small.yaml", "format": "pdf"}),
    ("render_draft", {"project": "small.yaml", "inline": "html"}),
    ("render_draft", {"project": "small.yaml", "locale": "fr-FR"}),
    ("render_draft", {"project": "small.yaml", "viewport": "wide"}),
    ("render_draft", {"project": "small.yaml", "viewport": "1600x0"}),
    ("render_draft", {"project": "small.yaml", "viewport": "1600xauto\n"}),
    ("render_draft", {"project": "small.yaml", "viewport": "01600xauto"}),
    ("render_draft", {"project": "small.yaml", "system_fonts": True}),
    ("render_draft", {"project": "small.yaml", "allow_missing_content_identity": True}),
    ("render_draft", {"project": "small.yaml", "font_metrics": "m.json"}),
])
def test_malformed_arguments_are_a_protocol_error(scope, name, arguments):
    with pytest.raises(InvalidArgumentsError):
        call_tool(scope, name, arguments)


def test_missing_arguments_mean_an_empty_object(scope):
    assert run(scope, "list_presets").structured["status"] == "ok"
    with pytest.raises(InvalidArgumentsError):
        call_tool(scope, "validate_project", None)


# --- validate_project ----------------------------------------------------------------------------------------

def test_validate_ok_carries_the_project_identity_of_the_file_bytes(scope, workspace):
    result = run(scope, "validate_project", project="small.yaml")
    assert result.structured == {
        "status": "ok", "diagnostics": [],
        "projectIdentity": "sha256:" + hashlib.sha256((workspace / "small.yaml").read_bytes()).hexdigest(),
    }
    assert not result.is_error and result.attachments == ()


def test_validate_rejection_is_a_result_not_an_error(scope):
    result = run(scope, "validate_project", project="bad.yaml")
    assert result.structured["status"] == "rejected" and not result.is_error
    (item,) = [row for row in result.structured["diagnostics"] if row["sourceRef"] == "/objects/a/schedule"]  # #1303: all of them
    assert (item["code"], item["sourceRef"], item["component"], item["severity"]) == (
        "E_SCHEMA", "/objects/a/schedule", "core", "error")
    assert result.structured["projectIdentity"].startswith("sha256:")


def test_validate_reports_a_cycle_exactly_as_the_cli_and_schedule_do(scope, monkeypatch, capsys, workspace):
    """#780: the tool, the command and `schedule_project` return one finding for a cycle."""
    validated = run(scope, "validate_project", project="cycle.yaml")
    rc, out, err = cli(monkeypatch, capsys, workspace, "validate", "cycle.yaml")
    expected = json.loads(out)["diagnostics"]
    assert (rc, err) == (1, "") and validated.structured["status"] == "rejected" and not validated.is_error
    assert set(codes(validated)) == {"E_UNSUPPORTED_CYCLE"} and len(expected) == 1
    keys = ("code", "severity", "component", "sourceRef", "message")
    assert [{key: item[key] for key in keys} for item in validated.structured["diagnostics"]] == [
        {key: item[key] for key in keys} for item in expected]
    assert validated.structured["diagnostics"][0]["sourceRef"] == "/relations/1"
    scheduled = run(scope, "schedule_project", project="cycle.yaml")
    assert scheduled.structured["diagnostics"] == validated.structured["diagnostics"]


def test_validate_and_the_cli_agree_on_a_rejection(scope, monkeypatch, capsys, workspace):
    rc, out, _ = cli(monkeypatch, capsys, workspace, "validate", "bad.yaml")
    expected = json.loads(out)["diagnostics"][0]
    got = run(scope, "validate_project", project="bad.yaml").structured["diagnostics"][0]
    assert rc == 1
    assert {key: got[key] for key in ("code", "severity", "component", "sourceRef", "message")} == {
        key: expected[key] for key in ("code", "severity", "component", "sourceRef", "message")}


# --- schedule_project ----------------------------------------------------------------------------------------

def test_schedule_returns_sorted_placements_and_analysis(scope):
    result = run(scope, "schedule_project", project="launch.yaml")
    assert result.structured["status"] == "ok"
    assert result.structured["placements"] == {
        "build": {"start": "2026-11-09", "end": "2026-12-01"},
        "design": {"start": "2026-11-02", "end": "2026-11-09"},
        "kickoff": {"at": "2026-11-02"},
        "launch": {"at": "2026-12-14"},
    }
    assert list(result.structured["placements"]) == sorted(result.structured["placements"])
    analysis = result.structured["analysis"]
    assert analysis["criticalObjectIds"] == ["kickoff", "launch"]
    assert list(analysis["totalFloat"]) == sorted(analysis["totalFloat"])
    assert analysis["totalFloat"] == {"build": 9, "design": 9, "kickoff": 0, "launch": 0}


def test_schedule_does_not_trust_the_key_order_of_total_float(scope, monkeypatch):
    real = agent_tools.schedule_project_file(scope.resolve_path("launch.yaml", "/project"))
    shuffled = type(real)(real.diagnostics, dict(reversed(list(real.placements.items()))),
                          {**real.analysis, "totalFloat": dict(reversed(list(real.analysis["totalFloat"].items())))})
    monkeypatch.setattr(agent_tools, "schedule_project_file", lambda path: shuffled)
    result = run(scope, "schedule_project", project="launch.yaml")
    assert list(result.structured["analysis"]["totalFloat"]) == ["build", "design", "kickoff", "launch"]
    assert list(result.structured["placements"]) == ["build", "design", "kickoff", "launch"]


def test_schedule_rejection_names_the_cycle(scope):
    result = run(scope, "schedule_project", project="cycle.yaml")
    assert result.structured["status"] == "rejected" and not result.is_error
    assert "placements" not in result.structured


def test_schedule_equals_the_cli_json(scope, monkeypatch, capsys, workspace):
    rc, out, _ = cli(monkeypatch, capsys, workspace, "schedule", "launch.yaml")
    expected = json.loads(out)
    got = run(scope, "schedule_project", project="launch.yaml").structured
    assert rc == 0
    assert got["placements"] == expected["placements"] and got["analysis"] == expected["analysis"]
    assert expected["diagnostics"] == got["diagnostics"] == []


def test_schedule_carries_a_missed_deadline_as_a_warning_and_still_schedules(workspace, scope):
    late = LAUNCH.replace("deadline: 2026-12-18", "deadline: 2026-12-01")
    assert late != LAUNCH
    (workspace / "late.yaml").write_text(late, encoding="utf-8")
    result = run(scope, "schedule_project", project="late.yaml")
    assert result.structured["status"] == "ok" and result.structured["diagnostics"] == []
    (warning,) = result.structured["warnings"]
    assert warning == {
        "code": "W_DEADLINE", "severity": "warning", "component": "core", "sourceRef": "/objects/launch/deadline",
        "message": "launch finishes 2026-12-14, 13 days after its deadline 2026-12-01",
        "detail": {"daysLate": 13, "deadline": "2026-12-01", "endpoint": "at", "finish": "2026-12-14", "object": "launch"},
    }
    assert result.structured["placements"] == run(scope, "schedule_project", project="launch.yaml").structured["placements"]


def test_schedule_without_a_missed_deadline_has_an_empty_warnings_list(scope):
    assert run(scope, "schedule_project", project="launch.yaml").structured["warnings"] == []


def test_schedule_warnings_equal_the_cli_records(workspace, scope, monkeypatch, capsys):
    (workspace / "late.yaml").write_text(LAUNCH.replace("deadline: 2026-12-18", "deadline: 2026-12-01"), encoding="utf-8")
    rc, out, _ = cli(monkeypatch, capsys, workspace, "schedule", "late.yaml")
    (expected,) = json.loads(out)["warnings"]
    (got,) = run(scope, "schedule_project", project="late.yaml").structured["warnings"]
    assert rc == 0
    assert got["detail"] == expected["details"]
    assert {key: got[key] for key in ("code", "severity", "component", "sourceRef", "message")} == {
        key: expected[key] for key in ("code", "severity", "component", "sourceRef", "message")}


# --- list_presets --------------------------------------------------------------------------------------------

def test_list_presets_equals_the_cli_in_the_cli_order(scope, monkeypatch, capsys, workspace):
    expected = json.loads(cli(monkeypatch, capsys, workspace, "preset", "list")[1])["presets"]
    result = run(scope, "list_presets")
    assert result.structured["presets"] == expected and len(expected) >= 7
    assert result.structured["default"] == "chrona-default-draft"


def test_the_default_preset_id_is_the_bundled_default():
    import yaml
    from chrona.resources import default_preset_resource
    assert yaml.safe_load(default_preset_resource().read_bytes())["id"] == agent_tools.DEFAULT_PRESET_ID


# --- render_draft --------------------------------------------------------------------------------------------

def sha(content: bytes) -> str:
    return "sha256:" + hashlib.sha256(content).hexdigest()


def test_render_draft_defaults_to_a_png_preview_and_identifies_the_svg(scope, monkeypatch, capsys, workspace):
    result = run(scope, "render_draft", project="small.yaml")
    structured = result.structured
    assert (structured["status"], structured["format"], structured["pngAvailable"]) == ("ok", "svg", True)
    assert [(item.kind, item.media_type) for item in result.attachments] == [("image", "image/png")]
    assert result.attachments[0].data.startswith(b"\x89PNG\r\n\x1a\n")
    assert cli(monkeypatch, capsys, workspace, "render", "small.yaml", "--output", "out.svg")[0] == 0
    svg = (workspace / "out.svg").read_bytes()
    assert structured["contentIdentity"] == sha(svg) and structured["byteLength"] == len(svg)


def test_render_draft_png_bytes_equal_the_cli_png(scope, monkeypatch, capsys, workspace):
    result = run(scope, "render_draft", project="small.yaml", format="png")
    assert cli(monkeypatch, capsys, workspace, "render", "small.yaml", "--output", "out.png")[0] == 0
    png = (workspace / "out.png").read_bytes()
    assert result.attachments[0].data == png and result.structured["contentIdentity"] == sha(png)
    assert result.structured["format"] == "png" and result.structured["byteLength"] == len(png)


def test_render_draft_inline_svg_is_an_embedded_resource_equal_to_the_cli_file(scope, monkeypatch, capsys, workspace):
    result = run(scope, "render_draft", project="small.yaml", inline="svg")
    assert cli(monkeypatch, capsys, workspace, "render", "small.yaml", "--output", "out.svg")[0] == 0
    svg = (workspace / "out.svg").read_bytes()
    (attachment,) = result.attachments
    assert (attachment.kind, attachment.media_type, attachment.data) == ("svg", "image/svg+xml", svg)
    assert attachment.uri == f"chrona://render/{sha(svg)}.svg"
    assert result.structured["contentIdentity"] == sha(svg)


def test_render_draft_inline_none_carries_only_the_structured_result(scope):
    result = run(scope, "render_draft", project="small.yaml", inline="none")
    assert result.attachments == () and result.structured["status"] == "ok"


def test_render_draft_inline_svg_of_a_png_artifact_renders_the_svg_too(scope):
    result = run(scope, "render_draft", project="small.yaml", format="png", inline="svg")
    assert result.structured["format"] == "png" and result.attachments[0].data.startswith(b"<svg")
    assert result.structured["contentIdentity"] != sha(result.attachments[0].data)


def test_render_draft_builtin_preset_and_viewport_equal_the_cli(scope, monkeypatch, capsys, workspace):
    result = run(scope, "render_draft", project="small.yaml", preset="editorial", viewport="1200x700", locale="en-US",
                 inline="none")
    rc, _, _ = cli(monkeypatch, capsys, workspace, "render", "small.yaml", "--preset", "editorial", "--viewport",
                   "1200x700", "--locale", "en-US", "--output", "out.svg")
    assert rc == 0 and result.structured["contentIdentity"] == sha((workspace / "out.svg").read_bytes())
    default = run(scope, "render_draft", project="small.yaml", inline="none")
    assert default.structured["contentIdentity"] != result.structured["contentIdentity"]


def test_render_draft_locale_gives_the_cli_verdict_whatever_fonts_are_installed(scope, monkeypatch, capsys, workspace):
    result = run(scope, "render_draft", project="small.yaml", locale="ja-JP", inline="none")
    rc, out, _ = cli(monkeypatch, capsys, workspace, "render", "small.yaml", "--locale", "ja-JP", "--output", "out.svg")
    if rc == 0:
        assert result.structured["contentIdentity"] == sha((workspace / "out.svg").read_bytes())
    else:
        assert result.structured["status"] == "rejected" and codes(result) == [json.loads(out)["diagnostics"][0]["code"]]


def test_render_draft_workspace_preset_equals_the_builtin_it_was_copied_from(scope, workspace):
    copy_builtin_preset("editorial", workspace / "looks")
    builtin = run(scope, "render_draft", project="small.yaml", preset="editorial", inline="none")
    copied = run(scope, "render_draft", project="small.yaml", preset="looks/preset.yaml", inline="none")
    assert copied.structured["contentIdentity"] == builtin.structured["contentIdentity"]


def test_render_draft_actual_view_theme_scheme_and_layout_are_workspace_paths(scope, workspace):
    copy_builtin_preset("editorial", workspace / "looks")
    result = run(scope, "render_draft", project="small.yaml", view="looks/view.yaml", theme="looks/theme.yaml",
                 scheme="looks/scheme.yaml", layout="looks/layout.yaml", inline="none")
    assert result.structured["status"] == "ok"


def test_a_workspace_preset_cannot_name_a_member_outside_its_directory(scope, workspace):
    import yaml
    copy_builtin_preset("editorial", workspace / "looks")
    (workspace.parent / "outside").mkdir()
    shutil.copy(workspace / "looks" / "view.yaml", workspace.parent / "outside" / "view.yaml")
    preset = workspace / "looks" / "preset.yaml"
    document = yaml.safe_load(preset.read_text(encoding="utf-8"))
    document["body"]["resources"]["view"]["path"] = "../../outside/view.yaml"
    preset.write_text(yaml.safe_dump(document), encoding="utf-8")
    result = run(scope, "render_draft", project="small.yaml", preset="looks/preset.yaml", inline="none")
    assert result.structured["status"] == "rejected" and "contentIdentity" not in result.structured
    assert str(workspace.parent) not in result.text()


def test_render_draft_rejections_are_typed_results(scope):
    unknown = run(scope, "render_draft", project="small.yaml", preset="nope")
    assert (unknown.structured["status"], codes(unknown)) == ("rejected", ["E_BUILTIN_PRESET_UNKNOWN"])
    bad = run(scope, "render_draft", project="bad.yaml", inline="none")
    assert bad.structured["status"] == "rejected" and codes(bad) == ["E_PROJECT_SCHEMA"]
    cycle = run(scope, "render_draft", project="cycle.yaml", inline="none")
    assert cycle.structured["status"] == "rejected" and set(codes(cycle)) == {"E_UNSUPPORTED_CYCLE"}
    assert not any(result.is_error or result.attachments for result in (unknown, bad, cycle))


def test_a_preset_value_with_a_separator_must_be_a_yaml_path(scope):
    result = run(scope, "render_draft", project="small.yaml", preset="looks/preset")
    assert (result.structured["status"], codes(result)) == ("failed", ["E_MCP_PATH_SYNTAX"])
    assert result.structured["diagnostics"][0]["sourceRef"] == "/preset"


def test_a_real_render_warning_is_normalised_into_the_envelope_shape(scope):
    result = run(scope, "render_draft", project="launch.yaml", viewport="300x300", inline="none")
    warnings = result.structured["warnings"]
    assert {"W_LAYOUT_LABEL_SUPPRESSED", "W_LAYOUT_LABEL_OVERFLOW", "I_LAYOUT_PLOT_LABELS_SUPPRESSED"} <= {
        item["code"] for item in warnings}
    assert {item["severity"] for item in warnings} == {"warning", "info"}
    assert all(item["component"] == "render" and isinstance(item["detail"], dict) and item["detail"] for item in warnings)
    assert result.structured["status"] == "ok" and result.structured["diagnostics"] == []


def test_warning_records_keep_their_fields_sorted_and_scrubbed(scope, monkeypatch, workspace):
    home = str(Path.home())
    payloads = [
        {"code": "W_X", "severity": "warning", "diagnostic": "W_X:1", "sourceRef": "/root/children/1",
         "zeta": 1, "alpha": {"b": 2, "a": [{"d": 1, "c": 2}]}, "message": f"see {home}/x"},
        {"code": "I_Y", "severity": "info", "surfaceId": "s", "count": 2, "message": "two labels were left out"},
        {"code": "W_X", "severity": "warning", "diagnostic": "W_X:2", "message": "merged", "count": 3,
         "occurrences": [f"W_X:{home}/a", "W_X:2"]},
    ]
    monkeypatch.setattr(agent_tools, "warning_payloads", lambda rendered: payloads)
    warnings = run(scope, "render_draft", project="small.yaml", inline="none").structured["warnings"]
    first, second, third = warnings
    assert list(first["detail"]) == ["alpha", "diagnostic", "zeta"] and list(first["detail"]["alpha"]["a"][0]) == ["c", "d"]
    assert home not in first["message"] and first["sourceRef"] == "/root/children/1"
    assert (second["severity"], second["component"], second["sourceRef"], second["message"]) == (
        "info", "render", "/", "two labels were left out")
    assert second["detail"] == {"count": 2, "surfaceId": "s"} and "count" not in second  # an info record's own count
    assert (third["count"], third["occurrences"]) == (3, ["W_X:<path>", "W_X:2"]) and "count" not in third["detail"]
    assert "count" not in first and "occurrences" not in first


def test_warnings_equal_the_cli_stdout_success_envelope(scope, monkeypatch, capsys, workspace):
    result = run(scope, "render_draft", project="launch.yaml", viewport="300x300", inline="none")
    rc, out, err = cli(monkeypatch, capsys, workspace, "render", "launch.yaml", "--viewport", "300x300", "--output", "o.svg")
    envelope = json.loads(out)
    printed = envelope["warnings"]
    assert rc == 0 and err == "" and envelope["status"] == "ok" and envelope["diagnostics"] == []
    assert len(printed) == len(result.structured["warnings"]) > 0
    for line, item in zip(printed, result.structured["warnings"], strict=True):
        warning = line["severity"] == "warning"  # an info record's own `count` is a number of labels, not a merge count
        top = {"code", "severity", "component", "sourceRef", "message"} | ({"count", "occurrences"} if warning else set())
        assert item["message"] and (item["code"], item["severity"], item["sourceRef"], item["message"]) == (
            line["code"], line["severity"], line.get("sourceRef", "/"), line["message"])
        assert item.get("count") == (line.get("count") if warning else None)
        assert item.get("occurrences") == (line.get("occurrences") if warning else None)
        assert item["detail"] == {key: value for key, value in line.items() if key not in top}


def _successful_render_warning_cases():
    golden = json.loads((REPO / "tests/fixtures/cli_characterization/golden.json").read_text(encoding="utf-8"))
    cases = []
    for name, record in golden.items():
        argv = record.get("argv", ())
        if not argv or argv[0] not in {"render", "render-review", "render-workspace"} or record.get("exit") != 0:
            continue
        stdout = record.get("stdout")
        assert isinstance(stdout, str), f"successful render {name} must retain its full CLI stdout envelope"
        envelope = json.loads(stdout)
        assert envelope.get("status") == "ok" and isinstance(envelope.get("warnings"), list), name
        warnings = envelope["warnings"]
        cases.append((name, warnings))
    assert cases
    return cases


@pytest.mark.parametrize(("case_name", "golden_warnings"), _successful_render_warning_cases(),
                         ids=lambda value: value if isinstance(value, str) else None)
def test_mcp_render_warning_projection_preserves_every_successful_cli_golden_row(
        scope, monkeypatch, case_name, golden_warnings):
    """Exercise the real MCP tool envelope against each checked-in successful CLI warning row."""
    artifact = RenderArtifact("svg", "image/svg+xml", b"<svg/>", "test-agent-transport")
    rendered = SimpleNamespace(artifact=artifact, rendered=object())
    monkeypatch.setattr(agent_tools, "render_draft", lambda request: rendered)
    monkeypatch.setattr(agent_tools, "warning_payloads", lambda _rendered: golden_warnings)

    result = run(scope, "render_draft", project="small.yaml", inline="none")
    actual = result.structured["warnings"]
    assert result.structured["status"] == "ok" and result.structured["diagnostics"] == []
    assert len(actual) == len(golden_warnings), case_name
    for source, output in zip(golden_warnings, actual, strict=True):
        is_warning = source.get("severity") != "info"
        known = {"code", "severity", "component", "sourceRef", "message"}
        if is_warning:
            known |= {"count", "occurrences"}
        assert (output["code"], output["severity"], output["component"], output["sourceRef"], output["message"]) == (
            source["code"], source.get("severity", "warning"), source.get("component", "render"),
            source.get("sourceRef", "/"), scope.scrub(str(source["message"])))
        assert output["detail"] == {
            key: value for key, value in source.items() if key not in known
        }
        if is_warning:
            if "count" in source:
                assert output["count"] == source["count"]
                assert output["occurrences"] == source.get("occurrences", [])
            else:
                assert "count" not in output and "occurrences" not in output
        else:
            # Info count is meaningful detail, not the warning-ledger merge count.
            assert output.get("count") is None and output["detail"].get("count") == source.get("count")


def test_without_the_rasterizer_png_is_reported_not_substituted(scope, monkeypatch):
    monkeypatch.setitem(sys.modules, "resvg_py", None)  # `import resvg_py` now raises ImportError
    preview = run(scope, "render_draft", project="small.yaml")
    assert (preview.structured["status"], preview.structured["pngAvailable"], preview.attachments) == ("ok", False, ())
    assert run(scope, "render_draft", project="small.yaml", inline="none").structured["pngAvailable"] is False
    png = run(scope, "render_draft", project="small.yaml", format="png")
    assert (png.structured["status"], codes(png), png.is_error) == ("failed", ["E_RENDER_RASTERIZER_UNAVAILABLE"], True)


def test_an_inline_payload_over_its_cap_is_refused_with_the_next_action(scope, monkeypatch):
    monkeypatch.setattr(agent_tools, "MAX_INLINE_SVG_BYTES", 10)
    monkeypatch.setattr(agent_tools, "MAX_INLINE_PNG_BYTES", 10)
    for inline in ("svg", "image"):
        result = run(scope, "render_draft", project="small.yaml", inline=inline)
        assert (result.structured["status"], codes(result), result.is_error) == ("failed", ["E_MCP_RESULT_TOO_LARGE"], True)
        assert "command line" in result.structured["diagnostics"][0]["message"] and result.attachments == ()
    assert run(scope, "render_draft", project="small.yaml", inline="none").structured["status"] == "ok"


# --- failure families: typed diagnostics, never a traceback --------------------------------------------------

FAMILIES = [
    ("validate_project", {"project": "missing.yaml"}, "failed", "E_INPUT_IO"),
    ("validate_project", {"project": "plans"}, "failed", "E_INPUT_IO"),
    ("validate_project", {"project": "broken.yaml"}, "failed", "E_INPUT_YAML"),
    ("validate_project", {"project": "bad.yaml"}, "rejected", "E_SCHEMA"),
    ("validate_project", {"project": "../x.yaml"}, "failed", "E_MCP_PATH_SYNTAX"),
    ("validate_project", {"project": "/etc/passwd"}, "failed", "E_MCP_PATH_SYNTAX"),
    ("validate_project", {"project": "con.yaml"}, "failed", "E_MCP_PATH_SYNTAX"),
    ("validate_project", {"project": "not-a-mapping.yaml"}, "rejected", "E_SCHEMA"),
    ("schedule_project", {"project": "missing.yaml"}, "failed", "E_INPUT_IO"),
    ("schedule_project", {"project": "broken.yaml"}, "failed", "E_INPUT_YAML"),
    ("schedule_project", {"project": "cycle.yaml"}, "rejected", "E_UNSUPPORTED_CYCLE"),
    ("schedule_project", {"project": "C:/x.yaml"}, "failed", "E_MCP_PATH_SYNTAX"),
    ("render_draft", {"project": "missing.yaml"}, "failed", "E_INPUT_IO"),
    ("render_draft", {"project": "broken.yaml"}, "failed", "E_INPUT_YAML"),
    ("render_draft", {"project": "bad.yaml"}, "rejected", "E_PROJECT_SCHEMA"),
    ("render_draft", {"project": "small.yaml", "actual": "missing.yaml"}, "failed", "E_INPUT_IO"),
    ("render_draft", {"project": "small.yaml", "preset": "nope"}, "rejected", "E_BUILTIN_PRESET_UNKNOWN"),
]


@pytest.mark.parametrize(("name", "arguments", "status", "code"), FAMILIES, ids=[f"{n}-{c}-{a}" for n, a, _, c in FAMILIES])
def test_each_failure_family_is_a_typed_envelope(scope, workspace, name, arguments, status, code):
    result = run(scope, name, **arguments)
    assert (result.structured["status"], codes(result)[0]) == (status, code)
    assert result.is_error == (status == "failed")
    text = result.text()
    assert "Traceback" not in text and str(workspace) not in text and str(workspace.parent) not in text
    assert all(item["severity"] == "error" for item in result.structured["diagnostics"])


def test_a_yaml_error_keeps_the_identity_of_the_bytes_that_were_read_and_no_host_path(scope, workspace):
    result = run(scope, "validate_project", project="broken.yaml")
    assert result.structured["projectIdentity"] == sha((workspace / "broken.yaml").read_bytes())
    assert 'in "broken.yaml"' in result.structured["diagnostics"][0]["message"]


def test_an_unexpected_exception_becomes_a_fixed_message_and_the_traceback_goes_to_the_log(scope, monkeypatch, caplog, capsys):
    def boom():
        raise RuntimeError(f"secret detail at {Path.home()}/x.py")

    monkeypatch.setattr(agent_tools, "list_builtin_presets", boom)
    with caplog.at_level(logging.ERROR, logger="chrona.agent"):
        result = run(scope, "list_presets")
    (item,) = result.structured["diagnostics"]
    assert (result.structured["status"], item["code"], item["message"]) == ("failed", "E_TOOL_FAILURE", "internal error: RuntimeError")
    assert "secret" not in result.text() and result.is_error
    assert any(record.exc_info and "secret detail" in str(record.exc_info[1]) for record in caplog.records)
    assert capsys.readouterr().out == ""


def test_an_internal_error_message_never_carries_a_host_path_from_a_value_error(scope, monkeypatch):
    def boom():
        raise ValueError(f"cannot load {Path.home()}/chrona/x.yaml")

    monkeypatch.setattr(agent_tools, "list_builtin_presets", boom)
    result = run(scope, "list_presets")
    assert str(Path.home()) not in result.text() and "<path>" in result.text()


def test_duplicates_are_merged_with_a_count_and_the_list_is_capped(scope, monkeypatch):
    items = [Diagnostic(f"E_NUM_{index % 60:02d}", f"finding {index % 60}", f"/objects/o{index % 60}") for index in range(120)]
    monkeypatch.setattr(agent_tools, "validate_project_file", lambda path: ProjectValidation(tuple(items)))
    result = run(scope, "validate_project", project="small.yaml")
    assert result.structured["status"] == "rejected"
    assert len(result.structured["diagnostics"]) == 50 and result.structured["omittedDiagnostics"] == 10
    assert len({item["code"] for item in result.structured["diagnostics"]}) == 50
    assert {item["count"] for item in result.structured["diagnostics"]} == {2}


def test_rows_that_scrubbing_makes_equal_merge_and_their_counts_add(scope, workspace, monkeypatch):
    items = [Diagnostic("E_IO", f"cannot read {Path.home()}/a/{name}.yaml", "/") for name in ("one", "two")]
    items += [Diagnostic("E_IO", f"cannot read {Path.home()}/a/three.yaml", "/")] * 2
    monkeypatch.setattr(agent_tools, "validate_project_file", lambda path: ProjectValidation(tuple(items)))
    result = run(scope, "validate_project", project="small.yaml")
    (row,) = result.structured["diagnostics"]
    assert row["message"] == "cannot read <path>" and row["count"] == 4
    assert str(Path.home()) not in result.text()


def test_the_tool_rows_equal_the_cli_rows_for_a_malformed_plan(scope, workspace, monkeypatch, capsys):
    status, out, _err = cli(monkeypatch, capsys, workspace, "validate", "not-a-mapping.yaml")
    assert status == 1
    cli_rows = [{key: value for key, value in row.items() if key not in {"revisionRefs", "sourceRange"}}  # the tool omits both
                for row in json.loads(out)["diagnostics"]]
    tool = run(scope, "validate_project", project="not-a-mapping.yaml").structured["diagnostics"]
    assert tool == cli_rows and tool[0]["message"].startswith("a Project must be a YAML mapping")


def test_an_unknown_preset_names_the_value_and_every_valid_id_in_the_tool_and_the_command(scope, workspace, monkeypatch, capsys):
    status, out, _err = cli(monkeypatch, capsys, workspace, "render", "small.yaml", "--preset", "nope", "--output", "o.svg")
    assert status == 1
    (cli_row,) = json.loads(out)["diagnostics"]
    (tool_row,) = run(scope, "render_draft", project="small.yaml", preset="nope").structured["diagnostics"]
    assert tool_row["message"] == cli_row["message"] and tool_row["code"] == "E_BUILTIN_PRESET_UNKNOWN"
    assert "'nope'" in tool_row["message"]
    assert all(preset["id"] in tool_row["message"] for preset in run(scope, "list_presets").structured["presets"])


def test_no_cap_note_appears_when_nothing_is_omitted(scope, monkeypatch):
    items = [Diagnostic("E_ONE", "one", "/a")] * 5
    monkeypatch.setattr(agent_tools, "validate_project_file", lambda path: ProjectValidation(tuple(items)))
    result = run(scope, "validate_project", project="small.yaml")
    assert len(result.structured["diagnostics"]) == 1 and "omittedDiagnostics" not in result.structured
    assert result.structured["diagnostics"][0]["count"] == 5


# --- path scoping through every path argument ----------------------------------------------------------------

PATH_ARGUMENTS = [("validate_project", "project"), ("schedule_project", "project"), ("render_draft", "project"),
                  ("render_draft", "actual"), ("render_draft", "view"), ("render_draft", "theme"),
                  ("render_draft", "scheme"), ("render_draft", "layout"), ("render_draft", "preset")]
ESCAPES = [("../outside.yaml", "E_MCP_PATH_SYNTAX"), ("plans/../../outside.yaml", "E_MCP_PATH_SYNTAX"),
           ("/etc/hosts", "E_MCP_PATH_SYNTAX"), ("C:/Windows/x.yaml", "E_MCP_PATH_SYNTAX"),
           ("..\\outside.yaml", "E_MCP_PATH_SYNTAX"), ("a:b.yaml", "E_MCP_PATH_SYNTAX"),
           ("NUL.yaml", "E_MCP_PATH_SYNTAX"), ("a\x00b.yaml", "E_MCP_PATH_SYNTAX")]


@pytest.mark.parametrize(("name", "argument"), PATH_ARGUMENTS)
@pytest.mark.parametrize(("value", "code"), ESCAPES, ids=[value.encode("unicode_escape").decode() for value, _ in ESCAPES])
def test_every_path_argument_refuses_every_escape(scope, name, argument, value, code):
    arguments = {"project": "small.yaml"} if argument != "project" else {}
    arguments[argument] = value  # every escape has a '/' or a .yaml suffix, so a preset value is read as a path
    result = run(scope, name, **arguments)
    assert (result.structured["status"], codes(result)) == ("failed", [code])
    assert result.structured["diagnostics"][0]["sourceRef"] == f"/{argument}"
    assert result.attachments == ()


@pytest.mark.parametrize(("name", "argument"), PATH_ARGUMENTS)
def test_every_path_argument_refuses_a_symlink_that_leaves_the_workspace(scope, workspace, tmp_path, name, argument):
    outside = tmp_path / "outside.yaml"
    outside.write_text(SMALL, encoding="utf-8")
    try:
        (workspace / "link.yaml").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("the OS refuses to create symbolic links here")
    arguments = {"project": "small.yaml"} if argument != "project" else {}
    arguments[argument] = "link.yaml"
    result = run(scope, name, **arguments)
    assert (result.structured["status"], codes(result)) == ("failed", ["E_MCP_PATH_CONTAINMENT"])
    assert result.structured["diagnostics"][0]["sourceRef"] == f"/{argument}"


def test_a_project_larger_than_the_cap_is_refused_by_every_tool_that_reads_it(scope, workspace):
    (workspace / "huge.yaml").write_bytes(b"#" * (2 * 1024 * 1024 + 1))
    for name in ("validate_project", "schedule_project", "render_draft"):
        result = run(scope, name, project="huge.yaml")
        assert codes(result) == ["E_MCP_INPUT_TOO_LARGE"] and result.is_error


def test_a_non_ascii_project_name_works_end_to_end(scope, workspace):
    (workspace / "計画 2026.yaml").write_text(SMALL, encoding="utf-8")
    assert run(scope, "validate_project", project="計画 2026.yaml").structured["status"] == "ok"
    assert run(scope, "schedule_project", project="計画 2026.yaml").structured["status"] == "ok"


# --- determinism and hygiene ---------------------------------------------------------------------------------

CALLS = [("validate_project", {"project": "launch.yaml"}), ("validate_project", {"project": "bad.yaml"}),
         ("schedule_project", {"project": "launch.yaml"}), ("schedule_project", {"project": "cycle.yaml"}),
         ("list_presets", {}), ("render_draft", {"project": "launch.yaml", "viewport": "300x300", "inline": "none"}),
         ("render_draft", {"project": "small.yaml", "inline": "svg"})]


def snapshot(scope: WorkspaceScope) -> list[tuple[str, str, list[tuple[str, bytes]]]]:
    out = []
    for name, arguments in CALLS:
        result = call_tool(scope, name, arguments)
        out.append((name, result.text(), [(item.kind, item.data) for item in result.attachments]))
    return out


def test_the_same_calls_twice_and_from_two_working_directories_give_equal_results(scope, workspace, tmp_path, monkeypatch):
    first = snapshot(scope)
    assert first == snapshot(scope)
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    assert first == snapshot(scope)
    monkeypatch.chdir(workspace)
    assert first == snapshot(scope)


def test_no_result_carries_a_host_path_a_clock_or_a_process_id(scope, workspace, tmp_path):
    needles = {str(workspace), workspace.as_posix(), str(workspace.resolve()), str(tmp_path), str(Path.home()), str(Path.cwd()),
               str(REPO)}
    for name, text, _ in snapshot(scope):
        for needle in needles:
            assert needle not in text, (name, needle)
        assert not re.search(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", text), name  # no timestamp, only plan dates


def test_results_do_not_depend_on_the_hash_seed(workspace, tmp_path):
    script = tmp_path / "seed_probe.py"
    script.write_text(textwrap.dedent("""
        import json, sys
        from chrona.app.agent_workspace import WorkspaceScope
        from chrona.app.agent_tools import call_tool
        scope = WorkspaceScope(sys.argv[1])
        for name, arguments in [("schedule_project", {"project": "launch.yaml"}), ("validate_project", {"project": "bad.yaml"}),
                                ("render_draft", {"project": "small.yaml", "inline": "none"})]:
            print(call_tool(scope, name, arguments).text())
    """), encoding="utf-8")
    outputs = []
    for seed in ("1", "2", "3"):
        env = {**os.environ, "PYTHONHASHSEED": seed}
        done = subprocess.run([sys.executable, str(script), str(workspace)], env=env, capture_output=True, text=True,
                              encoding="utf-8", check=False, cwd=tmp_path)
        assert done.returncode == 0, done.stderr
        outputs.append(done.stdout)
    assert outputs[0] == outputs[1] == outputs[2] and outputs[0].count("\n") == 3


def test_no_tool_writes_to_standard_output_or_the_workspace(scope, workspace, capsys):
    before = sorted(path.relative_to(workspace).as_posix() for path in workspace.rglob("*"))
    snapshot(scope)
    for name, arguments, _, _ in FAMILIES:
        call_tool(scope, name, arguments)
    assert capsys.readouterr().out == ""
    assert before == sorted(path.relative_to(workspace).as_posix() for path in workspace.rglob("*"))



def test_the_tool_core_imports_without_the_sdk():
    done = subprocess.run(
        [sys.executable, "-c", "import sys; import chrona.app.agent_tools; assert 'mcp' not in sys.modules, 'SDK imported'"],
        capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stderr
