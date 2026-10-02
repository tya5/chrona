"""Layering of the agent tool core (#142): use cases only, and the MCP SDK in exactly one module."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools import check_import_direction as tool

REPO = Path(__file__).resolve().parents[3]


def _tree(tmp_path: Path, files: dict[str, str]) -> None:
    root = tmp_path / "src" / "chrona"
    for relative, text in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        (path.parent / "__init__.py").touch()
        path.write_text(text, encoding="utf-8")


def _run(tmp_path: Path, monkeypatch, capsys, files: dict[str, str]) -> tuple[int, str]:
    _tree(tmp_path, files)
    monkeypatch.setattr(tool, "SOURCE", tmp_path / "src")
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    return tool.main(), capsys.readouterr().out


PRODUCT = {"usecases/u.py": "X = 1\n", "resources/r.py": "R = 1\n", "core/store_address.py": "Y = 1\n", "core/validation.py": "Z = 1\n",
           "presentation/p.py": "P = 1\n", "scheduling/s.py": "S = 1\n", "operational/o.py": "O = 1\n",
           "storage/st.py": "T = 1\n", "app/cli.py": "C = 1\n", "app/agent_workspace.py": "W = 1\n"}


def test_the_real_tree_passes_and_has_the_agent_rules():
    assert tool.main() == 0
    assert "chrona.app.agent_" in tool.MODULE_RULES and "chrona.app.mcp_server" in tool.MODULE_RULES
    assert tool.SDK_MODULE == "chrona.app.mcp_server"


@pytest.mark.parametrize("target", [
    "chrona.presentation.p", "chrona.scheduling.s", "chrona.operational.o", "chrona.storage.st", "chrona.core.validation",
])
def test_a_tool_handler_importing_below_the_use_cases_is_flagged(tmp_path, monkeypatch, capsys, target):
    module = target.removeprefix("chrona.")
    code, out = _run(tmp_path, monkeypatch, capsys,
                     {**PRODUCT, "app/agent_tools.py": f"from chrona.{module} import *\n"})
    assert code == 1
    assert f"chrona.app.agent_tools must not import {target} (module rule)" in out


@pytest.mark.parametrize("statement", [
    "from chrona.usecases.u import X", "from chrona.core.store_address import Y", "from chrona.app.agent_workspace import W",
    "import chrona.usecases.u", "from chrona.resources import R", "from chrona.resources.r import R",
])
def test_use_cases_the_shared_path_guard_and_sibling_tool_modules_are_allowed(tmp_path, monkeypatch, capsys, statement):
    code, out = _run(tmp_path, monkeypatch, capsys, {**PRODUCT, "app/agent_tools.py": statement + "\n"})
    assert (code, out.splitlines()[-1].endswith("all inward")) == (0, True), out


@pytest.mark.parametrize("statement", ["from chrona.app.cli import C", "from chrona.core import validation"])
def test_a_tool_module_importing_the_cli_or_a_bare_core_package_is_flagged(tmp_path, monkeypatch, capsys, statement):
    code, out = _run(tmp_path, monkeypatch, capsys, {**PRODUCT, "app/agent_workspace.py": statement + "\n"})
    assert code == 1 and "(module rule)" in out


def test_the_binding_module_follows_the_same_rule(tmp_path, monkeypatch, capsys):
    code, out = _run(tmp_path, monkeypatch, capsys,
                     {**PRODUCT, "app/mcp_server.py": "from chrona.presentation.p import P\nimport mcp\n"})
    assert code == 1 and "chrona.app.mcp_server must not import chrona.presentation.p (module rule)" in out
    assert "only chrona.app.mcp_server may import the mcp SDK" not in out


def test_other_app_modules_keep_the_package_wide_allowance(tmp_path, monkeypatch, capsys):
    code, out = _run(tmp_path, monkeypatch, capsys,
                     {**PRODUCT, "app/other.py": "from chrona.presentation.p import P\nfrom chrona.app.cli import C\n"})
    assert code == 0, out


@pytest.mark.parametrize("statement", ["import mcp", "import mcp.server.stdio", "from mcp import types",
                                       "from mcp.server import Server", "import os, mcp"])
@pytest.mark.parametrize("path", ["app/agent_tools.py", "app/cli.py", "usecases/u.py", "presentation/p.py"])
def test_the_sdk_import_outside_the_binding_module_is_flagged(tmp_path, monkeypatch, capsys, statement, path):
    code, out = _run(tmp_path, monkeypatch, capsys, {**PRODUCT, path: statement + "\n"})
    assert code == 1 and "only chrona.app.mcp_server may import the mcp SDK" in out


@pytest.mark.parametrize("statement", ["import mcp", "from mcp.server import Server"])
def test_the_sdk_import_inside_the_binding_module_passes(tmp_path, monkeypatch, capsys, statement):
    code, out = _run(tmp_path, monkeypatch, capsys, {**PRODUCT, "app/mcp_server.py": statement + "\n"})
    assert code == 0, out


def test_a_similarly_named_module_is_not_the_sdk(tmp_path, monkeypatch, capsys):
    code, out = _run(tmp_path, monkeypatch, capsys,
                     {**PRODUCT, "app/agent_tools.py": "import mcpx\nimport yaml\nfrom mcpx import y\n"})
    assert code == 0, out


def test_the_real_tool_core_imports_only_use_cases_the_path_guard_and_the_validator_factory():
    seen: set[str] = set()
    import ast
    for name in ("agent_tools.py", "agent_workspace.py"):
        for node in ast.walk(ast.parse((REPO / "src" / "chrona" / "app" / name).read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("chrona"):
                seen.add(node.module)
            elif isinstance(node, ast.Import):
                seen.update(item.name for item in node.names if item.name.startswith("chrona"))
    assert {module for module in seen if not module.startswith("chrona.usecases.")} == {
        "chrona.app.agent_workspace", "chrona.core.store_address", "chrona.resources"}


OPERATIONAL = {**PRODUCT, "operational/store_commands.py": "Q = 1\n", "operational/command_engine.py": "E = 1\n"}


def test_the_tool_core_may_import_the_one_shared_store_command_module(tmp_path, monkeypatch, capsys):
    code, out = _run(tmp_path, monkeypatch, capsys,
                     {**OPERATIONAL, "app/agent_tools.py": "from chrona.operational.store_commands import Q\n"})
    assert (code, out.splitlines()[-1].endswith("all inward")) == (0, True), out


@pytest.mark.parametrize("statement", [
    "from chrona.operational.command_engine import E", "from chrona.operational import store_commands",
    "import chrona.operational.command_engine",
])
def test_no_other_operational_import_is_allowed_to_the_tool_core(tmp_path, monkeypatch, capsys, statement):
    code, out = _run(tmp_path, monkeypatch, capsys, {**OPERATIONAL, "app/agent_tools.py": statement + "\n"})
    assert code == 1 and "chrona.app.agent_tools must not import chrona.operational" in out


def test_the_binding_gets_no_operational_edge(tmp_path, monkeypatch, capsys):
    code, out = _run(tmp_path, monkeypatch, capsys,
                     {**OPERATIONAL, "app/mcp_server.py": "from chrona.operational.store_commands import Q\n"})
    assert code == 1 and "chrona.app.mcp_server must not import chrona.operational.store_commands" in out
