"""Every code an MCP tool emits is explained by an MCP resource (#1892 row 4)."""
from __future__ import annotations

from pathlib import Path
import re

from chrona.app.agent_diagnostics import catalog_markdown, diagnostic_catalog
from chrona.resources import skill_resource

_SRC = Path(__file__).resolve().parents[4] / "src" / "chrona"
_CODE = re.compile(r"\b[EW]_[A-Z][A-Z0-9_]{2,}\b")
# Source files whose literal codes reach an MCP tool result: the tool layer, the guided authoring and Store command
# transactions and their use cases.
_EMITTERS = (
    "app/agent_tools.py", "app/agent_workspace.py", "app/mcp_server.py",
    "operational/authoring_commands.py", "operational/command_engine.py", "operational/references.py",
    "operational/store_commands.py", "operational/baselines.py", "operational/workspace_initialization.py",
    "usecases/authoring_commands.py", "usecases/authoring_materialization.py", "usecases/authoring_workspace.py",
    "usecases/input_violations.py", "usecases/resource_checks.py", "usecases/failure_report.py",
    "usecases/project_commands.py",
)


def _codes(path: Path) -> set[str]:
    return set(_CODE.findall(path.read_text(encoding="utf-8")))


def _skill_table_codes() -> set[str]:
    return _codes_in(skill_resource().joinpath("references", "diagnostics.md").read_text(encoding="utf-8"))


def _codes_in(text: str) -> set[str]:
    return set(_CODE.findall(text))


def test_every_code_an_mcp_emitter_names_has_an_entry():
    explained = set(diagnostic_catalog()) | _skill_table_codes()
    missing = {}
    for relative in _EMITTERS:
        for code in sorted(_codes(_SRC / relative) - explained):
            missing.setdefault(code, []).append(relative)
    assert not missing, f"codes MCP tools can emit without a meaning and remedy: {missing}"


def test_every_mcp_prefixed_code_in_the_package_has_an_entry():
    emitted = {code for path in _SRC.rglob("*.py") for code in _codes(path) if code.startswith("E_MCP_")}
    assert emitted <= set(diagnostic_catalog())


def test_no_catalog_entry_is_stale_and_each_row_is_complete():
    in_source = {code for path in _SRC.rglob("*.py") if path.name != "agent_diagnostics.py" for code in _codes(path)}
    assert set(diagnostic_catalog()) <= in_source
    for code, row in diagnostic_catalog().items():
        assert all(isinstance(cell, str) and cell.strip() for cell in row), code


def test_markdown_lists_each_entry_once():
    text = catalog_markdown()
    for code in diagnostic_catalog():
        assert text.count(f"| `{code}` |") == 1
