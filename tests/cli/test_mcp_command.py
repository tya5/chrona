"""`chrona mcp` without the SDK (#142, I142-S4): the registry listing needs none, serving says how to install it.

These tests never import the MCP SDK, so they run in every install; the binding itself is tested in
``tests/mcp`` where the extra is present.
"""
from __future__ import annotations

import ast
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest

from chrona.app import cli
from chrona.app.agent_tools import registry_document
from chrona.app.cli import main

REPO = next(parent for parent in Path(__file__).resolve().parents if (parent / "pyproject.toml").is_file())


def run_main(monkeypatch, capsys, *arguments: str) -> tuple[int, str, str]:
    monkeypatch.setattr(sys, "argv", ["chrona", "mcp", *arguments])
    code = 0
    try:
        main()
    except SystemExit as error:
        code = error.code if isinstance(error.code, int) else 0
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_list_tools_prints_the_registry_and_needs_no_sdk(monkeypatch, capsys):
    monkeypatch.setitem(sys.modules, "mcp", None)  # `import mcp` raises ImportError, as in a base install
    code, out, err = run_main(monkeypatch, capsys, "--list-tools")
    assert (code, err) == (0, "")
    assert json.loads(out) == registry_document()
    assert [tool["name"] for tool in json.loads(out)["tools"]] == [
        "validate_project", "schedule_project", "render_draft", "list_presets", "check_command", "apply_command"]


def test_list_tools_validates_an_explicit_workspace(monkeypatch, capsys, tmp_path):
    code, out, _ = run_main(monkeypatch, capsys, "--list-tools", "--workspace", str(tmp_path))
    assert code == 0 and json.loads(out)["toolSet"] == "chrona/agent-tools/v0.3"
    code, out, _ = run_main(monkeypatch, capsys, "--list-tools", "--workspace", str(tmp_path / "absent"))
    assert code == 2 and json.loads(out)["diagnostics"][0]["code"] == "E_INPUT_IO"
    code, out, _ = run_main(monkeypatch, capsys, "--list-tools", "--workspace", str(Path(tmp_path.anchor)))
    assert code == 2 and json.loads(out)["diagnostics"][0]["code"] == "E_MCP_WORKSPACE_TOO_BROAD"
    assert "--workspace" in json.loads(out)["diagnostics"][0]["message"]


def test_serving_without_the_sdk_says_how_to_install_it(monkeypatch, capsys):
    monkeypatch.setattr(cli, "_mcp_sdk_installed", lambda: False)
    code, out, err = run_main(monkeypatch, capsys)
    report = json.loads(out)
    assert (code, err) == (2, "") and report["status"] == "failed"
    (item,) = report["diagnostics"]
    assert (item["code"], item["component"]) == ("E_MCP_UNAVAILABLE", "mcp")
    assert "pip install 'chrona[mcp]'" in item["message"]


def test_a_directory_named_mcp_is_not_the_sdk(monkeypatch, tmp_path):
    # A project folder called `mcp` is a namespace package, so `import mcp` succeeds without the SDK.
    (tmp_path / "mcp").mkdir()
    for name in [name for name in sys.modules if name == "mcp" or name.startswith("mcp.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setattr(sys, "path", [str(tmp_path), *[item for item in sys.path if "site-packages" not in item]])
    assert cli._mcp_sdk_installed() is False


def test_the_sdk_check_is_false_when_the_package_is_blocked(monkeypatch):
    for name in [name for name in sys.modules if name == "mcp" or name.startswith("mcp.")]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.setitem(sys.modules, "mcp", None)
    assert cli._mcp_sdk_installed() is False


def test_serving_hands_the_workspace_to_the_binding(monkeypatch, capsys, tmp_path):
    served: list[object] = []
    binding = types.ModuleType("chrona.app.mcp_server")
    binding.serve = lambda workspace, *, allow_write=False: served.append((workspace, allow_write))
    monkeypatch.setitem(sys.modules, "chrona.app.mcp_server", binding)
    monkeypatch.setattr(cli, "_mcp_sdk_installed", lambda: True)
    assert run_main(monkeypatch, capsys, "--workspace", str(tmp_path)) == (0, "", "")
    assert run_main(monkeypatch, capsys) == (0, "", "")
    assert run_main(monkeypatch, capsys, "--allow-write", "--workspace", str(tmp_path)) == (0, "", "")
    assert served == [(str(tmp_path), False), (".", False), (str(tmp_path), True)]


def test_allow_write_is_a_flag_with_no_value_and_defaults_off(monkeypatch, capsys):
    served: list[object] = []
    binding = types.ModuleType("chrona.app.mcp_server")
    binding.serve = lambda workspace, *, allow_write=False: served.append(allow_write)
    monkeypatch.setitem(sys.modules, "chrona.app.mcp_server", binding)
    monkeypatch.setattr(cli, "_mcp_sdk_installed", lambda: True)
    assert run_main(monkeypatch, capsys, "--allow-write=yes")[0] == 2 and served == []
    assert run_main(monkeypatch, capsys, "--allow-write")[0] == 0 and served == [True]


def test_the_module_entry_point_lists_tools_without_the_sdk(tmp_path):
    done = subprocess.run([sys.executable, "-m", "chrona", "mcp", "--list-tools"], cwd=tmp_path, capture_output=True,
                          text=True, encoding="utf-8", check=False)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout) == registry_document()


@pytest.mark.parametrize("arguments", [["--bogus"], ["--workspace"], ["extra"]])
def test_a_bad_flag_is_a_command_syntax_error(monkeypatch, capsys, arguments):
    code, out, _ = run_main(monkeypatch, capsys, *arguments)
    assert code == 2 and json.loads(out)["diagnostics"][0]["code"] == "E_COMMAND_SYNTAX"


def test_the_sdk_is_imported_by_the_binding_alone():
    importers = []
    for path in sorted((REPO / "src" / "chrona").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = ([node.module] if isinstance(node, ast.ImportFrom) and node.module and not node.level
                     else [item.name for item in node.names] if isinstance(node, ast.Import) else [])
            if any(name.split(".")[0] == "mcp" for name in names):
                importers.append(path.relative_to(REPO).as_posix())
                break
    assert importers == ["src/chrona/app/mcp_server.py"]
