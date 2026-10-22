"""``save_baseline``: the file-route baseline of a Project, end to end through ``call_tool`` only (#1892 row 2, item 5)."""
from __future__ import annotations

import copy
import hashlib

from chrona.app.agent_tools import call_tool, tool_specs
from chrona.app.agent_workspace import WorkspaceScope

PROJECT = {
    "version": "timeline/v0.7",
    "project": {"id": "launch"},
    "objects": {
        "design": {"type": "task", "title": "Design", "schedule": {"mode": "fixed-span", "start": "2026-11-02", "end": "2026-11-06"}},
        "build": {"type": "task", "title": "Build", "schedule": {"mode": "scheduled", "amount": "5d"}},
    },
    "relations": [{"type": "dependency", "from": {"object": "design", "endpoint": "end"},
                   "to": {"object": "build", "endpoint": "start"}}],
}


def _call(root, name, arguments, *, allow_write=True):
    return call_tool(WorkspaceScope(root), name, arguments, allow_write=allow_write)


def _created(root):
    result = _call(root, "create_project", {"file": "project.yaml", "project": copy.deepcopy(PROJECT)})
    assert result.structured["status"] == "ok", result.structured
    return result.structured["projectRevision"]


def _move_design(root, revision):
    result = _call(root, "apply_project_command", {"project": "project.yaml", "command": {
        "version": "chrona/project-command/v0.1", "commandId": "slip", "type": "setObject",
        "target": {"kind": "project", "path": "project.yaml"}, "baseRevision": revision,
        "payload": {"id": "design", "object": {"type": "task", "title": "Design", "schedule": {
            "mode": "fixed-span", "start": "2026-11-09", "end": "2026-11-20"}}}}})
    assert result.structured["projectResult"]["status"] == "accepted", result.structured
    return result.structured["projectResult"]


def _svg(root, **extra):
    result = _call(root, "render_draft", {"project": "project.yaml", "preset": "target-b", "inline": "svg", **extra})
    assert result.structured["status"] == "ok", result.structured
    return next(item.data for item in result.attachments if item.kind == "svg").decode("utf-8")


def test_a_baseline_taken_before_an_edit_is_drawn_by_render_draft(tmp_path):
    revision = _created(tmp_path)
    saved = _call(tmp_path, "save_baseline", {"project": "project.yaml", "name": "week-1"}).structured

    assert saved["status"] == "ok" and saved["baseline"] == "baselines/week-1.yaml" and "replayed" not in saved
    copied = (tmp_path / "baselines" / "week-1.yaml").read_bytes()
    assert copied == (tmp_path / "project.yaml").read_bytes()
    assert saved["contentIdentity"] == "sha256:" + hashlib.sha256(copied).hexdigest()

    _move_design(tmp_path, revision)
    assert (tmp_path / "baselines" / "week-1.yaml").read_bytes() == copied  # the copy never follows the plan
    plain = _svg(tmp_path)
    against = _svg(tmp_path, snapshot=saved["baseline"])
    ghosts = [line for line in against.splitlines() if "stroke-dasharray" in line]
    assert ghosts and against != plain
    assert not [line for line in plain.splitlines() if "stroke-dasharray" in line and line in ghosts]


def test_the_same_content_replays_and_other_content_is_never_overwritten(tmp_path):
    revision = _created(tmp_path)
    first = _call(tmp_path, "save_baseline", {"project": "project.yaml", "name": "b"}).structured
    again = _call(tmp_path, "save_baseline", {"project": "project.yaml", "name": "b"}).structured
    assert again == {**first, "replayed": True}

    _move_design(tmp_path, revision)
    refused = _call(tmp_path, "save_baseline", {"project": "project.yaml", "name": "b"})
    assert refused.structured["status"] == "failed" and refused.is_error
    assert [row["code"] for row in refused.structured["diagnostics"]] == ["E_BASELINE_FILE_EXISTS"]
    assert (tmp_path / "baselines" / "b.yaml").read_text(encoding="utf-8").count("2026-11-02") == 1


def test_an_invalid_name_or_project_or_directory_writes_nothing(tmp_path):
    _created(tmp_path)
    for name in ("", "../x", "a/b", ".hidden", "x.yaml", "a" * 65, "sp ace"):
        result = _call(tmp_path, "save_baseline", {"project": "project.yaml", "name": name})
        assert result.structured["status"] == "rejected", name
        assert result.structured["diagnostics"][0]["code"] == "E_MCP_INPUT_INVALID"
        assert result.structured["diagnostics"][0]["sourceRef"] == "/name"
    assert not (tmp_path / "baselines").exists()

    (tmp_path / "broken.yaml").write_text("version: timeline/v0.7\nproject: {}\n", encoding="utf-8")
    broken = _call(tmp_path, "save_baseline", {"project": "broken.yaml", "name": "x"})
    assert broken.structured["status"] == "rejected" and not (tmp_path / "baselines").exists()

    (tmp_path / "baselines").write_text("a file", encoding="utf-8")
    blocked = _call(tmp_path, "save_baseline", {"project": "project.yaml", "name": "x"})
    assert blocked.structured["status"] == "failed"
    assert [row["code"] for row in blocked.structured["diagnostics"]] == ["E_BASELINE_DIRECTORY"]


def test_the_baseline_sits_beside_a_project_in_a_subdirectory_and_needs_the_write_gate(tmp_path):
    (tmp_path / "plan").mkdir()
    (tmp_path / "plan" / "project.yaml").write_bytes(b"")
    created = _call(tmp_path, "create_project", {"file": "plan/other.yaml", "project": copy.deepcopy(PROJECT)})
    assert created.structured["status"] == "ok"
    saved = _call(tmp_path, "save_baseline", {"project": "plan/other.yaml", "name": "b"}).structured
    assert saved["baseline"] == "plan/baselines/b.yaml" and (tmp_path / "plan" / "baselines" / "b.yaml").is_file()

    denied = _call(tmp_path, "save_baseline", {"project": "plan/other.yaml", "name": "c"}, allow_write=False)
    assert denied.structured["status"] == "failed" and denied.structured["diagnostics"][0]["code"] == "E_MCP_WRITE_DISABLED"
    assert not (tmp_path / "plan" / "baselines" / "c.yaml").exists()


def test_save_baseline_is_registered_as_a_mutating_tool():
    spec = next(spec for spec in tool_specs() if spec.name == "save_baseline")
    assert spec.mutating and spec.input_schema["required"] == ["project", "name"]
