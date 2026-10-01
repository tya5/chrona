"""Doc-check handling of ```chrona fences (#148): excluded from command scanning, compiled as terse plans."""
from __future__ import annotations

from pathlib import Path

import pytest

from tools.check_documented_commands import DocumentedCommandError, TersePlan, check_plans, discover, discover_plans

ROOT = Path(__file__).resolve().parents[3]
GOOD = "project p\nchrona \"Chrona\" task 2d\nnext task 1d after chrona\n"


def _root(tmp_path: Path, content: str) -> Path:
    (tmp_path / "docs" / "guides").mkdir(parents=True, exist_ok=True)
    (tmp_path / "README.md").write_text(content, encoding="utf-8")
    return tmp_path


def _fence(text: str, info: str = "chrona") -> str:
    return f"```{info}\n{text}```\n"


def test_an_object_named_chrona_is_not_read_as_a_cli_command(tmp_path):
    root = _root(tmp_path, _fence(GOOD))
    assert discover(root) == ()
    (plan,) = discover_plans(root)
    assert plan.text == GOOD and plan.line == 2 and plan.path == Path("README.md")
    check_plans((plan,))


def test_other_fences_are_not_plans_and_still_scan_commands(tmp_path):
    root = _root(tmp_path, _fence("chrona render project.yaml\n", "sh") + _fence(GOOD, "chrona text"))
    assert [command.tokens[1] for command in discover(root)] == ["render"]
    assert len(discover_plans(root)) == 1


def test_a_plan_that_does_not_compile_fails_the_check_with_its_codes_and_position(tmp_path):
    root = _root(tmp_path, "intro\n\n" + _fence("project p\na tsak 1d\n"))
    with pytest.raises(DocumentedCommandError, match=r"E_DOCUMENTED_PLAN_REJECTED:README.md:4:E_TERSE_KIND_UNKNOWN"):
        check_plans(discover_plans(root))


def test_expect_error_marks_a_deliberately_wrong_example(tmp_path):
    marker = "<!-- chrona:doc-check expect-error: E_TERSE_KIND_UNKNOWN -->\n"
    root = _root(tmp_path, marker + _fence("project p\na tsak 1d\n"))
    assert discover(root) == ()
    (plan,) = discover_plans(root)
    assert plan.expect_error == "E_TERSE_KIND_UNKNOWN"
    check_plans((plan,))


def test_expect_error_fails_when_the_plan_compiles_or_fails_differently(tmp_path):
    marker = "<!-- chrona:doc-check expect-error: E_TERSE_KIND_UNKNOWN -->\n"
    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_PLAN_EXPECTED_ERROR:README.md:3:E_TERSE_KIND_UNKNOWN"):
        check_plans(discover_plans(_root(tmp_path, marker + _fence(GOOD))))
    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_PLAN_EXPECTED_ERROR"):
        check_plans(discover_plans(_root(tmp_path, marker + _fence("project p\na task 1d after zzz\n"))))


def test_skip_marker_leaves_a_plan_unchecked(tmp_path):
    root = _root(tmp_path, "<!-- chrona:doc-check skip: shows a fragment -->\n" + _fence("a tsak 1d\n"))
    assert discover(root) == ()
    (plan,) = discover_plans(root)
    assert plan.skip_reason == "shows a fragment"
    check_plans((plan,))


def test_a_marker_applies_only_to_the_next_fence(tmp_path):
    marker = "<!-- chrona:doc-check expect-error: E_TERSE_KIND_UNKNOWN -->\n"
    root = _root(tmp_path, marker + _fence("project p\na tsak 1d\n") + _fence("project p\nb task 1d\n"))
    first, second = discover_plans(root)
    assert first.expect_error and second.expect_error is None
    check_plans((first, second))


EXPECT_YAML = "<!-- chrona:doc-check expect-yaml: next -->\n"
SMALL = 'project p "P"\na "A" task 2026-10-01..2026-10-05\n'
SMALL_YAML = (
    "version: timeline/v0.7\nproject:\n  id: p\n  title: P\nobjects:\n  a:\n    type: task\n    title: A\n"
    "    schedule: {mode: fixed-span, start: '2026-10-01', end: '2026-10-05'}\n"
)


def test_expect_yaml_accepts_the_emitted_project_without_its_header_comment(tmp_path):
    root = _root(tmp_path, EXPECT_YAML + _fence(SMALL) + "\nwhich becomes\n\n" + _fence(SMALL_YAML, "yaml"))
    assert discover(root) == ()
    (plan,) = discover_plans(root)
    assert plan.expect_yaml and plan.yaml_text == SMALL_YAML
    check_plans((plan,))


def test_expect_yaml_fails_when_the_yaml_differs(tmp_path):
    wrong = SMALL_YAML.replace("2026-10-05", "2026-10-06")
    root = _root(tmp_path, EXPECT_YAML + _fence(SMALL) + _fence(wrong, "yaml"))
    with pytest.raises(DocumentedCommandError, match=r"E_DOCUMENTED_PLAN_YAML_MISMATCH:README.md:3:"):
        check_plans(discover_plans(root))


def test_expect_yaml_keeps_the_header_comment_out_of_the_comparison(tmp_path):
    root = _root(tmp_path, EXPECT_YAML + _fence(SMALL) + _fence("# a header the emitter wrote\n" + SMALL_YAML, "yaml"))
    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_PLAN_YAML_MISMATCH"):
        check_plans(discover_plans(root))


@pytest.mark.parametrize("tail", ["", _fence("echo hi\n", "sh") + _fence(SMALL_YAML, "yaml"), "text only\n"])
def test_expect_yaml_fails_when_the_next_fence_is_not_a_yaml_fence(tail, tmp_path):
    root = _root(tmp_path, EXPECT_YAML + _fence(SMALL) + tail)
    (plan,) = discover_plans(root)
    assert plan.expect_yaml and plan.yaml_text is None
    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_PLAN_YAML_MISSING:README.md:3"):
        check_plans((plan,))


def test_expect_yaml_fails_when_the_plan_does_not_compile(tmp_path):
    root = _root(tmp_path, EXPECT_YAML + _fence("project p\na tsak 1d\n") + _fence(SMALL_YAML, "yaml"))
    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_PLAN_REJECTED"):
        check_plans(discover_plans(root))


def test_the_expect_yaml_marker_applies_only_to_the_next_plan(tmp_path):
    root = _root(tmp_path, EXPECT_YAML + _fence(SMALL) + _fence(SMALL_YAML, "yaml") + _fence(GOOD))
    first, second = discover_plans(root)
    assert first.expect_yaml and not second.expect_yaml and second.yaml_text is None
    check_plans((first, second))


def test_two_markers_before_one_fence_are_still_rejected(tmp_path):
    root = _root(tmp_path, EXPECT_YAML + "<!-- chrona:doc-check expect-error: E_TERSE_KIND_UNKNOWN -->\n" + _fence(SMALL))
    with pytest.raises(DocumentedCommandError, match="E_DOCUMENTED_COMMAND_SKIP"):
        discover(root)


def test_the_live_documents_compile_and_the_card_is_among_them():
    plans = discover_plans(ROOT)
    assert any(plan.path == Path("docs/guides/terse-plan.md") for plan in plans)
    check_plans(plans)
    assert isinstance(plans[0], TersePlan)
