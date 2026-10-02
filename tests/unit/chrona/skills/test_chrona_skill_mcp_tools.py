"""The skill's MCP tool table says what the tool registry says (#142, I142-S5): one source of truth, pinned by test."""
from __future__ import annotations

import re

from chrona.app.agent_tools import tool_specs
from chrona.app.cli import _parser
from tests.support.skill_files import SKILL_DIR, skill_documents
from tools.check_documented_commands import surface

SKILL = SKILL_DIR / "SKILL.md"
ROW = re.compile(r"^\|\s*`(?P<tool>[a-z_]+)`\s*\|\s*`(?P<command>chrona [^`]+)`\s*\|", re.MULTILINE)
TOOL_LIKE = re.compile(r"`((?:validate|schedule|render|list|compare|apply|check|init|workspace)_[a-z_]+)`")
# The commands each tool is documented to equal (design D2.3): the table may not drift from them.
EQUIVALENT_COMMANDS = {
    "validate_project": "chrona validate", "schedule_project": "chrona schedule",
    "render_draft": "chrona render", "list_presets": "chrona preset list",
    "render_review": "chrona render-review", "compare_baseline": "chrona baseline-compare",
    "check_command": "chrona command-check", "apply_command": "chrona command-apply",
}


def test_the_table_lists_exactly_the_registered_tools_in_order():
    rows = [(match["tool"], match["command"]) for match in ROW.finditer(SKILL.read_text(encoding="utf-8"))]

    assert [tool for tool, _ in rows] == [spec.name for spec in tool_specs()]
    assert dict(rows) == EQUIVALENT_COMMANDS


def test_every_command_in_the_table_is_a_real_command_of_the_cli():
    real = {" ".join(path) for path in surface(_parser())}
    shown = [match["command"] for match in ROW.finditer(SKILL.read_text(encoding="utf-8"))]

    assert shown and all(command in real for command in shown), [command for command in shown if command not in real]


def test_every_tool_named_anywhere_in_the_skill_exists():
    registered = {spec.name for spec in tool_specs()}
    named: set[str] = set()
    for document in skill_documents():
        named.update(TOOL_LIKE.findall(document.read_text(encoding="utf-8")))

    assert named and named <= registered, sorted(named - registered)


def test_the_skill_prefers_the_tools_only_when_connected_and_states_the_status_rule():
    text = SKILL.read_text(encoding="utf-8")

    assert "## If the chrona MCP server is connected" in text
    assert "Otherwise use the commands" in text
    assert "`status`" in text and "rejected" in text
    assert "Structure and dependency cycles, no dates" in text


def test_the_table_notes_agree_with_the_tool_descriptions():
    descriptions = {spec.name: spec.description for spec in tool_specs()}

    assert "A dependency cycle is rejected here" in descriptions["validate_project"]
    assert "computes no dates" in descriptions["validate_project"]
    assert "not by validate_project (a dependency cycle is rejected by both)" in descriptions["schedule_project"]
    assert "writes no file" in descriptions["render_draft"] and "inline 'svg'" in descriptions["render_draft"]


def test_the_skill_teaches_the_pinned_evidence_path_and_agrees_with_the_store_tools():
    text = SKILL.read_text(encoding="utf-8")
    descriptions = {spec.name: spec.description for spec in tool_specs()}
    section = text.split("## Pinned evidence from a Store", 1)[1].split("\n## ", 1)[0]

    for needle in ("Render Context", "Store configuration", "`.chrona/store.yaml`", "reference file", "`render_review`",
                   "`compare_baseline`", "only read", "outside the workspace", "pinned identity", "`integrity`"):
        assert needle in section, needle
    assert "only when the user asks" in text.split("## Pinned evidence from a Store", 1)[1].split("\n", 1)[0]
    assert "do not use them unless the user asks for pinned evidence" in text
    for name in ("render_review", "compare_baseline"):
        assert "read-only" in descriptions[name] and "no argument lowers" in descriptions[name]
    assert "fixes its own format and viewport" in descriptions["render_review"]
