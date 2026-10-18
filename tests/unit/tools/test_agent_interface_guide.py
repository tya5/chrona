"""The user-facing MCP tool table is a checked projection of the live registry."""
from pathlib import Path

from chrona.app.agent_tools import registry_document


ROOT = Path(__file__).resolve().parents[3]


def test_guide_tool_table_matches_the_live_server_registry():
    guide = (ROOT / "docs/guides/agent-interface.md").read_text(encoding="utf-8")
    table = guide.split("<!-- chrona:agent-tool-table -->", 1)[1].split("<!-- /chrona:agent-tool-table -->", 1)[0].strip()
    rows = ["| Tool | Purpose | Writes |", "| --- | --- | --- |"]
    for tool in registry_document()["tools"]:
        writes = "no" if tool["annotations"]["readOnlyHint"] else "yes"
        rows.append(f"| `{tool['name']}` | {tool['title']} | {writes} |")
    assert table == "\n".join(rows)
    assert "no authoring command" not in guide and "no revert command" not in guide
    assert "`revertActualCommand`" in guide and "`apply_authoring_command`" in guide
    assert "authoringResult.resultRevision" in guide
